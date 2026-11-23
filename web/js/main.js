// Point d'entrée de l'application web (module ES).
// Orchestration : refresh depuis l'API, boutons, mode vs ordinateur,
// overlay API injoignable. Le JS n'implémente aucune règle d'échecs.

import { ChessAPI } from "./api.js";
import { renderAll, renderReviewBar, reviewStep, safeRender, render } from "./board-view.js";
import { initClock, renderClocks, resetClock } from "./clock.js";
import { initInteractions } from "./interactions.js";
import {
  maybeShowGameOver,
  renderEval,
  renderMovesTable,
  renderPlayers,
  renderVsControls,
} from "./panels.js";
import { playMoveSound, initSound } from "./sound.js";
import { lsSet, setStatus, state, statusText, wireChips } from "./state.js";
import { reportError, toast } from "./toasts.js";

// --- API injoignable : overlay + réessai automatique toutes les 3 s ---------
// Une erreur réseau (fetch qui échoue) est un TypeError ; une erreur HTTP
// de l'API est une Error(detail) et ne déclenche PAS l'overlay.
function isNetworkError(err) {
  return err instanceof TypeError;
}

let apiDown = false;
function setApiDown(down) {
  apiDown = down;
  const el = document.getElementById("api-down");
  if (el) el.classList.toggle("hidden", !down);
  if (!down) refresh();
}
async function probeApi() {
  try {
    await ChessAPI.status();
    if (apiDown) setApiDown(false);
  } catch (err) {
    if (isNetworkError(err)) setApiDown(true);
  }
}
setInterval(() => {
  if (apiDown) probeApi();
}, 3000);

// --- Rafraîchissement depuis l'API -------------------------------------------

async function refresh() {
  state.refreshing = true;
  const loadingEl = document.getElementById("board-loading");
  if (!state.boardData && state.reviewPly === null && loadingEl) {
    loadingEl.classList.remove("hidden");
  }
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
    if (typeof status.version === "number") state.lastVersion = status.version;
    // Retour automatique du plateau en mode 2 joueurs : on voit toujours son camp en bas
    if (state.autoFlip && !state.vs) state.flipped = status.turn === "b";
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
    if (loadingEl) loadingEl.classList.add("hidden");
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
    if (isNetworkError(err)) setApiDown(true);
    else reportError("Erreur API", err);
  } finally {
    state.refreshing = false;
  }
}

// --- Synchro live (V5) : poll /api/status chaque seconde ----------------------
// Si `version` a changé (coup joué via la CLI, un autre navigateur, un agent),
// on rafraîchit tout : un coup extérieur apparaît en moins de 2 s.
async function pollStatus() {
  if (state.refreshing || apiDown) return;
  let st;
  try {
    st = await ChessAPI.status();
  } catch {
    return; // silencieux : les erreurs visibles sont gérées par refresh()
  }
  if (typeof st.version !== "number") return;
  if (state.lastVersion !== null && st.version !== state.lastVersion) {
    await refresh();
  } else {
    state.lastVersion = st.version;
  }
}
setInterval(pollStatus, 1000);

// --- Mode « Contre l'ordinateur » -----------------------------------------------

async function maybeAiMove(status) {
  const cc = state.vs
    ? state.colorChoice === "random"
      ? state.actualColor
      : state.colorChoice
    : null;
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

// --- Modale « Nouvelle partie » -------------------------------------------------

function openNewGameModal() {
  const modal = document.getElementById("newgame-modal");
  document.getElementById("newgame-computer-opts").classList.toggle("hidden", !state.vs);
  document.getElementById("newgame-autoflip").classList.toggle("hidden", state.vs);
  document.getElementById("chip-autoflip").setAttribute("aria-pressed", String(state.autoFlip));
  renderVsControls();
  modal.classList.remove("hidden");
}

document.getElementById("btn-new").addEventListener("click", openNewGameModal);
for (const id of ["mode-human", "mode-computer"]) {
  document.getElementById(id).addEventListener("click", () => {
    state.vs = id === "mode-computer";
    lsSet("chess.vs", state.vs ? "1" : "0");
    document.getElementById("newgame-computer-opts").classList.toggle("hidden", !state.vs);
    document.getElementById("newgame-autoflip").classList.toggle("hidden", state.vs);
    renderVsControls();
  });
}
document.getElementById("chip-autoflip").addEventListener("click", () => {
  state.autoFlip = !state.autoFlip;
  lsSet("chess.autoflip", state.autoFlip ? "1" : "0");
  document.getElementById("chip-autoflip").setAttribute("aria-pressed", String(state.autoFlip));
});
document.getElementById("btn-start-game").addEventListener("click", () => {
  document.getElementById("newgame-modal").classList.add("hidden");
  newGame();
});
document.getElementById("btn-cancel-newgame").addEventListener("click", () => {
  document.getElementById("newgame-modal").classList.add("hidden");
});
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

// --- Navigation dans l'historique (boutons + clavier) ---------------------------

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

// --- Adversaire : segmenté + options ----------------------------------------------

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
wireChips("opt-color", (v) => {
  state.colorChoice = v;
  lsSet("chess.color", v);
  if (v === "random") state.actualColor = Math.random() < 0.5 ? "w" : "b";
  renderPlayers();
}, state.colorChoice);
wireChips("opt-depth", (v) => {
  state.depth = parseInt(v, 10);
  lsSet("chess.depth", v);
}, String(state.depth));

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

// --- Onglets du panneau droit (Partie / Outils) -----------------------------------

document.querySelectorAll(".tabs .tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tabs .tab").forEach((t) =>
      t.setAttribute("aria-selected", String(t === tab))
    );
    document.getElementById("tabpanel-partie").classList.toggle("hidden", tab.dataset.tab !== "partie");
    document.getElementById("tabpanel-outils").classList.toggle("hidden", tab.dataset.tab !== "outils");
  });
});

// --- Init ------------------------------------------------------------------------

initSound();
initClock();
initInteractions({ refresh });
renderVsControls();
renderReviewBar();
resetClock();
refresh();
