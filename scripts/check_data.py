"""Invariants the committed dataset must satisfy. Run in CI on every push.

This is deliberately about the claims the app makes, not about JSON being valid.
If one of these fails, a screen somewhere is telling a clinician something untrue.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
d = json.loads((ROOT / "data" / "ntpf.json").read_text())
meta, rows = d["meta"], d["rows"]
fail = []


def check(ok, msg):
    if not ok:
        fail.append(msg)


check(meta["rows"] == len(rows), f"meta.rows {meta['rows']} != actual {len(rows)}")
check(meta["urgencyField"] is False, "meta claims an urgency field; the published data has none")
check(meta["newReturnField"] is False, "meta claims a new/return field; the published data has none")
check(bool(meta.get("published")) and bool(meta.get("extracted")), "provenance dates missing")

for r in rows:
    key = f"{r['specialty']}/{r['hospital']}/{r['ageGroup']}"
    check(sum(r["bands"].values()) == r["total"], f"{key}: bands do not sum to total")
    check(r["over12m"] == r["bands"]["12-18 Months"] + r["bands"]["18+ Months"], f"{key}: over12m mismatch")
    check(r["total"] > 0, f"{key}: zero total should not be published")
    check(abs(r["pctOver12m"] - r["over12m"] * 100 / r["total"]) < 0.06, f"{key}: pctOver12m mismatch")
    check(0 <= r["pctOver12m"] <= 100, f"{key}: percentage out of range")

seen = set()
for r in rows:
    key = (r["specialty"], r["hospital"], r["ageGroup"])
    check(key not in seen, f"duplicate row {key}")
    seen.add(key)

if fail:
    print(f"FAILED {len(fail)} check(s):")
    for f in fail[:20]:
        print("  -", f)
    sys.exit(1)
print(f"ok: {len(rows)} rows, {len({r['hospital'] for r in rows})} hospitals, "
      f"{len({r['specialty'] for r in rows})} specialties, published {meta['published']}")
