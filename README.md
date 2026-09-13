# Vouch Evidence Engine

[![verify](https://github.com/anyapages/vouch-evidence-engine/actions/workflows/verify.yml/badge.svg)](https://github.com/anyapages/vouch-evidence-engine/actions/workflows/verify.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![data: NTPF](https://img.shields.io/badge/data-NTPF%20open%20data-1A3FAE)](https://www.ntpf.ie/home/outpatient.htm)
[![data: DoH NI](https://img.shields.io/badge/data-Dept%20of%20Health%20NI-1A3FAE)](https://www.health-ni.gov.uk/publications/northern-ireland-waiting-time-statistics-outpatient-waiting-times-june-2026)
[![licence: MIT](https://img.shields.io/badge/licence-MIT-555)](LICENSE)

The first badge is the only one that means anything: it is green because the
figures in `data/` re-derive from the published sources on every push, and it
goes red when one of them stops being true.

> **This repository is Vouch's public evidence layer.** It reproduces the
> published waiting-list calculations the Vouch demo shows. It does **not**
> contain the Vouch application, its model prompts, its referral-reading or
> disagreement logic, its evaluation corpus, any clinical decision-making code,
> or any patient data.

Open infrastructure for reproducible healthcare waiting-list evidence, for the
island of Ireland.

Waiting-list figures are published. Reproducing them is another matter: the
Republic's are inside an interactive report rather than a file, the North's are
a quarterly workbook whose band scheme changed mid-series, and both are easy to
quote in a way the source does not support. This repository is the derivation,
end to end, so that a figure quoted from these sources can be checked by
somebody who does not trust the person quoting it.

```bash
git clone https://github.com/anyapages/vouch-evidence-engine
cd vouch-evidence-engine
python3 scripts/check_data.py
python3 scripts/build_ambiguity.py
```

Both print what they found. Nothing is fetched; the committed files are the
ones the checks run against.

## Correction, 13 September 2026

The first version of `data/ntpf.json` combined three NTPF waiting lists (outpatient,
inpatient/day case and GI endoscopy) while describing itself as outpatient. The
report's fact table carries all three lists, and the list type sits on a related table
the extraction did not filter on. `scripts/ntpf.py` now filters to outpatient, and the
adult total matches NTPF's published outpatient file (610,700 at 30 July 2026).

What moved: 808 rows became 734, GI Endoscopy is no longer listed as a specialty, and
the same-hospital ambiguity summary is now 230 pairs, median 9.4 points, 52 at or
above 20 points, maximum 73.1 (it was 269, 8.9, 53 and 73.5).

What did not move: Letterkenny ENT, 1 of 784 waiting over a year, and neurology, 542
of 1,057; Cavan endocrinology, 0 of 231; St. Columcille's, 6,938 of 9,032; and the
endocrinology stability finding, the same hospital last in 13 of 13 archives with the
gap never below 72.7 points.

## What is here

| Path | What it is |
|---|---|
| `data/ntpf.json` | Republic of Ireland, outpatient waiting list, **hospital x specialty**. 734 rows, 44 hospitals, 58 specialties, outpatient lists only. Archive 2026-07-30, published 2026-08-14. |
| `data/ni.json` | Northern Ireland, outpatient waiting times, **HSC Trust x specialty**. 234 rows, five Trusts, 90 specialties. Position 30 June 2026, published 3 September 2026. |
| `data/raw/` | The bytes each file was built from, committed so the derivation can be diffed rather than trusted. |
| `data/README.md` | **Read this before doing arithmetic on any of it.** What the bands are, and the three things they cannot tell you. |
| `scripts/build_dataset.py` | Republic: query the published report, fold rollup rows out, write `ntpf.json`. |
| `scripts/ni.py` | North: read the Department's workbook, refuse to write unless all thirteen bands sum to the published total on every row. |
| `scripts/check_data.py` | The invariants the served file must hold. |
| `scripts/build_ambiguity.py` | One derivation the sources do not publish: how far apart two plausible specialties are, at the same hospital. |
| `scripts/stability.py` | The same question across thirteen monthly archives. |

## The two levels are not the same level, and are never merged

The Republic publishes by **hospital**. The Department of Health publishes by
**HSC Trust**, and there are five, with no hospital sites in the file. Any
comparison across the border is a comparison of two different grains. The two
files stay separate here for that reason, and anything built on them should say
which grain it is showing.

## What this is not

It is not medical advice, not a referral system, and not a prediction. The
bands are time **already waited by people currently on a list**. They are not
time remaining, they do not convert into a number of weeks, and a population
band is not a personal prediction. The source carries no urgency field, no new
versus return distinction, no acceptance criteria and no travel information, so
nothing derived from it can account for any of those. `data/README.md` sets out
each of these with the consequence that follows from it.

## The reading is measured elsewhere, and the results are open too

This repository is the evidence half: the published figures and the derivation
that produces them. The other half, how a referral letter is read and what the
routing rule costs, is measured separately and published at
**<https://vouch.aqta.ai/evaluation>**.

That page is worth reading alongside this one, because it is the same discipline
applied to the models rather than to the data: 153 invented letters, five
samples from every reader on every letter, held-out split only, and both a
lenient and a strict score so the scoring rule cannot do the arguing. Three
readers were tested and two serve: `gpt-4.1-mini`, `gemini-3.6-flash`, and
NVIDIA Nemotron 3 Super served by NVIDIA NIM as an independent third opinion,
brought in to check whether the disagreements were real or an artefact of one
model family. The third has never answered a clinical request and is not in the
serving path.

No corpus, prompts or model code are in this repository, and none are planned
here. The figures are what this repository is for.

## The boundary

This repository is the evidence layer: the published sources, the derivation,
the provenance and the checks. It is open because a figure nobody can reproduce
is a claim rather than evidence.

The application that reads a referral letter, compares two independent readings,
asks a clinician when they differ and refuses to choose a destination is
**proprietary** and is not here. Nor is the evaluation corpus, the prompts, or
any clinical workflow.

## Sources

- **National Treatment Purchase Fund**, outpatient waiting list by hospital and
  specialty. <https://www.ntpf.ie/> Published monthly, on the second Friday of
  the month after the archive it describes. Since 2022 it is served from an
  interactive report rather than a downloadable file; `scripts/ntpf.py` talks to
  the same public query endpoint the report's own browser session uses. Nothing
  is authenticated and nothing is scraped from behind a login.
- **Department of Health, Northern Ireland**, outpatient waiting times by HSC
  Trust and specialty, quarterly.
  <https://www.health-ni.gov.uk/publications/northern-ireland-waiting-time-statistics-outpatient-waiting-times-june-2026>
  The workbook's own caveats travel in `data/ni.json` under `meta.caveats` and
  should be shown wherever its figures are.

Both are public statistical publications and remain subject to their
publishers' terms. The code here is Apache-2.0; the figures belong to the
bodies that published them.

## Provenance, and how a number stops being true

Every file records the archive or quarter it describes, the day it was
released, the day it was extracted, the script that built it, and for Northern
Ireland the SHA-256 of the workbook it came from. The publication date is
**derived**, never read off the archive label, because the two are different
questions and conflating them serves last month's figures as current.
`scripts/tests/test_publication_date.py` pins that derivation, including the
December rollover and the months whose first day is itself a Friday.

CI re-derives `data/ambiguity.json` on every push and fails if the committed
file and the recomputed one differ.

---

Built in Ireland during the TechIreland National AI Challenge 2026. No patient
data is used anywhere in this repository; it contains published aggregate
statistics only.
