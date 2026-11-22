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
    renderPlayers();
    renderMovesTable();
    if (state.reviewPly === null) {
      setStatus(statusText(status));
    }
  } catch (err) {
    setStatus("Erreur : " + err.message);
  }
}

// Barre de statut, 100 % en français.
function statusText(status) {
  if (status.result === "ongoing") {
    const qui = status.turn === "w" ? "Blancs" : "Noirs";
    return `Aux ${qui.toLowerCase()} de jouer${status.in_check ? " — Échec !" : ""}`;
  }
  if (status.result === "checkmate") {
    return status.winner === "w"
      ? "Échec et mat — les Blancs gagnent."
      : "Échec et mat — les Noirs gagnent.";
  }
  if (status.result === "stalemate") return "Pat — partie nulle.";
  if (status.result === "draw_fifty_move") return "Nulle — règle des 50 coups.";
  if (status.result === "draw_threefold") return "Nulle — triple répétition.";
  if (status.result === "draw_insufficient_material") return "Nulle — matériel insuffisant.";
  return status.result;
}

// --- Cartes joueurs -----------------------------------------------------------

const VALUES = { p: 1, n: 3, b: 3, r: 5, q: 9, k: 0 };
const START_COUNTS = { p: 8, n: 2, b: 2, r: 2, q: 1, k: 1 };

function computeCaptured(symbols) {
  const counts = { w: { p: 0, n: 0, b: 0, r: 0, q: 0 }, b: { p: 0, n: 0, b: 0, r: 0, q: 0 } };
  for (const sym of Object.values(symbols)) {
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

function playerName(color) {
  return color === "w" ? "Blancs" : "Noirs";
}

function renderPlayers() {
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

function renderMovesTable() {
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

function renderAll() {
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
    render();
    setStatus(`Position passée — après ${state.reviewPly} demi-coup${state.reviewPly > 1 ? "s" : ""}`);
  } else if (state.boardData) {
    state.symbols = state.boardData.squares;
    render();
  }
  renderPlayers();
  renderMovesTable();
}

// --- Boutons de base -------------------------------------------------------------

async function newGame() {
  state.selected = null;
  state.reviewPly = null;
  try {
    await ChessAPI.newGame();
  } catch (err) {
    setStatus("Nouvelle partie : " + err.message);
  }
  await refresh();
}

document.getElementById("btn-new").addEventListener("click", newGame);
document.getElementById("btn-undo").addEventListener("click", async () => {
  state.selected = null;
  state.reviewPly = null;
  try {
    await ChessAPI.undo();
  } catch (err) {
    setStatus("Annuler : " + err.message);
  }
  await refresh();
});
document.getElementById("btn-flip").addEventListener("click", () => {
  state.flipped = !state.flipped;
  lsSet("chess.flip", state.flipped ? "1" : "0");
  render();
  renderPlayers();
});

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
