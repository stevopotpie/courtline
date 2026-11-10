"""Build the Courtline site (docs/) from data/courtline.json.

Pages: index (home), predictions, research, calculator, bet-log. Each gets the shared top bar (with the odds
format switch) and the site map footer. Styles and the odds switch live in site/courtline.css and courtline.js.

Usage: python3 -I site/build.py REPO_DIR
"""
import hashlib, html, json, math, os, shutil, sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

REPO = sys.argv[1]
SITE = os.path.join(REPO, "site")
DOCS = os.path.join(REPO, "docs")
D = json.load(open(os.path.join(REPO, "data", "courtline.json"), encoding="utf-8"))
ET = ZoneInfo("America/New_York")
BASE = "https://stevopotpie.github.io/courtline/"
GH = "https://github.com/stevopotpie/courtline"
GRIDLINE = "https://stevopotpie.github.io/gridline/"
e = html.escape

os.makedirs(DOCS, exist_ok=True)
assets = {}
for f in ("courtline.css", "courtline.js"):
    shutil.copy(os.path.join(SITE, f), os.path.join(DOCS, f))
    assets[f] = hashlib.sha1(open(os.path.join(SITE, f), "rb").read()).hexdigest()[:8]

PAGES = [  # file, nav label, site map name, description
    ("index.html", None, "Home", "What Courtline is and how it has done"),
    ("predictions.html", "Predictions", "Predictions", "Today's games: the market number, Courtline's projection and every graded pick this season"),
    ("research.html", "Research", "Research", "The backtest, back to backs, home court by season and team ratings"),
    ("calculator.html", "Calculator", "Matchup Calculator", "Pick any two teams, rest and a line to see Courtline's number"),
    ("bet-log.html", "Bet log", "Bet Log", "Log bets, see Courtline's chance against the price, saved in your browser"),
]
ABOUT = [("Method and results (README)", f"{GH}#readme"), ("Runbook: data, findings, how each run works", f"{GH}/blob/main/RUNBOOK.md"),
         ("Every projection as a CSV", f"{GH}/blob/main/data/predictions.csv"), ("Source code", GH),
         ("Gridline, the NFL companion model", GRIDLINE)]


def et(ts, fmt="%-I:%M %p"):
    return datetime.fromisoformat(ts).astimezone(ET).strftime(fmt)


def built_text():
    return datetime.fromisoformat(D["built_utc"]).astimezone(ET).strftime("%b %-d, %-I:%M %p ET")


def head(title, desc, page):
    url = BASE + ("" if page == "index.html" else page)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}og.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/png" href="icon.png">
<link rel="apple-touch-icon" href="icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=IBM+Plex+Mono:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<link rel="stylesheet" href="courtline.css?v={assets['courtline.css']}">
<script src="courtline.js?v={assets['courtline.js']}"></script>
</head>
<body>
"""


def nav(current):
    links = "".join(f'<a href="{f}"{" aria-current=\"page\"" if f == current else ""}>{lab}</a>' for f, lab, _, _ in PAGES if lab)
    links += f'<a class="ext" href="{GRIDLINE}">Gridline (NFL)</a><a class="ext" href="{GH}">GitHub</a>'
    return (f'<nav class="cl-nav" aria-label="Courtline pages"><div class="cl-in">'
            f'<a class="cl-brand" href="./"{" aria-current=\"page\"" if current == "index.html" else ""}><img src="icon.png" alt="" width="26" height="26">Courtline</a>'
            f'<div class="cl-links">{links}</div>'
            f'<div class="odds-toggle" role="group" aria-label="Odds format"><button type="button" data-fmt="am" aria-pressed="true">&minus;110</button>'
            f'<button type="button" data-fmt="dec" aria-pressed="false">1.91x</button></div></div></nav>\n')


def footer(current):
    items = ""
    for f, _, name, desc in PAGES:
        if f == current:
            items += f'<li><span class="here">{name} (you are here)</span><span class="d">{e(desc)}</span></li>'
        else:
            items += f'<li><a href="{"./" if f == "index.html" else f}">{name}</a><span class="d">{e(desc)}</span></li>'
    about = "".join(f'<li><a href="{u}">{e(n)}</a></li>' for n, u in ABOUT)
    return (f'<footer class="cl-map"><div class="cl-in">'
            f'<nav aria-label="Site map"><h2>Site map</h2><ul>{items}</ul></nav>'
            f'<nav aria-label="About Courtline"><h2>About</h2><ul>{about}</ul></nav>'
            f'<div class="foot"><span>Built by Steven Sutcliffe</span><a href="https://www.linkedin.com/in/steven-sutcliffe/">LinkedIn</a>'
            f'<a href="https://github.com/stevopotpie">GitHub</a><span>Rebuilt {built_text()}</span>'
            f'<span>Research, not betting advice. Sports betting is not legal in every state.</span></div></div></footer>\n</body>\n</html>\n')


def page(fname, title, desc, body, extra=""):
    with open(os.path.join(DOCS, fname), "w", encoding="utf-8") as f:
        f.write(head(title, desc, fname) + nav(fname) + body + extra + footer(fname))


# ------------------------------------------------------------------ shared bits
B, S = D["backtest"], D["season"]
GAMES = D["games"]
TEAMS = {r["team"]: r for r in D["ratings"]}


def rec_text(r):
    return f'{r["w"]}–{r["l"]}' + (f'–{r["p"]}' if r["p"] else "")


def pct(r):
    n = r["w"] + r["l"]
    return f'{100 * r["w"] / n:.1f}%' if n else "n/a"


def team_rec(ab):
    t = TEAMS.get(ab)
    return f'{t["wins"]}–{t["losses"]}' if t else ""


def spread_text(g):
    hs = g.get("home_spread")
    if hs is None:
        return "–"
    if hs == 0:
        return "Pick'em"
    fav, n = (g["home"], hs) if hs < 0 else (g["away"], -hs)
    return f"{fav} &minus;{abs(n):g}"


def margin_text(g, m):
    if m is None:
        return "–"
    if abs(m) < 0.05:
        return "Even"
    return f"{g['home'] if m > 0 else g['away']} by {abs(m):.1f}"


def board_html(head_l, head_r, rows, foot):
    body = "".join(f'<span class="row-label" role="rowheader">{l}</span><span class="digit" role="cell">{a}</span><span class="digit" role="cell">{b}</span>' for l, a, b in rows)
    return (f'<div class="board" role="table" aria-label="{e(head_r)}"><div class="board-head"><span>{head_l}</span><span>{head_r}</span></div>'
            f'<div class="board-grid" role="rowgroup"><span role="columnheader"></span><span class="col" role="columnheader">Vegas</span>'
            f'<span class="col" role="columnheader">Courtline</span><span class="rule" aria-hidden="true"></span>{body}</div>'
            f'<p class="board-foot">{foot}</p></div>')


def lean_chart():
    rows = []
    for t in B["thresholds"]:
        for kind, w, l_ in (("Spread", t["spread_w"], t["spread_l"]), ("Total", t["total_w"], t["total_l"])):
            if w + l_ >= 100:
                rows.append((f"{kind}, lean {t['edge']:g}+", w, l_))
    rows.sort(key=lambda r: (r[0][0] != "S", r[0]))
    lo, hi = 46.0, 54.0
    x = lambda p: 170 + (p - lo) / (hi - lo) * 440
    h = 40 + 44 * len(rows) + 50
    s = [f'<svg viewBox="0 0 640 {h}" role="img" aria-label="Win rate by lean size against the closing line">']
    for v in (46, 48, 50, 52, 54):
        s.append(f'<line class="grid" x1="{x(v):.0f}" y1="24" x2="{x(v):.0f}" y2="{h - 46}"></line>'
                 f'<text class="t-axis" x="{x(v):.0f}" y="{h - 26}" text-anchor="middle">{v}%</text>')
    s.append(f'<line class="coin" x1="{x(50):.0f}" y1="24" x2="{x(50):.0f}" y2="{h - 46}"></line>')
    s.append(f'<line class="be" x1="{x(52.38):.1f}" y1="20" x2="{x(52.38):.1f}" y2="{h - 46}"></line>'
             f'<text class="t-acc" x="{x(52.38) - 4:.0f}" y="14" text-anchor="end">Breakeven at &minus;110: 52.4%</text>')
    for i, (lab, w, l_) in enumerate(rows):
        y = 52 + 44 * i
        p = 100 * w / (w + l_)
        cx = x(max(lo, min(hi, p)))
        s.append(f'<text class="t-label" x="0" y="{y - 4}">{lab}</text><text class="t-sub" x="0" y="{y + 12}">{w + l_:,} bets</text>'
                 f'<line class="track" x1="{x(lo):.0f}" y1="{y}" x2="{x(hi):.0f}" y2="{y}"></line><circle class="dot" cx="{cx:.1f}" cy="{y}" r="7"></circle>'
                 f'<text class="t-val" x="{cx + (12 if p < 51.3 else -12):.0f}" y="{y - 6}" text-anchor="{"start" if p < 51.3 else "end"}">{p:.1f}%</text>')
    s.append(f'<text class="t-axis" x="{x(50):.0f}" y="{h - 6}" text-anchor="middle">Win rate against the closing line (dashed line = coin flip)</text></svg>')
    return '<figure class="panel chart" style="margin:0"><div class="scroll">' + "".join(s) + '</div><figcaption class="caption">Lean size is how far Courtline\'s projection sat from the closing number, in points. Groups under 100 bets are left out.</figcaption></figure>'


def season_chart():
    rows = B["by_season"]
    top = max(max(r["home_margin"], r["home_line"]) for r in rows)
    top = math.ceil(top + 0.5)
    W, H0, L_, R_ = 640, 250, 40, 20
    bw = (W - L_ - R_) / len(rows)
    y = lambda v: 200 - v / top * 170
    s = [f'<svg viewBox="0 0 {W} {H0}" role="img" aria-label="Average home margin and closing line by season">']
    for v in range(0, top + 1):
        s.append(f'<line class="grid" x1="{L_}" y1="{y(v):.1f}" x2="{W - R_}" y2="{y(v):.1f}"></line><text class="t-axis" x="{L_ - 8}" y="{y(v) + 4:.1f}" text-anchor="end">{v}</text>')
    for i, r in enumerate(rows):
        cx = L_ + bw * i + bw / 2
        s.append(f'<rect class="bar" x="{cx - bw * 0.3:.1f}" y="{y(r["home_margin"]):.1f}" width="{bw * 0.3:.1f}" height="{200 - y(r["home_margin"]):.1f}"></rect>'
                 f'<rect class="bar2" x="{cx:.1f}" y="{y(r["home_line"]):.1f}" width="{bw * 0.3:.1f}" height="{200 - y(r["home_line"]):.1f}"></rect>'
                 f'<text class="t-axis" x="{cx:.1f}" y="220" text-anchor="middle">{r["season"]}</text>'
                 f'<text class="t-axis" x="{cx:.1f}" y="236" text-anchor="middle">{r["games"]:,} g</text>')
    s.append('</svg>')
    leg = ('<p class="caption"><span style="display:inline-block;width:10px;height:10px;background:var(--accent);border-radius:2px"></span> Average home margin, in points '
           '&nbsp; <span style="display:inline-block;width:10px;height:10px;background:var(--muted);opacity:.55;border-radius:2px"></span> Average closing spread for the home team. '
           '2019–20 covers only the bubble restart games that have lines.</p>')
    return '<figure class="panel chart" style="margin:0"><div class="scroll">' + "".join(s) + '</div>' + leg + '</figure>'


# ------------------------------------------------------------------ home
finals = [g for g in GAMES if g["final"] and g.get("proj_margin") is not None]
upcoming = [g for g in GAMES if not g["final"]]
home_body = f"""<main class="wrap">
<header class="page-head" style="padding-top:3rem">
  <span class="eyebrow">Courtline · NBA model vs. the betting market</span>
  <h1>Vegas missed by <span style="color:var(--accent-ink)">{B['vegas_miss_margin']:.2f}</span>. My model missed by <span style="color:var(--accent-ink)">{B['model_miss_margin']:.2f}</span>.</h1>
  <p class="lede">I built an NBA model from public data and tested it on {B['games']:,} games it had never seen. It found no edge against the closing line on sides or totals. Now it runs every day of the {D['season_label']} season, projects every game against the market, and grades itself in public.</p>
  <div class="actions"><a class="btn primary" href="predictions.html">Today's projections</a><a class="btn" href="research.html">Read the research</a></div>
