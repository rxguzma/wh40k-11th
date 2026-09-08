#!/usr/bin/env python3
import csv
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "universal"


def fail(message):
    raise SystemExit(message)


def read_csv(name, expected_header):
    path = DATA / name
    if not path.is_file():
        fail(f"missing {path.relative_to(ROOT)}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != expected_header:
            fail(f"{path.relative_to(ROOT)} header must be exactly {expected_header!r}; found {reader.fieldnames!r}")
        return list(reader)


def require_unique(rows, field, label):
    seen = set()
    for line_no, row in enumerate(rows, start=2):
        value = (row.get(field) or "").strip()
        if not value:
            fail(f"{label} line {line_no}: blank {field}")
        if value in seen:
            fail(f"{label} line {line_no}: duplicate {field} {value!r}")
        seen.add(value)
    return seen


dispositions = read_csv(
    "Dispositions.csv",
    ["Disposition_ID", "Disposition_Name", "Sort_Order"],
)
missions = read_csv(
    "Primary_Missions.csv",
    ["Primary_Mission_ID", "Disposition_ID", "Mission_Name", "Sort_Order"],
)
matchups = read_csv(
    "Primary_Mission_Matchups.csv",
    ["Matchup_ID", "Your_Disposition_ID", "Opponent_Disposition_ID", "Primary_Mission_ID"],
)

disposition_ids = require_unique(dispositions, "Disposition_ID", "Dispositions.csv")
require_unique(dispositions, "Disposition_Name", "Dispositions.csv")
mission_ids = require_unique(missions, "Primary_Mission_ID", "Primary_Missions.csv")
require_unique(missions, "Mission_Name", "Primary_Missions.csv")
require_unique(matchups, "Matchup_ID", "Primary_Mission_Matchups.csv")

sort_orders = set()
for line_no, row in enumerate(dispositions, start=2):
    raw = (row.get("Sort_Order") or "").strip()
    if not raw.isdigit() or int(raw) < 1:
        fail(f"Dispositions.csv line {line_no}: Sort_Order must be a positive integer")
    order = int(raw)
    if order in sort_orders:
        fail(f"Dispositions.csv line {line_no}: duplicate Sort_Order {order}")
    sort_orders.add(order)

mission_owner = {}
mission_order_by_disposition = {}
for line_no, row in enumerate(missions, start=2):
    mission_id = row["Primary_Mission_ID"].strip()
    disposition_id = (row.get("Disposition_ID") or "").strip()
    if disposition_id not in disposition_ids:
        fail(f"Primary_Missions.csv line {line_no}: unknown Disposition_ID {disposition_id!r}")
    raw = (row.get("Sort_Order") or "").strip()
    if not raw.isdigit() or int(raw) < 1:
        fail(f"Primary_Missions.csv line {line_no}: Sort_Order must be a positive integer")
    order = int(raw)
    key = (disposition_id, order)
    if key in mission_order_by_disposition:
        fail(f"Primary_Missions.csv line {line_no}: duplicate Sort_Order {order} for {disposition_id}")
    mission_order_by_disposition[key] = mission_id
    mission_owner[mission_id] = disposition_id

pairs = {}
for line_no, row in enumerate(matchups, start=2):
    yours = (row.get("Your_Disposition_ID") or "").strip()
    opponent = (row.get("Opponent_Disposition_ID") or "").strip()
    mission_id = (row.get("Primary_Mission_ID") or "").strip()
    if yours not in disposition_ids:
        fail(f"Primary_Mission_Matchups.csv line {line_no}: unknown Your_Disposition_ID {yours!r}")
    if opponent not in disposition_ids:
        fail(f"Primary_Mission_Matchups.csv line {line_no}: unknown Opponent_Disposition_ID {opponent!r}")
    if mission_id not in mission_ids:
        fail(f"Primary_Mission_Matchups.csv line {line_no}: unknown Primary_Mission_ID {mission_id!r}")
    if mission_owner[mission_id] != yours:
        fail(
            f"Primary_Mission_Matchups.csv line {line_no}: mission {mission_id!r} belongs to "
            f"{mission_owner[mission_id]!r}, not Your_Disposition_ID {yours!r}"
        )
    expected_matchup_id = f"{yours}__VS__{opponent}"
    if row["Matchup_ID"].strip() != expected_matchup_id:
        fail(
            f"Primary_Mission_Matchups.csv line {line_no}: Matchup_ID must be "
            f"{expected_matchup_id!r}"
        )
    pair = (yours, opponent)
    if pair in pairs:
        fail(f"Primary_Mission_Matchups.csv line {line_no}: duplicate matchup {pair!r}")
    pairs[pair] = mission_id

expected_pairs = set(product(disposition_ids, disposition_ids))
actual_pairs = set(pairs)
if actual_pairs != expected_pairs:
    missing = sorted(expected_pairs - actual_pairs)
    extra = sorted(actual_pairs - expected_pairs)
    fail(f"Primary matchup matrix incomplete: missing={missing!r} extra={extra!r}")

print(
    f"cards data: OK — {len(dispositions)} dispositions, "
    f"{len(missions)} primary missions, {len(matchups)} matchup rows"
)
