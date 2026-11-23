// Point d'entrée de l'application web (module ES).
// Orchestration : refresh depuis l'API, boutons, mode vs ordinateur,
// overlay API injoignable. Le JS n'implémente aucune règle d'échecs.

import { ChessAPI } from "./api.js";
import { boardEl, renderAll, renderReviewBar, reviewStep, safeRender, render } from "./board-view.js";
import { initClock, renderClocks, resetClock } from "./clock.js";
import { initInteractions, tryMove } from "./interactions.js";
import { initSettings, renderGames } from "./settings.js";
import {
  maybeShowGameOver,
  renderEval,
  renderMovesTable,
  renderPlayers,
  renderPuzzleBlock,
  renderReviewResults,
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
    if (state.autoFlip && !state.vs && !state.spectator) state.flipped = status.turn === "b";
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
    safeRender("problème", renderPuzzleBlock);
    if (state.analysis) safeRender("revue", renderReviewResults);
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
      if (state.spectator) {
        setStatus("👁 Mode spectateur — la partie est suivie en direct (coups joués par CLI/agent)");
      } else if (state.puzzle) {
        const p = state.puzzle;
        setStatus(`🧩 Problème — mat en ${p.n} (${p.theme}). À vous de trouver le premier coup !`);
      } else {
        setStatus(statusText(status));
      }
    }
    // Ouverture reconnue (V9) affichée au-dessus de la liste des coups
    safeRender("ouverture", () => {
      const el = document.getElementById("opening-label");
      if (el) el.textContent = status.opening ? `${status.opening.code} — ${status.opening.name}` : "";
    });
    boardEl.classList.toggle("checkmate", status.result === "checkmate");
    maybeShowGameOver(status);
    maybeAiMove(status);
    firePremove(status).catch(() => {}); // V10 : prémouvement en attente
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
  if (state.spectator) return; // jamais d'IA en mode spectateur
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
    await ChessAPI.aiMove({ level: state.level });
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
  state.puzzle = null;
  state.analysis = null;
  state.hint = null;
  if (state.vs && state.colorChoice === "random") {
    state.actualColor = Math.random() < 0.5 ? "w" : "b";
  }
  try {
    const body = {};
    if (state.vs) {
      body.mode = "computer";
      body.level = state.level;
    } else if (state.chess960Mode) {
      body.mode = "human";
      body.chess960 = chess960Index();
    } else {
      body.mode = "human";
    }
    await ChessAPI.newGame(body);
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

function chess960Index() {
  const el = document.getElementById("opt-chess960-index");
  const n = parseInt(el && el.value, 10);
  return Number.isInteger(n) && n >= 0 && n <= 959 ? n : 518;
}

function syncNewGameOpts() {
  document.getElementById("newgame-computer-opts").classList.toggle("hidden", !state.vs);
  document.getElementById("newgame-puzzle-opts").classList.toggle("hidden", !state.puzzleMode);
  document.getElementById("newgame-chess960-opts").classList.toggle("hidden", !state.chess960Mode);
  document.getElementById("newgame-autoflip").classList.toggle(
    "hidden", state.vs || state.spectator || state.puzzleMode || state.chess960Mode
  );
}

function openNewGameModal() {
  const modal = document.getElementById("newgame-modal");
  syncNewGameOpts();
  document.getElementById("chip-autoflip").setAttribute("aria-pressed", String(state.autoFlip));
  renderVsControls();
  modal.classList.remove("hidden");
}

document.getElementById("btn-new").addEventListener("click", openNewGameModal);
for (const id of ["mode-human", "mode-computer", "mode-spectator", "mode-puzzle", "mode-chess960"]) {
  document.getElementById(id).addEventListener("click", () => {
    state.spectator = id === "mode-spectator";
    state.vs = id === "mode-computer";
    state.puzzleMode = id === "mode-puzzle";
    state.chess960Mode = id === "mode-chess960";
    lsSet("chess.spectator", state.spectator ? "1" : "0");
    lsSet("chess.vs", state.vs ? "1" : "0");
    syncNewGameOpts();
    renderVsControls();
  });
}
document.getElementById("btn-chess960-random").addEventListener("click", () => {
  document.getElementById("opt-chess960-index").value = String(Math.floor(Math.random() * 960));
});
document.getElementById("chip-autoflip").addEventListener("click", () => {
  state.autoFlip = !state.autoFlip;
  lsSet("chess.autoflip", state.autoFlip ? "1" : "0");
  document.getElementById("chip-autoflip").setAttribute("aria-pressed", String(state.autoFlip));
});
document.getElementById("btn-start-game").addEventListener("click", async () => {
  document.getElementById("newgame-modal").classList.add("hidden");
  if (state.spectator) {
    // Spectateur : on ne touche PAS à la partie persistée, on la suit juste.
    await refresh();
    return;
  }
  if (state.puzzleMode) {
    // Problème (V7) : charge un mat-en-n dans l'état partagé.
    state.selected = null;
    state.reviewPly = null;
    state.analysis = null;
    state.puzzle = null;
    try {
      const r = await ChessAPI.puzzle(parseInt(state.puzzleLevel, 10));
      state.puzzle = r.puzzle;
      toast(`Problème chargé — mat en ${r.puzzle.n} (${r.puzzle.theme}).`, "info");
    } catch (err) {
      reportError("Problème", err);
    }
    await refresh();
    resetClock();
    return;
  }
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
  if (state.spectator) {
    refresh(); // spectateur : on ne réinitialise jamais la partie suivie
  } else {
    openNewGameModal();
  }
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
  state.level = v;
  lsSet("chess.level", v);
}, state.level);
wireChips("opt-puzzle-level", (v) => {
  state.puzzleLevel = v;
  lsSet("chess.puzzleLevel", v);
}, state.puzzleLevel);

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
    document.getElementById("tabpanel-parties").classList.toggle("hidden", tab.dataset.tab !== "parties");
    if (tab.dataset.tab === "parties") renderGames();
  });
});