</header>

{board_html("Backtest v0 · walk forward", f"{B['games']:,} games · {B['seasons']}",
            [("Avg miss, margin", f"{B['vegas_miss_margin']:.2f}", f"{B['model_miss_margin']:.2f}"), ("Avg miss, total", f"{B['vegas_miss_total']:.2f}", f"{B['model_miss_total']:.2f}")],
            "Average points between the projection and the final score, on games each season's model had never seen.")}

<section class="block" aria-labelledby="season-h">
  <span class="eyebrow">This season, out of sample</span>
  <h2 id="season-h">{D['season_label']}: {S['graded']} games graded</h2>
  <p>Every game is projected against the consensus line from my last odds pull before tip, using a model trained only on earlier seasons. Courtline always takes a side, so these records include every graded game, not a hand-picked list.</p>
  <div class="stats">
    <div class="stat"><span class="big">{rec_text(S['spread_all'])}</span><span class="what">Against the spread</span><span class="n">{pct(S['spread_all'])} · every game</span></div>
    <div class="stat"><span class="big">{rec_text(S['total_all'])}</span><span class="what">Totals, over or under</span><span class="n">{pct(S['total_all'])} · every game</span></div>
    <div class="stat"><span class="big">{S['model_miss_margin'] if S['model_miss_margin'] is not None else '–'}</span><span class="what">Avg miss on the margin</span><span class="n">Vegas: {S['vegas_miss_margin'] if S['vegas_miss_margin'] is not None else '–'}</span></div>
  </div>
  <p><a href="predictions.html#graded">See every graded game</a></p>
</section>

<section class="block" aria-labelledby="how-h">
  <span class="eyebrow">How it works</span>
  <h2 id="how-h">Five steps, run every day</h2>
  <ol class="steps">
    <li><h3>Collect the data</h3><p>Team box scores, schedules and closing lines from the open hoopR NBA dataset: about {B['lined_games']:,} lined games since 2020, plus every game this season.</p></li>
    <li><h3>Model team form</h3><p>Exponentially weighted offensive rating, defensive rating and pace with a {D['model']['half_life']} game half life, regressed {int(D['model']['regression'] * 100)}% toward average between seasons, plus rest days and back to backs.</p></li>
    <li><h3>Backtest walk forward</h3><p>Each season from {B['seasons']} is projected only from the games before it, then scored against final results and the closing line.</p></li>
    <li><h3>Save the market</h3><p>A daily pull from The Odds API saves spreads, totals and moneylines across US sportsbooks before the evening slate, so every projection is graded against a real number.</p></li>
    <li><h3>Publish and grade</h3><p>This site rebuilds itself every evening after the odds pull and every morning after the results, so each projection is posted before tip and graded after the final.</p></li>
  </ol>
</section>

<section class="block" aria-labelledby="explore-h">
  <span class="eyebrow">Explore</span>
  <h2 id="explore-h">Four ways in</h2>
  <div class="cards">
    <a class="card" href="predictions.html"><h3>Predictions</h3><p>{len(upcoming)} upcoming games with the market number, Courtline's projection and the lean.</p></a>
    <a class="card" href="research.html"><h3>Research</h3><p>The backtest, the back to back finding, home court by season and today's team ratings.</p></a>
    <a class="card" href="calculator.html"><h3>Calculator</h3><p>Any two teams, any rest, any line. See the projected margin, total and fair price.</p></a>
    <a class="card" href="bet-log.html"><h3>Bet log</h3><p>Log a bet and see Courtline's chance against the price. Saved in your browser only.</p></a>
  </div>
