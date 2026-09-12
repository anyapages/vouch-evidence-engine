"""Build data/ni.json, the Northern Ireland outpatient file the app can serve,
from the Department of Health's quarterly workbook.

    python3 scripts/ni.py --pull            # fetch the current workbook, then build
    python3 scripts/ni.py path/to/hs-niwts-tables-outpatients-q1-26-27.xlsx

Writes data/ni.json and data/raw/ni_outpatients_<quarter>.csv. Both are committed,
so a reviewer can diff what changed rather than take the app on trust. Needs
openpyxl to read the workbook; the app and the tests read only the JSON.

What this file is, and is not. The Department publishes first consultant-led
outpatient waits by HSC Trust and specialty. There are five Trusts and no
hospital sites in the workbook, so this is a different level of evidence from
the NTPF file (hospital by specialty), and the app says so wherever it shows
it. Vouch's two-queues finding was measured on the Republic's hospital-level
file and has not been measured on Northern Ireland letters; nothing here claims
that it transfers.
"""
import csv
import datetime
import hashlib
import io
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent

# The publication page, and the date it states. The workbook itself carries the
# quarter it describes but not the day it was released.
PAGE = ("https://www.health-ni.gov.uk/publications/"
        "northern-ireland-waiting-time-statistics-outpatient-waiting-times-june-2026")
WORKBOOK = "https://www.health-ni.gov.uk/sites/default/files/2026-09/hs-niwts-tables-outpatients-q1-26-27.xlsx"
PUBLISHED = "2026-09-03"

# Table 2 is the encompass-era series (South Eastern from Dec 2023, all five
# Trusts validated from Sep 2025). Table 1 is the legacy series with a different
# band scheme; it is not read. These thirteen bands are the ones populated in the
# current quarter and they sum to the published total, which the build checks.
BANDS = ["0 - 6 Wks", ">6 - 9 Wks", ">9 - 12 Wks", ">12 - 15 Wks", ">15 - 18 Wks",
         ">18 - 26 Wks", ">26 - 39 Wks", ">39 - 52 Wks", ">52 - 65 Wks", ">65 - 78 Wks",
         ">78 - 91 Wks", ">91 - 104 Wks", ">104 Wks"]
OVER_52 = BANDS[8:]
TRUSTS = {"Belfast", "Northern", "South Eastern", "Southern", "Western"}

# Caveats the Department attaches to the workbook, carried into the file so they
# reach the screen. Quoted from the Notes sheet of the June 2026 workbook.
CAVEATS = [
    "Data for Belfast, Southern and Western Trusts may include duplicate records "
    "that could not be validated by the Trusts in time for publication.",
    "Community Paediatrics data sourced from encompass are currently under review "
    "and are higher than in previous quarters.",
    "Due to system issues, a small number of outpatient Ophthalmology waits have "
    "been captured as day case waits.",
    "Published by HSC Trust, not by hospital site.",
]


def to_int(v):
    if v in (None, "", "NA"):
        return 0
    return int(round(float(v)))


def main(argv):
    if len(argv) > 1 and argv[1] == "--pull":
        raw = urllib.request.urlopen(WORKBOOK, timeout=60).read()
    elif len(argv) > 1:
        raw = pathlib.Path(argv[1]).read_bytes()
    else:
        sys.exit(__doc__)
    sha = hashlib.sha256(raw).hexdigest()

    import openpyxl  # only the build needs it
    wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    rows = list(wb["Table 2"].iter_rows(values_only=True))
    hdr = [str(h) for h in rows[0]]
    idx = {h: i for i, h in enumerate(hdr)}
    missing = [b for b in BANDS + ["Quarter Ending", "HSC Trust", "Specialty", "Total Waiting"] if b not in idx]
    if missing:
        sys.exit(f"workbook layout changed, columns missing: {missing}")

    quarters = sorted({str(r[0])[:10] for r in rows[1:] if r[0]})
    quarter = quarters[-1]
    latest = [r for r in rows[1:] if str(r[0])[:10] == quarter]
    if not latest:
        sys.exit("no rows in the latest quarter")

    out, raw_rows, bad = [], [], []
    for r in latest:
        trust, specialty = str(r[idx["HSC Trust"]]).strip(), str(r[idx["Specialty"]]).strip()
        bands = {b: to_int(r[idx[b]]) for b in BANDS}
        total = to_int(r[idx["Total Waiting"]])
        if sum(bands.values()) != total:
            bad.append((trust, specialty, sum(bands.values()), total))
            continue
        if not total:
            continue
        over = sum(bands[b] for b in OVER_52)
        out.append({"trust": trust, "specialty": specialty, "bands": bands, "total": total,
                    "over52w": over, "pctOver52w": round(over * 100 / total, 1)})
        raw_rows.append([quarter, trust, specialty] + [bands[b] for b in BANDS] + [total])
    if bad:
        for b in bad[:5]:
            print("bands do not sum to the published total:", b)
        sys.exit(f"{len(bad)} rows fail the sum check; not writing")
    found = {r["trust"] for r in out}
    if not TRUSTS <= found:
        sys.exit(f"expected the five Trusts, found {sorted(found)}")
    extra = sorted(found - TRUSTS)

    out.sort(key=lambda r: (r["specialty"], r["trust"]))
    meta = {
        "source": "Department of Health NI, outpatient waiting times, HSC Trust x specialty",
        "jurisdiction": "Northern Ireland",
        "level": "HSC Trust",
        "quarterEnding": quarter,
        "published": PUBLISHED,
        "page": PAGE,
        "workbook": WORKBOOK,
        "workbookSha256": sha,
        "extracted": datetime.date.today().isoformat(),
        "extraction": "scripts/ni.py",
        "bands": BANDS,
        "over52wBands": OVER_52,
        "trusts": sorted(TRUSTS),
        "otherRows": extra,
        "caveats": CAVEATS,
        "rows": len(out),
    }
    (ROOT / "data" / "ni.json").write_text(json.dumps({"meta": meta, "rows": out}, indent=1) + "\n")
    with (ROOT / "data" / "raw" / f"ni_outpatients_{quarter}.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Quarter Ending", "HSC Trust", "Specialty"] + BANDS + ["Total Waiting"])
        w.writerows(raw_rows)
    total = sum(r["total"] for r in out)
    over = sum(r["over52w"] for r in out)
    print(f"quarter {quarter}, published {PUBLISHED}, workbook sha256 {sha[:16]}")
    print(f"rows {len(out)}, trusts {sorted(found)}, specialties {len({r['specialty'] for r in out})}")
    print(f"total waiting {total}, over 52 weeks {over} ({over * 100 / total:.1f}%)")


if __name__ == "__main__":
    main(sys.argv)
