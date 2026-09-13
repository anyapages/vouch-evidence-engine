"""Rebuild data/ntpf.json, the file the app serves, from the published report.

    python3 scripts/build_dataset.py 2026-07-30

Writes data/ntpf.json and data/raw/ntpf_hospital_specialty_<date>.csv. Both are
committed, so a reviewer can diff what changed rather than take the app on trust.
"""
import collections
import csv
import datetime
import json
import pathlib
import sys

import ntpf

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-07-30"

# Category and WLType are sub-list rows (suspensions, planned procedures) in the same
# table; keeping them would double count, so both must be null for a leaf row. The
# list type itself (outpatient only) is filtered inside ntpf.query.
select = [
    ntpf.col("HospitalName"), ntpf.col("SpecialtyName"), ntpf.col("Publication Time Band"),
    ntpf.col("WLType"), ntpf.col("Category"), ntpf.col("Age Group"), ntpf.agg("Amount"),
]
rows, restart = ntpf.decode(ntpf.query(select, ntpf.on_archive_date(DATE)), 7)
if restart:
    sys.exit("truncated: raise the window in ntpf.query and re-run")
# An archive label that was never published answers with no rows. Writing that
# out would replace the served dataset with an empty one and every downstream
# check would then fail somewhere less obvious than here.
if not rows:
    sys.exit(f"no rows for archive {DATE}: the report does not publish that archive. "
             f"Ask scripts/ntpf.py archive_dates() for the labels that exist.")
print(f"raw rows: {len(rows)}")

acc = collections.defaultdict(lambda: dict.fromkeys(ntpf.BANDS, 0))
for hospital, specialty, band, wl, category, age, amount in rows:
    if category is not None or wl is not None or not band or not age:
        continue
    band = band.strip()
    if band not in ntpf.BANDS:
        continue
    acc[(specialty, hospital, age)][band] += ntpf.to_int(amount)

out = []
for (specialty, hospital, age), bands in sorted(acc.items()):
    total = sum(bands.values())
    if not total:
        continue
    over = sum(bands[b] for b in ntpf.LONG_BANDS)
    out.append({
        "specialty": specialty, "hospital": hospital, "ageGroup": age, "bands": bands,
        "total": total, "over12m": over, "pctOver12m": round(over * 100 / total, 1),
    })

(ROOT / "data" / "ntpf.json").write_text(json.dumps({
    "meta": {
        "source": "NTPF outpatient waiting list, hospital x specialty",
        "published": DATE,
        "extracted": datetime.date.today().isoformat(),
        "extraction": "scripts/build_dataset.py",
        # Neither field exists in the published data. The app must never imply otherwise.
        "urgencyField": False,
        "newReturnField": False,
        "bands": ntpf.BANDS,
        "rows": len(out),
    },
    "rows": out,
}, indent=1))

with (ROOT / "data" / "raw" / f"ntpf_hospital_specialty_{DATE}.csv").open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["specialty", "hospital", "age_group", "waiting_over_12m", "total_waiting", "pct_over_12m"])
    for r in out:
        w.writerow([r["specialty"], r["hospital"], r["ageGroup"], r["over12m"], r["total"], r["pctOver12m"]])

print(f"wrote {len(out)} rows | {len({r['hospital'] for r in out})} hospitals | {len({r['specialty'] for r in out})} specialties")