</section>
</main>
"""
home_css = """<style>
.steps{list-style:none;margin:.25rem 0 0;padding:0;display:grid;gap:1.3rem;counter-reset:step}
.steps li{display:grid;grid-template-columns:2.5rem minmax(0,1fr);gap:.2rem 1rem;counter-increment:step}
.steps li::before{content:counter(step);grid-row:span 2;font:700 1.9rem/1 var(--font-display);color:var(--accent)}
.steps h3{align-self:end}.steps p{color:var(--muted)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(14rem,1fr));gap:.9rem}
.card{display:grid;gap:.4rem;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:1rem 1.1rem;color:var(--ink);text-decoration:none}
.card:hover{border-color:var(--accent)}.card h3{color:var(--accent-ink)}.card p{color:var(--muted);font-size:.95rem}
</style>
"""
page("index.html", "Courtline: an NBA model tested against the betting market",
     "An NBA model built on public data and tested against Vegas closing lines, run daily and graded in public. By Steven Sutcliffe.",
     home_css + home_body)

# ------------------------------------------------------------------ predictions
latest = D.get("latest_pull")
by_date = {}
for g in upcoming:
    by_date.setdefault(datetime.fromisoformat(g["tip"]).astimezone(ET).strftime("%A, %B %-d"), []).append(g)


def game_card(g):
    tags = []
    for side in ("away", "home"):
        if g[f"{side}_b2b"]:
            tags.append(f'<span class="pill b2b">{g[side]} on a back to back</span>')
    has = g.get("proj_margin") is not None or g.get("proj_total") is not None
    if g.get("proj_margin") is not None:
        lean = abs(g["spread_edge"]) >= D["thresholds"]["spread"]
        pick = g["spread_pick"]
        line_for_pick = (g["home_spread"] if pick == g["home"] else -g["home_spread"]) if pick else None
        cover = g["home_cover"] if pick == g["home"] else 1 - g["home_cover"]
        sp = (f'<div class="mk"><span class="lab">Spread</span><span class="mkt">{spread_text(g)}</span>'
              f'<span class="cl">Courtline: {margin_text(g, g["proj_margin"])}</span>'
              f'<span class="pick">{"<span class=\"pill lean\">Lean</span> " if lean else ""}{pick or "No side"} {line_for_pick:+g} · {100 * cover:.1f}%</span></div>' if pick else
              f'<div class="mk"><span class="lab">Spread</span><span class="mkt">{spread_text(g)}</span><span class="cl">Courtline: {margin_text(g, g["proj_margin"])}</span><span class="pick">No side</span></div>')
    else:
        sp = f'<div class="mk"><span class="lab">Spread</span><span class="mkt">Not posted</span><span class="cl">Ratings only: {margin_text(g, g["ratings_margin"])}</span><span class="pick"></span></div>'
    if g.get("proj_total") is not None:
        lean = abs(g["total_edge"]) >= D["thresholds"]["total"]
        ch = g["over_chance"] if g["total_pick"] == "over" else 1 - g["over_chance"]
        tt = (f'<div class="mk"><span class="lab">Total</span><span class="mkt">{g["total"]:g}</span><span class="cl">Courtline: {g["proj_total"]:.1f}</span>'
              f'<span class="pick">{"<span class=\"pill lean\">Lean</span> " if lean else ""}{(g["total_pick"] or "no side").title()} {g["total"]:g} · {100 * ch:.1f}%</span></div>')
    else:
        tt = f'<div class="mk"><span class="lab">Total</span><span class="mkt">Not posted</span><span class="cl">Ratings only: {g["ratings_total"]:.1f}</span><span class="pick"></span></div>'
    ml = ""
    if g.get("ml_home") is not None:
        ml = (f'<div class="mk"><span class="lab">Moneyline</span><span class="mkt">{g["away"]} <span class="odds" data-am="{g["ml_away"]:.0f}">{g["ml_away"]:+.0f}</span> · '
              f'{g["home"]} <span class="odds" data-am="{g["ml_home"]:.0f}">{g["ml_home"]:+.0f}</span></span><span class="cl"></span><span class="pick"></span></div>')
    pulled = f'Line from the {et(g["pulled_utc"], "%-I:%M %p ET %b %-d")} pull, median of {g["books"]} books' if g.get("pulled_utc") else "No line in an odds pull yet"
    return (f'<article class="game"><div class="g-top"><span class="tip">{et(g["tip"])} ET</span>{"".join(tags)}</div>'
            f'<div class="teams"><span><strong>{e(g["away_name"])}</strong> <span class="muted small">{team_rec(g["away"])}</span></span>'
            f'<span class="at">at</span><span><strong>{e(g["home_name"])}</strong> <span class="muted small">{team_rec(g["home"])}</span></span></div>'
            f'<div class="mks">{sp}{tt}{ml}</div><p class="small muted">{pulled}.</p></article>')


def day_html(d, gs):
    lined = [g for g in gs if g.get("proj_margin") is not None or g.get("proj_total") is not None]
    rest = [g for g in gs if g not in lined]
    out = f'<h3 class="day">{d}</h3>'
    if lined:
        out += f'<div class="games">{"".join(game_card(g) for g in lined)}</div>'
    if rest:
        rows = "".join(f'<tr><td class="m">{et(g["tip"])}</td><td>{e(g["away_name"])} <span class="muted small">{team_rec(g["away"])}</span> at {e(g["home_name"])} <span class="muted small">{team_rec(g["home"])}</span>'
                       f'{"".join(f" <span class=\"pill b2b\">{g[s]} b2b</span>" for s in ("away", "home") if g[f"{s}_b2b"])}</td>'
                       f'<td class="m">{margin_text(g, g["ratings_margin"])}</td><td class="r m">{g["ratings_total"]:.1f}</td></tr>' for g in rest)
        out += (f'<div class="panel scroll" style="padding:0;margin-top:{".9rem" if lined else "0"}"><table class="t"><thead><tr><th>Tip</th><th>Lines not posted yet</th>'
                f'<th>Ratings margin</th><th class="r">Ratings total</th></tr></thead><tbody>{rows}</tbody></table></div>')
    return out


days = "".join(day_html(d, gs) for d, gs in by_date.items()) or '<div class="panel"><p>No games in the next three days.</p></div>'


def res_pill(gr):
    if not gr:
        return '<span class="muted">–</span>'
    return f'<span class="pill {gr["result"]}">{gr["result"]}</span>' + (' <span class="pill lean">lean</span>' if gr["lean"] else "")


graded_rows = ""
for g in sorted(finals, key=lambda x: x["tip"], reverse=True)[:60]:
    pick_line = (g["home_spread"] if g.get("spread_pick") == g["home"] else -g["home_spread"]) if g.get("spread_pick") else None
    graded_rows += (f'<tr><td>{datetime.fromisoformat(g["tip"]).astimezone(ET).strftime("%b %-d")}</td><td>{g["away"]} {g["away_score"]} · {g["home"]} {g["home_score"]}</td>'
                    f'<td class="m">{spread_text(g)}</td><td class="m">{(g["spread_pick"] + f" {pick_line:+g}") if g.get("spread_pick") else "–"}</td><td>{res_pill(g.get("spread_grade"))}</td>'
                    f'<td class="m">{g["total"]:g}</td><td class="m">{(g["total_pick"] or "–").title()} ({g["proj_total"]:.1f})</td><td>{res_pill(g.get("total_grade"))}</td></tr>'
                    if g.get("total") is not None else
                    f'<tr><td>{datetime.fromisoformat(g["tip"]).astimezone(ET).strftime("%b %-d")}</td><td>{g["away"]} {g["away_score"]} · {g["home"]} {g["home_score"]}</td>'
                    f'<td class="m">{spread_text(g)}</td><td class="m">{(g["spread_pick"] + f" {pick_line:+g}") if g.get("spread_pick") else "–"}</td><td>{res_pill(g.get("spread_grade"))}</td><td class="m">–</td><td class="m">–</td><td>–</td></tr>')

pred_body = f"""<main class="wrap wide">
<header class="page-head">
  <span class="eyebrow">Predictions · {D['season_label']}</span>
  <h1>Today's board</h1>
  <p class="lede">Every NBA game in the next three days: the market's consensus number, Courtline's projection, and the side it takes. A lean means Courtline disagrees with the market by at least {D['thresholds']['spread']:g} point on the spread or {D['thresholds']['total']:g} points on the total.</p>
  <p class="small muted">Lines are the median across US sportsbooks from the latest odds pull{(' (' + et(latest, '%b %-d, %-I:%M %p ET') + ')') if latest else ''}. Team data through {datetime.fromisoformat(D['data_through']).strftime('%b %-d')}. Percentages are Courtline's chance that its side wins at the market number.</p>
