"""Courtline v0: does a simple team-form model add anything to NBA closing spreads and totals?
Data: hoopR-nba-data (ESPN team box scores, schedules) and its Odds API closing lines (2020-21 to 2025-26).
Usage: python3 -I backtest_v0.py HOOPR_DIR"""
import sys, os, glob, numpy as np, pandas as pd
from sklearn.linear_model import Ridge
H = sys.argv[1]
tb = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(os.path.join(H, "nba/team_box/parquet/team_box_20*.parquet")))])
tb = tb[tb.season_type.isin([2, 3])].copy()
tb["game_date"] = pd.to_datetime(tb.game_date)
tb["poss"] = tb.field_goals_attempted - tb.offensive_rebounds + tb.turnovers + 0.44 * tb.free_throws_attempted
g = tb.sort_values(["game_date", "game_id"])
# pregame EWMA form per team (half life 12 games), regressed 30% to league between seasons
HL = 12; A = 1 - 0.5 ** (1 / HL)
state, last, rows = {}, {}, []
LG = {"ortg": 112.0, "drtg": 112.0, "pace": 99.0}
for gid, grp in g.groupby("game_id", sort=False):
    if len(grp) != 2: continue
    pre = {}
    for r in grp.itertuples():
        s = state.setdefault(r.team_abbreviation, dict(LG))
        if last.get(r.team_abbreviation, (r.season, None))[0] != r.season:
            for k in s: s[k] += 0.3 * (LG[k] - s[k])
        prev = last.get(r.team_abbreviation, (None, None))[1]
        rest = (r.game_date - prev).days if prev is not None else 7
        pre[r.team_home_away] = dict(team=r.team_abbreviation, rest=min(rest, 7), **s)
    if set(pre) != {"home", "away"}: continue
    h, a = grp[grp.team_home_away == "home"].iloc[0], grp[grp.team_home_away == "away"].iloc[0]
    rows.append(dict(game_id=gid, season=h.season, date=h.game_date, home=h.team_abbreviation, away=a.team_abbreviation,
                     hs=h.team_score, as_=a.team_score, **{f"h_{k}": v for k, v in pre["home"].items() if k != "team"},
                     **{f"a_{k}": v for k, v in pre["away"].items() if k != "team"}))
    poss = (h.poss + a.poss) / 2
    for r, opp in ((h, a), (a, h)):
        s = state[r.team_abbreviation]
        s["ortg"] += A * (100 * r.team_score / poss - s["ortg"]); s["drtg"] += A * (100 * opp.team_score / poss - s["drtg"]); s["pace"] += A * (poss - s["pace"])
        last[r.team_abbreviation] = (r.season, r.game_date)
G = pd.DataFrame(rows)
L = pd.read_parquet(os.path.join(H, "nba/betting_lines/closing_lines_odds_api.parquet"))
L["game_id"] = L.game_id.astype(int)
G = G.merge(L[["game_id", "home_point", "over_under"]], on="game_id")
G["margin"] = G.hs - G.as_; G["total"] = G.hs + G.as_
G["v_margin"] = -G.home_point; G["v_total"] = G.over_under
G["d_net"] = (G.h_ortg - G.h_drtg) - (G.a_ortg - G.a_drtg)
G["h_b2b"] = (G.h_rest == 1).astype(int); G["a_b2b"] = (G.a_rest == 1).astype(int); G["rest_diff"] = G.h_rest - G.a_rest
G["pace_sum"] = G.h_pace + G.a_pace; G["off_sum"] = G.h_ortg + G.a_ortg; G["def_sum"] = G.h_drtg + G.a_drtg
G["exp_total"] = (G.h_pace + G.a_pace) / 2 * ((G.h_ortg + G.a_drtg) / 2 + (G.a_ortg + G.h_drtg) / 2) / 100
FS = ["d_net", "h_b2b", "a_b2b", "rest_diff"]
FT = ["exp_total", "pace_sum", "off_sum", "def_sum", "h_b2b", "a_b2b"]
print("games with closing lines:", len(G), "| seasons", sorted(G.season.unique()))
out = []
for season in sorted(G.season.unique())[2:]:
    tr, te = G[G.season < season], G[G.season == season].copy()
    te["sm"] = te.v_margin + Ridge(50).fit(tr[FS], tr.margin - tr.v_margin).predict(te[FS])
    te["tm"] = te.v_total + Ridge(50).fit(tr[FT + ["v_total"]], tr.total - tr.v_total).predict(te[FT + ["v_total"]])
    out.append(te)
P = pd.concat(out)
def rec(pred, line, act):
    pk = pred > line; cv = act - line; push = cv == 0; w = np.where(pk, cv > 0, cv < 0)[~push]; return f"{w.sum()}-{(~w).sum()} ({w.mean():.1%})" if len(w) else "n/a"
print("test seasons", sorted(P.season.unique()), "games", len(P))
print("Vegas avg miss: margin %.2f, total %.2f | model: margin %.2f, total %.2f" % ((P.v_margin - P.margin).abs().mean(), (P.v_total - P.total).abs().mean(), (P.sm - P.margin).abs().mean(), (P.tm - P.total).abs().mean()))
for e in (0.5, 1, 1.5, 2, 3):
    s = P[(P.sm - P.v_margin).abs() >= e]; t = P[(P.tm - P.v_total).abs() >= e]
    print(f"edge {e}+: spread {rec(s.sm.values, s.v_margin.values, s.margin.values)} [{len(s)}] | total {rec(t.tm.values, t.v_total.values, t.total.values)} [{len(t)}]")
for nm, m in [("home b2b", P.h_b2b == 1), ("away b2b", P.a_b2b == 1), ("both b2b", (P.h_b2b == 1) & (P.a_b2b == 1))]:
    x = P[m]; print(f"{nm}: n={len(x)} home margin vs line {(x.margin - x.v_margin).mean():+.2f}, total vs line {(x.total - x.v_total).mean():+.2f}")
