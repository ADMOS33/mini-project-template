// Interactions plateau : clic-clic, glisser-déposer et promotion.
// Les coups légaux viennent de l'API (state.legalMoves) — aucune règle ici.

import { ChessAPI } from "./api.js";
import { boardEl, render, renderAll, renderDraw } from "./board-view.js";
import { reportError, toast } from "./toasts.js";
import { FILES, lsSet, myPieceAt, pieceSrc, setStatus, state, symAt } from "./state.js";

function squareFromEvent(e) {
  const el = document.elementFromPoint(e.clientX, e.clientY);
  const sq = el && el.closest ? el.closest(".square") : null;
  return sq ? sq.dataset.square : null;
}

// Sélecteur de promotion superposé sur le plateau, façon lichess : une
// colonne de 4 pièces (D/T/F/C) alignée sur la case d'arrivée.
function askPromotion(from, to, color) {
  return new Promise((resolve) => {
    const overlay = document.getElementById("promo-overlay");
    overlay.innerHTML = "";
    const wrap = boardEl.parentElement.getBoundingClientRect();
    const sqSize = wrap.width / 8;
    const file = FILES.indexOf(to[0]);
    const rank = parseInt(to[1], 10) - 1;
    // colonne verticale centrée sur la case d'arrivée
    const left = state.flipped ? (7 - file) * sqSize : file * sqSize;
    const topEdge = (7 - rank) * sqSize;
    overlay.style.left = left + "px";
    overlay.style.width = sqSize + "px";
    // la colonne s'ouvre vers le haut ou vers le bas selon la rangée d'arrivée
    const openUp = state.flipped ? rank > 3 : rank < 4;
    overlay.style.top = (openUp ? topEdge - 3 * sqSize : topEdge) + "px";
    overlay.style.height = 4 * sqSize + "px";
    for (const letter of ["q", "r", "b", "n"]) {
      const btn = document.createElement("button");
      const img = document.createElement("img");
      img.src = pieceSrc(color === "w" ? letter.toUpperCase() : letter);
      img.alt = letter.toUpperCase();
      btn.appendChild(img);
      btn.addEventListener("click", () => {
        overlay.classList.add("hidden");
        resolve(letter);
      });
      overlay.appendChild(btn);
    }
    overlay.classList.remove("hidden");
    const cancel = (e) => {
      if (!overlay.contains(e.target)) {
        overlay.classList.add("hidden");
        document.removeEventListener("pointerdown", cancel, true);
        resolve(null);
      }
    };
    document.addEventListener("pointerdown", cancel, true);
  });
}

export async function tryMove(from, to, refresh, silent = false) {
  if (state.spectator) return; // aucun coup depuis le navigateur en mode spectateur
  const candidates = state.legalMoves.filter((m) => m.startsWith(from + to));
  if (candidates.length === 0) {
    setStatus(`Case ${to} non atteignable depuis ${from}.`);
    return;
  }
  let uci = candidates[0];
  if (candidates.length > 1) {
    // promotion : plusieurs variantes (q/r/b/n)
    const sym = symAt(from);
    const color = sym === sym.toUpperCase() ? "w" : "b";
    const promo = await askPromotion(from, to, color);
    if (!promo) return; // annulé
    uci = from + to + promo;
  }
  state.selected = null;
  try {
    if (state.puzzle) {
      // Mode problème (V7) : le coup est jugé par /api/solve (solution puis mat conservé)
      const r = await ChessAPI.solve(uci);
      if (r.puzzle && r.puzzle.solved) {
        state.puzzleScore += 1;
        state.puzzleStreak += 1;
        lsSet("chess.puzzleScore", String(state.puzzleScore));
        lsSet("chess.puzzleStreak", String(state.puzzleStreak));
        toast(`🧩 Bravo ! Problème résolu (${r.san}). Score ${state.puzzleScore}, série ${state.puzzleStreak}.`, "info");
      } else if (r.puzzle) {
        toast(`Coup accepté (${r.san}) — mat toujours forcé en ${r.puzzle.remaining}.`, "info");
      }
    } else {
      await ChessAPI.move(uci);
    }
  } catch (err) {
    if (state.puzzle) {
      state.puzzleStreak = 0;
      lsSet("chess.puzzleStreak", "0");
    }
    if (!silent) reportError("Coup refusé", err);
  }
  state.reviewPly = null;
  await refresh();
}

