# In-game page for site/build.py (run with exec inside build.py, so it shares its names: D, M, GAMES, page, e, ...).
# Live scores come from ESPN's public scoreboard, read in the viewer's browser every 30 seconds.
# The live win chance uses data/live_model.json, trained by live_train.py on 2020 to 2026 play by play.
LM = json.load(open(os.path.join(REPO, "data", "live_model.json"), encoding="utf-8"))
LT = LM["test"]

pregame = {}
for g in GAMES:
    if g["final"]:
        continue
    if g.get("home_spread") is not None:
        mu, src = -g["home_spread"], "market"
    elif g.get("proj_margin") is not None:
        mu, src = g["proj_margin"], "courtline"
    else:
        mu, src = g["ratings_margin"], "ratings"
    pregame[str(g["game_id"])] = dict(mu=mu, src=src, home=g["home"], away=g["away"], hn=g["home_name"], an=g["away_name"],
                                      home_rest=g["home_rest"], away_rest=g["away_rest"], spread=g.get("home_spread"),
                                      ml_home=g.get("ml_home"), ml_away=g.get("ml_away"), tip=g["tip"])
ig_data = dict(live=dict(a=LM["a"], b=LM["b"], d=LM["d"]), pregame=pregame,
               teams=[dict(team=r["team"], name=r["name"], ortg=r["ortg"], drtg=r["drtg"]) for r in D["ratings"]],
               rm=M["ratings_margin"])

cal_rows = "".join(f'<tr><td>{r["bin"]}</td><td class="r m">{r["states"]:,}</td><td class="r m">{100 * r["predicted"]:.1f}%</td><td class="r m">{100 * r["actual"]:.1f}%</td></tr>'
                   for r in LT["calibration"])
q_rows = "".join(f'<tr><td>{r["quarter"]}</td><td class="r m">{100 * r["accuracy"]:.1f}%</td><td class="r m">{r["brier"]:.3f}</td></tr>' for r in LT["by_quarter"])
TOGI = ('<div class="odds-toggle inline" role="group" aria-label="Odds format"><button type="button" data-fmt="am" aria-pressed="true" title="American odds">&minus;110</button>'
        '<button type="button" data-fmt="dec" aria-pressed="false" title="Decimal odds">1.91x</button></div>')

