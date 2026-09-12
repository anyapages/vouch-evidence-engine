"""How much does the ordering move month to month?

    python3 scripts/stability.py Endocrinology

Pulls the last 13 published archives and records, for each, every hospital's share
waiting over a year. This is what licenses the caution the app shows: if a ranking
churns, a screen that presents it as settled is misleading. See data/README.md.
"""
import collections
import json
import pathlib
import sys
import time

import ntpf

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPECIALTY = sys.argv[1] if len(sys.argv) > 1 else "Endocrinology"
MIN_LIST = 200  # below this a share is too noisy to rank on
DATES = json.loads((ROOT / "data" / "raw" / "archive_dates.json").read_text())[-13:]


def order_for(date):
    select = [
        ntpf.col("HospitalName"), ntpf.col("SpecialtyName"), ntpf.col("Publication Time Band"),
        ntpf.col("WLType"), ntpf.col("Category"), ntpf.col("Age Group"), ntpf.agg("Amount"),
    ]
    rows, _ = ntpf.decode(ntpf.query(select, ntpf.on_archive_date(date)), 7)
    acc = collections.defaultdict(lambda: [0, 0])
    for hospital, specialty, band, wl, category, age, amount in rows:
        if category is not None or wl is not None or specialty != SPECIALTY or age != "Adult" or not band:
            continue
        n = ntpf.to_int(amount)
        acc[hospital][1] += n
        if band.strip() in ntpf.LONG_BANDS:
            acc[hospital][0] += n
    return {h: long / total for h, (long, total) in acc.items() if total >= MIN_LIST}


history = {}
for date in DATES:
    try:
        history[date] = order_for(date)
        print(f"  {date}: {len(history[date])} hospitals", flush=True)
    except Exception as exc:
        print(f"  {date}: FAILED {exc}", flush=True)
    time.sleep(0.7)

path = ROOT / "data" / "raw" / f"stability_{SPECIALTY}.json"
path.write_text(json.dumps(history, indent=1))
print("wrote", path.relative_to(ROOT))
