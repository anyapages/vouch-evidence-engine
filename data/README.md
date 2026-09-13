# What this data is, and what it will not support

Source: **NTPF outpatient waiting list, hospital by specialty.** Published monthly.
Archive used: **2026-07-30.** Extracted: **2026-08-22**, by `scripts/build_dataset.py`.

NTPF stopped publishing this as a downloadable file in 2022. The figures are still
public, but only inside an interactive report. `scripts/ntpf.py` talks to the same
query endpoint the report's own browser session uses, so these are the published
numbers rather than an estimate of them. Nothing is authenticated and nothing is
scraped from a login.

`ntpf.json` holds 734 rows: 44 hospitals, 58 specialties, split Adult and Child, outpatient lists only.

## The band trap. Read this before doing arithmetic.

The four bands (`0-6`, `6-12`, `12-18`, `18+ Months`) are **time already waited by
people currently on the list.** They are not time remaining, and they are not the
wait a new patient should expect.

Two consequences, both of which have to hold in code and in copy:

1. **You cannot convert bands into a number of weeks.** The top band is open ended.
   A hospital whose median sits in `18+` has a median of "at least 18 months" and no
   arithmetic recovers more than that. Anything reported as "22 weeks" is invented.
2. **A population band is not a personal prediction.** It describes who is queuing
   now, not what happens to this patient.

We publish the share of a list waiting over 12 months, which the bands do support,
and we say that is what it is.

## Fields the source does not have

- **No urgency or priority field.** This is why the API refuses `assign_urgency`.
- **No new versus return distinction.**
- **No referral acceptance criteria.** Whether a hospital takes this referral at all
  is decided locally and is not in here.
- **No travel, transport, or catchment information.**

## The ordering moves, and the app has to say so

`scripts/stability.py` pulled the last 13 monthly archives for adult endocrinology
(`data/raw/stability_Endocrinology.json`). Hospitals with at least 200 people on the
list, which is where a share stops being noise.

- The worst-ranked hospital was the **same in 13 of 13 archives**. Its share waiting
  over a year rose from 72.7% to 76.8%, up in 11 of 12 months.
- The gap between best and worst never fell below **73 percentage points**.
- But the **fastest hospital changed 6 times in 12 transitions.** Kendall tau between
  consecutive months averages 0.923. The broad order is fairly stable; the top is not.
- Individual hospitals swing hard: one fell 11 places in a year, another rose 11.

So: "this is not a bad month, it has been like this for 13 months" is earned. "This
hospital is the fastest" is not. Treat the ordering as indicative, not settled, and
make the screen say so.

**One caveat that constrains our own copy:** the hospital showing 0% in July 2026
appears in only 3 of 13 archives at the 200 threshold. It is a small list that drops
in and out. Never describe it as consistently fastest.

## Small lists

Below 100 people a percentage jumps around on a handful of patients. Those rows are
flagged `lowVolume` and should be shown with a caution rather than ranked on quietly.

## Files

| File | What it is |
| --- | --- |
| `ntpf.json` | what the app serves, rebuilt by `scripts/build_dataset.py` |
| `raw/ntpf_hospital_specialty_2026-07-30.csv` | the same rows, flat, for reading in a spreadsheet |
| `raw/ntpf_raw_2026-07-30.json` | the undecoded response, kept so a decode bug is provable |
| `raw/stability_Endocrinology.json` | 13 archives of shares, the basis of the section above |
| `raw/archive_dates.json` | every archive date the report exposes |


## What Ireland's regulator says about this gap

Independent support for the product's premise, from an Irish source rather than
our own reasoning or NHS audit figures. HIQA, *Report and Recommendations on
Patient Referrals from General Practice to Outpatient and Radiology Services,
including the National Standard for Patient Referral Information*:

- **The gap Vouch fills, named as a benefit GPs should have:** "GPs will benefit
  from improved information relating to the services provided including waiting
  times."
- **Why that information is hard to get:** "there is limited collection and
  reporting of data relating to the patient referral pathway... at best gives
  only a partial picture of waiting times for outpatient services."
- **The stakes, in the regulator's words rather than ours:** waiting times "of
  well over a year for access to some services in some hospitals... Such long
  waiting times are unacceptable and unsafe."
- **Variation between providers is not our invention:** "Significant variations
  also exist in access between" services.
- **Clinician time:** the report expects the time GPs spend processing referrals
  to be reduced by better information and clearer routes.

Two things this does and does not license. It lets us stop asserting that the
information gap and the variation are real, because the regulator says so, and
it lets the word "unsafe" be quoted rather than claimed. It does not license any
claim that Vouch shortens waits, and the report predates the NTPF file we use,
so it is context for the problem, never a source for a figure on screen.


## Does the finding replicate? A second specialty says: partly

`stability.py` was run for a second specialty on 2 September 2026, because a
pattern found in one is a coincidence until it is tried in another. Cardiology
was chosen for two reasons: 29 hospitals carry a list of 200 or more, and it is
one half of the ambiguity pair the demo is built on.

| | Endocrinology | Cardiology |
|---|---|---|
| Archives | 13 | 13 |
| Hospitals present throughout | 20 | 29 |
| Same hospital worst every month | **13 of 13** | **7 of 13** |
| Median rank swing across the window | 4 of 20 places | 6 of 29 places |
| Median best-to-worst spread | **74 points** | **46 points** |

**What does not replicate, and the screen must not claim it does.** "The bottom
never moved" is true of Endocrinology and false as a general statement. In
Cardiology the worst hospital changes about half the time, and one hospital
moved 23 of 29 places across the window. So a stable ordering is a property of
some specialties, not of the data as a whole, and anything on screen that
implies otherwise is overclaiming from a single case.

**What does replicate, and it is the more important claim anyway.** The spread
is enormous in both, 74 points and 46 points at the median, and it is present in
every one of the 26 archives examined. The product's premise never depended on
the ordering being stable. It depends on the gap being large and invisible at
the moment of referral, and that holds in both specialties.

There is also a usable secondary result: Cardiology churns more than
Endocrinology, which is itself an argument for showing the publication date
beside every figure rather than presenting a ranking as settled.

## Northern Ireland: `ni.json`, a second source, not a second copy

Source: **Department of Health NI, outpatient waiting times, HSC Trust by
specialty.** Published quarterly. Quarter used: **2026-06-30**, released
**2026-09-03**. Extracted by `scripts/ni.py` from the Department's workbook
(SHA-256 recorded in `meta.workbookSha256`); the quarter's rows are also in
`raw/ni_outpatients_2026-06-30.csv` so a reviewer can diff them.

`ni.json` holds 234 rows: five Trusts (plus one row the Department publishes as
"DPC", carried as published and labelled as not a Trust), 90 specialties, no age
split. The bands are **weeks already waited**, thirteen of them, and they sum to
the published total on every row or the build refuses to write. "Over 52 weeks"
is the top five bands, which the source supports; nothing here is converted to
an expected wait.

**What it will not support.** The Department publishes no hospital sites, so
this cannot say which hospital inside a Trust. It is served on its own screen,
behind `VOUCH_NI`, and never merged with `ntpf.json`. The two-queues finding was
measured on Irish letters against the NTPF file; it has not been measured on
Northern Ireland letters and the screen says so. The Department's caveats
(possible duplicate records in three Trusts, Community Paediatrics under
review, some Ophthalmology waits captured as day cases) travel in `meta.caveats`
and are rendered, not footnoted.
