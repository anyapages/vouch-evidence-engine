"""Precompute data/ambiguity.json: what an unresolved specialty costs, per hospital.

The rest of the field compares hospitals. This holds the hospital constant and asks a
different question: if a referral letter could plausibly be read as either of two
specialties, how far apart are those two lists at the same hospital on the same day?

That is the number the product exists to show, so it is computed here rather than in a
page, and CI re-derives it on every push.

THE PAIR LIST BELOW IS OUR CLINICAL JUDGEMENT, NOT A PUBLISHED STANDARD. No source
defines which specialties a GP referral is commonly ambiguous between; we wrote these
down from presentations where the choice is genuinely open at the point of referral.
It is the single most challengeable input here, which is why it is a visible constant
and not a heuristic. A clinician reviewing this should expect to add and remove rows.
"""
import json
import pathlib
import statistics

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Presentation -> the two specialties a referral could reasonably be addressed to.
PAIRS = [
    ("chest pain or breathlessness", "Cardiology", "Respiratory Medicine"),
    ("abdominal pain", "Gastro-Enterology", "General Surgery"),
    ("chronic joint pain", "Orthopaedics", "Rheumatology"),
    ("dizziness or vertigo", "Neurology", "Otolaryngology (ENT)"),
    ("skin lesion", "Dermatology", "Plastic Surgery"),
    ("pelvic or lower urinary symptoms", "Gynaecology", "Urology"),
    ("persistent cough", "Otolaryngology (ENT)", "Respiratory Medicine"),
    ("visual disturbance with headache", "Neurology", "Ophthalmology"),
    ("chronic pain, no surgical target", "Pain Relief", "Orthopaedics"),
    ("glycaemic and endocrine overlap", "Endocrinology", "Diabetes Mellitus"),
    ("groin or abdominal wall", "General Surgery", "Urology"),
    ("jaundice or upper abdominal", "Gastro-Enterology", "Hepato-Biliary Surgery"),
    ("leg pain or claudication", "Vascular Surgery", "General Surgery"),
    ("functional neurological symptoms", "Neurology", "Psychiatry"),
    # GI endoscopy is its own NTPF waiting list, not an outpatient clinic, so it has no
    # outpatient rows to compare against; the dyspepsia pair was removed with that fix.
    ("breast symptom", "Breast Surgery", "General Surgery"),
    ("multi-system inflammatory", "Rheumatology", "General Medicine"),
    ("palpitations or general decline", "Cardiology", "General Medicine"),
]

# Below this, a list's share is too volatile to compare against another list. Same floor
# the stability analysis uses; raising it drops pairs, it never invents them.
MIN_LIST = 40
WIDE = 20.0  # a gap we would call material on screen

d = json.loads((ROOT / "data" / "ntpf.json").read_text())
meta, rows = d["meta"], d["rows"]

by_key = {(r["hospital"], r["specialty"], r["ageGroup"]): r for r in rows}
age_groups = sorted({r["ageGroup"] for r in rows})

found = []
for presentation, a, b in PAIRS:
    for (hospital, specialty, age), row in by_key.items():
        if specialty != a:
            continue
        other = by_key.get((hospital, b, age))
        if other is None:
            continue
        if row["total"] < MIN_LIST or other["total"] < MIN_LIST:
            continue
        found.append(
            {
                "presentation": presentation,
                "hospital": hospital,
                "ageGroup": age,
                "a": {"specialty": a, "pctOver12m": row["pctOver12m"], "total": row["total"]},
                "b": {"specialty": b, "pctOver12m": other["pctOver12m"], "total": other["total"]},
                "gap": round(abs(row["pctOver12m"] - other["pctOver12m"]), 1),
            }
        )

found.sort(key=lambda f: f["gap"], reverse=True)
gaps = [f["gap"] for f in found]

out = {
    "meta": {
        "source": meta["source"],
        "archiveDate": meta["published"],
        "extracted": meta["extracted"],
        "minListSize": MIN_LIST,
        "wideGapThreshold": WIDE,
        "pairsConsidered": len(PAIRS),
        "pairListIsOurJudgement": True,
        "note": (
            "Gap is the difference in the share of each list that has already waited over "
            "twelve months. It is not a predicted wait and no arithmetic converts it to weeks."
        ),
    },
    "summary": {
        "pairsFound": len(found),
        "medianGap": round(statistics.median(gaps), 1) if gaps else None,
        "meanGap": round(statistics.fmean(gaps), 1) if gaps else None,
        "maxGap": max(gaps) if gaps else None,
        "wideGaps": sum(1 for g in gaps if g >= WIDE),
        "ageGroups": age_groups,
    },
    "pairs": found,
}

(ROOT / "data" / "ambiguity.json").write_text(json.dumps(out, indent=1) + "\n")
s = out["summary"]
print(
    f"ok: {s['pairsFound']} same-hospital ambiguous pairs, median {s['medianGap']} pts, "
    f"{s['wideGaps']} at or above {WIDE} pts, max {s['maxGap']} pts"
)
