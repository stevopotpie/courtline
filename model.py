"""Courtline: team form model, current ratings, projections against the market, and a graded season log.

Builds on backtest_v0.py. Every run recomputes everything from source data, so the output is reproducible:
  - hoopR-nba-data (ESPN box scores and schedules; Odds API closing lines for 2020-21 to 2025-26)
  - odds/snapshots/*.json in this repo (our own daily pulls from The Odds API, 2026-27 season on)

The model is trained only on seasons before the current one, so every 2026-27 projection is out of sample.
For each current-season game, the market number is the consensus (median across books) from the last pull
taken before tip. Projections are graded against that number once the game is final.

Usage: python3 -I model.py HOOPR_DIR REPO_DIR    (writes REPO_DIR/data/courtline.json and predictions.csv)
"""
import glob, json, math, os, sys
from datetime import datetime, timezone, timedelta
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge

H, REPO = sys.argv[1], sys.argv[2]
OUT = os.path.join(REPO, "data")
os.makedirs(OUT, exist_ok=True)
NOW = datetime.now(timezone.utc)
CURRENT = 2027                      # season label = year the season ends (2027 = 2026-27)
HL = 12; A = 1 - 0.5 ** (1 / HL)    # EWMA half life, in games
REG = 0.3                           # regression toward league average between seasons
LG = {"ortg": 112.0, "drtg": 112.0, "pace": 99.0}
SPREAD_LEAN, TOTAL_LEAN = 1.0, 1.5  # points of disagreement with the market that count as a lean
NAME_FIX = {"Los Angeles Clippers": "LA Clippers"}

# ---------------------------------------------------------------- box scores and team form
files = sorted(glob.glob(os.path.join(H, "nba/team_box/parquet/team_box_20*.parquet")))
tb = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
tb = tb[tb.season_type.isin([2, 3])].copy()
tb["game_date"] = pd.to_datetime(tb.game_date)
tb["poss"] = tb.field_goals_attempted - tb.offensive_rebounds + tb.turnovers + 0.44 * tb.free_throws_attempted
g = tb.sort_values(["game_date", "game_id"])

TEAM = {}   # abbreviation -> display name, latest seen
state, last, rows, recent = {}, {}, [], {}
for gid, grp in g.groupby("game_id", sort=False):
    if len(grp) != 2:
        continue
    pre = {}
    for r in grp.itertuples():
        TEAM[r.team_abbreviation] = r.team_display_name
        s = state.setdefault(r.team_abbreviation, dict(LG))
        if last.get(r.team_abbreviation, (r.season, None))[0] != r.season:
            for k in s:
                s[k] += REG * (LG[k] - s[k])
        prev = last.get(r.team_abbreviation, (None, None))[1]
        rest = (r.game_date - prev).days if prev is not None else 7
        pre[r.team_home_away] = dict(team=r.team_abbreviation, rest=min(rest, 7), **s)
    if set(pre) != {"home", "away"}:
        continue
    h, a = grp[grp.team_home_away == "home"].iloc[0], grp[grp.team_home_away == "away"].iloc[0]
    rows.append(dict(game_id=int(gid), season=int(h.season), date=h.game_date, home=h.team_abbreviation, away=a.team_abbreviation,
                     hs=int(h.team_score), as_=int(a.team_score),
                     **{f"h_{k}": v for k, v in pre["home"].items() if k != "team"},
                     **{f"a_{k}": v for k, v in pre["away"].items() if k != "team"}))
    poss = (h.poss + a.poss) / 2
    for r, opp in ((h, a), (a, h)):
        s = state[r.team_abbreviation]
        s["ortg"] += A * (100 * r.team_score / poss - s["ortg"])
        s["drtg"] += A * (100 * opp.team_score / poss - s["drtg"])
        s["pace"] += A * (poss - s["pace"])
        last[r.team_abbreviation] = (r.season, r.game_date)
        if r.season == CURRENT:
            recent.setdefault(r.team_abbreviation, []).append(1 if r.team_score > opp.team_score else 0)

G = pd.DataFrame(rows)


