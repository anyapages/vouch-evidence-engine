"""Read the NTPF outpatient waiting list out of the state's published Power BI report.

NTPF stopped publishing hospital-by-specialty waiting lists as a downloadable file
in 2022. The figures are still public, but only inside an interactive report. This
module talks to the same query endpoint the report's own browser session uses, so
the numbers here are the published numbers, not an estimate of them.

Nothing here is authenticated. The resource key below is the public report's key,
visible to anyone who opens the report. Be polite: sleep between archive pulls.
"""
import json
import subprocess

HOST = "https://wabi-north-europe-o-primary-api.analysis.windows.net/public/reports/querydata?synchronous=true"
KEY = "a0ca2b6e-d818-4bda-a39a-6d4eee1e4f18"
DS = "03415ab8-e1e7-453a-84a3-de1e5d8df302"
RID = "287a857e-dec8-46c2-b4f5-281a5775f635"
VID = "f05b6b361117cc4bb08e"

BANDS = ["0-6 Months", "6-12 Months", "12-18 Months", "18+ Months"]
# The two bands that mean "waiting longer than a year". Note these describe time
# ALREADY waited, not time remaining. See data/README.md before doing arithmetic.
LONG_BANDS = {"12-18 Months", "18+ Months"}


def col(prop):
    return {"Column": {"Expression": {"SourceRef": {"Source": "o"}}, "Property": prop}, "Name": "o." + prop}


def agg(prop):
    return {
        "Aggregation": {
            "Expression": {"Column": {"Expression": {"SourceRef": {"Source": "o"}}, "Property": prop}},
            "Function": 0,
        },
        "Name": f"Sum(o.{prop})",
    }


def on_archive_date(date):
    """Where-clause restricting a query to one published archive, e.g. 2026-07-30."""
    return [
        {
            "Condition": {
                "Comparison": {
                    "ComparisonKind": 0,
                    "Left": {"Column": {"Expression": {"SourceRef": {"Source": "o"}}, "Property": "ArchiveDate"}},
                    "Right": {"Literal": {"Value": f"datetime'{date}T00:00:00'"}},
                }
            }
        }
    ]


def query(select, where, window=30000, restart=None):
    """One SemanticQueryDataShapeCommand.

    `window` raises the row cap. The report's own default is 100, which silently
    truncates; 30000 comfortably covers a full archive. If `decode` returns a
    restart token, the result WAS truncated and you need to page.
    """
    q = {"Version": 2, "From": [{"Name": "o", "Entity": "OpenDataMaster", "Type": 0}], "Select": select}
    if where:
        q["Where"] = where
    primary = {"Window": {"Count": window}}
    if restart:
        primary["Window"]["RestartTokens"] = restart
    body = {
        "version": "1.0.0",
        "queries": [
            {
                "Query": {
                    "Commands": [
                        {
                            "SemanticQueryDataShapeCommand": {
                                "Query": q,
                                "Binding": {
                                    "Primary": {"Groupings": [{"Projections": list(range(len(select)))}]},
                                    "DataReduction": {"DataVolume": 4, "Primary": primary},
                                    "Version": 1,
                                },
                                "ExecutionMetricsKind": 1,
                            }
                        }
                    ]
                },
                "QueryId": "",
                "ApplicationContext": {"DatasetId": DS, "Sources": [{"ReportId": RID, "VisualId": VID}]},
            }
        ],
        "cancelQueries": [],
        "modelId": 1950463,
    }
    # curl rather than urllib: --data-binary @- sets Content-Length correctly, and
    # the endpoint returns 411 without it.
    p = subprocess.run(
        [
            "curl", "-s", "-m", "180", HOST, "-X", "POST",
            "-H", "Content-Type: application/json;charset=UTF-8",
            "-H", "X-PowerBI-ResourceKey: " + KEY,
            "-H", "User-Agent: Mozilla/5.0",
            "-H", "Accept: application/json",
            "--data-binary", "@-",
        ],
        input=json.dumps(body).encode(),
        capture_output=True,
    )
    return json.loads(p.stdout.decode(errors="replace"))


