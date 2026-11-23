// Rendu du plateau : cases, coordonnées, pièces SVG, indices de coups,
// dernier coup, échec — plus la navigation dans l'historique (revue).

import { renderMovesTable, renderPlayers } from "./panels.js";
import { toast } from "./toasts.js";
import {
  FILES,
  isEpCapture,
  kingSquareOf,
  pieceSrc,
  setStatus,
  squareName,
  state,
  symAt,
} from "./state.js";

export const boardEl = document.getElementById("board");

export function sizeBoard() {
  const w = boardEl.clientWidth || 512;
  boardEl.style.setProperty("--sq", w / 8 + "px");
}
window.addEventListener("resize", sizeBoard);

export function render() {
  boardEl.innerHTML = "";
  const ranks = state.flipped ? [0, 1, 2, 3, 4, 5, 6, 7] : [7, 6, 5, 4, 3, 2, 1, 0];
  const files = state.flipped ? [7, 6, 5, 4, 3, 2, 1, 0] : [0, 1, 2, 3, 4, 5, 6, 7];
  const lastFrom = state.lastMove ? state.lastMove.from : null;
  const lastTo = state.lastMove ? state.lastMove.to : null;
  const checkSq = state.inCheck && state.reviewPly === null ? kingSquareOf(state.turn) : null;
  // Coups légaux de la pièce sélectionnée : uci "e2e4" -> destination "e4"
  const hintTargets = new Map();
  if (state.selected && state.reviewPly === null) {
    for (const uci of state.legalMoves) {
      if (uci.startsWith(state.selected)) {
        const to = uci.slice(2, 4);
        hintTargets.set(to, hintTargets.get(to) || Boolean(symAt(to)) || isEpCapture(state.selected, to));
      }
    }
  }
  for (const rank of ranks) {
    for (const file of files) {
      const name = squareName(file, rank);
      const sq = document.createElement("div");
      sq.className = "square " + ((file + rank) % 2 === 0 ? "dark" : "light");
      sq.dataset.square = name;
      sq.setAttribute("role", "gridcell");
      // coordonnées en bord de plateau
      const isLeftEdge = state.flipped ? file === 7 : file === 0;
      const isBottomEdge = state.flipped ? rank === 7 : rank === 0;
      if (isLeftEdge) {
        const c = document.createElement("span");
        c.className = "coord rank";
        c.textContent = String(rank + 1);
        sq.appendChild(c);
      }
      if (isBottomEdge) {
        const c = document.createElement("span");
        c.className = "coord file";
        c.textContent = FILES[file];
        sq.appendChild(c);
      }
      if (name === lastFrom || name === lastTo) sq.classList.add("last-move");
      if (name === checkSq) sq.classList.add("in-check");
      if (name === state.selected) sq.classList.add("selected");
      if (hintTargets.has(name)) {
        sq.classList.add(hintTargets.get(name) ? "hint-capture" : "hint");
      }
      const sym = symAt(name);
      if (sym) {
        const src = pieceSrc(sym);
        const span = document.createElement("span");
        span.className = "piece";
        const img = document.createElement("img");
        if (src) img.src = src;
        img.alt = sym;
        img.draggable = false;
        span.appendChild(img);
        sq.appendChild(span);
      }
      boardEl.appendChild(sq);
    }
  }
  animateLastMove();
}

// Animation du dernier coup (~180 ms).
function animateLastMove() {
  if (state.reviewPly !== null) return;
  if (!state.lastMove || state.lastMove.uci === state.prevLastMoveUci) return;
  state.prevLastMoveUci = state.lastMove.uci;
  const { from, to } = state.lastMove;
  const fromEl = boardEl.querySelector(`[data-square="${from}"]`);
  const toEl = boardEl.querySelector(`[data-square="${to}"]`);
  const pieceEl = toEl && toEl.querySelector(".piece");
  if (!fromEl || !toEl || !pieceEl) return;
  const dx = fromEl.offsetLeft - toEl.offsetLeft;
  const dy = fromEl.offsetTop - toEl.offsetTop;
  pieceEl.animate(
    [{ transform: `translate(${dx}px, ${dy}px)` }, { transform: "translate(0, 0)" }],
    { duration: 180, easing: "ease-out" }
  );
}

// Rendu isolé : log console + toast, les autres rendus continuent.
export function renderFail(name, err) {
  console.error(`[render:${name}]`, err);
  toast(`Erreur d'affichage « ${name} » — le reste est intact.`);
}

export function safeRender(name, fn) {
  try {
    const r = fn();
    if (r && typeof r.catch === "function") r.catch((err) => renderFail(name, err));
  } catch (err) {
    renderFail(name, err);
  }
}

export function renderAll() {
  if (state.reviewPly !== null) {
    const entry = state.history[state.reviewPly];
    const rows = entry.fen.split(" ")[0].split("/");
    const symbols = {};
    for (let r = 0; r < 8; r++) {
      let f = 0;
      for (const ch of rows[r]) {
        if (/\d/.test(ch)) f += parseInt(ch, 10);
        else {
          symbols[FILES[f] + (8 - r)] = ch;
          f++;
        }
      }
    }
    state.symbols = symbols;
    state.lastMove = entry.uci
      ? { from: entry.uci.slice(0, 2), to: entry.uci.slice(2, 4), uci: entry.uci }
      : null;
    render();
    setStatus(`Position passée — après ${state.reviewPly} demi-coup${state.reviewPly > 1 ? "s" : ""}`);
  } else if (state.boardData) {
    state.symbols = state.boardData.squares || {};
    render();
  }
  renderPlayers();
  renderMovesTable();
  renderReviewBar();
}

// --- Navigation dans l'historique (boutons + clavier) ---------------------------

export function renderReviewBar() {
  const bar = document.getElementById("review-bar");
  const banner = document.getElementById("review-banner");
  if (state.reviewPly === null) {
    bar.classList.add("hidden");
    banner.classList.add("hidden");
    return;
  }
  bar.classList.remove("hidden");
  banner.classList.remove("hidden");
  const lastPly = state.history.length - 1;
  document.getElementById("review-label").textContent =
    `coup ${state.reviewPly}/${lastPly}`;
}

export function reviewStep(which) {
  const lastPly = state.history.length - 1;
  const cur = state.reviewPly === null ? lastPly : state.reviewPly;
  const next = {
    first: 0,
    prev: Math.max(0, cur - 1),
    next: Math.min(lastPly, cur + 1),
    last: lastPly,
  }[which];
  state.reviewPly = next;
  state.selected = null;
  renderAll();
}
