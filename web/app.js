"use strict";

// QTc arithmetic for education only. This is not a Chan nomogram classifier.
function calculateQT(qtValue, hrValue) {
  const qt = Number(qtValue), hr = Number(hrValue);
  if (String(qtValue).trim() === "" || !Number.isFinite(qt) || qt < 100 || qt > 1000)
    throw new RangeError("QT must be a finite number between 100 and 1000 ms.");
  if (String(hrValue).trim() === "" || !Number.isFinite(hr) || hr < 20 || hr > 220)
    throw new RangeError("Heart rate must be a finite number between 20 and 220 bpm.");
  const rr = 60 / hr;
  const round = n => Math.round(n * 10) / 10;
  const bazett = qt / Math.sqrt(rr);
  const fridericia = qt / Math.cbrt(rr);
  return Object.freeze({
    qt_ms: round(qt), hr_bpm: round(hr), rr_ms: round(rr * 1000),
    qtc_bazett_ms: round(bazett), qtc_fridericia_ms: round(fridericia),
    bazett_500ms_screen: bazett >= 500, chan_nomogram_assessed: false
  });
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { calculateQT };

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("qt-form");
    const result = document.getElementById("result");
    const err = document.getElementById("error");
    const copy = document.getElementById("copy");
    let last = null;
    form.addEventListener("submit", e => {
      e.preventDefault();
      err.textContent = "";
      result.hidden = true;
      copy.disabled = true;
      try {
        last = calculateQT(document.getElementById("qt").value, document.getElementById("hr").value);
        document.getElementById("rr-out").textContent = last.rr_ms;
        document.getElementById("bazett-out").textContent = last.qtc_bazett_ms;
        document.getElementById("fridericia-out").textContent = last.qtc_fridericia_ms;
        const flag = document.getElementById("flag");
        flag.textContent = last.bazett_500ms_screen ?
          "Bazett QTc is at least 500 ms: clinical evaluation threshold, not an event prediction." :
          "Bazett QTc is below 500 ms. This does not exclude torsades de pointes.";
        flag.className = last.bazett_500ms_screen ? "high" : "low";
        result.hidden = false;
        copy.disabled = false;
      } catch (e) {
        last = null;
        err.textContent = e.message;
      }
    });
    copy.addEventListener("click", async () => {
      if (!last) return;
      try {
        await navigator.clipboard.writeText(JSON.stringify(last, null, 2));
        copy.textContent = "Copied";
      } catch (e) {
        err.textContent = "Clipboard unavailable: select the results to copy manually.";
      }
    });
    form.addEventListener("input", () => { copy.textContent = "Copy JSON"; });
    form.requestSubmit();
  });
}
