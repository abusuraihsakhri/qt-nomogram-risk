"use strict";
const {test} = require("node:test");
const assert = require("node:assert/strict");
const {calculateQT} = require("./app.js");
test("QTc at 60 bpm", () => {
  const x = calculateQT(440, 60);
  assert.equal(x.qtc_bazett_ms, 440);
  assert.equal(x.qtc_fridericia_ms, 440);
  assert.equal(x.chan_nomogram_assessed, false);
});
test("QTc reference input", () => {
  const x = calculateQT(420, 72);
  assert.equal(x.rr_ms, 833.3);
  assert.equal(x.qtc_bazett_ms, 460.1);
  assert.equal(x.qtc_fridericia_ms, 446.3);
});
test("500 ms screen is not nomogram", () => {
  assert.equal(calculateQT(500, 60).bazett_500ms_screen, true);
  assert.equal(calculateQT(499, 60).bazett_500ms_screen, false);
});
test("input validation", () => {
  for(const x of [[0,70],[500,0],[Infinity,70],["NaN",70],["",70],[400,""],[400,500]])
    assert.throws(() => calculateQT(...x), RangeError);
});
