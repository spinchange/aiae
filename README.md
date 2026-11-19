# aiae

A self-updating page tracking the **Aggregate Investor Allocation to Equities (AIAE)**, the share of investors' total holdings of equities, bonds and cash held in equities. It shows two versions:

- **Original AIAE**, compared with its full history since 1952.
- **Detrended AIAE**, the AIAE minus its trailing 20-year (80-quarter) average. This shows how stretched the reading is against recent norms rather than mid-century ones.

**Live page:** https://spinchange.github.io/aiae/

## Formula

```
AIAE = (NCBEILQ027S + FBCELLQ027S)
       / (NCBEILQ027S + FBCELLQ027S + BCNSDODNS + CMDEBT + FGSDODNS + SLGSDODNS + DODFFSWCMI)
```

All series come from the Federal Reserve's Z.1 Financial Accounts via [FRED](https://fred.stlouisfed.org/). Live FRED chart of the original: https://fred.stlouisfed.org/graph/?g=2178M

## How it updates

`.github/workflows/update.yml` runs every Tuesday, on demand from the Actions tab, and whenever the script or workflow changes. It runs `scripts/update.py`, which:

1. downloads the seven series (through the FRED API if the `FRED_API_KEY` secret is set, otherwise FRED's public CSV download);
2. rebuilds `data/aiae.json` (`[quarter, aiae_pct, detrended_pts]` rows);
3. writes `data/status.json` with the time of the check.

The workflow commits only when the data changes, plus a heartbeat about once a month. GitHub disables scheduled workflows in repos with no activity for 60 days, and the heartbeat prevents that. The page warns you if the last check is more than 21 days old.

The Fed publishes Z.1 quarterly, roughly 10 weeks after each quarter ends, so new data arrives around mid-March, June, September and December.

## Run locally

```
python scripts/update.py          # standard library only; set FRED_API_KEY to use the API
python -m http.server             # then open http://localhost:8000
```
