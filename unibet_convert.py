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

# ----- Suit map: stöd för både gamla svenska (r/k/s/h) och nya engelska (d/c/s/h) -----
# r/d = diamond, k/c = club, s = spade, h = heart
SUIT_MAP = {
    "r": "D", "d": "D",
    "k": "C", "c": "C",
    "s": "S",
    "h": "H",
}

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

def _money(s: str) -> str:
    """
    Robust money parser:
    - klarar '33.61', '33,61', '33.61:', '€33.61,' etc.
    - tar första hittade talet och formaterar till 2 decimaler
    """
    s = str(s)
    m = re.search(r"(\d+(?:[.,]\d+)?)", s)
    if not m:
        raise ValueError(f"Could not parse money from: {s!r}")
    val = m.group(1).replace(",", ".")
    return f"{float(val):.2f}"


def _card_to_target(token: str) -> str:
    """
    Konvertera korttoken till formatet "SUIT+RANK", t.ex:
      'Kh' -> 'HK'
      'Jc' -> 'CJ'
      '10d'/'Td' -> 'D10'
    Stöd för både svenska suit-bokstäver (r/k/s/h) och engelska (d/c/s/h).
    """
    token = token.strip().lower()
    # tillåt 10 eller t, och suit i [rdcksh]
    m = re.match(r"^([0-9]{1,2}|[tjqka])([rdcksh])$", token)
    if not m:
        return token.upper()
    rank, suit = m.groups()
    suit_en = SUIT_MAP.get(suit, suit.upper())
    rank_en = _rank_norm(rank)
    return f"{suit_en}{rank_en}"

def _parse_cards_block(block: str) -> str:
    """
    Tar en bräda i form '[7s 8c Kc]' och ger '[S7 C8 CK]'.
    """
    within = re.search(r"\[(.*?)\]", block)
    if not within:
        return "[]"
    tokens = within.group(1).split()
    conv = [_card_to_target(tok) for tok in tokens]
    return "[" + " ".join(conv) + "]"

