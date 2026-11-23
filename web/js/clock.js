// Horloge optionnelle (5 min, 10 min, 3 min + 2 s) avec perte au temps.

import { showGameOver } from "./panels.js";
import { lsSet, state, wireChips } from "./state.js";

function clockBase() {
  const m = state.clockMode;
  if (m === "none") return null;
  if (m === "182") return { base: 180, inc: 2 };
  return { base: parseInt(m, 10), inc: 0 };
}

export function resetClock() {
  const c = clockBase();
  state.clock = c
    ? { w: c.base, b: c.base, inc: c.inc, active: state.turn, lastTs: null }
    : { w: 0, b: 0, inc: 0, active: null, lastTs: null };
  renderClocks();
}

function fmtClock(sec) {
  const s = Math.max(0, Math.ceil(sec));
  return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
}

export function renderClocks() {
  const mode = state.clockMode;
  for (const [elId, color] of [
    ["clock-top", state.flipped ? "w" : "b"],
    ["clock-bottom", state.flipped ? "b" : "w"],
  ]) {
    const el = document.getElementById(elId);
    if (!el) continue;
    if (mode === "none") {
      el.textContent = "";
      el.classList.remove("low");
    } else {
      el.textContent = fmtClock(state.clock[color]);
      el.classList.toggle("low", state.clock[color] <= 30);
    }
  }
}

function tickClock() {
  if (state.clockMode === "none" || state.reviewPly !== null) return;
  const now = performance.now();
  const c = state.clock;
  if (c.active) {
    if (c.lastTs != null) {
      c[c.active] = Math.max(0, c[c.active] - (now - c.lastTs) / 1000);
      if (c[c.active] <= 0) {
        const loser = c.active;
        c.active = null;
        c[loser] = 0;
        renderClocks();
        showGameOver(
          "Temps écoulé",
          `${loser === "w" ? "Les Blancs" : "Les Noirs"} perdent au temps — ${loser === "w" ? "les Noirs" : "les Blancs"} gagnent.`
        );
        return;
      }
    }
    c.lastTs = now;
  }
  renderClocks();
}

// Branche le groupe de chips d'horloge et démarre le tick (200 ms).
export function initClock() {
  setInterval(tickClock, 200);
  wireChips("opt-clock", (v) => {
    state.clockMode = v;
    lsSet("chess.clock", v);
    resetClock();
  }, state.clockMode);
}
