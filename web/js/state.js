// État global de l'application web + helpers purs.
// Aucune règle d'échecs ici : légalité, SAN, fin de partie et évaluation
// viennent exclusivement de l'API (/api/*).

export const FILES = "abcdefgh";

export const state = {
  boardData: null, // dernier /api/board
  symbols: {}, // case -> symbole FEN ("P", "k", ...) ou null
  turn: "w",
  inCheck: false,
  legalMoves: [],
  lastMove: null, // {from, to, uci}
  prevLastMoveUci: null,
  prevSoundUci: null,
  flipped: false,
  selected: null,
  reviewPly: null, // null = position live
  history: [],
  gameOverShownFor: null,
  vs: false,
  colorChoice: "w",
  actualColor: "w",
  depth: 3,
  thinking: false,
  sound: true,
  clockMode: "none",
  clock: { w: 0, b: 0, inc: 0, active: null, lastTs: null },
  drag: null,
};

// localStorage toujours entouré de try/catch (préférences thème/son/etc.).
export function ls(key, def) {
  try {
    return localStorage.getItem(key) ?? def;
  } catch {
    return def;
  }
}
export function lsSet(key, val) {
  try {
    localStorage.setItem(key, val);
  } catch { /* stockage indisponible : on ignore */ }
}

state.flipped = ls("chess.flip", "0") === "1";
state.vs = ls("chess.vs", "0") === "1";
state.colorChoice = ls("chess.color", "w");
state.depth = parseInt(ls("chess.depth", "3"), 10);
state.sound = ls("chess.sound", "1") === "1";
state.clockMode = ls("chess.clock", "none");
state.autoFlip = ls("chess.autoflip", "0") === "1";

export const statusEl = document.getElementById("status");
export function setStatus(text) {
  statusEl.textContent = text;
}

// Groupe de chips segmentées (remplace les <select> natifs) : boutons
// natifs -> utilisables au clavier (Tab / Entrée / Espace), avec
// role="group" + aria-pressed et focus visible (voir style.css).
export function wireChips(id, onPick, initial) {
  const group = document.getElementById(id);
  if (!group) return;
  const chips = group.querySelectorAll(".chip");
  const select = (value) => {
    chips.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.value === value)));
  };
  select(initial);
  chips.forEach((btn) => {
    btn.addEventListener("click", () => {
      select(btn.dataset.value);
      onPick(btn.dataset.value);
    });
  });
}

export function squareName(file, rank) {
  return FILES[file] + (rank + 1);
}

// Accès sûr à state.symbols : jamais null/undefined, toujours une chaîne.
export function symAt(name) {
  return (state.symbols && state.symbols[name]) || "";
}

export function pieceSrc(sym) {
  // sym est une lettre FEN : "P" = pion blanc, "k" = roi noir...
  // Sûr face à null/undefined : renvoie "" (l'appelant ignore alors l'image).
  if (!sym || typeof sym !== "string") return "";
  const color = sym === sym.toUpperCase() ? "w" : "b";
  return `pieces/${color}${sym.toUpperCase()}.svg`;
}

// Vrai si from->to est une prise en passant (case vide = case ep du FEN).
export function isEpCapture(from, to) {
  const sym = symAt(from);
  if (sym.toLowerCase() !== "p") return false;
  if (symAt(to)) return false;
  const ep = state.boardData ? state.boardData.fen.split(" ")[3] : "-";
  return ep !== "-" && ep === to;
}

export function myPieceAt(name) {
  const sym = symAt(name);
  if (!sym) return false;
  return state.turn === "w" ? sym === sym.toUpperCase() : sym === sym.toLowerCase();
}

export function kingSquareOf(color) {
  for (const [name, sym] of Object.entries(state.symbols || {})) {
    if (sym && sym.toLowerCase() === "k" && (color === "w" ? sym === "K" : sym === "k")) {
      return name;
    }
  }
  return null;
}

export function computerColor() {
  if (!state.vs) return null;
  return state.colorChoice === "random" ? state.actualColor : state.colorChoice;
}

export function playerName(color) {
  const cc = computerColor();
  if (cc === "w") return color === "w" ? "Ordinateur" : "Vous";
  if (cc === "b") return color === "b" ? "Ordinateur" : "Vous";
  return color === "w" ? "Blancs" : "Noirs";
}

// Barre de statut, 100 % en français.
export function statusText(status) {
  if (status.result === "ongoing") {
    const qui = status.turn === "w" ? "Blancs" : "Noirs";
    return `Aux ${qui.toLowerCase()} de jouer${status.in_check ? " — Échec !" : ""}`;
  }
  if (status.result === "checkmate") {
    return status.winner === "w"
      ? "Échec et mat — les Blancs gagnent."
      : "Échec et mat — les Noirs gagnent.";
  }
  if (status.result === "flag") {
    return status.winner === "w"
      ? "Temps écoulé — les Blancs gagnent."
      : "Temps écoulé — les Noirs gagnent.";
  }
  if (status.result === "stalemate") return "Pat — partie nulle.";
  if (status.result === "draw_fifty_move") return "Nulle — règle des 50 coups.";
  if (status.result === "draw_threefold") return "Nulle — triple répétition.";
  if (status.result === "draw_insufficient_material") return "Nulle — matériel insuffisant.";
  return status.result;
}

export const VALUES = { p: 1, n: 3, b: 3, r: 5, q: 9, k: 0 };
export const START_COUNTS = { p: 8, n: 2, b: 2, r: 2, q: 1, k: 1 };