// Branche pointerdown/move/up sur le plateau. `refresh` est passé par main.js
// (évite une dépendance circulaire).
export function initInteractions({ refresh }) {
  boardEl.addEventListener("contextmenu", (e) => e.preventDefault());

  boardEl.addEventListener("pointerdown", (e) => {
    if (state.reviewPly !== null) return;
    const name = squareFromEvent(e);
    if (e.button === 2) {
      // Dessin (V10) : clic droit simple = cercle, glissé = flèche
      if (!name) return;
      const color = e.shiftKey ? "shift" : e.altKey ? "alt" : "default";
      state.drawing = { from: name, startX: e.clientX, startY: e.clientY, moved: false, color };
      e.preventDefault();
      return;
    }
    if (state.spectator) {
      toast("Mode spectateur : les coups se jouent hors du navigateur (CLI)", "info");
      return;
    }
    if (!name) return;
    state.drag = { from: name, startX: e.clientX, startY: e.clientY, ghost: null, moved: false };
  });

  boardEl.addEventListener("pointermove", (e) => {
    // Aperçu de dessin en cours (V10)
    const dr = state.drawing;
    if (dr && e.buttons === 2) {
      if (!dr.moved && Math.hypot(e.clientX - dr.startX, e.clientY - dr.startY) > 6) dr.moved = true;
      if (dr.moved) {
        const target = squareFromEvent(e);
        if (target && target !== dr.from) {
          state.drawings = state.drawings.filter((d) => !(d.type === "arrow" && d.from === dr.from));
          state.drawings.push({ type: "arrow", from: dr.from, to: target, color: dr.color });
          renderDraw();
        }
      }
      return;
    }
    const d = state.drag;
    if (!d || state.reviewPly !== null) return;
    if (!d.moved && Math.hypot(e.clientX - d.startX, e.clientY - d.startY) > 6 && myPieceAt(d.from)) {
      d.moved = true;
      const rect = boardEl.getBoundingClientRect();
      const ghost = document.createElement("span");
      ghost.className = "drag-ghost";
      const img = document.createElement("img");
      const ghostSrc = pieceSrc(symAt(d.from));
      if (ghostSrc) img.src = ghostSrc;
      img.draggable = false;
      ghost.appendChild(img);
      ghost.style.left = e.clientX - rect.left + "px";
      ghost.style.top = e.clientY - rect.top + "px";
      boardEl.parentElement.appendChild(ghost);
      d.ghost = ghost;
    }
    if (d.ghost) {
      const rect = boardEl.getBoundingClientRect();
      d.ghost.style.left = e.clientX - rect.left + "px";
      d.ghost.style.top = e.clientY - rect.top + "px";
    }
  });

  boardEl.addEventListener("pointerup", (e) => {
    // Fin de dessin (V10) : clic droit simple = cercle
    if (state.drawing && e.button === 2) {
      const dr = state.drawing;
      state.drawing = null;
      if (!dr.moved) {
        state.drawings = state.drawings.filter((d) => !(d.type === "circle" && d.sq === dr.from));
        state.drawings.push({ type: "circle", sq: dr.from, color: dr.color });
        renderDraw();
      }
      return;
    }
    const d = state.drag;
    state.drag = null;
    if (!d || state.reviewPly !== null) return;
    if (d.moved && d.ghost) {
      d.ghost.remove();
      const target = squareFromEvent(e);
      if (target && target !== d.from) {
        tryMove(d.from, target, refresh);
      } else {
        render();
      }
      return;
    }
    // clic-clic
    const name = squareFromEvent(e);
    if (!name) return;
    if (!state.selected) {
      if (myPieceAt(name)) state.selected = name;
      else {
        // clic gauche sur une case vide sans sélection : efface les dessins (V10)
        state.drawings = [];
        renderDraw();
      }
    } else if (state.selected === name) {
      state.selected = null;
    } else {
      const from = state.selected;
      state.selected = null;
      // Prémouvement (V10) : pendant que l'ordinateur réfléchit, on met le coup en attente
      if (state.thinking && state.vs && !state.spectator) {
        const uciMoves = state.legalMoves.filter((m) => m.startsWith(from + name));
        if (uciMoves.length > 0) {
          state.premove = { from, to: name, uci: uciMoves[0] };
          render();
          toast(`Prémouvement enregistré : ${from}-${name} (partira dès votre tour).`, "info");
          return;
        }
      }
      tryMove(from, name, refresh);
      return;
    }
    render();
  });
}
