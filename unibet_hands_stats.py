import json
import re
import sqlite3
from pathlib import Path
from datetime import datetime, date, timedelta
from collections import defaultdict
from typing import Optional

import streamlit as st
import pandas as pd


# ----------------------- Hjälpfunktioner ----------------------- #

def parse_big_blind_eur(label: str):
    """Extraherar BB-storlek i € från t.ex. '€100 NL' → 1.0, '€50 NL' → 0.5."""
    if not isinstance(label, str):
        return None
    m = re.search(r"€\s*([0-9]+)", label)
    if not m:
        return None
    euros = int(m.group(1))
    return euros / 100.0


def fix_encoding(s: str) -> str:
    """
    Fixar vanliga UTF-8/Latin1-strul, t.ex. 'â‚¬100 NL' → '€100 NL'.
    Om det redan är korrekt händer inget.
    """
    if not isinstance(s, str):
        return s
    try:
        return s.encode("latin1").decode("utf-8")
    except Exception:
        return s


def format_cards_pretty_html(cards: str) -> str:
    """
    Gör om t.ex. 'kskd' → 'K♠ K♦' med färger via HTML:
      s → svart ♠
      h → röd ♥
      d → blå ♦
      c → grön ♣
    Returnerar en HTML-sträng (används med unsafe_allow_html=True).
    """
    if not cards:
        return ""
    s = cards.strip().lower()

    suit_map = {
        "s": ("♠", "black"),
        "h": ("♥", "red"),
        "d": ("♦", "blue"),
        "c": ("♣", "green"),
    }
    rank_map = {"t": "T", "j": "J", "q": "Q", "k": "K", "a": "A"}

    chunks = [s[i:i + 2] for i in range(0, len(s), 2)]
    pieces = []
    for ch in chunks:
        if len(ch) != 2:
            continue
        r_raw, su_raw = ch[0], ch[1]
        r = rank_map.get(r_raw, r_raw.upper())
        sym, color = suit_map.get(su_raw, ("?", "black"))
        span = f'<span style="color:{color}">{sym}</span>'
        pieces.append(f"{r}{span}")
    return " ".join(pieces)


def load_records_from_har_bytes(har_bytes: bytes, override_date: Optional[date] = None):
    """
    Läser händer ur HAR och bestämmer datum enligt:
      1. override_date (manuellt i GUI)
      2. stime (UTC timestamp) + 1 dag
      3. startedDateTime fallback
    Returnerar en lista med dicts.
    """
    har = json.loads(har_bytes.decode("utf-8"))
    entries = har.get("log", {}).get("entries", [])
    records = []
    level_labels = {}

    for entry in entries:
        req = entry.get("request", {})
        if "gethands" not in req.get("url", ""):
            continue

        # --- Försök läsa stime från request-body ---
        stime_date = None
        body_text = req.get("postData", {}).get("text")
        if body_text:
            try:
                body = json.loads(body_text)
                stime = body.get("stime")
                if stime:
                    # stime verkar vara kvällen innan "din" dag → +1 dag
                    dt_stime = datetime.utcfromtimestamp(stime) + timedelta(days=1)
                    stime_date = dt_stime.date()
            except Exception:
                pass

        # --- Fallback: startedDateTime från HAR ---
        started_date = None
        started = entry.get("startedDateTime")
        if started:
            try:
                dt_started = datetime.fromisoformat(started.replace("Z", "+00:00"))
                started_date = dt_started.date()
            except Exception:
                pass

        # --- Välj datum ---
        if override_date is not None:
            the_date = override_date
        elif stime_date is not None:
            the_date = stime_date
        else:
            the_date = started_date

        if the_date:
            day_str = the_date.strftime("%Y-%m-%d")
            month_str = the_date.strftime("%Y-%m")
        else:
            day_str = None
            month_str = None

        # --- Läs response-content ---
        content = entry.get("response", {}).get("content", {}) or {}
        text = content.get("text") or ""
        if not text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue

        # refs innehåller stakes-namn etc.
        refs = data.get("refs", {}) or {}
        for k, v in refs.items():
            try:
                level_labels[int(k)] = v
            except ValueError:
                pass

        for h in data.get("hands", []):
            if len(h) < 9:
                continue

            hand_id = h[0]
            saldo_before = h[1]
            pot_cent = h[3]
            level_id = h[5]
            table_id = h[6]
            cards = h[7]
            saldo_after = h[8]

            raw_delta = saldo_after - saldo_before
            result_eur = -raw_delta / 100.0
            pot_eur = pot_cent / 100.0

            stake_label = refs.get(str(level_id), level_labels.get(level_id, f"Level {level_id}"))

            records.append({
                "hand_id": hand_id,
                "date": day_str,
                "month": month_str,
                "stake": stake_label,
                "table_id": table_id,
                "cards": cards,
                "pot_eur": pot_eur,
                "result_eur": result_eur,
            })

    return records


