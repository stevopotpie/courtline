"""Courtline in-game model: the home team's chance to win from the score, the time left and the pregame spread.

Idea: the rest of a game behaves like a random walk. The final margin is roughly the current margin plus the
pregame expected margin scaled by the share of the game left, with noise that shrinks as time runs out:
    P(home wins) = F( a * margin / sqrt(tau + d)  +  b * expected_margin * sqrt(tau + d) )
where tau = seconds left / 2880 and F is the logistic function. a and b are fitted on real game states.

Data: hoopR-nba-data play by play (ESPN) and Odds API closing spreads, 2020 to 2026.
Trained once and saved to data/live_model.json (the daily site build reuses it; rerun after a season ends).
Usage: python3 -I live_train.py HOOPR_DIR REPO_DIR
"""
import glob, json, math, os, sys
from datetime import datetime, timezone
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression

H, REPO = sys.argv[1], sys.argv[2]
D_ = 0.002   # about 6 seconds, keeps the end of the game finite

lines = pd.read_parquet(os.path.join(H, "nba/betting_lines/closing_lines_odds_api.parquet"))
lines["game_id"] = lines.game_id.astype(int)
mu = dict(zip(lines.game_id, -lines.home_point))

parts = []
for f in sorted(glob.glob(os.path.join(H, "nba/pbp/parquet/play_by_play_20*.parquet"))):
    p = pd.read_parquet(f, columns=["game_id", "season", "season_type", "period_number", "clock_minutes", "clock_seconds", "home_score", "away_score"])
    p = p[p.season_type.isin([2, 3])]
    p["game_id"] = p.game_id.astype(int)
    p = p[p.game_id.isin(mu)]
    parts.append(p)
P = pd.concat(parts, ignore_index=True)
P["clock"] = pd.to_numeric(P.clock_minutes, errors="coerce") * 60 + pd.to_numeric(P.clock_seconds, errors="coerce")
P = P.dropna(subset=["clock"])
P["t"] = np.where(P.period_number <= 4, (4 - P.period_number) * 720 + P.clock, P.clock)   # overtime: seconds left in the OT period
P["margin"] = P.home_score - P.away_score

final = P.sort_values(["game_id", "period_number", "t"], ascending=[True, True, False]).groupby("game_id").tail(1)
final = final[final.margin != 0]
win = dict(zip(final.game_id, (final.margin > 0).astype(int)))
P = P[P.game_id.isin(win)].copy()
P["win"] = P.game_id.map(win)
P["mu"] = P.game_id.map(mu)
P = P.drop_duplicates(["game_id", "period_number", "t", "margin"])
P = P[P.t >= 0]


def feats(df):
    tau = df.t / 2880 + D_
    return np.column_stack([df.margin / np.sqrt(tau), df.mu * np.sqrt(tau)])


def calib(pred, y, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (pred >= lo) & (pred < hi) if hi < 1 else (pred >= lo)
        if m.sum():
            rows.append(dict(bin=f"{int(lo * 100)}–{int(hi * 100)}%", states=int(m.sum()), predicted=round(float(pred[m].mean()), 3), actual=round(float(y[m].mean()), 3)))
    return rows


test_season = int(P.season.max())
tr, te = P[P.season < test_season], P[P.season == test_season]
m = LogisticRegression(fit_intercept=False, C=1e6, max_iter=1000).fit(feats(tr), tr.win)
pt = m.predict_proba(feats(te))[:, 1]
brier = float(np.mean((pt - te.win) ** 2))
pre = te.groupby("game_id").head(1)
brier_pre = float(np.mean((m.predict_proba(feats(pre))[:, 1] - pre.win) ** 2))
by_q = []
for q, lab in ((1, "1st quarter"), (2, "2nd quarter"), (3, "3rd quarter"), (4, "4th quarter")):
    x = te[te.period_number == q]
    px = m.predict_proba(feats(x))[:, 1]
    by_q.append(dict(quarter=lab, states=int(len(x)), brier=round(float(np.mean((px - x.win) ** 2)), 4),
                     accuracy=round(float(np.mean((px >= 0.5) == (x.win == 1))), 3)))
test = dict(season=f"{test_season - 1}–{str(test_season)[2:]}", games=int(te.game_id.nunique()), states=int(len(te)), brier=round(brier, 4),
            brier_tip=round(brier_pre, 4), calibration=calib(pt, te.win.values), by_quarter=by_q)

full = LogisticRegression(fit_intercept=False, C=1e6, max_iter=1000).fit(feats(P), P.win)
a, b = (float(v) for v in full.coef_[0])
out = dict(built_utc=datetime.now(timezone.utc).isoformat(), a=round(a, 5), b=round(b, 5), d=D_,
           games=int(P.game_id.nunique()), states=int(len(P)), seasons=f"{int(P.season.min()) - 1}–{str(int(P.season.max()))[2:]}",
           test=test, formula="P(home wins) = 1 / (1 + exp(-(a * margin / sqrt(tau + d) + b * expected_margin * sqrt(tau + d)))), tau = seconds left / 2880")
os.makedirs(os.path.join(REPO, "data"), exist_ok=True)
json.dump(out, open(os.path.join(REPO, "data", "live_model.json"), "w"), indent=1)
print(f"a={a:.4f} b={b:.4f} | {out['games']} games, {out['states']:,} states | test {test['season']}: brier {test['brier']} (at tip {test['brier_tip']})")
for r in test["calibration"]:
    print(r)
print(by_q)
