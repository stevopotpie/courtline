"""Courtline NBA odds puller for GitHub Actions.

Same pull as the PC script (fetch_nba_odds.py in Documents\\courtline): NBA moneylines, spreads and
totals from US books, about 3 credits. Writes odds/snapshots/nba_odds_<UTC stamp>.json in this repo.
The workflow (.github/workflows/odds.yml) commits and pushes.

The Odds API key comes from the ODDS_API_KEY repository secret. Standard library only.
Usage: python3 -I actions/fetch_nba_odds.py <odds folder>
"""
import json, os, sys, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"


def log(msg):
    print(f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S}Z {msg}", flush=True)


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: fetch_nba_odds.py <odds folder>")
    out = Path(sys.argv[1])
    key = os.environ.get("ODDS_API_KEY", "").strip()
    if not key:
        log("ERROR: the ODDS_API_KEY secret is not set (repo Settings > Secrets and variables > Actions).")
        sys.exit(1)

    q = urllib.parse.urlencode({"apiKey": key, "regions": "us", "markets": "h2h,spreads,totals",
                                "oddsFormat": "american", "dateFormat": "iso"})
    try:
        with urllib.request.urlopen(f"{API}?{q}", timeout=60) as r:
            games = json.load(r)
            used, left = r.headers.get("x-requests-used"), r.headers.get("x-requests-remaining")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300].replace(key, "***")
        log(f"ERROR: API returned {e.code}: {body}")
        sys.exit(1)
    except urllib.error.URLError as e:
        log(f"ERROR: could not reach The Odds API ({e.reason})")
        sys.exit(1)

    log(f"pulled {len(games)} NBA games | credits used {used}, remaining {left}")
    if not games:
        log("no games listed (off day or off season); nothing to save")
        return

    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%d_%H%MZ")
    snap = {"sport": "basketball_nba", "pulled_utc": now.isoformat(), "games": games}
    path = out / "snapshots" / f"nba_odds_{stamp}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snap), encoding="utf-8")
    log(f"saved {path}")

    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write(f"stamp={stamp}\n")


if __name__ == "__main__":
    main()