# ----------------------- SQLite-hantering ----------------------- #

def get_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection):
    """Skapa tabell + index om de inte finns."""
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS hands (
                hand_id    INTEGER PRIMARY KEY,
                date       TEXT,
                month      TEXT,
                stake      TEXT,
                table_id   INTEGER,
                cards      TEXT,
                pot_eur    REAL,
                result_eur REAL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hands_date ON hands(date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hands_month ON hands(month)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hands_stake ON hands(stake)")


def insert_hands(conn: sqlite3.Connection, records):
    """
    Lägg in händer i SQLite med INSERT OR IGNORE (dubblettskydd på hand_id).
    Returnerar antal nyinsatta rader.
    """
    if not records:
        return 0
    with conn:
        before = conn.total_changes
        conn.executemany(
            """
            INSERT OR IGNORE INTO hands
            (hand_id, date, month, stake, table_id, cards, pot_eur, result_eur)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    r["hand_id"],
                    r["date"],
                    r["month"],
                    r["stake"],
                    r["table_id"],
                    r["cards"],
                    r["pot_eur"],
                    r["result_eur"],
                )
                for r in records
            ],
        )
        after = conn.total_changes
    return after - before


def load_all_hands(conn: sqlite3.Connection):
    """Hämtar alla händer som lista med dictar."""
    rows = conn.execute(
        "SELECT hand_id, date, month, stake, table_id, cards, pot_eur, result_eur FROM hands"
    ).fetchall()
    return [dict(r) for r in rows]


# ----------------------- Aggregat-funktioner ----------------------- #

def aggregate_hands(records):
    """Tar en lista med hand-records och ger total + per stake."""
    if not records:
        return {"hands": 0, "result_eur": 0.0, "bb100": 0.0, "stakes": {}}

    stakes = defaultdict(lambda: {"hands": 0, "eur": 0.0, "bb_sum": 0.0})
    total_hands = 0
    total_eur = 0.0
    total_bb_sum = 0.0

    for r in records:
        eur = r["result_eur"]
        stake = r["stake"]
        bb_size = parse_big_blind_eur(stake) or 1.0
        bb = eur / bb_size

        stakes[stake]["hands"] += 1
        stakes[stake]["eur"] += eur
        stakes[stake]["bb_sum"] += bb

        total_hands += 1
        total_eur += eur
        total_bb_sum += bb

    bb100 = total_bb_sum / (total_hands / 100.0) if total_hands > 0 else 0.0

    stakes_out = {}
    for stake, d in stakes.items():
        h = d["hands"]
        stakes_out[stake] = {
            "hands": h,
            "result_eur": d["eur"],
            "bb100": d["bb_sum"] / (h / 100.0) if h > 0 else 0.0,
        }

    return {
        "hands": total_hands,
        "result_eur": total_eur,
        "bb100": bb100,
        "stakes": stakes_out,
    }


def aggregate_by_date(all_hands):
    by_date = defaultdict(list)
    for r in all_hands:
        if r.get("date"):
            by_date[r["date"]].append(r)
    return {d: aggregate_hands(recs) for d, recs in by_date.items()}


def aggregate_by_month(all_hands):
    by_month = defaultdict(list)
    for r in all_hands:
        if r.get("month"):
            by_month[r["month"]].append(r)
    return {m: aggregate_hands(recs) for m, recs in by_month.items()}


# ------------------------ STREAMLIT GUI ------------------------ #

def main():
    st.title("Unibet HAR → SQLite-handdatabas & resultat")

    # Datamapp & DB
    default_folder = Path("unibet_data").resolve()
    folder_str = st.sidebar.text_input("Datamapp", str(default_folder))
    data_folder = Path(folder_str)
    data_folder.mkdir(parents=True, exist_ok=True)
    db_path = data_folder / "unibet_hands.sqlite"
    st.sidebar.write(f"Databasfil: `{db_path}`")

    conn = get_connection(db_path)
    init_db(conn)

    # Import HAR
    st.sidebar.header("Importera HAR")
    use_manual_date = st.sidebar.checkbox("Sätt datum manuellt")
    manual_date: Optional[date] = None
    if use_manual_date:
        manual_date = st.sidebar.date_input("Datum för dessa HAR", value=date.today())

    uploads = st.sidebar.file_uploader(
        "Välj en eller flera HAR-filer",
        type=["har"],
        accept_multiple_files=True,
    )

    if uploads:
        total_added = 0
        for uf in uploads:
            st.sidebar.write(f"Läser {uf.name}...")
            recs = load_records_from_har_bytes(
                uf.getvalue(),
                override_date=manual_date if use_manual_date else None,
            )
            added = insert_hands(conn, recs)
            total_added += added
            st.sidebar.success(f"{uf.name}: {added} nya händer")
        st.sidebar.info(f"Totalt nya händer denna import: {total_added}")

    # Läs alla händer från DB
    all_hands = load_all_hands(conn)
    if not all_hands:
        st.info("Inga händer i databasen ännu. Importera en HAR-fil.")
        return

    st.sidebar.write(f"Totalt antal händer: **{len(all_hands)}**")

    view = st.radio(
        "Vy",
        [
            "Per dag",
            "Per månad",
            "Alla dagar (tabell + grafer)",
            "Alla händer (sortable)",
            "Graf – kumulativ resultatkurva",
            "Total (alla händer)",
        ],
    )

    # ---------------- PER DAG ----------------
    if view == "Per dag":
        per_date = aggregate_by_date(all_hands)
        dates = sorted(per_date.keys())
        chosen = st.selectbox("Datum", dates)
        agg = per_date[chosen]

        st.header(f"Datum: {chosen}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Resultat (€)", f"{agg['result_eur']:.2f}")
        col2.metric("Händer", agg["hands"])
        col3.metric("BB/100", f"{agg['bb100']:.2f}")

        rows = []
        for stake, info in agg["stakes"].items():
            rows.append({
                "Stake": fix_encoding(stake),
                "Händer": info["hands"],
                "Result (€)": round(info["result_eur"], 2),
                "BB/100": round(info["bb100"], 2),
            })
        st.subheader("Per stake")
        st.table(pd.DataFrame(rows))

    # ---------------- PER MÅNAD ----------------
    elif view == "Per månad":
        per_month = aggregate_by_month(all_hands)
        months = sorted(per_month.keys())
        chosen = st.selectbox("Månad", months)
        agg = per_month[chosen]

        st.header(f"Månad: {chosen}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Resultat (€)", f"{agg['result_eur']:.2f}")
        col2.metric("Händer", agg["hands"])
        col3.metric("BB/100", f"{agg['bb100']:.2f}")

        rows = []
        for stake, info in agg["stakes"].items():
            rows.append({
                "Stake": fix_encoding(stake),
                "Händer": info["hands"],
                "Result (€)": round(info["result_eur"], 2),
                "BB/100": round(info["bb100"], 2),
            })
        st.subheader("Per stake")
        st.table(pd.DataFrame(rows))

    # ---------------- ALLA DAGAR (TABELL + GRAF) ----------------
    elif view == "Alla dagar (tabell + grafer)":
        per_date = aggregate_by_date(all_hands)
        rows = []
        for d, agg in per_date.items():
            rows.append({
                "Datum": d,
                "Händer": agg["hands"],
                "Result (€)": round(agg["result_eur"], 2),
                "BB/100": round(agg["bb100"], 2),
            })
        df = pd.DataFrame(rows).sort_values("Datum")
        st.subheader("Tabell per dag")
        st.table(df)

        df_plot = df.copy()
        df_plot["Datum"] = pd.to_datetime(df_plot["Datum"], errors="coerce")
        df_plot = df_plot.set_index("Datum").sort_index()

        if not df_plot.empty:
            st.subheader("Resultat (€) över dagar")
            st.line_chart(df_plot["Result (€)"])

            st.subheader("BB/100 över dagar")
            st.line_chart(df_plot["BB/100"])
        else:
            st.info("Kunde inte tolka datum till grafer.")

    # ---------------- ALLA HÄNDER (SORTABLE + FÄRGADE KORT) ----------------
    elif view == "Alla händer (sortable)":
        st.header("Alla händer – sortera t.ex. på största pott")

        rows = []
        for r in all_hands:
            stake = r["stake"]
            eur = r["result_eur"]
            bb_size = parse_big_blind_eur(stake) or 1.0
            bb = eur / bb_size
            rows.append({
                "Datum": r["date"],
                "Hand ID": r["hand_id"],
                "Stake": fix_encoding(stake),
                "Bord": r["table_id"],
                "Kort": format_cards_pretty_html(r.get("cards", "")),
                "Pott (€)": r["pot_eur"],
                "Result (€)": round(eur, 2),
                "BB": round(bb, 2),
            })

        df = pd.DataFrame(rows)
        if "Pott (€)" in df.columns:
            df = df.sort_values("Pott (€)", ascending=False)

        st.info("Tips: sortera genom att klicka i tabellhuvudet (tabellen nedan).")
        html_table = df.to_html(escape=False, index=False)
        st.markdown(html_table, unsafe_allow_html=True)

    # ---------------- KUMULATIV RESULTATKURVA ----------------
    elif view == "Graf – kumulativ resultatkurva":
        st.header("Kumulativ resultatkurva (alla händer i ordning)")

        df = pd.DataFrame(all_hands)
        df["Datum"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.sort_values(["Datum", "hand_id"])

        df["eur"] = df["result_eur"]
        df["bb"] = df.apply(
            lambda r: r["result_eur"] / (parse_big_blind_eur(r["stake"]) or 1.0),
            axis=1,
        )
        df["cum_eur"] = df["eur"].cumsum()
        df["cum_bb"] = df["bb"].cumsum()
        df["hand_index"] = range(1, len(df) + 1)

        df_idx = df.set_index("hand_index")

        st.subheader("Kumulativt resultat (€)")
        st.line_chart(df_idx["cum_eur"])

        st.subheader("Kumulativt resultat (BB)")
        st.line_chart(df_idx["cum_bb"])

    # ---------------- TOTAL ----------------
    else:  # "Total (alla händer)"
        agg = aggregate_hands(all_hands)

        st.header("Total – alla händer")

        col1, col2, col3 = st.columns(3)
        col1.metric("Resultat (€)", f"{agg['result_eur']:.2f}")
        col2.metric("Händer", agg["hands"])
        col3.metric("BB/100", f"{agg['bb100']:.2f}")

        rows = []
        for stake, info in agg["stakes"].items():
            rows.append({
                "Stake": fix_encoding(stake),
                "Händer": info["hands"],
                "Result (€)": round(info["result_eur"], 2),
                "BB/100": round(info["bb100"], 2),
            })
        st.subheader("Per stake")
        st.table(pd.DataFrame(rows))


if __name__ == "__main__":
    main()
