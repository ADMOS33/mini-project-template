// Échecs — application web. Le JS ne fait qu'afficher ce que renvoie l'API :
// aucune règle d'échecs ici, tout vient de /api/*.

const boardEl = document.getElementById("board");
const statusEl = document.getElementById("status");
const FILES = "abcdefgh";

const state = {
  boardData: null, // dernier /api/board
  symbols: {}, // case -> symbole FEN ("P", "k", ...)
  turn: "w",
  inCheck: false,
  legalMoves: [],
  lastMove: null, // {from, to, uci}
  prevLastMoveUci: null,
  flipped: false,
  selected: null,
  reviewPly: null, // null = position live
  history: [],
};

function ls(key, def) {
  try {
    return localStorage.getItem(key) ?? def;
  } catch {
    return def;
  }
}
function lsSet(key, val) {
  try {
    localStorage.setItem(key, val);
  } catch { /* stockage indisponible : on ignore */ }
}
state.flipped = ls("chess.flip", "0") === "1";

function squareName(file, rank) {
  return FILES[file] + (rank + 1);
}

function pieceSrc(sym) {
  // sym est une lettre FEN : "P" = pion blanc, "k" = roi noir...
  const color = sym === sym.toUpperCase() ? "w" : "b";
  return `pieces/${color}${sym.toUpperCase()}.svg`;
}

function kingSquareOf(color) {
  for (const [name, sym] of Object.entries(state.symbols)) {
    if (sym && sym.toLowerCase() === "k" && (color === "w" ? sym === "K" : sym === "k")) {
      return name;
    }
  }
  return null;
}

// --- Rendu du plateau -------------------------------------------------------

function render() {
  boardEl.innerHTML = "";
  const ranks = state.flipped ? [0, 1, 2, 3, 4, 5, 6, 7] : [7, 6, 5, 4, 3, 2, 1, 0];
  const files = state.flipped ? [7, 6, 5, 4, 3, 2, 1, 0] : [0, 1, 2, 3, 4, 5, 6, 7];
  const lastFrom = state.lastMove ? state.lastMove.from : null;
  const lastTo = state.lastMove ? state.lastMove.to : null;
  const checkSq = state.inCheck && state.reviewPly === null ? kingSquareOf(state.turn) : null;
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
      const sym = state.symbols[name];
      if (sym) {
        const span = document.createElement("span");
        span.className = "piece";
        const img = document.createElement("img");
        img.src = pieceSrc(sym);
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

// --- Rafraîchissement depuis l'API -------------------------------------------

function setStatus(text) {
  statusEl.textContent = text;
}

async function refresh() {
  try {
    const [board, status, moves, hist] = await Promise.all([
      ChessAPI.board(),
      ChessAPI.status(),
      ChessAPI.moves(),
      ChessAPI.history(),
    ]);
    state.boardData = board;
    state.turn = status.turn;
    state.inCheck = status.in_check;
    state.history = hist.entries;
    state.lastMove = status.last_move
      ? { from: status.last_move.slice(0, 2), to: status.last_move.slice(2, 4), uci: status.last_move }
      : null;
    state.legalMoves = moves.moves;
    if (state.reviewPly === null) {
      state.symbols = board.squares;
    }
    render();
    const turn = status.turn === "w" ? "Blancs" : "Noirs";
    setStatus(
      status.result === "ongoing"
        ? `Aux ${turn.toLowerCase()} de jouer${status.in_check ? " — échec !" : ""}`
        : status.result
    );
  } catch (err) {
    setStatus("Erreur : " + err.message);
  }
}

refresh();
