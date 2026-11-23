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
  prevSoundUci: null,
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
state.gameOverShownFor = null;

function squareName(file, rank) {
  return FILES[file] + (rank + 1);
}

// Accès sûr à state.symbols : jamais null/undefined, toujours une chaîne.
function symAt(name) {
  return (state.symbols && state.symbols[name]) || "";
}

function pieceSrc(sym) {
  // sym est une lettre FEN : "P" = pion blanc, "k" = roi noir...
  // Sûr face à null/undefined : renvoie "" (l'appelant ignore alors l'image).
  if (!sym || typeof sym !== "string") return "";
  const color = sym === sym.toUpperCase() ? "w" : "b";
  return `pieces/${color}${sym.toUpperCase()}.svg`;
}

// Vrai si from->to est une prise en passant (case vide = case ep du FEN).
function isEpCapture(from, to) {
  const sym = symAt(from);
  if (sym.toLowerCase() !== "p") return false;
  if (state.symbols[to]) return false;
  const ep = state.boardData ? state.boardData.fen.split(" ")[3] : "-";
  return ep !== "-" && ep === to;
}

function myPieceAt(name) {
  const sym = symAt(name);
  if (!sym) return false;
  return state.turn === "w" ? sym === sym.toUpperCase() : sym === sym.toLowerCase();
}