def features(df):
    df = df.copy()
    df["d_net"] = (df.h_ortg - df.h_drtg) - (df.a_ortg - df.a_drtg)
    df["h_b2b"] = (df.h_rest == 1).astype(int)
    df["a_b2b"] = (df.a_rest == 1).astype(int)
    df["rest_diff"] = df.h_rest - df.a_rest
    df["pace_sum"] = df.h_pace + df.a_pace
    df["off_sum"] = df.h_ortg + df.a_ortg
    df["def_sum"] = df.h_drtg + df.a_drtg
    df["exp_total"] = (df.h_pace + df.a_pace) / 2 * ((df.h_ortg + df.a_drtg) / 2 + (df.a_ortg + df.h_drtg) / 2) / 100
    return df


G = features(G)
G["margin"] = G.hs - G.as_
G["total"] = G.hs + G.as_
FS = ["d_net", "h_b2b", "a_b2b", "rest_diff"]
FT = ["exp_total", "pace_sum", "off_sum", "def_sum", "h_b2b", "a_b2b"]

# ---------------------------------------------------------------- historical closing lines and the walk forward backtest
L = pd.read_parquet(os.path.join(H, "nba/betting_lines/closing_lines_odds_api.parquet"))
L["game_id"] = L.game_id.astype(int)
HG = G.merge(L[["game_id", "home_point", "over_under"]], on="game_id")
HG["v_margin"] = -HG.home_point
HG["v_total"] = HG.over_under

bt = []
for season in sorted(HG.season.unique())[2:]:
    tr, te = HG[HG.season < season], HG[HG.season == season].copy()
    te["sm"] = te.v_margin + Ridge(alpha=50).fit(tr[FS], tr.margin - tr.v_margin).predict(te[FS])
    te["tm"] = te.v_total + Ridge(alpha=50).fit(tr[FT + ["v_total"]], tr.total - tr.v_total).predict(te[FT + ["v_total"]])
    bt.append(te)
P = pd.concat(bt)


def wl(pred, line, act):
    side = np.sign(pred - line)
    res = np.sign(act - line) * side
    keep = (side != 0) & (res != 0)
    w = int((res[keep] > 0).sum()); l_ = int((res[keep] < 0).sum())
    return w, l_


thresholds = []
for e in (0.5, 1, 1.5, 2):
    s = P[(P.sm - P.v_margin).abs() >= e]
    t = P[(P.tm - P.v_total).abs() >= e]
    sw, sl = wl(s.sm.values, s.v_margin.values, s.margin.values)
    tw, tl = wl(t.tm.values, t.v_total.values, t.total.values)
    thresholds.append(dict(edge=e, spread_w=sw, spread_l=sl, total_w=tw, total_l=tl))

b2b = []
for nm, m in [("Home team on a back to back", P.h_b2b == 1),
              ("Road team on a back to back", P.a_b2b == 1),
              ("Both teams on a back to back", (P.h_b2b == 1) & (P.a_b2b == 1)),
              ("Neither team on a back to back", (P.h_b2b == 0) & (P.a_b2b == 0))]:
    x = P[m]
    se_t = (x.total - x.v_total).std() / math.sqrt(len(x))
    b2b.append(dict(label=nm, n=int(len(x)), margin_vs_line=round(float((x.margin - x.v_margin).mean()), 2),
                    total_vs_line=round(float((x.total - x.v_total).mean()), 2), total_se=round(float(se_t), 2)))

by_season = []
for season, x in HG.groupby("season"):
    lab = f"{season - 1}–{str(season)[2:]}"
    by_season.append(dict(season=lab, games=int(len(x)), home_margin=round(float(x.margin.mean()), 2),
                          home_line=round(float(x.v_margin.mean()), 2),
                          vegas_miss_margin=round(float((x.v_margin - x.margin).abs().mean()), 2),
                          vegas_miss_total=round(float((x.v_total - x.total).abs().mean()), 2)))

backtest = dict(
    games=int(len(P)), seasons=f"{P.season.min() - 1}–{str(P.season.max())[2:]}",
    vegas_miss_margin=round(float((P.v_margin - P.margin).abs().mean()), 2),
    vegas_miss_total=round(float((P.v_total - P.total).abs().mean()), 2),
    model_miss_margin=round(float((P.sm - P.margin).abs().mean()), 2),
    model_miss_total=round(float((P.tm - P.total).abs().mean()), 2),
    thresholds=thresholds, back_to_back=b2b, by_season=by_season,
    lined_games=int(len(HG)))