def decode(resp, ncols):
    """Unpack Power BI's DSR wire format into plain rows.

    DSR compresses hard and none of it is optional:
      C  the values actually present on this row
      R  bitmask, bit i set means "repeat column i from the previous row"
      Ø  bitmask, bit i set means "column i is null"
      DN names a ValueDict; an int in C is then an index into that dictionary
    Ignoring R alone shifts every repeated column and produces plausible, wrong rows.

    Returns (rows, restart_token). A non-null token means the result was truncated.
    """
    dsr = resp["results"][0]["result"]["data"]["dsr"]
    ds = (dsr.get("DS") or dsr.get("DataShapes"))[0]
    vd = ds.get("ValueDicts") or dsr.get("ValueDicts") or {}
    dm = ds["PH"][0]["DM0"]

    # A query for an archive that does not exist is answered with an empty DM0.
    # Indexing dm[0] for the column descriptors then raised IndexError, so a
    # perfectly ordinary "no such archive" was indistinguishable from a network
    # fault or a schema change. No rows is an answer, so return it as one.
    if not dm:
        return [], ds.get("RT")

    dicts = [None] * ncols
    for i, s in enumerate(dm[0].get("S", [])):
        if "DN" in s:
            dicts[i] = vd.get(s["DN"])

    prev = [None] * ncols
    out = []
    for row in dm:
        c = row.get("C", [])
        repeat = row.get("R", 0)
        nulls = row.get("Ø", 0)
        vals = [None] * ncols
        ci = 0
        for i in range(ncols):
            if nulls >> i & 1:
                vals[i] = None
                continue
            if repeat >> i & 1:
                vals[i] = prev[i]
                continue
            v = c[ci] if ci < len(c) else None
            ci += 1
            if dicts[i] is not None and isinstance(v, int):
                v = dicts[i][v]
            vals[i] = v
        prev = vals[:]
        out.append(vals)
    return out, ds.get("RT")


def to_int(a):
    return int(float(str(a).replace(",", "") or 0))


# --- Publication schedule -------------------------------------------------
#
# The dataset's `meta.published` currently holds the ARCHIVE date, which is the
# snapshot label inside the report, not the date the figures became public. NTPF
# publishes an archive on the second Friday of the FOLLOWING month. Anything that
# tells a clinician how current a number is has to use the publication date, and
# a refresh agent has to wake on that schedule rather than on the archive label.
#
# Kept as a pure function so it is testable without a network call.

import calendar
import datetime


def second_friday(year: int, month: int) -> datetime.date:
    """The second Friday of a given month."""
    first_weekday, _ = calendar.monthrange(year, month)
    # weekday(): Monday is 0, Friday is 4.
    first_friday = 1 + (4 - first_weekday) % 7
    return datetime.date(year, month, first_friday + 7)


def publication_date(archive_date) -> datetime.date:
    """The date an archive became public: the second Friday of the next month.

    `archive_date` is the snapshot label (a date or an ISO string such as
    "2026-07-30"), NOT a publication date. Returning a distinct value is the
    point: the two must never be conflated on screen.
    """
    if isinstance(archive_date, str):
        archive_date = datetime.date.fromisoformat(archive_date)
    year, month = archive_date.year, archive_date.month
    if month == 12:
        year, month = year + 1, 1
    else:
        month += 1
    return second_friday(year, month)


def archive_dates() -> list[str]:
    """Every archive label the report exposes, oldest first, as ISO strings.

    The label has to be asked for, never derived. The refresh used to construct
    it as the month-end, which is wrong: all 63 archives NTPF has published are
    Thursdays, so the month-end matched only in the months where the two
    coincide. Asking for a date that was never published returns no rows, which
    is a silent, confusing failure rather than a loud one.

    The last Thursday would be a better guess and is still a guess: the December
    2025 archive is labelled the 18th, not the 25th. There is no rule to infer,
    so this reads the list instead.

    The response is a grouping, not a row set, so the values arrive as epoch
    milliseconds under "G0" and `decode` (which reads "C") does not apply.
    """
    resp = query([col("ArchiveDate")], None, window=500)
    dm = resp["results"][0]["result"]["data"]["dsr"]["DS"][0]["PH"][0]["DM0"]
    out = {
        datetime.datetime.fromtimestamp(row["G0"] / 1000, datetime.timezone.utc).date().isoformat()
        for row in dm if "G0" in row
    }
    return sorted(out)
