"""Pull NBA odds (spreads, totals, moneylines; US books) from The Odds API and push the snapshot to GitHub.

Lives next to fetch_odds.py in C:\\Users\\stsut\\Documents\\gridline and uses the same odds_key.txt and repo\\ clone.
Writes repo\\odds\\snapshots\\nba_odds_<UTC stamp>.json (same layout as the NFL snapshots) and pushes ONLY that file.
About 3 credits per pull. Usage: python fetch_nba_odds.py
"""
import json, os, re, subprocess, sys, urllib.request, urllib.parse
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, "repo")
LOG = os.path.join(HERE, "logs", "nba_odds_log.txt")


def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def read_keys():
    """odds_key.txt: accepts KEY=value or KEY: value lines; a bare first line is taken as the Odds API key."""
    keys = {}
    with open(os.path.join(HERE, "odds_key.txt"), encoding="utf-8-sig") as f:
        lines = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
    for l in lines:
        m = re.match(r"^([A-Za-z_]+)\s*[=:]\s*(.+)$", l)
        if m: keys[m.group(1).upper()] = m.group(2).strip().strip('"')
    if "ODDS_API_KEY" not in keys and lines and "=" not in lines[0] and ":" not in lines[0]:
        keys["ODDS_API_KEY"] = lines[0]
    return keys


def git(*args):
    r = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout.strip()


def main():
    keys = read_keys()
    api = keys.get("ODDS_API_KEY")
    if not api: log("no ODDS_API_KEY in odds_key.txt"); sys.exit(1)
    q = urllib.parse.urlencode({"apiKey": api, "regions": "us", "markets": "h2h,spreads,totals", "oddsFormat": "american", "dateFormat": "iso"})
    url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/odds?{q}"
    with urllib.request.urlopen(url, timeout=60) as r:
        games = json.load(r)
        used, left = r.headers.get("x-requests-used"), r.headers.get("x-requests-remaining")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%MZ")
    snap = {"sport": "basketball_nba", "pulled_utc": datetime.now(timezone.utc).isoformat(), "games": games}
    log(f"pulled {len(games)} NBA games | credits used {used}, remaining {left}")
    if not games: log("no games listed (off day or off season); nothing to push"); return

    # Bring the clone up to date FIRST so we never commit an old copy of the repo over newer work.
    git("fetch", "-q", "origin", "main")
    git("checkout", "-q", "main")
    git("reset", "-q", "--hard", "origin/main")          # the PC clone is only a drop box for odds; GitHub is the truth
    rel = os.path.join("odds", "snapshots", f"nba_odds_{stamp}.json")
    path = os.path.join(REPO, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snap, f)
    git("add", "-f", "--", rel)                          # only the new snapshot, never "add -A"; -f because .gitignore skips *.json
    git("commit", "-q", "-m", f"NBA odds snapshot {stamp}")
    token, user = keys.get("GITHUB_TOKEN"), "stevopotpie"
    if token:
        git("push", "-q", f"https://{user}:{token}@github.com/stevopotpie/gridline.git", "HEAD:main")
    else:
        git("push", "-q", "origin", "HEAD:main")
    log(f"pushed {rel}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"FAILED: {e}"); sys.exit(1)