</header>
<div class="panel note"><p><strong>Read this first.</strong> Courtline v0 found no edge against closing lines in {B['games']:,} backtested games, and team form alone rarely moves it far from the market. These are paper projections, posted before tip and graded in public, not betting advice.</p></div>
{days}

<section class="block" id="graded" aria-labelledby="graded-h">
  <span class="eyebrow">Graded this season</span>
  <h2 id="graded-h">{S['graded']} games, every one counted</h2>
  <div class="stats">
    <div class="stat"><span class="big">{rec_text(S['spread_all'])}</span><span class="what">Spread, every game</span><span class="n">{pct(S['spread_all'])}</span></div>
    <div class="stat"><span class="big">{rec_text(S['spread_leans'])}</span><span class="what">Spread leans ({D['thresholds']['spread']:g}+ pts)</span><span class="n">{pct(S['spread_leans'])}</span></div>
    <div class="stat"><span class="big">{rec_text(S['total_all'])}</span><span class="what">Totals, every game</span><span class="n">{pct(S['total_all'])}</span></div>
    <div class="stat"><span class="big">{rec_text(S['total_leans'])}</span><span class="what">Total leans ({D['thresholds']['total']:g}+ pts)</span><span class="n">{pct(S['total_leans'])}</span></div>
  </div>
  <p class="small muted">Average miss on the final margin: Courtline {S['model_miss_margin']}, Vegas {S['vegas_miss_margin']}. On the total: Courtline {S['model_miss_total']}, Vegas {S['vegas_miss_total']}. A win needs about 52.4% at standard &minus;110 pricing to break even.</p>
  <div class="panel scroll" style="padding:0"><table class="t">
    <thead><tr><th>Date</th><th>Final</th><th>Spread</th><th>Courtline side</th><th>Result</th><th>Total</th><th>Courtline</th><th>Result</th></tr></thead>
    <tbody>{graded_rows}</tbody></table></div>
  <p class="small"><a href="{GH}/blob/main/data/predictions.csv">Every projection this season as a CSV</a>, including games without a captured line.</p>
