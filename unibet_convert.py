import re
from datetime import datetime
import clipboard
import tkinter as tk
from tkinter import ttk, messagebox
import os, json, sys, subprocess

VERSION_STR = "24.7.1.16"

# ----- Bas-katalog: där skriptet/exen ligger -----
if getattr(sys, 'frozen', False):  # t.ex. PyInstaller
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ----- Konfig & historik i samma mapp som programmet -----
CONFIG_PATH = os.path.join(BASE_DIR, "unibet_hand_converter_config.json")
HISTORY_DIR = os.path.join(BASE_DIR, "Unibet_Converter_History")

# ----- Svenska -> Engelsk kortfärg -----
# r = ruter(D), k = klöver(C), s = spader(S), h = hjärter(H)
SUIT_MAP = {"r": "D", "k": "C", "s": "S", "h": "H"}

# ===================== Preferenser =====================
def load_prefs() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_prefs(d: dict):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def current_history_file() -> str:
    """
    Returnera dagens historikfil som 'converted_YYYY-MM-DD.txt'.
    Migrerar ev. gammal fil utan ändelse -> .txt om den finns.
    """
    os.makedirs(HISTORY_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    new_path = os.path.join(HISTORY_DIR, f"converted_{today}.txt")
    old_path = os.path.join(HISTORY_DIR, f"converted_{today}")  # gammalt namn utan .txt
    try:
        if os.path.exists(old_path) and not os.path.exists(new_path):
            os.rename(old_path, new_path)
    except Exception:
        pass
    return new_path

# ===================== Hjälpfunktioner =====================
def _rank_norm(tok: str) -> str:
    tok = tok.upper()
    return "10" if tok in ("10", "T") else tok

def _card_sv_to_target(token: str) -> str:
    """
    Konvertera t.ex. '7h' -> 'H7', 'Jk' -> 'CJ', 'Kr' -> 'DK'.
    Tar höjd för blandade format (t.ex. '10k', 'T k').
    """
    token = token.strip().lower()
    m = re.match(r"^([0-9]{1,2}|[tjqka])([rksh])$", token)
    if not m:
        return token.upper()
    rank, suit = m.groups()
    suit_en = SUIT_MAP.get(suit, suit.upper())
    rank_en = _rank_norm(rank)
    return f"{suit_en}{rank_en}"

def _parse_cards_block(block: str) -> str:
    """
    Tar en svensk bräda i form '[7r 3k Kr]' och ger '[D7 C3 DK]'.
    """
    within = re.search(r"\[(.*?)\]", block)
    if not within:
        return "[]"
    tokens = within.group(1).split()
    conv = [_card_sv_to_target(tok) for tok in tokens]
    return "[" + " ".join(conv) + "]"

def _money(s: str) -> str:
    """Säker formatering av pengar med två decimaler."""
    return f"{float(s):.2f}"

# ===================== Konverterare =====================
def convert(raw: str, version: str = VERSION_STR, preferred_hero: str = "JullyEggy") -> str:
    # --- Header ---
    m_head = re.search(
        r"Spel\s+#(?P<id>\d+):\s*Bord\s*(?P<table_name>.+?)\s*-\s*(?P<sb>\d+\.?\d*)/(?P<bb>\d+\.?\d*)\s*-\s*No Limit Hold'Em\s*-\s*(?P<time>\d{2}:\d{2}:\d{2})\s*(?P<date>\d{4}/\d{2}/\d{2})",
        raw, flags=re.I
    )
    if not m_head:
        raise ValueError("Kunde inte tolka handens header.")
    hand_id = m_head.group("id")
    table_name = m_head.group("table_name").strip()
    sb = _money(m_head.group("sb"))
    bb = _money(m_head.group("bb"))
    time_str = m_head.group("time")
    date_str = m_head.group("date").replace("/", "-")
    header_line = f"GAME #{hand_id} Version:{version} Uncalled:Y Texas Hold'em NL €{sb}/€{bb} {date_str} {time_str}/GMT"

    # --- Seats / Stacks ---
    seats = re.findall(r"Platser\s+(\d+):\s*([^\(]+)\(€([\d\.]+)\)", raw)
    table_size = len(seats) if len(seats) > 0 else 6

    # Button (dealern)
    m_btn = re.search(r"([^\s]+)\s+har knappen", raw, flags=re.I)
    button_name = m_btn.group(1) if m_btn else None
    button_seat = None
    for seat_no, name, stack in seats:
        if button_name and name.strip() == button_name:
            button_seat = int(seat_no)
            break

    # --- Blinds ---
    m_sb = re.search(r"([^\s]+)\s+lägger lilla mörken\s+€([\d\.]+)", raw, flags=re.I)
    m_bb = re.search(r"([^\s]+)\s+lägger stora mörken\s+€([\d\.]+)", raw, flags=re.I)
    sb_name, sb_amt = (m_sb.group(1), _money(m_sb.group(2))) if m_sb else (None, None)
    bb_name, bb_amt = (m_bb.group(1), _money(m_bb.group(2))) if m_bb else (None, None)

    # --- Hole cards (alla "Delat ut till") ---
    dealt = re.findall(r"Delat ut till\s+([^\s]+)\s+\[([^\]]+)\]", raw, flags=re.I)

    # --- Gata-för-gata-aktion ---
    def parse_street_actions(street_block: str, preflop: bool = False):
        out = []
        current_to = float(bb) if preflop and bb else 0.0  # preflop utgångspunkt

        for line in street_block.strip().splitlines():
            line = line.strip()
            if not line:
                continue

            # Fold
            if re.search(r"lägger sig", line, flags=re.I):
                name = line.split()[0].rstrip(":")
                out.append(f"{name}: Fold")
                continue

            # Check
            if re.search(r"passar", line, flags=re.I):
                name = line.split()[0].rstrip(":")
                out.append(f"{name}: Check")
                continue

            # Bet
            m_bet = re.search(r"([^\s:]+).*satsar\s+€([\d\.]+)", line, flags=re.I)
            if m_bet:
                name = m_bet.group(1)
                amt = float(m_bet.group(2))
                current_to = amt  # ny bet-nivå
                out.append(f"{name}: Bet €{amt:.2f}")
                continue

            # Call (beloppet är vad spelaren lägger in nu)
            m_call = re.search(r"([^\s:]+).*synar\s+€([\d\.]+)", line, flags=re.I)
            if m_call:
                name = m_call.group(1)
                amt = float(m_call.group(2))
                out.append(f"{name}: Call €{amt:.2f}")
                continue

            # Raise all-in: "höjer €X med €Y, och är all-in" eller "höjer till €Y ... all-in"
            m_allin_raise = re.search(
                r"([^\s:]+).*höjer(?:\s+till)?\s+€([\d\.]+)(?:\s+med\s+€([\d\.]+))?.*all-?in",
                line, flags=re.I
            )
            if m_allin_raise:
                name = m_allin_raise.group(1)
                first_amt = m_allin_raise.group(2)
                with_amt = m_allin_raise.group(3)
                new_to = float(with_amt) if with_amt else float(first_amt)
                current_to = new_to
                out.append(f"{name}: Raise to €{new_to:.2f} (all-in)")
                continue

            # Vanlig raise: "höjer €X med €Y" (Y = nytt 'to'), eller "höjer till €Y"
            m_raise = re.search(
                r"([^\s:]+).*höjer(?:\s+till)?\s+€([\d\.]+)(?:\s+med\s+€([\d\.]+))?",
                line, flags=re.I
            )
            if m_raise:
                name = m_raise.group(1)
                first_amt = m_raise.group(2)   # vad spelaren lägger in nu, om "med" följer
                with_amt = m_raise.group(3)    # nytt 'to'-belopp när "med" finns
                new_to = float(with_amt) if with_amt else float(first_amt)
                current_to = new_to
                out.append(f"{name}: Raise to €{new_to:.2f}")
                continue

            # All-in bet (utan explicit "raise")
            m_allin_bet = re.search(r"([^\s:]+).*satsar\s+€([\d\.]+).*all-?in", line, flags=re.I)
            if m_allin_bet:
                name = m_allin_bet.group(1)
                amt = float(m_allin_bet.group(2))
                current_to = amt
                out.append(f"{name}: Bet €{amt:.2f}")
                continue

            # Om inget matchar, ignorera
        return out

    # Plocka gat-block
    pre_block = re.search(r"\*\*\*\s*Innan flop\s*\*\*\*(.*?)(?=\*\*\*|$)", raw, flags=re.I|re.S)
    flop_line = re.search(r"\*\*\*\s*Flop\s*\*\*\*\s*(\[[^\]]+\])", raw, flags=re.I)
    flop_block = re.search(r"\*\*\*\s*Flop\s*\*\*\*.*?\]\s*(.*?)(?=\*\*\*|$)", raw, flags=re.I|re.S)
    turn_line = re.search(r"\*\*\*\s*Turn\s*\*\*\*\s*\[[^\]]+\]\s*(\[[^\]]+\])", raw, flags=re.I)
    turn_block = re.search(r"\*\*\*\s*Turn\s*\*\*\*.*?\]\s*\[[^\]]+\]\s*(.*?)(?=\*\*\*|$)", raw, flags=re.I|re.S)
    river_line = re.search(r"\*\*\*\s*River\s*\*\*\*\s*\[[^\]]+\]\s*\[[^\]]+\]\s*(\[[^\]]+\])", raw, flags=re.I)
    river_block = re.search(r"\*\*\*\s*River\s*\*\*\*.*?\]\s*\[[^\]]+\]\s*(.*?)(?=\*\*\*|$)", raw, flags=re.I|re.S)

    # --- Summary info ---
    m_pot_rake = re.search(r"Totalpot\s+€([\d\.]+)\s+Avgift\s+€([\d\.]+)", raw, flags=re.I)
    total_pot = _money(m_pot_rake.group(1)) if m_pot_rake else None
    rake = _money(m_pot_rake.group(2)) if m_pot_rake else None

    # Showdown / winner
    shows = re.findall(r"([^\s:]+)\s+visar\s+\[([^\]]+)\]\s*,?\s*([^\n\r]*)", raw, flags=re.I)
    m_wins = re.search(r"([^\s:]+)\s+vinner\s+€([\d\.]+)", raw, flags=re.I)
    winner_name = m_wins.group(1) if m_wins else None
    winner_amt = _money(m_wins.group(2)) if m_wins else None

    # --- Bygg output ---
    out = []
    out.append(header_line)
    out.append(f"Table Size {table_size}")
    out.append(f"Table {table_name}, {hand_id}")

    # Seat-rader (lägg DEALER på button-seat)
    for seat_no, name, stack in seats:
        tag = "  DEALER" if (button_seat is not None and int(seat_no) == button_seat) else ""
        out.append(f"Seat {int(seat_no)}: {name.strip()} (€{_money(stack)} in chips){(' ' + tag).rstrip()}")

    # Blinds
    if sb_name and sb_amt:
        out.append(f"{sb_name}: Post SB €{sb_amt}")
    if bb_name and bb_amt:
        out.append(f"{bb_name}: Post BB €{bb_amt}")

    # -------- HERO-logik --------
    out.append("*** HOLE CARDS ***")
    hero_name = None
    hero_cards = None
    if dealt:
        # 1) Försök hitta preferred_hero
        for name, cards in dealt:
            if preferred_hero and name.strip().lower() == preferred_hero.strip().lower():
                hero_name = name
                hero_cards = cards
                break
        # 2) Fallback: första
        if hero_name is None:
            hero_name, hero_cards = dealt[0]

    if hero_name and hero_cards:
        cards_tok = hero_cards.strip().split()
        conv = [_card_sv_to_target(t) for t in cards_tok]
        out.append(f"Dealt to {hero_name} [{' '.join(conv)}]")

    # Preflop actions
    if pre_block:
        out.extend(parse_street_actions(pre_block.group(1), preflop=True))

    # FLOP
    if flop_line:
        out.append(f"*** FLOP *** {_parse_cards_block(flop_line.group(1))}")
        if flop_block:
            out.extend(parse_street_actions(flop_block.group(1), preflop=False))

    # TURN
    if turn_line:
        out.append(f"*** TURN *** {_parse_cards_block(turn_line.group(1))}")
        if turn_block:
            out.extend(parse_street_actions(turn_block.group(1), preflop=False))

    # RIVER
    if river_line:
        out.append(f"*** RIVER *** {_parse_cards_block(river_line.group(1))}")
        if river_block:
            out.extend(parse_street_actions(river_block.group(1), preflop=False))

    # SUMMARY
    out.append("*** SUMMARY ***")
    if total_pot and rake:
        out.append(f"Total pot €{total_pot} Rake €{rake}")

    # Showdown lines
    handdesc_map = {
        "kåk": "Full House",
        "färg": "Flush",
        "stege": "Straight",
        "triss": "Three of a Kind",
        "två par": "Two Pair",
        "par": "One Pair",
        "fyrtal": "Four of a Kind"
    }
    for name, cards, sv_desc in shows:
        card_tokens = cards.strip().split()
        conv_cards = " ".join(_card_sv_to_target(t) for t in card_tokens)
        desc_en = ""
        if sv_desc:
            sv_l = sv_desc.strip().lower()
            for k_sv, k_en in handdesc_map.items():
                if k_sv in sv_l:
                    desc_en = k_en
                    break
        if desc_en:
            out.append(f"{name}: Shows [{conv_cards}] {desc_en}")
        else:
            out.append(f"{name}: Shows [{conv_cards}]")

    if winner_name and winner_amt:
        out.append(f"{winner_name}: wins €{winner_amt}")

    return "\n".join(out)

# ===================== GUI =====================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Unibet Hand Converter")
        self.geometry("880x660")

        # Ladda preferenser
        prefs = load_prefs()
        default_nick = prefs.get("nickname", "JullyEggy")

        # Nickname
        frm_top = ttk.Frame(self, padding=10)
        frm_top.pack(fill="x")
        ttk.Label(frm_top, text="Ditt nickname (Hero):").pack(side="left")
        self.nick_var = tk.StringVar(value=default_nick)
        self.nick_entry = ttk.Entry(frm_top, textvariable=self.nick_var, width=32)
        self.nick_entry.pack(side="left", padx=8)

        # Knappar
        frm_btn = ttk.Frame(self, padding=(10, 0))
        frm_btn.pack(fill="x")
        self.auto_copy_var = tk.BooleanVar(value=True)
        self.log_history_var = tk.BooleanVar(value=True)
        ttk.Button(frm_btn, text="Konvertera från urklipp", command=self.on_convert).pack(side="left")
        ttk.Button(frm_btn, text="Kopiera texten", command=self.copy_output).pack(side="left", padx=8)
        ttk.Checkbutton(frm_btn, text="Kopiera automatiskt", variable=self.auto_copy_var).pack(side="left", padx=8)
        ttk.Checkbutton(frm_btn, text="Spara till dagsfil", variable=self.log_history_var).pack(side="left", padx=8)
        ttk.Button(frm_btn, text="Öppna dagens fil", command=self.open_today_file).pack(side="left", padx=8)
        ttk.Button(frm_btn, text="Öppna historikmapp", command=self.open_history_folder).pack(side="left", padx=8)

        # Output
        frm_out = ttk.Frame(self, padding=10)
        frm_out.pack(fill="both", expand=True)
        ttk.Label(frm_out, text="Konverterad hand:").pack(anchor="w")
        self.txt = tk.Text(frm_out, wrap="none", height=24)
        self.txt.pack(fill="both", expand=True)
        yscroll = ttk.Scrollbar(self.txt, orient="vertical", command=self.txt.yview)
        self.txt.configure(yscrollcommand=yscroll.set)
        yscroll.pack(side="right", fill="y")

        # Status
        today_file = current_history_file()
        self.status_var = tk.StringVar(value=f"Klar. Dagens fil: {today_file}")
        self.status = ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w")
        self.status.pack(fill="x")

        # Spara prefs vid stängning
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_convert(self):
        try:
            raw = clipboard.paste()
            if not raw or not raw.strip():
                messagebox.showwarning("Tomt urklipp", "Urklippet är tomt eller saknas.")
                self.status_var.set("Urklippet var tomt.")
                return
            preferred = self.nick_var.get().strip() or "JullyEggy"
            result = convert(raw, version=VERSION_STR, preferred_hero=preferred)
            self.txt.delete("1.0", "end")
            self.txt.insert("1.0", result)

            if self.auto_copy_var.get():
                clipboard.copy(result)

            if self.log_history_var.get():
                self.append_to_today_file(result)

            self.status_var.set(
                f"Konverterat{' och kopierat' if self.auto_copy_var.get() else ''}. "
                f"Sparat i: {current_history_file()}"
            )
            self.persist_prefs()
        except ValueError as ve:
            messagebox.showerror("Konverteringsfel", str(ve))
            self.status_var.set("Fel vid konvertering.")
        except Exception as e:
            messagebox.showerror("Okänt fel", f"Något gick fel:\n{e}")
            self.status_var.set("Okänt fel.")

    def append_to_today_file(self, text: str):
        try:
            path = current_history_file()
            os.makedirs(HISTORY_DIR, exist_ok=True)
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"--- Converted {stamp} ---\n")
                f.write(text)
                f.write("\n\n")
        except Exception as e:
            messagebox.showwarning("Kunde inte skriva historik",
                                   f"Kunde inte skriva till:\n{current_history_file()}\n\n{e}")

    def copy_output(self):
        text = self.txt.get("1.0", "end").strip()
        if not text:
            self.status_var.set("Inget att kopiera.")
            return
        clipboard.copy(text)
        self.status_var.set("Kopierat till urklipp.")

    def open_today_file(self):
        try:
            path = current_history_file()
            os.makedirs(HISTORY_DIR, exist_ok=True)
            # Skapa om saknas så att OS kan öppna den
            if not os.path.exists(path):
                with open(path, "a", encoding="utf-8"):
                    pass
            if os.name == "nt":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showwarning("Kunde inte öppna fil", f"{e}")

    def open_history_folder(self):
        try:
            os.makedirs(HISTORY_DIR, exist_ok=True)
            if os.name == "nt":
                os.startfile(HISTORY_DIR)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", HISTORY_DIR])
            else:
                subprocess.Popen(["xdg-open", HISTORY_DIR])
        except Exception as e:
            messagebox.showwarning("Kunde inte öppna mapp", f"{e}")

    def persist_prefs(self):
        nick = (self.nick_var.get() or "JullyEggy").strip()
        save_prefs({"nickname": nick})

    def on_close(self):
        self.persist_prefs()
        self.destroy()

# ===================== Main =====================
if __name__ == "__main__":
    # Se till att historikmappen finns (och ev. migrera dagens filnamn)
    os.makedirs(HISTORY_DIR, exist_ok=True)
    _ = current_history_file()
    app = App()
    app.mainloop()