// --- Init ------------------------------------------------------------------------

// --- V8 : Abandonner / Proposer nulle / Reprendre (modale de confirmation) -------

function askConfirm(text) {
  return new Promise((resolve) => {
    const modal = document.getElementById("confirm-modal");
    document.getElementById("confirm-text").textContent = text;
    modal.classList.remove("hidden");
    const yes = document.getElementById("btn-confirm-yes");
    const no = document.getElementById("btn-confirm-no");
    const onYes = () => done(true);
    const onNo = () => done(false);
    function done(val) {
      modal.classList.add("hidden");
      yes.removeEventListener("click", onYes);
      no.removeEventListener("click", onNo);
      resolve(val);
    }
    yes.addEventListener("click", onYes);
    no.addEventListener("click", onNo);
  });
}

document.getElementById("btn-resign").addEventListener("click", async () => {
  if (!(await askConfirm("Abandonner la partie ? Le camp au trait perd la partie."))) return;
  try {
    await ChessAPI.resign();
    toast("Abandon enregistré.", "info");
  } catch (err) {
    reportError("Abandon", err);
  }
  await refresh();
});
document.getElementById("btn-offer-draw").addEventListener("click", async () => {
  if (!(await askConfirm("Proposer une nulle ?"))) return;
  try {
    const r = await ChessAPI.offerDraw(!state.vs); // acceptée d'office en mode 2 joueurs
    toast(r.accepted ? "Nulle acceptée — partie nulle." : "Nulle refusée par l'ordinateur (évaluation défavorable).", "info");
  } catch (err) {
    reportError("Nulle", err);
  }
  await refresh();
});
document.getElementById("btn-takeback").addEventListener("click", async () => {
  if (!(await askConfirm("Reprendre le dernier échange (votre coup + la réponse de l'ordinateur) ?"))) return;
  try {
    const r = await ChessAPI.takeback();
    toast(`Échange repris : ${r.undone.join(", ")}.`, "info");
  } catch (err) {
    reportError("Reprendre", err);
  }
  await refresh();
});

// --- V7 : bouton « Solution » du problème ------------------------------------------
document.getElementById("btn-puzzle-solution").addEventListener("click", () => {
  if (state.puzzle) toast(`Solution : ${state.puzzle.solution}`, "info");
});

// --- V9 : Indice (meilleur coup) + Revue de partie ---------------------------------
document.getElementById("btn-hint").addEventListener("click", async () => {
  try {
    const r = await ChessAPI.analyzePosition(3);
    state.hint = { from: r.best_move.slice(0, 2), to: r.best_move.slice(2, 4) };
    render();
    toast(`Meilleur coup : ${r.san} (score ${r.score} cp).`, "info");
  } catch (err) {
    reportError("Indice", err);
  }
});
document.getElementById("btn-review").addEventListener("click", async () => {
  try {
    state.analysis = await ChessAPI.analyze(2);
    safeRender("revue", renderReviewResults);
    renderMovesTable();
    toast("Revue prête : étiquettes sur les coups + courbe d'évaluation.", "info");
  } catch (err) {
    reportError("Revue", err);
  }
});

// --- V10 : raccourcis clavier (désactivés dans les champs texte) --------------------
document.addEventListener("keydown", (e) => {
  const tag = (e.target && e.target.tagName) || "";
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
  if (e.key === "?") {
    e.preventDefault();
    document.getElementById("shortcuts-overlay").classList.toggle("hidden");
    return;
  }
  if (!document.getElementById("shortcuts-overlay").classList.contains("hidden")) return;
  switch (e.key) {
    case "ArrowLeft": e.preventDefault(); reviewStep("prev"); break;
    case "ArrowRight": e.preventDefault(); reviewStep("next"); break;
    case "Home": e.preventDefault(); reviewStep("first"); break;
    case "End": e.preventDefault(); reviewStep("last"); break;
    case "f": document.getElementById("btn-flip").click(); break;
    case "n": openNewGameModal(); break;
    case "u": document.getElementById("btn-undo").click(); break;
  }
});
document.getElementById("btn-close-shortcuts").addEventListener("click", () => {
  document.getElementById("shortcuts-overlay").classList.add("hidden");
});

// --- V10 : le prémouvement part dès que c'est à nous de jouer ------------------------
async function firePremove(status) {
  if (!state.premove || state.thinking) return;
  if (status.result !== "ongoing") { state.premove = null; return; }
  const myColor = state.vs
    ? state.colorChoice === "random" ? state.actualColor : state.colorChoice
    : null;
  if (!myColor || status.turn !== myColor) return;
  const pm = state.premove;
  state.premove = null;
  render();
  try {
    await tryMove(pm.from, pm.to, refresh, true); // refusé -> annulé sans message
  } catch { /* annulé silencieusement */ }
}

document.getElementById("btn-help").addEventListener("click", () => {
  document.getElementById("help-modal").classList.remove("hidden");
});
document.getElementById("btn-close-help").addEventListener("click", () => {
  document.getElementById("help-modal").classList.add("hidden");
});

initSound();
initClock();
initInteractions({ refresh });
initSettings();
renderVsControls();
renderReviewBar();
resetClock();
refresh();