# ---------------------------------------------------------------- live models: trained on every season before the current one
TR = HG[HG.season < CURRENT]
m_spread = Ridge(alpha=50).fit(TR[FS], TR.margin - TR.v_margin)
m_total = Ridge(alpha=50).fit(TR[FT + ["v_total"]], TR.total - TR.v_total)
TRG = G[G.season < CURRENT]        # ratings only (no market line), for the calculator
r_margin = Ridge(alpha=1).fit(TRG[FS], TRG.margin)
r_total = Ridge(alpha=1).fit(TRG[["exp_total", "h_b2b", "a_b2b"]], TRG.total)
sd_margin = float(np.std(TR.margin - (TR.v_margin + m_spread.predict(TR[FS]))))
sd_total = float(np.std(TR.total - (TR.v_total + m_total.predict(TR[FT + ["v_total"]]))))
sd_r_margin = float(np.std(TRG.margin - r_margin.predict(TRG[FS])))
sd_r_total = float(np.std(TRG.total - r_total.predict(TRG[["exp_total", "h_b2b", "a_b2b"]])))


def coef(m, cols):
    return dict(intercept=float(m.intercept_), **{c: float(v) for c, v in zip(cols, m.coef_)})


# ---------------------------------------------------------------- current season: schedule, our odds pulls, projections
sched = pd.read_parquet(os.path.join(H, f"nba/schedules/parquet/nba_schedule_{CURRENT}.parquet"))
sched = sched[sched.season_type.isin([2, 3])].copy()
sched["tip"] = pd.to_datetime(sched["date"], utc=True)
sched["gdate"] = pd.to_datetime(sched.game_date)
abbr = {}
for side in ("home", "away"):
    for nm, ab in zip(sched[f"{side}_display_name"], sched[f"{side}_abbreviation"]):
        abbr[nm] = ab
        TEAM.setdefault(ab, nm)


def consensus(game):
    sp, tot, mlh, mla = [], [], [], []
    for bk in game.get("bookmakers", []):
        for mk in bk.get("markets", []):
            oc = {o["name"]: o for o in mk.get("outcomes", [])}
            if mk["key"] == "spreads" and game["home_team"] in oc and "point" in oc[game["home_team"]]:
                sp.append(oc[game["home_team"]]["point"])
            elif mk["key"] == "totals" and "Over" in oc and "point" in oc["Over"]:
                tot.append(oc["Over"]["point"])
            elif mk["key"] == "h2h" and game["home_team"] in oc and game["away_team"] in oc:
                mlh.append(oc[game["home_team"]]["price"]); mla.append(oc[game["away_team"]]["price"])
    med = lambda v: float(np.median(v)) if v else None
    dec = lambda am: 1 + am / 100 if am > 0 else 1 + 100 / abs(am)
    amer = lambda d: round((d - 1) * 100) if d >= 2 else round(-100 / (d - 1))
    mml = lambda v: float(amer(float(np.median([dec(x) for x in v])))) if v else None   # median price, taken in decimal odds
    return dict(spread=med(sp), total=med(tot), ml_home=mml(mlh), ml_away=mml(mla), books=len(game.get("bookmakers", [])))


# the last pull taken before each game's tip
market = {}
snaps = sorted(glob.glob(os.path.join(REPO, "odds/snapshots/nba_odds_*.json")))
for f in snaps:
    snap = json.load(open(f, encoding="utf-8"))
    pulled = pd.Timestamp(snap["pulled_utc"])
    for gm in snap.get("games", []):
        tip = pd.Timestamp(gm["commence_time"])
        if tip <= pulled:
            continue
        hn = NAME_FIX.get(gm["home_team"], gm["home_team"]); an = NAME_FIX.get(gm["away_team"], gm["away_team"])
        if hn not in abbr or an not in abbr:
            continue
        c = consensus(gm)
        if c["spread"] is None and c["total"] is None:
            continue
        key = (abbr[hn], abbr[an])
        cand = sched[(sched.home_abbreviation == key[0]) & (sched.away_abbreviation == key[1]) & ((sched.tip - tip).abs() <= pd.Timedelta(hours=8))]
        if cand.empty:
            continue
        gid = int(cand.iloc[0].game_id)
        market[gid] = dict(c, pulled_utc=pulled.isoformat())

# rest days from the full schedule (works for games not yet played)
order = []
for side in ("home", "away"):
    order.append(sched[["game_id", "gdate", f"{side}_abbreviation"]].rename(columns={f"{side}_abbreviation": "team"}))