# ===================== Konverterare =====================
def convert(raw: str, version: str = VERSION_STR, preferred_hero: str = "JullyEggy") -> str:
    raw = raw.strip()

    # --- Header (ENG) ---
    m_head = re.search(
        r"Game\s+#(?P<id>\d+):\s*Table\s*(?P<table_name>.+?)\s*-\s*"
        r"(?P<sb>\d+[.,]?\d*)/(?P<bb>\d+[.,]?\d*)\s*-\s*"
        r"No Limit Hold'?Em\s*-\s*"
        r"(?P<time>\d{2}:\d{2}:\d{2})\s+"
        r"(?P<date>\d{4}/\d{2}/\d{2})",
        raw, flags=re.I
    )
    if not m_head:
        raise ValueError("Kunde inte tolka handens header (Unibet verkar vara i nytt/engelskt format).")

    hand_id = m_head.group("id")
    table_name = m_head.group("table_name").strip()
    sb = _money(m_head.group("sb"))
    bb = _money(m_head.group("bb"))
    time_str = m_head.group("time")
    date_str = m_head.group("date").replace("/", "-")

    header_line = f"GAME #{hand_id} Version:{version} Uncalled:Y Texas Hold'em NL €{sb}/€{bb} {date_str} {time_str}/GMT"

    # --- Seats / Stacks (ENG) ---
    seats = re.findall(r"Seat\s+(\d+):\s*([^\(]+)\(€([\d\.,]+)\)", raw, flags=re.I)
    table_size = len(seats) if seats else 6

    # Button (dealern)
    m_btn = re.search(r"([^\s]+)\s+has the button", raw, flags=re.I)
    button_name = m_btn.group(1) if m_btn else None
    button_seat = None
    for seat_no, name, stack in seats:
        if button_name and name.strip() == button_name:
            button_seat = int(seat_no)
            break

    # --- Blinds (ENG) ---
    m_sb = re.search(r"([^\s]+)\s+posts small blind\s+€([\d\.,]+)", raw, flags=re.I)
    m_bb = re.search(r"([^\s]+)\s+posts big blind\s+€([\d\.,]+)", raw, flags=re.I)
    sb_name, sb_amt = (m_sb.group(1), _money(m_sb.group(2))) if m_sb else (None, None)
    bb_name, bb_amt = (m_bb.group(1), _money(m_bb.group(2))) if m_bb else (None, None)

    # --- Hole cards (ENG) ---
    dealt = re.findall(r"Dealt to\s+([^\s]+)\s+\[([^\]]+)\]", raw, flags=re.I)

    # --- Gat-block extractor (tolerant för Unibets ordning) ---
    def block_between(street_name: str) -> str | None:
        # Ex: "*** Preflop *** ... (till nästa *** eller slut)"
        m = re.search(rf"\*\*\*\s*{re.escape(street_name)}\s*\*\*\*(.*?)(?=\*\*\*|$)", raw, flags=re.I | re.S)
        return m.group(1) if m else None

    pre_text = block_between("Preflop")
    flop_text = block_between("Flop")
    turn_text = block_between("Turn")
    river_text = block_between("River")

    # --- Board lines ---
    flop_line = re.search(r"\*\*\*\s*Flop\s*\*\*\*\s*(\[[^\]]+\])", raw, flags=re.I)
    turn_line = re.search(r"\*\*\*\s*Turn\s*\*\*\*\s*\[[^\]]+\]\s*(\[[^\]]+\])", raw, flags=re.I)
    river_line = re.search(r"\*\*\*\s*River\s*\*\*\*\s*\[[^\]]+\]\s*\[[^\]]+\]\s*(\[[^\]]+\])", raw, flags=re.I)

    # --- Actions parser (ENG) ---
    def parse_street_actions(street_block: str):
        out = []
        if not street_block:
            return out

        for line in street_block.strip().splitlines():
            line = line.strip()
            if not line:
                continue

            # Stoppa om Unibet skriver extra section headers i blocket
            if line.startswith("***"):
                continue

            # Uncalled bet returned
            m_uncalled = re.search(r"Uncalled bet returned to\s+([^\s:]+):\s*€([\d\.,]+)", line, flags=re.I)
            if m_uncalled:
                name = m_uncalled.group(1)
                amt = _money(m_uncalled.group(2))
                out.append(f"Uncalled bet (€{amt}) returned to {name}")
                continue

            # Fold
            m_fold = re.search(r"^([^\s:]+)\s+folds\b", line, flags=re.I)
            if m_fold:
                out.append(f"{m_fold.group(1)}: Fold")
                continue

            # Check
            m_check = re.search(r"^([^\s:]+)\s+checks\b", line, flags=re.I)
            if m_check:
                out.append(f"{m_check.group(1)}: Check")
                continue

            # Call
            m_call = re.search(r"^([^\s:]+)\s+calls\s+€([\d\.,]+)", line, flags=re.I)
            if m_call:
                name = m_call.group(1)
                amt = _money(m_call.group(2))
                out.append(f"{name}: Call €{amt}")
                continue

            # Bet
            m_bet = re.search(r"^([^\s:]+)\s+bets\s+€([\d\.,]+)", line, flags=re.I)
            if m_bet:
                name = m_bet.group(1)
                amt = _money(m_bet.group(2))
                out.append(f"{name}: Bet €{amt}")
                continue

            # Raise (Unibet: "raises €X to €Y" och ibland ", and is all-in")
            m_raise = re.search(
                r"^([^\s:]+)\s+raises\s+€([\d\.,]+)\s+to\s+€([\d\.,]+)(.*)$",
                line, flags=re.I
            )
            if m_raise:
                name = m_raise.group(1)
                to_amt = _money(m_raise.group(3))
                tail = (m_raise.group(4) or "").lower()
                if "all-in" in tail or "all in" in tail:
                    out.append(f"{name}: Raise to €{to_amt} (all-in)")
                else:
                    out.append(f"{name}: Raise to €{to_amt}")
                continue

            # Some HH have "raises to €Y" (without the first amount)
            m_raise2 = re.search(r"^([^\s:]+)\s+raises\s+to\s+€([\d\.,]+)(.*)$", line, flags=re.I)
            if m_raise2:
                name = m_raise2.group(1)
                to_amt = _money(m_raise2.group(2))
                tail = (m_raise2.group(3) or "").lower()
                if "all-in" in tail or "all in" in tail:
                    out.append(f"{name}: Raise to €{to_amt} (all-in)")
                else:
                    out.append(f"{name}: Raise to €{to_amt}")
                continue

            # Ignore everything else (t.ex. "Dealt in ...")
        return out

    # --- Summary info ---
    m_pot_rake = re.search(r"Total pot\s+€([\d\.,]+)\s+Rake\s+€([\d\.,]+)", raw, flags=re.I)
    total_pot = _money(m_pot_rake.group(1)) if m_pot_rake else None
    rake = _money(m_pot_rake.group(2)) if m_pot_rake else None

    # Showdown / winner
    # Ex: "CanSom1Bluff shows [Jc Jd], Two pairs, Jacks up"
    shows = re.findall(r"^([^\s:]+)\s+shows\s+\[([^\]]+)\](?:,\s*(.*))?$", raw, flags=re.I | re.M)
    m_wins = re.search(r"^([^\s:]+)\s+wins\s+€([\d\.,]+)", raw, flags=re.I | re.M)
    winner_name = m_wins.group(1) if m_wins else None
    winner_amt = _money(m_wins.group(2)) if m_wins else None

    # Normalisera showdown-handtyp (om texten innehåller kända kategorier)
    handtype_keywords = [
        ("full house", "Full House"),
        ("four of a kind", "Four of a Kind"),
        ("flush", "Flush"),
        ("straight", "Straight"),
        ("three of a kind", "Three of a Kind"),
        ("two pair", "Two Pair"),
        ("two pairs", "Two Pair"),
        ("one pair", "One Pair"),
        ("pair", "One Pair"),
        ("high card", "High Card"),
    ]

    # -------- HERO-logik --------
    hero_name = None
    hero_cards = None
    if dealt:
        # 1) Försök hitta preferred_hero
        for name, cards in dealt:
            if preferred_hero and name.strip().lower() == preferred_hero.strip().lower():
                hero_name = name
                hero_cards = cards
                break
        # 2) Fallback: första "Dealt to"
        if hero_name is None:
            hero_name, hero_cards = dealt[0]

    # --- Bygg output ---
    out = []
    out.append(header_line)
    out.append(f"Table Size {table_size}")
    out.append(f"Table {table_name}, {hand_id}")

    # Seats (lägg DEALER på button-seat)
    for seat_no, name, stack in seats:
        is_dealer = (button_seat is not None and int(seat_no) == button_seat)
        tag = "  DEALER" if is_dealer else ""
        out.append(f"Seat {int(seat_no)}: {name.strip()} (€{_money(stack)} in chips){tag}")

    # Blinds
    if sb_name and sb_amt:
        out.append(f"{sb_name}: Post SB €{sb_amt}")
    if bb_name and bb_amt:
        out.append(f"{bb_name}: Post BB €{bb_amt}")

    # Hole cards
    out.append("*** HOLE CARDS ***")
    if hero_name and hero_cards:
        cards_tok = hero_cards.strip().split()
        conv = [_card_to_target(t) for t in cards_tok]
        out.append(f"Dealt to {hero_name} [{' '.join(conv)}]")

    # Preflop actions
    if pre_text:
        out.extend(parse_street_actions(pre_text))

    # FLOP
    if flop_line:
        out.append(f"*** FLOP *** {_parse_cards_block(flop_line.group(1))}")
        if flop_text:
            out.extend(parse_street_actions(flop_text))

    # TURN
    if turn_line:
        out.append(f"*** TURN *** {_parse_cards_block(turn_line.group(1))}")
        if turn_text:
            out.extend(parse_street_actions(turn_text))

    # RIVER
    if river_line:
        out.append(f"*** RIVER *** {_parse_cards_block(river_line.group(1))}")
        if river_text:
            out.extend(parse_street_actions(river_text))

    # SHOWDOWN lines (om de finns)
    if shows:
        out.append("*** SHOWDOWN ***")
        for name, cards, desc in shows:
            card_tokens = cards.strip().split()
            conv_cards = " ".join(_card_to_target(t) for t in card_tokens)

            desc_en = ""
            if desc:
                dl = desc.strip().lower()
                for key, pretty in handtype_keywords:
                    if key in dl:
                        desc_en = pretty
                        break

            if desc_en:
                out.append(f"{name}: Shows [{conv_cards}] {desc_en}")
            else:
                out.append(f"{name}: Shows [{conv_cards}]")

    # SUMMARY
    out.append("*** SUMMARY ***")
    if total_pot and rake:
        out.append(f"Total pot €{total_pot} Rake €{rake}")

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

        # Output (fixad scrollbar-layout)
        frm_out = ttk.Frame(self, padding=10)
        frm_out.pack(fill="both", expand=True)
        ttk.Label(frm_out, text="Konverterad hand:").pack(anchor="w")

        txt_wrap = ttk.Frame(frm_out)
        txt_wrap.pack(fill="both", expand=True)

        self.txt = tk.Text(txt_wrap, wrap="none", height=24)
        self.txt.pack(side="left", fill="both", expand=True)

        yscroll = ttk.Scrollbar(txt_wrap, orient="vertical", command=self.txt.yview)
        yscroll.pack(side="right", fill="y")
        self.txt.configure(yscrollcommand=yscroll.set)

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
            with open(path, "a", encoding="utf-8") as f:
                f.write(text)
                f.write("\n\n")
        except Exception as e:
            messagebox.showwarning(
                "Kunde inte skriva historik",
                f"Kunde inte skriva till:\n{current_history_file()}\n\n{e}"
            )

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
    os.makedirs(HISTORY_DIR, exist_ok=True)
    _ = current_history_file()
    app = App()
    app.mainloop()
