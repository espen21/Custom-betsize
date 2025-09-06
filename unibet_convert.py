import re
from datetime import datetime
import clipboard
import time
import keyboard

VERSION_STR = "24.7.1.16"

# Alltid använd detta namn som Hero om det finns i handen,
# annars faller vi tillbaka till första "Delat ut till ..."
PREFERRED_HERO = "JullyEggy"

# Svenska -> Engelsk kortfärg (målsystemets bokstav först, sedan valör)
# r = ruter(D), k = klöver(C), s = spader(S), h = hjärter(H)
SUIT_MAP = {"r": "D", "k": "C", "s": "S", "h": "H"}

# Hjälpfunktioner
def _rank_norm(tok: str) -> str:
    """Normalisera valör: 10 stavas '10', annars A,K,Q,J,9..2."""
    tok = tok.upper()
    return "10" if tok in ("10", "T") else tok

def _card_sv_to_target(token: str) -> str:
    """
    Konvertera t.ex. '7h' -> 'H7', 'Jk' -> 'CJ', 'Kr' -> 'DK'.
    Tar höjd för blandade format (t.ex. '10k', 'T k').
    """
    token = token.strip().lower()
    # Ex: '7h', 'kh', '10k', 'jk'
    m = re.match(r"^([0-9]{1,2}|[tjqka])([rksh])$", token)
    if not m:
        # För säkerhets skull: lämna tillbaka orört om vi inte matchar
        return token.upper()
    rank, suit = m.groups()
    suit_en = SUIT_MAP.get(suit, suit.upper())
    rank_en = _rank_norm(rank)
    # Målets stil: Suit först, sedan rank (t.ex. 'H7', 'CQ', 'S10')
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

def _parse_single_card(token: str) -> str:
    return _card_sv_to_target(token)

def _money(s: str) -> str:
    """Säker formatering av pengar med två decimaler."""
    return f"{float(s):.2f}"

def convert(raw: str, version: str = VERSION_STR) -> str:
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
    # Lägg till /GMT enligt målets format (vi antar att given tid kan presenteras så)
    header_line = f"GAME #{hand_id} Version:{version} Uncalled:Y Texas Hold'em NL €{sb}/€{bb} {date_str} {time_str}/GMT"

    # --- Seats / Stacks ---
    seats = re.findall(r"Platser\s+(\d+):\s*([^\(]+)\(€([\d\.]+)\)", raw)
    # Bestäm table size som antal listade seats (fallback 6)
    table_size = len(seats) if len(seats) > 0 else 6

    # Hitta button (dealern)
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

    # --- Hole cards (lista på alla "Delat ut till") ---
    dealt = re.findall(r"Delat ut till\s+([^\s]+)\s+\[([^\]]+)\]", raw, flags=re.I)

    # --- Actions per gata ---
    # Vi håller "current_to" per gata för att kunna räkna "raises to".
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
                current_to = amt
                out.append(f"{name}: Bet €{amt:.2f}")
                continue
            # Call
            m_call = re.search(r"([^\s:]+).*synar\s+€([\d\.]+)", line, flags=re.I)
            if m_call:
                name = m_call.group(1)
                amt = float(m_call.group(2))
                out.append(f"{name}: Call €{amt:.2f}")
                # current_to förblir oförändrat (call påverkar inte "to"-nivån)
                continue
            # Raise (svenska loggen kan skriva "höjer €X med €Y")
            m_raise = re.search(r"([^\s:]+).*höjer\s+€([\d\.]+)(?:\s+med\s+€([\d\.]+))?", line, flags=re.I)
            if m_raise:
                name = m_raise.group(1)
                inc = float(m_raise.group(2))
                # Heuristik: i dessa loggar har första talet oftast varit "raise-increment".
                new_to = current_to + inc
                current_to = new_to
                out.append(f"{name}: Raise (NF) €{new_to:.2f}")
                continue
            # All-in bet text (t.ex. "satsar €44.80, och är all-in")
            m_allin_bet = re.search(r"([^\s:]+).*satsar\s+€([\d\.]+).*all-?in", line, flags=re.I)
            if m_allin_bet:
                name = m_allin_bet.group(1)
                amt = float(m_allin_bet.group(2))
                current_to = amt
                out.append(f"{name}: Bet €{amt:.2f}")
                continue
            # All-in raise text (fallback)
            m_allin_raise = re.search(r"([^\s:]+).*höjer\s+.*all-?in", line, flags=re.I)
            if m_allin_raise:
                name = m_allin_raise.group(1)
                out.append(f"{name}: Raise (NF) (all-in)")
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

    # -------- HERO-logik här --------
    out.append("*** HOLE CARDS ***")
    hero_name = None
    hero_cards = None
    if dealt:
        # 1) Försök hitta "JullyEggy" (case-insensitivt)
        for name, cards in dealt:
            if name.strip().lower() == PREFERRED_HERO.lower():
                hero_name = name
                hero_cards = cards
                break
        # 2) Fallback: ta första "Delat ut till ..."
        if hero_name is None:
            hero_name, hero_cards = dealt[0]

    # Skriv endast hero-raden
    if hero_name and hero_cards:
        cards_tok = hero_cards.strip().split()
        conv = [_card_sv_to_target(t) for t in cards_tok]
        out.append(f"Dealt to {hero_name} [{' '.join(conv)}]")

    # Preflop actions
    if pre_block:
        pre_actions = parse_street_actions(pre_block.group(1), preflop=True)
        out.extend(pre_actions)

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

    # Showdown lines (översätter bara kort – lämnar svensk handtext utanför)
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
        # enkel översättning av handtyp om den finns
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


# -------------------------------
# Exempel: klistra in din hand här
if __name__ == "__main__":
    stop = False
    while stop is False:
        input("Will read your clipboard and convert Unibet handhistory   press [Enter] to continue or \n [S] to stop: ")
        print(clipboard.paste())
        clipboard.copy((convert(clipboard.paste())))
        print("Converted hand is copied to your clipboard")
        if (keyboard.is_pressed("S")):
            stop = True
            break
