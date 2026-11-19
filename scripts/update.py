#!/usr/bin/env python3
"""Fetch Fed Z.1 series from FRED and rebuild data/aiae.json.

AIAE (Aggregate Investor Allocation to Equities):
    (NCBEILQ027S + FBCELLQ027S) /
    (NCBEILQ027S + FBCELLQ027S + BCNSDODNS + CMDEBT + FGSDODNS + SLGSDODNS + DODFFSWCMI)

Detrended AIAE: AIAE minus its trailing 80-observation (20-year) average.

Uses the FRED API when FRED_API_KEY is set, otherwise FRED's public CSV download.
Standard library only.
"""
import csv
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SERIES = {
    "nonfin_equities": "NCBEILQ027S",
    "fin_equities": "FBCELLQ027S",
    "nonfin_corp_debt": "BCNSDODNS",
    "household_debt": "CMDEBT",
    "federal_debt": "FGSDODNS",
    "state_local_debt": "SLGSDODNS",
    "rest_of_world_debt": "DODFFSWCMI",
}
WINDOW = 80  # observations in the trailing average (80 quarters = 20 years)
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "aiae.json"
STATUS = ROOT / "data" / "status.json"
UA = {"User-Agent": "aiae-updater (github.com/spinchange/aiae)"}


def get(url, tries=4):
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read().decode("utf-8")
        except Exception as e:  # network hiccup or throttling: back off and retry
            if attempt == tries - 1:
                raise
            print(f"  retry {attempt + 1} after error: {e}", file=sys.stderr)
            time.sleep(5 * (attempt + 1))


def fetch(series_id, api_key):
    """Return {date 'YYYY-MM-DD': float} for one series."""
    if api_key:
        q = urllib.parse.urlencode({"series_id": series_id, "api_key": api_key, "file_type": "json"})
        obs = json.loads(get(f"https://api.stlouisfed.org/fred/series/observations?{q}"))["observations"]
        pairs = ((o["date"], o["value"]) for o in obs)
    else:
        text = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}")
        pairs = (tuple(row[:2]) for row in list(csv.reader(io.StringIO(text)))[1:])
    out = {}
    for d, v in pairs:
        try:
            out[d] = float(v)
        except ValueError:  # "." marks a missing value
            pass
    if not out:
        raise RuntimeError(f"{series_id}: no observations returned")
    return out


def quarter_label(d):
    y, m, _ = d.split("-")
    return f"{y}Q{(int(m) - 1) // 3 + 1}"


def compute(data):
    s = list(data.values())
    dates = sorted(d for d in s[0] if all(d in x for x in s))
    rows, vals = [], []
    for d in dates:
        eq = data["nonfin_equities"][d] + data["fin_equities"][d]
        debt = sum(data[k][d] for k in SERIES if k.endswith("_debt"))
        a = eq / (eq + debt) * 100
        vals.append(a)
        dt = a - sum(vals[-WINDOW:]) / WINDOW if len(vals) >= WINDOW else None
        rows.append([quarter_label(d), round(a, 2), None if dt is None else round(dt, 2)])
    return rows


def main():
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    print(f"Source: {'FRED API' if api_key else 'FRED CSV download (no FRED_API_KEY set)'}")
    data = {}
    for key, sid in SERIES.items():
        data[key] = fetch(sid, api_key)
        print(f"  {sid}: {len(data[key])} observations, latest {max(data[key])}")
    rows = compute(data)
    if len(rows) < WINDOW + 20:
        raise RuntimeError(f"Only {len(rows)} combined observations; refusing to overwrite data")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    old = json.loads(DATA.read_text()) if DATA.exists() else {}
    changed = old.get("rows") != rows
    DATA.parent.mkdir(exist_ok=True)
    if changed:
        DATA.write_text(json.dumps({
            "latest_quarter": rows[-1][0],
            "data_updated": now,
            "window_quarters": WINDOW,
            "series": SERIES,
            "columns": ["quarter", "aiae_pct", "detrended_pts"],
            "rows": rows,
        }, separators=(",", ":")) + "\n")
    STATUS.write_text(json.dumps({"last_checked": now, "latest_quarter": rows[-1][0]}) + "\n")

    last = rows[-1]
    print(f"Latest {last[0]}: AIAE {last[1]:.1f}%, detrended {last[2]:+.1f} pts. "
          f"{'Data changed.' if changed else 'No change.'}")
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"changed={'true' if changed else 'false'}\n")


if __name__ == "__main__":
    main()
