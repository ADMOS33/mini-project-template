// Panneaux latéraux : cartes joueurs + captures, table des coups (SAN),
// barre d'évaluation, contrôles vs ordinateur, modale de fin de partie.

import { ChessAPI } from "./api.js";
import { renderAll } from "./board-view.js";
import {
  START_COUNTS,
  VALUES,
  computerColor,
  playerName,
  state,
  statusText,
} from "./state.js";

// --- Cartes joueurs -----------------------------------------------------------

export function computeCaptured(symbols) {
  const counts = { w: { p: 0, n: 0, b: 0, r: 0, q: 0 }, b: { p: 0, n: 0, b: 0, r: 0, q: 0 } };
  for (const sym of Object.values(symbols || {})) {
    if (!sym) continue;
    const c = sym === sym.toUpperCase() ? "w" : "b";
    counts[c][sym.toLowerCase()]++;
  }
  const missingOf = (color) => {
    const list = [];
    for (const t of ["q", "r", "b", "n", "p"]) {
      for (let i = counts[color][t]; i < START_COUNTS[t]; i++) list.push(t);
    }
    return list;
  };
  const material = (c) => Object.entries(counts[c]).reduce((s, [t, n]) => s + VALUES[t] * n, 0);
  return {
    capturedByW: missingOf("b"), // pièces noires manquantes = prises par les Blancs
    capturedByB: missingOf("w"),
    diff: material("w") - material("b"), // > 0 : les Blancs mènent
  };
}

export function renderPlayers() {
  const topColor = state.flipped ? "w" : "b";
  const bottomColor = state.flipped ? "b" : "w";
  const { capturedByW, capturedByB, diff } = computeCaptured(state.symbols);
  for (const [cardId, capId, avId, color] of [
    ["player-top", "captured-top", "avatar-top", topColor],
    ["player-bottom", "captured-bottom", "avatar-bottom", bottomColor],
  ]) {
    const card = document.getElementById(cardId);
    card.classList.toggle("active", state.turn === color && state.reviewPly === null);
    document.getElementById(avId).innerHTML = `<img src="pieces/${color}K.svg" alt="">`;
    document.getElementById("pname-" + cardId.split("-")[1]).textContent = playerName(color);
    const mine = color === "w" ? capturedByW : capturedByB;
    const oppColor = color === "w" ? "b" : "w";
    const capEl = document.getElementById(capId);
    capEl.innerHTML = mine
      .map((t) => `<img src="pieces/${oppColor}${t.toUpperCase()}.svg" alt="${t}">`)
      .join("");
    const leading = (color === "w" && diff > 0) || (color === "b" && diff < 0);
    if (leading) {
      const s = document.createElement("span");
      s.className = "adv";
      s.textContent = "+" + Math.abs(diff);
      capEl.appendChild(s);
    }
  }
}

// --- Tableau des coups : n° | Blancs | Noirs ------------------------------------

export function renderMovesTable() {
  const body = document.getElementById("moves-body");
  body.innerHTML = "";
  const entries = state.history;
  if (entries.length <= 1) {
    body.innerHTML = '<tr class="empty-row"><td colspan="3">Aucun coup pour l\'instant</td></tr>';
    return;
  }
  const lastPly = entries.length - 1;
  for (let i = 1; i < entries.length; i += 2) {
    const tr = document.createElement("tr");
    const num = document.createElement("td");
    num.className = "num";
    num.textContent = i / 2 + 1 + ".";
    tr.appendChild(num);
    tr.appendChild(moveCell(entries[i], lastPly));
    tr.appendChild(
      i + 1 < entries.length ? moveCell(entries[i + 1], lastPly) : document.createElement("td")
    );
    body.appendChild(tr);
  }
  body.scrollTop = body.scrollHeight;
}

function moveCell(entry, lastPly) {
  const td = document.createElement("td");
  td.className = "move";
  td.textContent = entry.san || entry.uci;
  td.title = entry.uci;
  if (state.reviewPly === entry.ply || (state.reviewPly === null && entry.ply === lastPly)) {
    td.classList.add("current");
  }
  td.addEventListener("click", () => {
    state.reviewPly = state.reviewPly === entry.ply ? null : entry.ply;
    state.selected = null;
    renderAll();
  });
  return td;
}

// --- Modale de fin de partie -----------------------------------------------------

export function showGameOver(title, reason) {
  document.getElementById("gameover-title").textContent = title;
  document.getElementById("gameover-reason").textContent = reason;
  document.getElementById("gameover-modal").classList.remove("hidden");
}

// Fenêtre de fin de partie : résultat + raison exacte renvoyée par l'API.
export function maybeShowGameOver(status) {
  if (status.result === "ongoing") return;
  if (state.gameOverShownFor === status.fen) return;
  state.gameOverShownFor = status.fen;
  showGameOver(
    status.result === "checkmate" ? "Échec et mat !" : "Partie nulle",
    statusText(status) // raison exacte (checkmate/pat/50 coups/répétition/matériel)
  );
}

// --- Contrôles vs ordinateur ------------------------------------------------------

export function renderVsControls() {
  document.getElementById("seg-human").setAttribute("aria-selected", String(!state.vs));
  document.getElementById("seg-computer").setAttribute("aria-selected", String(state.vs));
  document.getElementById("vs-options").classList.toggle("hidden", !state.vs);
  const mh = document.getElementById("mode-human");
  const mc = document.getElementById("mode-computer");
  if (mh && mc) {
    mh.setAttribute("aria-pressed", String(!state.vs));
    mc.setAttribute("aria-pressed", String(state.vs));
  }
  for (const [id, val] of [["opt-color", state.colorChoice], ["opt-depth", String(state.depth)]]) {
    const group = document.getElementById(id);
    if (group) {
      group.querySelectorAll(".chip").forEach((b) =>
        b.setAttribute("aria-pressed", String(b.dataset.value === val))
      );
    }
  }
}

// --- Barre d'évaluation animée (score /api/eval, perspective camp au trait) -------

export async function renderEval() {
  try {
    const ev = await ChessAPI.eval();
    // score du point de vue du camp au trait -> pourcentage pour les Blancs
    let s = ev.score;
    if (ev.turn === "b") s = -s;
    const pct = 50 + 50 * (2 / (1 + Math.exp(-s / 300)) - 1); // sigmoïde douce
    document.getElementById("evalbar-fill").style.width = pct.toFixed(1) + "%";
    document.getElementById("evalbar-label").textContent = (s / 100).toFixed(1);
  } catch { /* la barre reste à sa valeur précédente */ }
}