order = pd.concat(order).sort_values("gdate")
prev_game = {}
for team, x in order.groupby("team"):
    dates = list(x.gdate)
    for i, (gid, d) in enumerate(zip(x.game_id, dates)):
        prev_game[(int(gid), team)] = min((d - dates[i - 1]).days, 7) if i else 7

pre_by_id = G.set_index("game_id")
cur_rows = []
for r in sched.itertuples():
    gid = int(r.game_id)
    final = bool(r.status_type_completed)
    if gid in pre_by_id.index:
        x = pre_by_id.loc[gid]
        feat = {k: float(x[k]) for k in ("h_ortg", "h_drtg", "h_pace", "a_ortg", "a_drtg", "a_pace", "h_rest", "a_rest")}
    elif not final and pd.Timestamp(NOW) - pd.Timedelta(hours=4) < r.tip < pd.Timestamp(NOW) + pd.Timedelta(days=3):
        hs, as_ = state.get(r.home_abbreviation, dict(LG)), state.get(r.away_abbreviation, dict(LG))
        feat = dict(h_ortg=hs["ortg"], h_drtg=hs["drtg"], h_pace=hs["pace"], a_ortg=as_["ortg"], a_drtg=as_["drtg"], a_pace=as_["pace"],
                    h_rest=prev_game.get((gid, r.home_abbreviation), 7), a_rest=prev_game.get((gid, r.away_abbreviation), 7))
    else:
        continue
    cur_rows.append(dict(game_id=gid, date=r.gdate.strftime("%Y-%m-%d"), tip=r.tip.isoformat(), home=r.home_abbreviation, away=r.away_abbreviation,
                         final=final, hs=int(r.home_score) if final else None, as_=int(r.away_score) if final else None, **feat))

C = features(pd.DataFrame(cur_rows))
C["v_margin"] = [(-market[g]["spread"] if g in market and market[g]["spread"] is not None else np.nan) for g in C.game_id]
C["v_total"] = [(market[g]["total"] if g in market and market[g]["total"] is not None else np.nan) for g in C.game_id]
C["r_margin"] = r_margin.predict(C[FS])
C["r_total"] = r_total.predict(C[["exp_total", "h_b2b", "a_b2b"]])
has_s, has_t = C.v_margin.notna(), C.v_total.notna()
C["sm"] = np.nan; C["tm"] = np.nan
C.loc[has_s, "sm"] = C.loc[has_s, "v_margin"] + m_spread.predict(C.loc[has_s, FS])
C.loc[has_t, "tm"] = C.loc[has_t, "v_total"] + m_total.predict(C.loc[has_t, FT + ["v_total"]].rename(columns={}))
phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))


def grade(pred, line, act, thr):
    if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in (pred, line, act)):
        return None
    side = np.sign(pred - line)
    if side == 0:
        return None
    r = np.sign(act - line) * side
    return dict(result="push" if r == 0 else ("win" if r > 0 else "loss"), lean=bool(abs(pred - line) >= thr))


games, csv_rows = [], []
for r in C.sort_values("tip").itertuples():
    mk = market.get(r.game_id, {})
    g_ = dict(game_id=r.game_id, date=r.date, tip=r.tip, home=r.home, away=r.away, home_name=TEAM.get(r.home, r.home), away_name=TEAM.get(r.away, r.away),
              final=r.final, home_score=int(r.hs) if r.final else None, away_score=int(r.as_) if r.final else None, home_rest=int(r.h_rest), away_rest=int(r.a_rest),
              home_b2b=bool(r.h_b2b), away_b2b=bool(r.a_b2b), pulled_utc=mk.get("pulled_utc"), books=mk.get("books"),
              ml_home=mk.get("ml_home"), ml_away=mk.get("ml_away"),
              home_spread=mk.get("spread"), total=mk.get("total"),
              ratings_margin=round(float(r.r_margin), 1), ratings_total=round(float(r.r_total), 1))
    if not math.isnan(r.sm):
        e = float(r.sm - r.v_margin)
        g_.update(proj_margin=round(float(r.sm), 1), spread_edge=round(e, 1),
                  spread_pick=r.home if e > 0 else (r.away if e < 0 else None),
                  home_cover=round(phi(e / sd_margin), 3))
    if not math.isnan(r.tm):
        e = float(r.tm - r.v_total)
        g_.update(proj_total=round(float(r.tm), 1), total_edge=round(e, 1),
                  total_pick="over" if e > 0 else ("under" if e < 0 else None), over_chance=round(phi(e / sd_total), 3))
    if r.final:
        g_["spread_grade"] = grade(r.sm, r.v_margin, (r.hs - r.as_) if r.final else None, SPREAD_LEAN)
        g_["total_grade"] = grade(r.tm, r.v_total, (r.hs + r.as_) if r.final else None, TOTAL_LEAN)
    games.append(g_)
    csv_rows.append({k: g_.get(k) for k in ("date", "away", "home", "home_spread", "total", "proj_margin", "proj_total", "spread_edge", "total_edge",
                                            "spread_pick", "total_pick", "away_score", "home_score")})