function kingSquareOf(color) {
  for (const [name, sym] of Object.entries(state.symbols || {})) {
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

// --- Rafraîchissement depuis l'API -------------------------------------------

function setStatus(text) {
  statusEl.textContent = text;
}

// Rendu isolé : log console + toast, les autres rendus continuent.
function renderFail(name, err) {
  console.error(`[render:${name}]`, err);
  toast(`Erreur d'affichage « ${name} » — le reste est intact.`);
}

function safeRender(name, fn) {
  try {
    const r = fn();
    if (r && typeof r.catch === "function") r.catch((err) => renderFail(name, err));
  } catch (err) {
    renderFail(name, err);
  }
}

async function refresh() {
  try {
    const [board, status, moves, hist] = await Promise.all([
      ChessAPI.board(),
      ChessAPI.status(),
      ChessAPI.moves(),
      ChessAPI.history(),
    ]);
    const prevTurn = state.turn;
    state.boardData = board;
    state.turn = status.turn;
    state.inCheck = status.in_check;
    state.history = hist.entries || [];
    state.lastMove = status.last_move
      ? { from: status.last_move.slice(0, 2), to: status.last_move.slice(2, 4), uci: status.last_move }
      : null;
    state.legalMoves = moves.moves || [];
    if (state.reviewPly === null) {
      state.symbols = board.squares || {};
    }
    // Chaque rendu est isolé : une exception dans l'un est loguée + toastée
    // et n'empêche pas les autres de s'afficher.
    safeRender("plateau", render);
    safeRender("joueurs", renderPlayers);
    safeRender("coups", renderMovesTable);
    safeRender("évaluation", renderEval);
    safeRender("horloge", renderClocks);
    // horloge : incrément pour le camp qui vient de jouer
    if (prevTurn && prevTurn !== status.turn && state.clockMode !== "none") {
      state.clock[prevTurn] += state.clock.inc;
    }
    state.clock.active = status.turn;
    // son du dernier coup (SAN de l'historique)
    const lastEntry = hist.entries[hist.entries.length - 1];
    if (lastEntry && lastEntry.uci && lastEntry.uci !== (state.prevSoundUci || null)) {
      state.prevSoundUci = lastEntry.uci;
      if (state.reviewPly === null) playMoveSound(lastEntry.san, status.result);
    }
    if (state.reviewPly === null) {
      setStatus(statusText(status));
    }
    maybeShowGameOver(status);
    maybeAiMove(status);
  } catch (err) {
    reportError("Erreur API", err);
  }
}

// Fenêtre de fin de partie : résultat + raison exacte renvoyée par l'API.
function maybeShowGameOver(status) {
  if (status.result === "ongoing") return;
  if (state.gameOverShownFor === status.fen) return;
  state.gameOverShownFor = status.fen;
  showGameOver(
    status.result === "checkmate" ? "Échec et mat !" : "Partie nulle",
    statusText(status) // raison exacte (checkmate/pat/50 coups/répétition/matériel)
  );
}

function showGameOver(title, reason) {
  document.getElementById("gameover-title").textContent = title;
  document.getElementById("gameover-reason").textContent = reason;
  document.getElementById("gameover-modal").classList.remove("hidden");
}

document.getElementById("btn-gameover-new").addEventListener("click", () => {
  document.getElementById("gameover-modal").classList.add("hidden");
  state.gameOverShownFor = null;
  newGame();
});
document.getElementById("btn-gameover-review").addEventListener("click", () => {
  document.getElementById("gameover-modal").classList.add("hidden");
  state.reviewPly = 0; // retour au début de la partie pour la revoir
  renderAll();
});

// --- Toasts (au lieu de alert()) -------------------------------------------------

function toast(message, kind = "error") {
  const box = document.getElementById("toasts");
  const el = document.createElement("div");
  el.className = "toast" + (kind === "info" ? " info" : "");
  el.textContent = message;
  box.appendChild(el);
  setTimeout(() => {
    el.style.transition = "opacity var(--tr)";
    el.style.opacity = "0";
    setTimeout(() => el.remove(), 200);
  }, 4000);
}

// Les erreurs visibles passent UNIQUEMENT par un toast : la barre de statut
// garde son texte normal (règle front-end AGENTS.md).
function reportError(prefix, err) {
  console.error(prefix, err);
  const msg = err && err.message ? err.message : String(err);
  toast(`${prefix} : ${msg}`);
}

// Toute erreur non interceptée (synchrone ou promesse) -> toast + console.
window.addEventListener("error", (e) => {
  console.error(e.error || e.message);
  toast("Erreur inattendue : " + (e.message || "inconnue"));
});
window.addEventListener("unhandledrejection", (e) => {
  console.error(e.reason);
  const msg = e.reason && e.reason.message ? e.reason.message : String(e.reason || "inconnue");
  toast("Erreur inattendue : " + msg);
});

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

function renderReviewBar() {
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

function reviewStep(which) {
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

document.querySelectorAll("#review-bar [data-review]").forEach((btn) => {
  btn.addEventListener("click", () => reviewStep(btn.dataset.review));
});
document.getElementById("btn-exit-review").addEventListener("click", () => {
  state.reviewPly = null;
  state.selected = null;
  renderAll();
  refresh();
});

document.addEventListener("keydown", (e) => {
  if (e.target && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;
  if (e.key === "ArrowLeft") reviewStep("prev");
  else if (e.key === "ArrowRight") reviewStep("next");
  else if (e.key === "Home") reviewStep("first");
  else if (e.key === "End") reviewStep("last");
});

// --- Boutons de base -------------------------------------------------------------

async function newGame() {
  state.selected = null;
  state.reviewPly = null;
  if (state.vs && state.colorChoice === "random") {
    state.actualColor = Math.random() < 0.5 ? "w" : "b";
  }
  try {
    await ChessAPI.newGame();
  } catch (err) {
    reportError("Nouvelle partie", err);
  }
  await refresh();
  resetClock();
  renderVsControls();
  renderPlayers();
  const st = await ChessAPI.status();
  maybeAiMove(st); // l'ordinateur ouvre si c'est à lui de jouer
}

document.getElementById("btn-new").addEventListener("click", newGame);
document.getElementById("btn-undo").addEventListener("click", async () => {
  state.selected = null;
  state.reviewPly = null;
  try {
    await ChessAPI.undo();
  } catch (err) {
    reportError("Annuler", err);
  }
  await refresh();
});
document.getElementById("btn-flip").addEventListener("click", () => {
  state.flipped = !state.flipped;
  lsSet("chess.flip", state.flipped ? "1" : "0");
  render();
  renderPlayers();
});

// --- Mode « Contre l'ordinateur » -----------------------------------------------

state.vs = ls("chess.vs", "0") === "1";
state.colorChoice = ls("chess.color", "w");
state.actualColor = "w";
state.depth = parseInt(ls("chess.depth", "3"), 10);
state.thinking = false;

function computerColor() {
  if (!state.vs) return null;
  return state.colorChoice === "random" ? state.actualColor : state.colorChoice;
}

function playerName(color) {
  const cc = computerColor();
  if (cc === "w") return color === "w" ? "Ordinateur" : "Vous";
  if (cc === "b") return color === "b" ? "Ordinateur" : "Vous";
  return color === "w" ? "Blancs" : "Noirs";
}

function renderVsControls() {
  document.getElementById("seg-human").setAttribute("aria-selected", String(!state.vs));
  document.getElementById("seg-computer").setAttribute("aria-selected", String(state.vs));
  document.getElementById("vs-options").classList.toggle("hidden", !state.vs);
  document.getElementById("opt-color").value = state.colorChoice;
  document.getElementById("opt-depth").value = String(state.depth);
}

document.getElementById("seg-human").addEventListener("click", () => {
  state.vs = false;
  lsSet("chess.vs", "0");
  renderVsControls();
  renderPlayers();
});
document.getElementById("seg-computer").addEventListener("click", async () => {
  state.vs = true;
  lsSet("chess.vs", "1");
  if (state.colorChoice === "random") state.actualColor = Math.random() < 0.5 ? "w" : "b";
  renderVsControls();
  renderPlayers();
  const st = await ChessAPI.status();
  maybeAiMove(st);
});
document.getElementById("opt-color").addEventListener("change", (e) => {
  state.colorChoice = e.target.value;
  lsSet("chess.color", state.colorChoice);
  if (state.colorChoice === "random") state.actualColor = Math.random() < 0.5 ? "w" : "b";
  renderPlayers();
});
document.getElementById("opt-depth").addEventListener("change", (e) => {
  state.depth = parseInt(e.target.value, 10);
  lsSet("chess.depth", e.target.value);
});

async function maybeAiMove(status) {
  const cc = computerColor();
  if (!cc || state.thinking || status.result !== "ongoing" || status.turn !== cc) return;
  if (state.reviewPly !== null) return;
  state.thinking = true;
  document.getElementById("thinking").classList.remove("hidden");
  try {
    await ChessAPI.aiMove(state.depth);
  } catch (err) {
    reportError("IA", err);
  }
  state.thinking = false;
  document.getElementById("thinking").classList.add("hidden");
  await refresh();
}

// --- Barre d'évaluation animée (score /api/eval, perspective camp au trait) ----

async function renderEval() {
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

// --- Section repliable FEN / PGN : importer + copier ---------------------------------

const ioText = document.getElementById("io-text");

document.getElementById("btn-load-fen").addEventListener("click", async () => {
  const fen = ioText.value.trim();
  if (!fen) return toast("Colle d'abord une FEN.", "info");
  try {
    await ChessAPI.load(fen);
    state.reviewPly = null;
    state.gameOverShownFor = null;
    await refresh();
    toast("FEN chargée.", "info");
  } catch (err) {
    reportError("FEN invalide", err);
  }
});
document.getElementById("btn-load-pgn").addEventListener("click", async () => {
  const pgn = ioText.value.trim();
  if (!pgn) return toast("Colle d'abord un PGN.", "info");
  try {
    await ChessAPI.loadPgn(pgn);
    state.reviewPly = null;
    state.gameOverShownFor = null;
    await refresh();
    toast("PGN chargé.", "info");
  } catch (err) {
    reportError("PGN invalide", err);
  }
});
async function copyText(text, what) {
  try {
    await navigator.clipboard.writeText(text);
    toast(what + " copié dans le presse-papiers.", "info");
  } catch {
    toast(what + " : " + text, "info");
  }
}
document.getElementById("btn-copy-fen").addEventListener("click", async () => {
  await copyText((await ChessAPI.fen()).fen, "FEN");
});
document.getElementById("btn-copy-pgn").addEventListener("click", async () => {
  await copyText((await ChessAPI.pgn()).pgn, "PGN");
});

// --- Sons (Web Audio API, optionnels, bouton muet) --------------------------------

state.sound = ls("chess.sound", "1") === "1";
let audioCtx = null;

function beep(freq, duration, type = "sine", gain = 0.08, when = 0) {
  if (!state.sound) return;
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    const osc = audioCtx.createOscillator();
    const g = audioCtx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    g.gain.setValueAtTime(gain, audioCtx.currentTime + when);
    g.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + when + duration);
    osc.connect(g).connect(audioCtx.destination);
    osc.start(audioCtx.currentTime + when);
    osc.stop(audioCtx.currentTime + when + duration);
  } catch { /* audio indisponible : on ignore */ }
}

function playMoveSound(san, result) {
  if (!san) return;
  if (result !== "ongoing") {
    beep(220, 0.5, "triangle", 0.1);
    beep(330, 0.4, "triangle", 0.08, 0.15);
    return;
  }
  if (san.includes("#") || san.includes("+")) {
    beep(880, 0.09, "square", 0.06);
    beep(880, 0.09, "square", 0.06, 0.12);
  } else if (san.includes("x")) {
    beep(440, 0.08, "square", 0.07);
  } else {
    beep(620, 0.06, "sine", 0.07);
  }
}

const btnSound = document.getElementById("btn-sound");
function renderSoundBtn() {
  btnSound.setAttribute("aria-pressed", String(state.sound));
}
btnSound.addEventListener("click", () => {
  state.sound = !state.sound;
  lsSet("chess.sound", state.sound ? "1" : "0");
  renderSoundBtn();
  if (state.sound) beep(620, 0.06);
});
renderSoundBtn();

// --- Horloge optionnelle (5 min, 10 min, 3 min + 2 s) --------------------------------

state.clockMode = ls("chess.clock", "none");
state.clock = { w: 0, b: 0, inc: 0, active: null, lastTs: null };

function clockBase() {
  const m = state.clockMode;
  if (m === "none") return null;
  if (m === "182") return { base: 180, inc: 2 };
  return { base: parseInt(m, 10), inc: 0 };
}

function resetClock() {
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

function renderClocks() {
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
setInterval(tickClock, 200);

const optClock = document.getElementById("opt-clock");
optClock.value = state.clockMode;
optClock.addEventListener("change", () => {
  state.clockMode = optClock.value;
  lsSet("chess.clock", state.clockMode);
  resetClock();
});

// Appelé aussi dans refresh() : l'ordinateur répond quand c'est à lui de jouer.
renderVsControls();

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
    const sym = symAt(from);
    const color = sym === sym.toUpperCase() ? "w" : "b";
    const promo = await askPromotion(from, to, color);
    if (!promo) return; // annulé
    uci = from + to + promo;
  }
  state.selected = null;
  try {
    await ChessAPI.move(uci);
  } catch (err) {
    reportError("Coup refusé", err);
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
