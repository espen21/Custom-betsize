import json
import sys
import csv
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict


# --------------------------------------------------
#       Extract BB size from stake label
# --------------------------------------------------
def parse_big_blind_eur(label: str):
    if not isinstance(label, str):
        return None
    m = re.search(r"€\s*([0-9]+)", label)
    if not m:
        return None
    euros = int(m.group(1))
    return euros / 100.0   # €100 → 1€ BB, €50 → 0.5€ BB etc.


# --------------------------------------------------
#       Load hands from HAR
# --------------------------------------------------
def load_hands_from_har(path: Path):
    with path.open("r", encoding="utf-8") as f:
        har = json.load(f)

    entries = har["log"]["entries"]
    records = []
    level_labels = {}

    for entry in entries:
        if "gethands" not in entry["request"]["url"]:
            continue

        started = entry.get("startedDateTime")
        dt = None
        if started:
            try:
                dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
            except:
                pass

        text = entry["response"]["content"].get("text")
        if not text:
            continue

        try:
            data = json.loads(text)
        except:
            continue

        refs = data.get("refs", {})
        for k, v in refs.items():
            try:
                level_labels[int(k)] = v
            except:
                pass

        for h in data.get("hands", []):
            if len(h) < 9:
                continue

            saldo_before = h[1]
            saldo_after  = h[8]
            level_id     = h[5]
            table_id     = h[6]
            cards        = h[7]

            # IMPORTANT: real hand result
            raw_delta_cent = saldo_after - saldo_before
            result_eur = - raw_delta_cent / 100.0

            label = refs.get(str(level_id)) or level_labels.get(level_id, f"Level {level_id}")
            month = dt.strftime("%Y-%m") if dt else None
            day = dt.strftime("%Y-%m-%d") if dt else None

            records.append({
                "date": day,
                "month": month,
                "label": label,
                "table_id": table_id,
                "cards": cards,
                "result_eur": result_eur,
            })

    return records


# --------------------------------------------------
#       Update monthly CSV
# --------------------------------------------------
def update_month_csv(month: str, day: str, stakes: dict,
                     total_result: float, total_bb100: float, total_hands: int,
                     month_path: Path):

    stake_names = sorted(stakes.keys())

    # new row for today
    new_row = [
        day,
        total_hands,
        f"{total_result:.2f}",
        f"{total_bb100:.2f}"
    ]

    # append each stake’s EUR, BB/100, hands
    for s in stake_names:
        d = stakes[s]
        new_row.extend([
            f"{d['eur']:.2f}",
            f"{d['bb100']:.2f}",
            d["hands"]
        ])

    # If file does NOT exist → create with headers
    if not month_path.exists():
        with month_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")

            headers = ["date", "hands", "total_eur", "total_bb100"]
            for s in stake_names:
                headers.extend([f"{s}_eur", f"{s}_bb100", f"{s}_hands"])
            headers.extend(["month_total_eur", "month_total_hands", "month_total_bb100"])
            writer.writerow(headers)

            # First entry = month total so far
            writer.writerow(
                new_row + [f"{total_result:.2f}", total_hands, f"{total_bb100:.2f}"]
            )
        return

    # If month file exists → append day and recalc totals
    with month_path.open("r", encoding="utf-8") as f:
        rows = list(csv.reader(f, delimiter=";"))

    headers = rows[0]
    day_rows = rows[1:]

    day_rows.append(new_row + ["", "", ""])

    # month totals
    month_total_eur = sum(float(r[2]) for r in day_rows)
    month_total_hands = sum(int(r[1]) for r in day_rows)
    month_total_bb100 = 0.0
    if month_total_hands > 0:
        # Use €100 NL BB size for normalization since it's consistent
        month_total_bb100 = month_total_eur / (month_total_hands / 100.0)

    # update total columns
    for r in day_rows:
        r[-3] = f"{month_total_eur:.2f}"
        r[-2] = month_total_hands
        r[-1] = f"{month_total_bb100:.2f}"

    # write updated CSV
    with month_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(headers)
        writer.writerows(day_rows)


# --------------------------------------------------
#       Update TOTAL CSV (per month)
# --------------------------------------------------
def update_total_csv(month: str, month_csv_path: Path, total_path: Path):

    # read last row (has totals)
    with month_csv_path.open("r", encoding="utf-8") as f:
        rows = list(csv.reader(f, delimiter=";"))
    last = rows[-1]

    month_total_eur = float(last[-3])
    month_total_hands = int(last[-2])
    month_total_bb100 = float(last[-1])

    # write new file if doesn't exist
    if not total_path.exists():
        with total_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["month", "total_eur", "total_hands", "bb100"])
            writer.writerow([month, month_total_eur, month_total_hands, month_total_bb100])
        return

    # update existing
    with total_path.open("r", encoding="utf-8") as f:
        rows = list(csv.reader(f, delimiter=";"))

    header = rows[0]
    month_rows = rows[1:]
    updated = False

    for r in month_rows:
        if r[0] == month:
            r[1] = f"{month_total_eur:.2f}"
            r[2] = month_total_hands
            r[3] = f"{month_total_bb100:.2f}"
            updated = True
            break

    if not updated:
        month_rows.append([month, f"{month_total_eur:.2f}", month_total_hands, f"{month_total_bb100:.2f}"])

    with total_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(header)
        writer.writerows(month_rows)


# --------------------------------------------------
#                MAIN SCRIPT
# --------------------------------------------------
def main(path_str):
    path = Path(path_str)
    records = load_hands_from_har(path)

    if not records:
        print("No hands found.")
        return

    day = records[0]["date"]
    month = records[0]["month"]

    stakes = defaultdict(lambda: {"eur": 0.0, "hands": 0, "bb100": 0.0})

    total_result = 0.0
    total_hands = len(records)
    total_bb = 0.0

    # accumulate results
    for r in records:
        stake = r["label"]
        eur = r["result_eur"]
        bb_size = parse_big_blind_eur(stake) or 1.0

        stakes[stake]["eur"] += eur
        stakes[stake]["hands"] += 1
        stakes[stake]["bb100"] += (eur / bb_size)

        total_result += eur
        total_bb += (eur / bb_size)

    # compute total bb/100
    total_bb100 = total_bb / (total_hands / 100.0)

    # compute per stake bb/100
    for s, d in stakes.items():
        if d["hands"] > 0:
            d["bb100"] = d["bb100"] / (d["hands"] / 100.0)

    # --------------------------------------------------
    #                DAILY PRINT (terminal)
    # --------------------------------------------------
    print("--------------------------------------------------")
    print(f"DAGENS RESULTAT ({day})")
    print("--------------------------------------------------")
    print(f"Totalt antal händer: {total_hands}")
    print(f"Totalt resultat: {total_result:.2f} €")
    print(f"Total winrate: {total_bb100:.2f} bb/100\n")

    print("Per stake:")
    for s in sorted(stakes.keys()):
        d = stakes[s]
        print(f"{s:10s} | Händer: {d['hands']:4d} | Resultat: {d['eur']:8.2f} € | bb/100: {d['bb100']:7.2f}")

    print("--------------------------------------------------\n")

    # --------------------------------------------------
    #       MONTH CSV + TOTAL CSV
    # --------------------------------------------------
    month_csv_path = Path(f"Unibet_resultat-{month}.csv")
    update_month_csv(month, day, stakes, total_result, total_bb100, total_hands, month_csv_path)

    total_csv_path = Path("Unibet_totalresultat.csv")
    update_total_csv(month, month_csv_path, total_csv_path)

    print("CSV files updated.")


# --------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python unibet_master_stats.py file.har")
    else:
        main(sys.argv[1])
