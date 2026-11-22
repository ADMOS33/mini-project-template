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

// Vrai si from->to est une prise en passant (case vide = case ep du FEN).
function isEpCapture(from, to) {
  const sym = state.symbols[from] || "";
  if (sym.toLowerCase() !== "p") return false;
  if (state.symbols[to]) return false;
  const ep = state.boardData ? state.boardData.fen.split(" ")[3] : "-";
  return ep !== "-" && ep === to;
}

function myPieceAt(name) {
  const sym = state.symbols[name];
  if (!sym) return false;
  return state.turn === "w" ? sym === sym.toUpperCase() : sym === sym.toLowerCase();
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
  // Coups légaux de la pièce sélectionnée : uci "e2e4" -> destination "e4"
  const hintTargets = new Map();
  if (state.selected && state.reviewPly === null) {
    for (const uci of state.legalMoves) {
      if (uci.startsWith(state.selected)) {
        const to = uci.slice(2, 4);
        hintTargets.set(to, hintTargets.get(to) || Boolean(state.symbols[to]) || isEpCapture(state.selected, to));
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

// --- Jouer un coup -----------------------------------------------------------

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
    const topEdge = state.flipped ? (7 - rank) * sqSize : (7 - rank) * sqSize;
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

async function tryMove(from, to) {
  const candidates = state.legalMoves.filter((m) => m.startsWith(from + to));
  if (candidates.length === 0) {
    setStatus(`Case ${to} non atteignable depuis ${from}.`);
    return;
  }
  let uci = candidates[0];
  if (candidates.length > 1) {
    // promotion : plusieurs variantes (q/r/b/n)
    const sym = state.symbols[from] || "";
    const color = sym === sym.toUpperCase() ? "w" : "b";
    const promo = await askPromotion(from, to, color);
    if (!promo) return; // annulé
    uci = from + to + promo;
  }
  state.selected = null;
  try {
    await ChessAPI.move(uci);
  } catch (err) {
    setStatus("Coup refusé : " + err.message);
  }
  state.reviewPly = null;
  await refresh();
}

// --- Clic-clic + glisser-déposer ----------------------------------------------

function squareFromEvent(e) {
  const el = document.elementFromPoint(e.clientX, e.clientY);
  const sq = el && el.closest ? el.closest(".square") : null;
  return sq ? sq.dataset.square : null;
}

boardEl.addEventListener("pointerdown", (e) => {
  if (state.reviewPly !== null) return;
  const name = squareFromEvent(e);
  if (!name) return;
  state.drag = { from: name, startX: e.clientX, startY: e.clientY, ghost: null, moved: false };
});

boardEl.addEventListener("pointermove", (e) => {
  const d = state.drag;
  if (!d || state.reviewPly !== null) return;
  if (!d.moved && Math.hypot(e.clientX - d.startX, e.clientY - d.startY) > 6 && myPieceAt(d.from)) {
    d.moved = true;
    const rect = boardEl.getBoundingClientRect();
    const ghost = document.createElement("span");
    ghost.className = "drag-ghost";
    const img = document.createElement("img");
    img.src = pieceSrc(state.symbols[d.from]);
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
  const d = state.drag;
  state.drag = null;
  if (!d || state.reviewPly !== null) return;
  if (d.moved && d.ghost) {
    d.ghost.remove();
    const target = squareFromEvent(e);
    if (target && target !== d.from) {
      tryMove(d.from, target);
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
  } else if (state.selected === name) {
    state.selected = null;
  } else {
    const from = state.selected;
    state.selected = null;
    tryMove(from, name);
    return;
  }
  render();
});

refresh();