ig_body = f"""<main class="wrap wide">
<header class="page-head">
  <span class="eyebrow">In-game · live</span>
  <h1>Live win chances</h1>
  <p class="lede">Today's games with live scores, Courtline's chance that each team wins from here, and a check for any live moneyline you are looking at. Type the price your book shows and see whether it is worth it right now.</p>
  <div class="ig-status"><span class="dot" id="ig-dot" aria-hidden="true"></span><span id="ig-status" class="small muted">Loading live scores…</span>
    <button type="button" class="btn small" id="ig-refresh">Refresh now</button><span class="small muted">Prices as</span>{TOGI}</div>
</header>
<div id="ig-games" class="ig-games"><div class="panel"><p class="muted">Loading today's games…</p></div></div>

<section class="block" aria-labelledby="man-h">
  <span class="eyebrow">Set it yourself</span>
  <h2 id="man-h">Any score, any clock</h2>
  <p>If live scores do not load, or you want to ask "what if", set the game state by hand.</p>
  <form class="panel grid2" id="mf" novalidate>
    <label class="field"><span>Away team</span><select id="m-away"></select></label>
    <label class="field"><span>Home team</span><select id="m-home"></select></label>
    <label class="field"><span>Away score</span><input id="m-as" type="number" min="0" step="1" inputmode="numeric" value="0"></label>
    <label class="field"><span>Home score</span><input id="m-hs" type="number" min="0" step="1" inputmode="numeric" value="0"></label>
    <label class="field"><span>Quarter</span><select id="m-q"><option value="1">1st</option><option value="2">2nd</option><option value="3">3rd</option><option value="4">4th</option><option value="5">Overtime</option></select></label>
    <label class="field"><span>Time left in the quarter (m:ss)</span><input id="m-clock" type="text" inputmode="numeric" value="12:00" autocomplete="off"></label>
    <label class="field"><span>Pregame home spread (e.g. &minus;4.5)</span><input id="m-spread" type="number" step="0.5" inputmode="decimal"></label>
    <div class="field full"><span>Live moneylines (optional)</span><div class="ig-prices"><input id="m-pa" type="number" step="any" inputmode="decimal" aria-label="Away moneyline" placeholder="Away"><input id="m-ph" type="number" step="any" inputmode="decimal" aria-label="Home moneyline" placeholder="Home"></div></div>
    <div class="full" id="m-out" aria-live="polite"></div>
  </form>
</section>

<section class="block" aria-labelledby="how-ig-h">
  <span class="eyebrow">The model</span>
  <h2 id="how-ig-h">How the live chance works</h2>
  <p>The rest of a basketball game behaves a lot like a random walk. The live chance starts from the current margin, adds the pregame expected margin for the share of the game still to play, and allows less and less room for swings as the clock runs down. The weights were fitted on {LM['states']:,} real game states from {LM['games']:,} games ({LM['seasons']}), using the closing spread as the pregame expectation.</p>
  <p>Tested on {LT['games']:,} games from {LT['season']} that it was not trained on, it called the eventual winner {100 * LT['by_quarter'][0]['accuracy']:.0f}% of the time during the 1st quarter and {100 * LT['by_quarter'][3]['accuracy']:.0f}% during the 4th. When it said a team had a given chance, that team won about that often:</p>
  <div class="ig-tables">
    <div class="panel scroll" style="padding:0"><table class="t"><thead><tr><th>Courtline said</th><th class="r">Game states</th><th class="r">Average</th><th class="r">Home team won</th></tr></thead><tbody>{cal_rows}</tbody></table></div>
    <div class="panel scroll" style="padding:0"><table class="t"><thead><tr><th>Quarter</th><th class="r">Picked winner</th><th class="r">Brier score</th></tr></thead><tbody>{q_rows}</tbody></table></div>
  </div>
  <p class="small muted">Brier score is the average squared miss of the chance (0 is perfect, 0.25 is a coin flip). What it does not know: who has the ball, fouls to give, timeouts, injuries during the game, or a team resting its starters in a blowout. The last minute or two of a close game moves faster than any model, and live prices can change before you place a bet.</p>
</section>
</main>
"""
ig_css = """<style>
.ig-status{display:flex;flex-wrap:wrap;gap:.5rem .75rem;align-items:center}
.ig-status .dot{width:9px;height:9px;border-radius:50%;background:var(--muted)}
.ig-status .dot.live{background:var(--good);box-shadow:0 0 0 4px var(--good-soft)}
.ig-status .dot.err{background:var(--bad)}
.ig-games{display:grid;gap:.9rem;grid-template-columns:repeat(auto-fill,minmax(min(100%,22rem),1fr))}
.ig{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:.9rem 1rem;display:grid;gap:.65rem;min-width:0}
.ig.live{border-color:var(--accent)}
.ig-top{display:flex;justify-content:space-between;gap:.5rem;align-items:baseline;flex-wrap:wrap}
.ig-state{font:600 .78rem var(--font-mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.ig.live .ig-state{color:var(--accent-ink)}
.ig-row{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:.2rem .9rem;align-items:baseline}
.ig-row .tm{font-weight:600;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ig-row .sc{font:600 1.6rem var(--font-mono);font-variant-numeric:tabular-nums;text-align:right}
.ig-row .ch{font:600 1rem var(--font-mono);font-variant-numeric:tabular-nums;text-align:right;min-width:4.2rem}
.ig-bar{display:flex;height:8px;border-radius:999px;overflow:hidden;background:var(--sunk)}
.ig-bar span{display:block;height:100%;transition:width .4s ease}
.ig-bar .a{background:var(--muted)}.ig-bar .h{background:var(--accent)}
.ig-prices{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.5rem}
.ig-prices input{font:500 1rem var(--font-body);color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:.5rem .6rem;width:100%;min-width:0}
.ig-prices input:focus{border-color:var(--accent);outline:none;box-shadow:0 0 0 3px var(--accent-soft)}
.ig-v{font-size:.9rem;display:grid;gap:.15rem}
.good{color:var(--good);font-weight:600}.bad{color:var(--bad);font-weight:600}
.ig-tables{display:grid;gap:1rem;grid-template-columns:repeat(auto-fit,minmax(min(100%,20rem),1fr))}
@media (prefers-reduced-motion:reduce){.ig-bar span{transition:none}}
</style>
"""
ig_js = r"""<script>
(function(){
var D = __DATA__, L = D.live, $ = function(i){return document.getElementById(i)};
var URL_ = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard";
var T = {}; D.teams.forEach(function(t){ T[t.team] = t; });
function esc(s){ return String(s == null ? "" : s).replace(/[&<>"']/g, function(c){ return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]; }); }
function pc(p){ return (100*p).toFixed(1) + "%"; }
function secsLeft(period, clock){ if (period <= 0) return 2880; return period <= 4 ? (4 - period) * 720 + clock : clock; }
function winHome(margin, secs, mu){
  if (secs <= 0) return margin > 0 ? 1 : margin < 0 ? 0 : 0.5;
  var tau = secs / 2880 + L.d, z = L.a * margin / Math.sqrt(tau) + L.b * mu * Math.sqrt(tau);
  return 1 / (1 + Math.exp(-z));
}
function ratingsMu(h, a){
  var th = T[h], ta = T[a]; if (!th || !ta) return 0;
  var c = D.rm; return c.intercept + c.d_net * ((th.ortg - th.drtg) - (ta.ortg - ta.drtg));
}
function readPrice(el){ var v = el.value; if (v === "" || isNaN(+v)) return null; v = +v;
  if (CL.format() === "dec") return v > 1 ? CL.toAm(v) : null; return (v >= 100 || v <= -100) ? v : null; }
function showPrice(am){ if (am == null) return ""; return CL.format() === "dec" ? CL.toDec(am).toFixed(2) : String(Math.round(am)); }
function verdict(teamA, teamH, ph, pa, phm){
  var ia = pa != null ? CL.implied(pa) : null, ih = phm != null ? CL.implied(phm) : null;
  if (ia == null && ih == null) return '<span class="muted">Type a live price to check it.</span>';
  var both = ia != null && ih != null, sum = both ? ia + ih : null, out = "";
  [[teamA, pa, ia, 1 - ph], [teamH, phm, ih, ph]].forEach(function(r){
    if (r[1] == null) return;
    var d = 100 * (r[3] - r[2]);
    out += '<div><strong>' + esc(r[0]) + ' ' + CL.fmt(r[1]) + '</strong>: needs ' + pc(r[2]) + (both ? ', market ' + pc(r[2] / sum) + ' without the cut' : '') +
      ', Courtline ' + pc(r[3]) + '. ' + (d >= 0 ? '<span class="good">Worth it by ' + d.toFixed(1) + ' pts</span>' : '<span class="bad">Short by ' + (-d).toFixed(1) + ' pts</span>') + '</div>';
  });
  if (both) out += '<div class="small muted">The book’s cut on these two prices: ' + (100 * (sum - 1)).toFixed(1) + '%.</div>';
  return out;
}

// ------------------------------------------------ live board
var cards = {}, games = {};
function cardHTML(id){
  return '<article class="ig" id="g-' + id + '"><div class="ig-top"><span class="ig-state"></span><span class="small muted ig-pre"></span></div>' +
    '<div class="ig-row"><span class="tm ig-an"></span><span class="sc ig-as"></span><span class="ch ig-ac"></span></div>' +
    '<div class="ig-row"><span class="tm ig-hn"></span><span class="sc ig-hs"></span><span class="ch ig-hc"></span></div>' +
    '<div class="ig-bar" aria-hidden="true"><span class="a"></span><span class="h"></span></div>' +
    '<div class="small muted ig-fair"></div>' +
    '<div class="ig-prices"><input type="number" step="any" inputmode="decimal" class="ig-pa" aria-label="Away live moneyline"><input type="number" step="any" inputmode="decimal" class="ig-ph" aria-label="Home live moneyline"></div>' +
    '<div class="ig-v"></div></article>';
}
function q(card, cls){ return card.querySelector("." + cls); }
function paintCard(id){
  var g = games[id], c = cards[id]; if (!g || !c) return;
  var pre = D.pregame[id], mu = pre ? pre.mu : ratingsMu(g.home, g.away);
  var secs = g.state === "pre" ? 2880 : secsLeft(g.period, g.clock);
  var margin = g.hs - g.as_, ph = g.state === "post" ? (margin > 0 ? 1 : 0) : winHome(margin, secs, mu);
  c.classList.toggle("live", g.state === "in");
  q(c, "ig-state").textContent = g.detail;
  q(c, "ig-pre").textContent = g.state === "post" ? "" : pre && pre.spread != null ? "Pregame: " + (pre.spread < 0 ? g.home + " −" + Math.abs(pre.spread) : pre.spread > 0 ? g.away + " −" + pre.spread : "Pick'em") :
    (pre ? "Pregame: Courtline " + (mu >= 0 ? g.home : g.away) + " by " + Math.abs(mu).toFixed(1) : "No pregame number; ratings only");
  q(c, "ig-an").textContent = g.an; q(c, "ig-hn").textContent = g.hn;
  q(c, "ig-as").textContent = g.state === "pre" ? "" : g.as_; q(c, "ig-hs").textContent = g.state === "pre" ? "" : g.hs;
  q(c, "ig-ac").textContent = pc(1 - ph); q(c, "ig-hc").textContent = pc(ph);
  q(c, "a").style.width = (100 * (1 - ph)).toFixed(1) + "%"; q(c, "h").style.width = (100 * ph).toFixed(1) + "%";
  var done = g.state === "post";
  q(c, "ig-prices").hidden = done;
  q(c, "ig-pa").placeholder = g.away + " price"; q(c, "ig-ph").placeholder = g.home + " price";
  q(c, "ig-fair").innerHTML = done ? "Final." : ("Fair price now: " + esc(g.away) + " " + CL.fmt(CL.fair(1 - ph)) + " · " + esc(g.home) + " " + CL.fmt(CL.fair(ph)) +
    (g.state === "pre" ? ". Before tip this is the pregame chance; it moves with the score once the game starts." : ""));
  q(c, "ig-v").innerHTML = done ? "" : verdict(g.away, g.home, ph, readPrice(q(c, "ig-pa")), readPrice(q(c, "ig-ph")));
}
function setStatus(cls, text){ $("ig-dot").className = "dot " + cls; $("ig-status").textContent = text; }
function load(){
  setStatus("", "Updating…");
  fetch(URL_, { cache: "no-store" }).then(function(r){ if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); }).then(function(j){
    var evs = (j.events || []).slice().sort(function(a, b){
      var ra = {in:0, pre:1, post:2}[a.status.type.state], rb = {in:0, pre:1, post:2}[b.status.type.state];
      return ra - rb || (a.date < b.date ? -1 : 1);
    });
    var wrap = $("ig-games"), live = 0;
    if (!evs.length) { wrap.innerHTML = '<div class="panel"><p>No NBA games on ESPN’s board today. Use the manual setter below.</p></div>'; cards = {}; }
    else if (!wrap.querySelector(".ig")) wrap.innerHTML = "";
    evs.forEach(function(ev){
      var comp = ev.competitions[0], st = ev.status, home = null, away = null;
      comp.competitors.forEach(function(x){ if (x.homeAway === "home") home = x; else away = x; });
      if (!home || !away) return;
      var id = String(ev.id);
      games[id] = { home: home.team.abbreviation, away: away.team.abbreviation, hn: home.team.shortDisplayName || home.team.displayName,
        an: away.team.shortDisplayName || away.team.displayName, hs: +home.score || 0, as_: +away.score || 0,
        state: st.type.state, period: st.period || 0, clock: +st.clock || 0,
        detail: st.type.state === "pre" ? new Date(ev.date).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone: "America/New_York" }) + " ET" : (st.type.shortDetail || st.type.detail || "") };
      if (st.type.state === "in") live++;
      if (!cards[id]) {
        wrap.insertAdjacentHTML("beforeend", cardHTML(id)); cards[id] = $("g-" + id);
        var pre = D.pregame[id];
        if (pre && st.type.state === "pre") { if (pre.ml_away != null) q(cards[id], "ig-pa").value = showPrice(pre.ml_away); if (pre.ml_home != null) q(cards[id], "ig-ph").value = showPrice(pre.ml_home); }
        ["ig-pa", "ig-ph"].forEach(function(cls){ q(cards[id], cls).addEventListener("input", function(){ paintCard(id); }); });
      }
      paintCard(id);
    });
    var now = new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", second: "2-digit" });
    setStatus(live ? "live" : "", (live ? live + (live === 1 ? " game live" : " games live") : "No games live right now") + ". Scores from ESPN, updated " + now + ", refreshing every 30 seconds.");
  }).catch(function(err){
    setStatus("err", "Live scores did not load (" + err.message + "). Try Refresh now, or set the game state by hand below.");
    if (!$("ig-games").querySelector(".ig")) $("ig-games").innerHTML = '<div class="panel"><p>Live scores are not available right now. The manual setter below works without them.</p></div>';
  });
}
var timer = null;
function start(){ if (timer) clearInterval(timer); timer = setInterval(function(){ if (document.visibilityState === "visible") load(); }, 30000); }
document.addEventListener("visibilitychange", function(){ if (document.visibilityState === "visible") load(); });
$("ig-refresh").addEventListener("click", load);

// ------------------------------------------------ manual setter
var sorted = D.teams.slice().sort(function(a, b){ return a.name.localeCompare(b.name); });
["m-away", "m-home"].forEach(function(id){ $(id).innerHTML = sorted.map(function(t){ return '<option value="' + t.team + '">' + esc(t.name) + '</option>'; }).join(""); });
var first = Object.keys(D.pregame).map(function(k){ return D.pregame[k]; }).sort(function(a, b){ return a.tip < b.tip ? -1 : 1; })[0];
if (first && T[first.home] && T[first.away]) { $("m-away").value = first.away; $("m-home").value = first.home; if (first.spread != null) $("m-spread").value = first.spread; }
else if (sorted.length > 1) { $("m-away").value = sorted[0].team; $("m-home").value = sorted[1].team; }
function manual(){
  var a = $("m-away").value, h = $("m-home").value;
  if (a === h) { $("m-out").innerHTML = '<p>Pick two different teams.</p>'; return; }
  var qn = +$("m-q").value, ck = ($("m-clock").value || "").trim().split(":"), clock = ck.length === 2 ? (+ck[0]) * 60 + (+ck[1]) : +ck[0] * 60;
  if (isNaN(clock)) clock = 0;
  clock = Math.max(0, Math.min(qn === 5 ? 300 : 720, clock));
  var sp = $("m-spread").value, mu = (sp !== "" && !isNaN(+sp)) ? -(+sp) : ratingsMu(h, a);
  var margin = (+$("m-hs").value || 0) - (+$("m-as").value || 0), ph = winHome(margin, secsLeft(qn, clock), mu);
  $("m-out").innerHTML = '<div class="panel" style="background:var(--sunk)"><div class="ig-row"><span class="tm">' + esc(T[a].name) + '</span><span></span><span class="ch">' + pc(1 - ph) + '</span></div>' +
    '<div class="ig-row"><span class="tm">' + esc(T[h].name) + '</span><span></span><span class="ch">' + pc(ph) + '</span></div>' +
    '<div class="ig-bar" aria-hidden="true"><span class="a" style="width:' + (100 * (1 - ph)).toFixed(1) + '%"></span><span class="h" style="width:' + (100 * ph).toFixed(1) + '%"></span></div>' +
    '<p class="small muted">Fair price: ' + a + ' ' + CL.fmt(CL.fair(1 - ph)) + ' · ' + h + ' ' + CL.fmt(CL.fair(ph)) + (sp === "" ? '. No spread entered, so the pregame expectation comes from team ratings.' : '') + '</p>' +
    '<div class="ig-v">' + verdict(a, h, ph, readPrice($("m-pa")), readPrice($("m-ph"))) + '</div></div>';
}
["m-away", "m-home", "m-as", "m-hs", "m-q", "m-clock", "m-spread", "m-pa", "m-ph"].forEach(function(id){ $(id).addEventListener("input", manual); $(id).addEventListener("change", manual); });

// ------------------------------------------------ odds format switch: convert typed prices, repaint
var lastFmt = CL.format();
document.addEventListener("cl-odds", function(){
  document.querySelectorAll(".ig-pa, .ig-ph, #m-pa, #m-ph").forEach(function(el){
    var v = el.value; if (v === "" || isNaN(+v)) return;
    var am = lastFmt === "dec" ? (+v > 1 ? CL.toAm(+v) : null) : +v; el.value = am == null ? "" : showPrice(am);
  });
  lastFmt = CL.format(); Object.keys(cards).forEach(paintCard); manual();
});
manual(); load(); start();
})();
</script>
""".replace("__DATA__", json.dumps(ig_data, separators=(",", ":")))
page("in-game.html", "Courtline In-game",
     "Live NBA scores with Courtline's live win chance for each team, plus a check for any live moneyline price.",
     ig_css + ig_body, ig_js)
