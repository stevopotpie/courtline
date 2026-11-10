/* Courtline shared script: odds format switch (American or decimal) and small math helpers.
   Any element <span class="odds" data-am="-110"></span> is rendered in the viewer's chosen format.
   Pages that draw odds themselves call CL.fmt(american) and listen for the "cl-odds" event. */
(function () {
  var KEY = "courtline-odds-format";
  var fmtPref = "am";
  try { var v = localStorage.getItem(KEY); if (v === "dec" || v === "am") fmtPref = v; } catch (e) {}

  function toDec(am) { am = Number(am); return am > 0 ? 1 + am / 100 : 1 + 100 / Math.abs(am); }
  function toAm(dec) { dec = Number(dec); return dec >= 2 ? Math.round((dec - 1) * 100) : Math.round(-100 / (dec - 1)); }
  function amText(am) { am = Math.round(Number(am)); return (am > 0 ? "+" : am < 0 ? "−" : "") + Math.abs(am); }
  function fmt(am) {
    if (am === null || am === undefined || am === "" || isNaN(Number(am))) return "—";
    return fmtPref === "dec" ? toDec(am).toFixed(2) + "x" : amText(am);
  }
  function implied(am) { return 1 / toDec(am); }
  function fair(p) { if (p <= 0 || p >= 1) return null; return p >= 0.5 ? -100 * p / (1 - p) : 100 * (1 - p) / p; }
  function phi(z) { var t = 1 / (1 + 0.2316419 * Math.abs(z)); var d = 0.3989423 * Math.exp(-z * z / 2);
    var p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274)))); return z > 0 ? 1 - p : p; }
  function paint() {
    document.querySelectorAll(".odds[data-am]").forEach(function (el) { el.textContent = fmt(el.getAttribute("data-am")); });
    document.querySelectorAll(".odds-toggle button").forEach(function (b) { b.setAttribute("aria-pressed", String(b.getAttribute("data-fmt") === fmtPref)); });
  }
  function set(f) {
    fmtPref = f;
    try { localStorage.setItem(KEY, f); } catch (e) {}
    paint();
    document.dispatchEvent(new CustomEvent("cl-odds", { detail: f }));
  }
  window.CL = { fmt: fmt, toDec: toDec, toAm: toAm, implied: implied, fair: fair, phi: phi,
    format: function () { return fmtPref; }, paint: paint };
  document.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest(".odds-toggle button");
    if (b) set(b.getAttribute("data-fmt"));
  });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", paint); else paint();
})();