</section>
</main>
"""
pred_css = """<style>
.note{border-left:3px solid var(--accent)}
.day{margin-top:1.75rem;margin-bottom:.75rem;font-size:1.5rem}
.games{display:grid;gap:.9rem}
.game{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:.9rem 1rem;display:grid;gap:.6rem;min-width:0}
.g-top{display:flex;flex-wrap:wrap;gap:.4rem .6rem;align-items:center}
.tip{font:600 .8rem var(--font-mono);color:var(--accent-ink);letter-spacing:.06em}
.teams{display:flex;flex-wrap:wrap;gap:.3rem .6rem;align-items:baseline;font-size:1.05rem}
.at{color:var(--muted);font-size:.85rem}
.mks{display:grid;gap:.35rem}
.mk{display:grid;grid-template-columns:6.5rem minmax(0,1fr) minmax(0,1.2fr) minmax(0,1.3fr);gap:.2rem .8rem;align-items:baseline;padding:.4rem 0;border-top:1px solid var(--line);font-size:.93rem}
.mk .lab{font:600 .7rem var(--font-mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.mk .mkt{font-family:var(--font-mono)}.mk .cl{color:var(--muted)}.mk .pick{font-weight:600}
@media (max-width:640px){.mk{grid-template-columns:5.5rem minmax(0,1fr)}.mk .cl,.mk .pick{grid-column:2}}
</style>
"""
page("predictions.html", "Courtline Predictions",
     "Today's NBA games with the market's consensus line, Courtline's projection and lean, plus every graded pick this season.",
     pred_css + pred_body)

# ------------------------------------------------------------------ research
b2b_rows = "".join(f'<tr><td>{e(r["label"])}</td><td class="r m">{r["n"]:,}</td><td class="r m">{r["margin_vs_line"]:+.2f}</td>'
                   f'<td class="r m">{r["total_vs_line"]:+.2f}</td><td class="r m">{r["total_vs_line"] / r["total_se"]:+.1f}</td></tr>' for r in B["back_to_back"])
road = next(r for r in B["back_to_back"] if r["label"].startswith("Road"))
homeb = next(r for r in B["back_to_back"] if r["label"].startswith("Home"))
season_rows = "".join(f'<tr><td>{r["season"]}</td><td class="r m">{r["games"]:,}</td><td class="r m">{r["home_margin"]:+.2f}</td><td class="r m">{r["home_line"]:+.2f}</td>'
                      f'<td class="r m">{r["vegas_miss_margin"]:.2f}</td><td class="r m">{r["vegas_miss_total"]:.2f}</td></tr>' for r in B["by_season"])
rating_rows = "".join(f'<tr><td class="r m">{i + 1}</td><td><strong>{e(r["name"])}</strong> <span class="muted small">{r["team"]}</span></td>'
                      f'<td class="r m">{r["wins"]}–{r["losses"]}</td><td class="r m">{r["ortg"]:.1f}</td><td class="r m">{r["drtg"]:.1f}</td>'
                      f'<td class="r m"><strong>{r["net"]:+.1f}</strong></td><td class="r m">{r["pace"]:.1f}</td></tr>' for i, r in enumerate(D["ratings"]))
res_body = f"""<main class="wrap">
<header class="page-head">
  <span class="eyebrow">Research</span>
  <h1>What the data says</h1>
  <p class="lede">Findings from {B['lined_games']:,} NBA games with closing lines since 2020, tested on games the model had never seen. Each section reruns every day with the newest data.</p>
  <nav class="toc small" aria-label="On this page"><a href="#close">Tested against the close</a> · <a href="#b2b">Back to backs</a> · <a href="#home">Home court by season</a> · <a href="#ratings">Team ratings</a> · <a href="#next">What comes next</a></nav>
</header>

<section class="block" id="close" aria-labelledby="close-h">
  <span class="eyebrow">The backtest</span>
  <h2 id="close-h">The market already knew</h2>
  <p>Vegas closing lines missed the final margin by {B['vegas_miss_margin']:.2f} points on average across {B['games']:,} games from {B['seasons']}. Courtline missed by {B['model_miss_margin']:.2f}. On totals both missed by about {B['vegas_miss_total']:.1f}. The model agreed with the close so closely that it almost never moved a spread by a full point, and no group of leans cleared the 52.4% needed to profit at &minus;110.</p>
  {lean_chart()}
  <p>That is the expected answer. NBA closing lines are some of the most efficient prices in sports, and team form is already built into them. A backtest that reports this plainly is doing its job.</p>
</section>

<section class="block" id="b2b" aria-labelledby="b2b-h">
  <span class="eyebrow">Rest</span>
  <h2 id="b2b-h">Tired road teams and the total</h2>
  <p>When the road team played its second game in two nights, games finished {road['total_vs_line']:+.2f} points against the closing total across {road['n']:,} games, about {road['total_vs_line'] / road['total_se']:.1f} standard errors from zero. Home teams on a back to back finished {homeb['margin_vs_line']:+.2f} points against the spread across {homeb['n']:,} games. Both are suggestive and unproven, so they get retested on new games before they count.</p>
  <div class="panel scroll" style="padding:0"><table class="t">
    <thead><tr><th>Situation</th><th class="r">Games</th><th class="r">Home margin vs spread</th><th class="r">Total vs closing total</th><th class="r">Std. errors</th></tr></thead>
    <tbody>{b2b_rows}</tbody></table></div>
  <p class="small muted">Positive margin means the home team beat the spread on average. Positive total means games went over. Seasons {B['seasons']}.</p>
</section>

<section class="block" id="home" aria-labelledby="home-h">
  <span class="eyebrow">Home court</span>
  <h2 id="home-h">Home court, season by season</h2>
  <p>Home teams have won by about 1 to 2.5 points a game in each full season since 2020, under the old 3 point rule of thumb, and the average closing spread has stayed within half a point of that every season. The market's average miss has held between about 10 and 11 points on the margin and near 14 on the total.</p>
  {season_chart()}
  <div class="panel scroll" style="padding:0"><table class="t">
    <thead><tr><th>Season</th><th class="r">Games</th><th class="r">Home margin</th><th class="r">Home spread</th><th class="r">Vegas miss, margin</th><th class="r">Vegas miss, total</th></tr></thead>
    <tbody>{season_rows}</tbody></table></div>
</section>

<section class="block" id="ratings" aria-labelledby="ratings-h">
  <span class="eyebrow">Ratings · {D['season_label']}</span>
  <h2 id="ratings-h">Team ratings today</h2>
  <p>Points scored and allowed per 100 possessions, weighted toward recent games ({D['model']['half_life']} game half life) and carried over from last season with a {int(D['model']['regression'] * 100)}% pull toward average. These feed the projections and the calculator. Data through {datetime.fromisoformat(D['data_through']).strftime('%B %-d')}.</p>
  <div class="panel scroll" style="padding:0"><table class="t">
    <thead><tr><th class="r">#</th><th>Team</th><th class="r">W–L</th><th class="r">Off. rating</th><th class="r">Def. rating</th><th class="r">Net</th><th class="r">Pace</th></tr></thead>
    <tbody>{rating_rows}</tbody></table></div>
</section>

<section class="block" id="next" aria-labelledby="next-h">
  <span class="eyebrow">What comes next</span>
  <h2 id="next-h">Player minutes and props</h2>
  <p>If a model like this has an NBA edge anywhere, props are the likeliest place: thinner markets, many more lines, and slower adjustments to minutes and role changes. The plan is a player minutes model first, then props, then totals, with sides last if ever.</p>
  <p>The obstacle is data. No public source has historical player prop lines, so Courtline will save its own prop odds going forward and grade early projections against results until enough market history builds up. Team form also knows nothing about injuries or trades yet, which is the first thing the next version needs.</p>
</section>
</main>
"""
res_css = "<style>.toc{display:flex;flex-wrap:wrap;gap:.25rem .5rem}</style>\n"
page("research.html", "Courtline Research",
     "NBA backtest results against closing lines, back to back effects, home court by season and current team ratings.",
     res_css + res_body)

# ------------------------------------------------------------------ calculator
M = D["model"]
calc_data = dict(th=D["thresholds"], teams=[dict(team=r["team"], name=r["name"], ortg=r["ortg"], drtg=r["drtg"], pace=r["pace"], wins=r["wins"], losses=r["losses"]) for r in D["ratings"]],
                 model=M, games=[dict(home=g["home"], away=g["away"], home_rest=g["home_rest"], away_rest=g["away_rest"], home_spread=g.get("home_spread"),
                                      total=g.get("total"), tip=g["tip"]) for g in upcoming])
calc_body = f"""<main class="wrap">
<header class="page-head">
  <span class="eyebrow">Matchup calculator</span>
  <h1>Set any matchup</h1>
  <p class="lede">Pick two teams and their rest. Courtline projects the margin and total from team ratings alone. Add the market's spread and total to see where Courtline would set them, which side it takes, and the fair price.</p>
</header>
<div class="calc">
  <form class="panel grid2" id="cf" novalidate>
    <label class="field"><span>Away team</span><select id="c-away"></select></label>
    <label class="field"><span>Home team</span><select id="c-home"></select></label>
    <label class="field"><span>Away rest</span><select id="c-arest"><option value="1">Back to back</option><option value="2" selected>1 day off</option><option value="3">2 days off</option><option value="4">3+ days off</option></select></label>
    <label class="field"><span>Home rest</span><select id="c-hrest"><option value="1">Back to back</option><option value="2" selected>1 day off</option><option value="3">2 days off</option><option value="4">3+ days off</option></select></label>
    <label class="field"><span>Home spread (optional, e.g. &minus;4.5)</span><input id="c-spread" type="number" step="0.5" inputmode="decimal"></label>
    <label class="field"><span>Total (optional, e.g. 226.5)</span><input id="c-total" type="number" step="0.5" inputmode="decimal"></label>
    <p class="full small muted" id="c-prefill"></p>
  </form>
  <div class="out" aria-live="polite">
    <div class="panel"><span class="eyebrow">From ratings alone</span><div class="stats" id="c-ratings"></div></div>
    <div class="panel" id="c-market-w"><span class="eyebrow">Against the market</span><div id="c-market"></div></div>
    <div class="panel"><span class="eyebrow">The two teams</span><div class="scroll"><table class="t" id="c-teams"></table></div></div>
  </div>
</div>
<p class="small muted" style="margin-top:1rem">Ratings come from games through {datetime.fromisoformat(D['data_through']).strftime('%B %-d')}. The model knows nothing about injuries, trades or lineups, so a missing star moves the real number more than anything here. Chances assume a normal spread of outcomes around the projection ({M['sd_ratings_margin']:.1f} points on the margin from ratings alone, {M['sd_margin']:.1f} with the market line).</p>
</main>
"""
calc_css = """<style>
.calc{display:grid;gap:1rem}
.out{display:grid;gap:1rem}
.verdict{font-size:1.05rem}.verdict strong{color:var(--accent-ink)}
.mrow{display:grid;grid-template-columns:repeat(auto-fit,minmax(12rem,1fr));gap:.9rem;margin-top:.5rem}
</style>
"""
calc_js = """<script>
(function(){
var D = __DATA__, M = D.model, $ = function(i){return document.getElementById(i)};
var T = {}; D.teams.forEach(function(t){T[t.team]=t});
var sorted = D.teams.slice().sort(function(a,b){return a.name.localeCompare(b.name)});
["c-away","c-home"].forEach(function(id){ $(id).innerHTML = sorted.map(function(t){return '<option value="'+t.team+'">'+t.name+'</option>'}).join("") });
function restSel(v){ return String(Math.max(1, Math.min(4, v))) }
var g = D.games.filter(function(x){return x.home_spread!==null})[0] || D.games[0];
if (g && T[g.home] && T[g.away]) {
  $("c-away").value=g.away; $("c-home").value=g.home; $("c-arest").value=restSel(g.away_rest); $("c-hrest").value=restSel(g.home_rest);
  if (g.home_spread!==null) $("c-spread").value=g.home_spread; if (g.total!==null) $("c-total").value=g.total;
  $("c-prefill").textContent = "Filled in with the next game on the board"+(g.home_spread!==null?" and its market number":"")+". Change anything.";
} else { $("c-away").value=sorted[0].team; $("c-home").value=sorted[1].team; }
function lin(c, f){ var s=c.intercept; for (var k in f) if (k in c) s+=c[k]*f[k]; return s }
function name(ab){ return T[ab]?T[ab].name:ab }
function pc(p){ return (100*p).toFixed(1)+"%" }
function render(){
  var a=T[$("c-away").value], h=T[$("c-home").value];
  if (!a||!h) return;
  var hr=+$("c-hrest").value, ar=+$("c-arest").value;
  var f={ d_net:(h.ortg-h.drtg)-(a.ortg-a.drtg), h_b2b:hr===1?1:0, a_b2b:ar===1?1:0, rest_diff:hr-ar };
  var exp=(h.pace+a.pace)/2*((h.ortg+a.drtg)/2+(a.ortg+h.drtg)/2)/100;
  var ft={ exp_total:exp, pace_sum:h.pace+a.pace, off_sum:h.ortg+a.ortg, def_sum:h.drtg+a.drtg, h_b2b:f.h_b2b, a_b2b:f.a_b2b };
  var rm=lin(M.ratings_margin,f), rt=lin(M.ratings_total,{exp_total:exp,h_b2b:f.h_b2b,a_b2b:f.a_b2b});
  var pH=CL.phi(rm/M.sd_ratings_margin), fav=rm>=0?h:a, pf=rm>=0?pH:1-pH;
  var same = a.team===h.team;
  $("c-ratings").innerHTML = same ? '<p>Pick two different teams.</p>' :
    '<div class="stat"><span class="big">'+(Math.abs(rm)<0.05?'Even':fav.team+' by '+Math.abs(rm).toFixed(1))+'</span><span class="what">Projected margin</span><span class="n">'+name(fav.team)+' wins '+pc(pf)+' of the time</span></div>'+
    '<div class="stat"><span class="big">'+rt.toFixed(1)+'</span><span class="what">Projected total</span><span class="n">Both teams combined</span></div>'+
    '<div class="stat"><span class="big">'+CL.fmt(CL.fair(pf))+'</span><span class="what">Fair price, '+fav.team+'</span><span class="n">'+(rm>=0?a:h).team+' fair: '+CL.fmt(CL.fair(1-pf))+'</span></div>';
  var sp=$("c-spread").value, tt=$("c-total").value, out="";
  if (!same && sp!=="" && !isNaN(+sp)) {
    var vm=-(+sp), sm=vm+lin(M.spread,f), edge=sm-vm, side=edge>=0?h:a, line=edge>=0?+sp:-(+sp);
    var ch=CL.phi(Math.abs(edge)/M.sd_margin);
    out+='<div class="mrow"><div class="stat"><span class="big">'+(Math.abs(sm)<0.05?'Even':(sm>=0?h:a).team+' by '+Math.abs(sm).toFixed(1))+'</span><span class="what">Courtline margin</span><span class="n">Market: '+(vm>=0?h:a).team+' by '+Math.abs(vm).toFixed(1)+'</span></div>'+
      '<div class="stat"><span class="big">'+side.team+' '+(line>0?'+':line<0?'\\u2212':'')+Math.abs(line)+'</span><span class="what">Courtline\\'s side</span><span class="n">'+(Math.abs(edge)>=D.th.spread?'Lean, ':'')+Math.abs(edge).toFixed(1)+' pts off · covers '+pc(ch)+'</span></div></div>';
  }
  if (!same && tt!=="" && !isNaN(+tt)) {
    var vt=+tt; ft.v_total=vt; var tm=vt+lin(M.total,ft), te=tm-vt, oc=CL.phi(te/M.sd_total), up=te>=0;
    out+='<div class="mrow"><div class="stat"><span class="big">'+tm.toFixed(1)+'</span><span class="what">Courtline total</span><span class="n">Market: '+vt+'</span></div>'+
      '<div class="stat"><span class="big">'+(up?'Over ':'Under ')+vt+'</span><span class="what">Courtline\\'s side</span><span class="n">'+(Math.abs(te)>=D.th.total?'Lean, ':'')+Math.abs(te).toFixed(1)+' pts off · hits '+pc(up?oc:1-oc)+'</span></div></div>';
  }
  $("c-market").innerHTML = out || '<p class="muted">Enter the home spread or the total to compare with the market.</p>';
  var row=function(l,x,y){return '<tr><td>'+l+'</td><td class="r m">'+x+'</td><td class="r m">'+y+'</td></tr>'};
  $("c-teams").innerHTML='<thead><tr><th></th><th class="r">'+a.team+'</th><th class="r">'+h.team+'</th></tr></thead><tbody>'+
    row('Record',a.wins+'\\u2013'+a.losses,h.wins+'\\u2013'+h.losses)+row('Off. rating',a.ortg.toFixed(1),h.ortg.toFixed(1))+row('Def. rating',a.drtg.toFixed(1),h.drtg.toFixed(1))+
    row('Net',(a.ortg-a.drtg).toFixed(1),(h.ortg-h.drtg).toFixed(1))+row('Pace',a.pace.toFixed(1),h.pace.toFixed(1))+'</tbody>';
}
["c-away","c-home","c-arest","c-hrest","c-spread","c-total"].forEach(function(id){ $(id).addEventListener("input",render); $(id).addEventListener("change",render) });
document.addEventListener("cl-odds",render); render();
})();
</script>
""".replace("__DATA__", json.dumps(calc_data, separators=(",", ":")))
page("calculator.html", "Courtline Matchup Calculator",
     "Pick any two NBA teams, their rest and a market line to see Courtline's projected margin, total, side and fair price.",
     calc_css + calc_body, calc_js)

# ------------------------------------------------------------------ bet log
bet_games = [dict(id=g["game_id"], tip=g["tip"], home=g["home"], away=g["away"], hn=g["home_name"], an=g["away_name"], final=g["final"],
                  hs=g["home_score"], as_=g["away_score"], sp=g.get("home_spread"), tot=g.get("total"), pm=g.get("proj_margin"),
                  pt=g.get("proj_total"), rm=g["ratings_margin"], rt=g["ratings_total"])
             for g in GAMES if (not g["final"]) or g.get("home_spread") is not None]
bet_data = dict(games=bet_games, sd=dict(m=M["sd_margin"], t=M["sd_total"], rm=M["sd_ratings_margin"], rt=M["sd_ratings_total"]))
bet_body = """<main class="wrap">
<header class="page-head">
  <span class="eyebrow">Bet log</span>
  <h1>Log a bet, see the meter</h1>
  <p class="lede">Pick a game and a bet. The meter shows Courtline's chance that the bet wins next to the chance the price needs to break even. Pending bets grade themselves once the game is final here.</p>
  <p class="small muted">Your bets are saved in this browser only. Nothing is sent anywhere, so export a copy now and then to keep it safe or move it to another device.</p>
</header>
<section class="panel" aria-labelledby="sb-h"><h2 id="sb-h" style="font-size:1.4rem">Scoreboard</h2><div class="stats" id="kpis"></div><p class="small muted" id="kpi-sim"></p></section>
<section class="panel" aria-labelledby="form-h" style="margin-top:1rem">
  <h2 id="form-h" style="font-size:1.4rem">Log a bet</h2>
  <form id="f" class="grid2" novalidate>
    <label class="field full"><span>Game</span><select id="f-game"></select></label>
    <label class="field full" id="f-desc-w" hidden><span>Game (type it in)</span><input id="f-desc" type="text" autocomplete="off" placeholder="e.g. Lakers at Celtics, Dec 25"></label>
    <label class="field"><span>Bet type</span><select id="f-market"><option value="spread">Spread</option><option value="over">Total: over</option><option value="under">Total: under</option><option value="ml">Moneyline</option></select></label>
    <label class="field" id="f-team-w"><span>Team</span><select id="f-team"></select></label>
    <label class="field" id="f-line-w"><span id="f-line-l">Line (your side, e.g. +3.5)</span><input id="f-line" type="number" step="0.5" inputmode="decimal"></label>
    <label class="field"><span id="f-odds-l">Odds</span><input id="f-odds" type="number" step="any" inputmode="decimal"></label>
    <label class="field"><span>Stake ($)</span><input id="f-stake" type="number" step="1" min="0" inputmode="decimal" value="20"></label>
    <label class="field"><span>Result</span><select id="f-result"><option value="pending">Pending</option><option value="win">Win</option><option value="loss">Loss</option><option value="push">Push</option></select></label>
    <label class="field"><span>Real or practice</span><select id="f-kind"><option value="real">Real bet</option><option value="sim">Practice (kept separate)</option></select></label>
    <label class="field full"><span>Notes</span><input id="f-notes" type="text" autocomplete="off" placeholder="Why you liked it"></label>
    <div class="meter full" id="meter" aria-live="polite"></div>
    <div class="full actions" style="align-items:center"><button type="submit" class="btn primary" id="f-save">Save bet</button><button type="button" class="btn" id="f-cancel" hidden>Cancel edit</button><span class="msg" id="f-msg"></span></div>
  </form>
</section>
<section class="panel" aria-labelledby="led-h" style="margin-top:1rem">
  <h2 id="led-h" style="font-size:1.4rem">Ledger</h2>
  <div class="actions"><button type="button" class="btn small" id="l-export">Export bets</button><button type="button" class="btn small" id="l-import">Import bets</button>
    <input type="file" id="l-file" accept="application/json,.json" hidden><span class="msg" id="l-msg"></span></div>
  <div class="bets" id="bets"></div>
</section>
</main>
"""
bet_css = """<style>
.meter{display:grid;gap:.45rem;padding:.8rem .9rem;background:var(--sunk);border-radius:8px}
.m-bar{position:relative;height:14px;border-radius:999px;background:linear-gradient(90deg,#C0392B 0%,#D98A1E 45%,#C9B23A 55%,#2E9E5B 100%)}
.m-mark{position:absolute;top:-5px;width:4px;height:24px;margin-left:-2px;background:var(--ink);border-radius:2px;box-shadow:0 0 0 2px var(--sunk)}
.m-be{position:absolute;top:-3px;width:2px;height:20px;margin-left:-1px;background:var(--surface);opacity:.95}
.m-scale{display:flex;justify-content:space-between;font:600 .68rem var(--font-mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.m-text{font-size:.95rem}.m-text strong.good{color:var(--good)}.m-text strong.bad{color:var(--bad)}
.bets{display:grid;gap:.6rem}
.bet{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:.3rem .8rem;padding:.75rem .85rem;border:1px solid var(--line);border-radius:8px;background:var(--bg)}
.bet .who{font-weight:600}.bet .meta{font-size:.85rem;color:var(--muted)}
.bet .right{text-align:right;display:grid;gap:.3rem;justify-items:end}
.bet .acts{display:flex;gap:.4rem}.bet .acts button{font:600 .78rem var(--font-body);background:none;border:0;color:var(--accent-ink);cursor:pointer;padding:0}
.empty{color:var(--muted);font-size:.95rem}
</style>
"""
bet_js = r"""<script>
(function(){
var D = __DATA__, $ = function(i){return document.getElementById(i)};
var KEY = "courtline-bets", bets = [], stored = true, editing = null;
try { bets = JSON.parse(localStorage.getItem(KEY) || "[]"); if (!Array.isArray(bets)) bets = []; } catch (e) { stored = false; bets = []; }
function save(){ try { localStorage.setItem(KEY, JSON.stringify(bets)); } catch (e) { stored = false; } }
var G = {}; D.games.forEach(function(g){ G[g.id] = g; });
function esc(s){ return String(s == null ? "" : s).replace(/[&<>"']/g, function(c){ return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]; }); }
function etDate(ts, opt){ return new Date(ts).toLocaleString("en-US", Object.assign({ timeZone: "America/New_York" }, opt)); }
function gameLabel(g){ return etDate(g.tip, {month:"short", day:"numeric"}) + " · " + g.an + " at " + g.hn; }
// game picker: upcoming first, then finals (most recent first)
var up = D.games.filter(function(g){return !g.final}).sort(function(a,b){return a.tip<b.tip?-1:1});
var fin = D.games.filter(function(g){return g.final}).sort(function(a,b){return a.tip<b.tip?1:-1});
$("f-game").innerHTML = (up.length ? '<optgroup label="Upcoming">' + up.map(function(g){return '<option value="'+g.id+'">'+esc(gameLabel(g))+'</option>'}).join("") + '</optgroup>' : "") +
  '<optgroup label="Final">' + fin.map(function(g){return '<option value="'+g.id+'">'+esc(gameLabel(g))+' (final)</option>'}).join("") + '</optgroup>' +
  '<option value="other">Another game (no Courtline number)</option>';
function selGame(){ var v = $("f-game").value; return v === "other" ? null : G[v]; }
function fillTeams(keep){
  var g = selGame(), cur = keep || $("f-team").value;
  $("f-desc-w").hidden = !!g;
  $("f-team").innerHTML = g ? ['away','home'].map(function(s){ var ab = g[s], nm = s==='home'?g.hn:g.an; return '<option value="'+ab+'">'+esc(nm)+'</option>'; }).join("")
    : '<option value="A">Team A</option><option value="B">Team B</option>';
  if (cur && Array.prototype.some.call($("f-team").options, function(o){return o.value===cur})) $("f-team").value = cur;
}
function setLabels(){
  var m = $("f-market").value;
  $("f-team-w").hidden = (m === "over" || m === "under");
  $("f-line-w").hidden = (m === "ml");
  $("f-line-l").textContent = m === "spread" ? "Line (your side, e.g. +3.5)" : "Total (e.g. 226.5)";
  $("f-odds-l").textContent = CL.format() === "dec" ? "Odds (decimal, e.g. 1.91)" : "Odds (American, e.g. \u2212110)";
}
function readOdds(){
  var v = $("f-odds").value; if (v === "" || isNaN(+v)) return null;
  v = +v;
  if (CL.format() === "dec") return v > 1 ? CL.toAm(v) : null;
  return (v >= 100 || v <= -100) ? v : null;
}
function showOdds(am){ if (am == null) return ""; return CL.format() === "dec" ? CL.toDec(am).toFixed(2) : String(Math.round(am)); }
function chance(b){
  var g = G[b.game]; if (!g) return null;
  var m = g.pm != null ? g.pm : g.rm, sm = g.pm != null ? D.sd.m : D.sd.rm;
  var t = g.pt != null ? g.pt : g.rt, st = g.pt != null ? D.sd.t : D.sd.rt;
  if (b.market === "spread") { if (b.line == null) return null; return b.team === g.home ? CL.phi((m + b.line)/sm) : CL.phi((b.line - m)/sm); }
  if (b.market === "over") { if (b.line == null) return null; return CL.phi((t - b.line)/st); }
  if (b.market === "under") { if (b.line == null) return null; return 1 - CL.phi((t - b.line)/st); }
  if (b.market === "ml") { var ph = CL.phi(m/sm); return b.team === g.home ? ph : 1 - ph; }
  return null;
}
function readForm(){
  var g = selGame(), m = $("f-market").value, line = $("f-line").value;
  return { id: editing || ("b" + Date.now().toString(36)), game: g ? g.id : null, desc: g ? gameLabel(g) : $("f-desc").value.trim(),
    market: m, team: (m === "over" || m === "under") ? null : $("f-team").value,
    teamName: (m === "over" || m === "under") ? null : $("f-team").options[$("f-team").selectedIndex].text,
    line: (m === "ml" || line === "" || isNaN(+line)) ? null : +line, odds: readOdds(), stake: +$("f-stake").value || 0,
    result: $("f-result").value, kind: $("f-kind").value, notes: $("f-notes").value.trim(), tip: g ? g.tip : null };
}
function pickText(b){
  var s = b.market === "spread" ? (b.teamName + " " + (b.line > 0 ? "+" : b.line < 0 ? "\u2212" : "") + Math.abs(b.line)) :
    b.market === "ml" ? (b.teamName + " moneyline") : ((b.market === "over" ? "Over " : "Under ") + b.line);
  return s;
}
function meterHTML(b){
  var c = chance(b), be = b.odds != null ? CL.implied(b.odds) : null;
  if (c == null && be == null) return '<p class="m-text muted">Pick a game, a bet and a price to see the meter.</p>';
  var h = '<div class="m-bar">' + (be != null ? '<span class="m-be" style="left:'+(100*be).toFixed(1)+'%" title="Breakeven"></span>' : '') +
          (c != null ? '<span class="m-mark" style="left:'+(100*c).toFixed(1)+'%" title="Courtline"></span>' : '') + '</div>' +
          '<div class="m-scale"><span>Long shot</span><span>Coin flip</span><span>Safe</span></div>';
  var t = "";
  if (c != null) t += 'Courtline gives this <strong>' + (100*c).toFixed(1) + '%</strong>. ';
  else t += 'No Courtline number for this game. ';
  if (be != null) t += 'The price needs ' + (100*be).toFixed(1) + '% to break even. ';
  if (c != null && be != null) { var d = 100*(c - be); t += d >= 0 ? '<strong class="good">Courtline\u2019s chance beats the price by ' + d.toFixed(1) + ' points.</strong>' : '<strong class="bad">The price asks ' + (-d).toFixed(1) + ' points more than Courtline\u2019s chance.</strong>'; }
  return h + '<p class="m-text">' + t + '</p>';
}
function update(){ $("meter").innerHTML = meterHTML(readForm()); }
function autoGrade(b){
  var g = G[b.game]; if (!g || !g.final || b.result !== "pending") return;
  var m = g.hs - g.as_, tot = g.hs + g.as_, r = null;
  if (b.market === "spread" && b.line != null) { var x = (b.team === g.home ? m : -m) + b.line; r = x > 0 ? "win" : x < 0 ? "loss" : "push"; }
  else if ((b.market === "over" || b.market === "under") && b.line != null) { var y = (tot - b.line) * (b.market === "over" ? 1 : -1); r = y > 0 ? "win" : y < 0 ? "loss" : "push"; }
  else if (b.market === "ml") { var w = b.team === g.home ? m > 0 : m < 0; r = m === 0 ? "push" : (w ? "win" : "loss"); }
  if (r) { b.result = r; b.auto = true; }
}
function profit(b){ if (b.result === "win") return b.odds != null ? b.stake * (CL.toDec(b.odds) - 1) : 0; if (b.result === "loss") return -b.stake; return 0; }
function money(v){ return (v < 0 ? "\u2212$" : "$") + Math.abs(v).toFixed(2); }
function kpis(list){
  var w = 0, l = 0, p = 0, st = 0, pr = 0, pend = 0;
  list.forEach(function(b){ if (b.result === "pending") { pend++; return; } st += b.stake; pr += profit(b); if (b.result === "win") w++; else if (b.result === "loss") l++; else p++; });
  return { w: w, l: l, p: p, st: st, pr: pr, pend: pend, roi: st ? 100 * pr / st : null };
}
function render(){
  bets.forEach(autoGrade); save();
  var real = bets.filter(function(b){return b.kind !== "sim"}), sim = bets.filter(function(b){return b.kind === "sim"});
  var k = kpis(real);
  $("kpis").innerHTML = '<div class="stat"><span class="big">'+k.w+'\u2013'+k.l+(k.p?'\u2013'+k.p:'')+'</span><span class="what">Record</span><span class="n">'+k.pend+' pending</span></div>'+
    '<div class="stat"><span class="big">'+money(k.pr)+'</span><span class="what">Profit</span><span class="n">on '+money(k.st)+' staked</span></div>'+
    '<div class="stat"><span class="big">'+(k.roi==null?'\u2013':k.roi.toFixed(1)+'%')+'</span><span class="what">Return on stake</span><span class="n">Real bets only</span></div>';
  var ks = kpis(sim);
  $("kpi-sim").textContent = sim.length ? ("Practice bets: " + ks.w + "\u2013" + ks.l + (ks.p ? "\u2013" + ks.p : "") + ", " + money(ks.pr) + " on " + money(ks.st) + " staked.") : "";
  var list = bets.slice().sort(function(a,b){ return (b.tip||"") < (a.tip||"") ? -1 : 1; });
  $("bets").innerHTML = list.length ? list.map(function(b){
    var c = chance(b), pl = b.result === "pending" ? "" : money(profit(b));
    return '<article class="bet"><div><div class="who">'+esc(pickText(b))+' <span class="muted">at</span> '+(b.odds!=null?'<span class="odds" data-am="'+b.odds+'">'+CL.fmt(b.odds)+'</span>':'\u2013')+'</div>'+
      '<div class="meta">'+esc(b.desc)+' \u00b7 '+money(b.stake)+(b.kind==="sim"?' \u00b7 practice':'')+(c!=null?' \u00b7 Courtline '+(100*c).toFixed(1)+'%':'')+'</div>'+
      (b.notes?'<div class="meta">'+esc(b.notes)+'</div>':'')+'</div>'+
      '<div class="right"><span class="pill '+(b.result==="win"?"win":b.result==="loss"?"loss":"")+'">'+b.result+(b.auto?' \u00b7 auto':'')+'</span><span class="mono small">'+pl+'</span>'+
      '<span class="acts"><button type="button" data-edit="'+b.id+'">Edit</button><button type="button" data-del="'+b.id+'">Delete</button></span></div></article>';
  }).join("") : '<p class="empty">No bets yet. Log one above and it shows up here.</p>';
  if (!stored) $("l-msg").textContent = "This browser is blocking storage, so bets last only until you close the page. Export to keep them.";
}
function resetForm(){ editing = null; $("f").reset(); $("f-stake").value = 20; $("f-cancel").hidden = true; $("f-save").textContent = "Save bet"; fillTeams(); setLabels(); prefillLine(); $("f-odds").value = showOdds(-110); update(); }
$("f").addEventListener("submit", function(ev){
  ev.preventDefault();
  var b = readForm();
  if (!b.game && !b.desc) { $("f-msg").textContent = "Pick a game or type one in."; return; }
  if (b.market !== "ml" && b.line == null) { $("f-msg").textContent = "Enter the line you got."; return; }
  if (b.odds == null) { $("f-msg").textContent = CL.format() === "dec" ? "Enter decimal odds above 1, like 1.91." : "Enter American odds like \u2212110 or +150."; return; }
  if (b.result === "pending") b.auto = false;
  var i = bets.findIndex(function(x){return x.id === b.id});
  if (i >= 0) bets[i] = b; else bets.push(b);
  render(); $("f-msg").textContent = i >= 0 ? "Bet updated." : "Bet saved."; resetForm();
});
$("f-cancel").addEventListener("click", function(){ resetForm(); $("f-msg").textContent = ""; });
$("bets").addEventListener("click", function(ev){
  var id = ev.target.getAttribute("data-edit"), del = ev.target.getAttribute("data-del");
  if (del) {
    if (ev.target.getAttribute("data-confirm")) { bets = bets.filter(function(x){return x.id !== del}); render(); $("l-msg").textContent = "Bet deleted."; }
    else { ev.target.setAttribute("data-confirm", "1"); ev.target.textContent = "Tap again to delete"; }
    return;
  }
  if (!id) return;
  var b = bets.find(function(x){return x.id === id}); if (!b) return;
  editing = b.id;
  $("f-game").value = b.game ? String(b.game) : "other"; if (!b.game) $("f-desc").value = b.desc || "";
  $("f-market").value = b.market; fillTeams(b.team); setLabels();
  $("f-line").value = b.line == null ? "" : b.line; $("f-odds").value = showOdds(b.odds); $("f-stake").value = b.stake;
  $("f-result").value = b.result; $("f-kind").value = b.kind; $("f-notes").value = b.notes || "";
  $("f-cancel").hidden = false; $("f-save").textContent = "Update bet"; update();
  $("f").scrollIntoView({ behavior: "smooth", block: "start" });
});
$("l-export").addEventListener("click", function(){
  var blob = new Blob([JSON.stringify({ app: "courtline-bet-log", exported: new Date().toISOString(), bets: bets }, null, 1)], { type: "application/json" });
  var a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "courtline-bets-" + new Date().toISOString().slice(0,10) + ".json";
  document.body.appendChild(a); a.click(); a.remove(); $("l-msg").textContent = "Exported " + bets.length + " bets.";
});
$("l-import").addEventListener("click", function(){ $("l-file").click(); });
$("l-file").addEventListener("change", function(){
  var f = this.files[0]; if (!f) return;
  var r = new FileReader();
  r.onload = function(){
    try { var d = JSON.parse(r.result), list = Array.isArray(d) ? d : d.bets; if (!Array.isArray(list)) throw 0;
      var ids = {}; bets.forEach(function(b){ ids[b.id] = 1; }); var n = 0;
      list.forEach(function(b){ if (b && b.id && !ids[b.id]) { bets.push(b); n++; } });
      render(); $("l-msg").textContent = "Imported " + n + " new bets.";
    } catch (e) { $("l-msg").textContent = "That file is not a Courtline bet export."; }
  };
  r.readAsText(f); this.value = "";
});
["f-game","f-market","f-team","f-line","f-odds","f-stake"].forEach(function(id){ $(id).addEventListener("input", update); $(id).addEventListener("change", update); });
$("f-game").addEventListener("change", function(){ fillTeams(); prefillLine(); update(); });
$("f-market").addEventListener("change", function(){ setLabels(); prefillLine(); update(); });
$("f-team").addEventListener("change", function(){ prefillLine(); update(); });
function prefillLine(){
  var g = selGame(), m = $("f-market").value; if (!g) return;
  if (m === "spread" && g.sp != null) { $("f-line").value = $("f-team").value === g.home ? g.sp : -g.sp; }
  else if ((m === "over" || m === "under") && g.tot != null) { $("f-line").value = g.tot; }
}
var lastFmt = CL.format();
document.addEventListener("cl-odds", function(){
  var v = $("f-odds").value;
  if (v !== "" && !isNaN(+v)) {
    var am = lastFmt === "dec" ? (+v > 1 ? CL.toAm(+v) : null) : +v;
    $("f-odds").value = am == null ? "" : showOdds(am);
  }
  lastFmt = CL.format(); setLabels(); update(); render();
});
fillTeams(); setLabels(); prefillLine(); $("f-odds").value = showOdds(-110); update(); render();
})();
</script>
""".replace("__DATA__", json.dumps(bet_data, separators=(",", ":")))
page("bet-log.html", "Courtline Bet Log",
     "Log NBA bets and see Courtline's chance against the price. Bets are saved in your browser only, with export and import.",
     bet_css + bet_body, bet_js)

print("built", ", ".join(f for f, *_ in PAGES), "| upcoming", len(upcoming), "| graded", S["graded"])