def record(key, lean_only):
    w = l_ = p = 0
    for g_ in games:
        gr = g_.get(key)
        if not gr or (lean_only and not gr["lean"]):
            continue
        w += gr["result"] == "win"; l_ += gr["result"] == "loss"; p += gr["result"] == "push"
    return dict(w=w, l=l_, p=p)


finals = [g_ for g_ in games if g_["final"]]
miss = lambda a, b: round(float(np.mean([abs(x - y) for x, y in zip(a, b)])), 2) if a else None
fm = [g_ for g_ in finals if g_.get("proj_margin") is not None]
ft = [g_ for g_ in finals if g_.get("proj_total") is not None]
season = dict(
    graded=len(fm),
    spread_all=record("spread_grade", False), spread_leans=record("spread_grade", True),
    total_all=record("total_grade", False), total_leans=record("total_grade", True),
    vegas_miss_margin=miss([-g_["home_spread"] for g_ in fm], [g_["home_score"] - g_["away_score"] for g_ in fm]),
    model_miss_margin=miss([g_["proj_margin"] for g_ in fm], [g_["home_score"] - g_["away_score"] for g_ in fm]),
    vegas_miss_total=miss([g_["total"] for g_ in ft], [g_["home_score"] + g_["away_score"] for g_ in ft]),
    model_miss_total=miss([g_["proj_total"] for g_ in ft], [g_["home_score"] + g_["away_score"] for g_ in ft]),
)

ratings = []
for ab, s in state.items():
    if last.get(ab, (None,))[0] != CURRENT:
        continue
    rec = recent.get(ab, [])
    ratings.append(dict(team=ab, name=TEAM.get(ab, ab), ortg=round(s["ortg"], 1), drtg=round(s["drtg"], 1),
                        net=round(s["ortg"] - s["drtg"], 1), pace=round(s["pace"], 1), games=len(rec),
                        wins=sum(rec), losses=len(rec) - sum(rec), last_game=last[ab][1].strftime("%Y-%m-%d")))
ratings.sort(key=lambda x: -x["net"])

out = dict(
    built_utc=NOW.isoformat(), season_label=f"{CURRENT - 1}–{str(CURRENT)[2:]}",
    data_through=g.game_date.max().strftime("%Y-%m-%d"), latest_pull=(json.load(open(snaps[-1]))["pulled_utc"] if snaps else None),
    snapshots=len(snaps), thresholds=dict(spread=SPREAD_LEAN, total=TOTAL_LEAN),
    model=dict(spread=coef(m_spread, FS), total=coef(m_total, FT + ["v_total"]), ratings_margin=coef(r_margin, FS),
               ratings_total=coef(r_total, ["exp_total", "h_b2b", "a_b2b"]),
               sd_margin=round(sd_margin, 2), sd_total=round(sd_total, 2), sd_ratings_margin=round(sd_r_margin, 2), sd_ratings_total=round(sd_r_total, 2),
               half_life=HL, regression=REG, train_games=int(len(TR))),
    backtest=backtest, season=season, ratings=ratings, games=games)
with open(os.path.join(OUT, "courtline.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
pd.DataFrame(csv_rows).to_csv(os.path.join(OUT, "predictions.csv"), index=False)
up = [g_ for g_ in games if not g_["final"]]
print(f"backtest {backtest['games']} games | vegas {backtest['vegas_miss_margin']} model {backtest['model_miss_margin']} | "
      f"season graded {season['graded']} | upcoming {len(up)} ({sum(1 for g_ in up if g_.get('proj_margin') is not None)} with lines) | ratings {len(ratings)}")
