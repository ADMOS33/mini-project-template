// HTTP client for the FastAPI server (chess/api/server.py).
// Every helper returns parsed JSON and throws Error(detail) on HTTP errors;
// a network failure (server down) surfaces as a TypeError from fetch.

export const ChessAPI = {
  async _req(path, options) {
    const res = await fetch(path, options);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(typeof data.detail === "string" ? data.detail : res.statusText);
    }
    return data;
  },

  status: () => ChessAPI._req("/api/status"),
  board: () => ChessAPI._req("/api/board"),
  moves: () => ChessAPI._req("/api/moves"),
  fen: () => ChessAPI._req("/api/fen"),
  eval: () => ChessAPI._req("/api/eval"),
  history: () => ChessAPI._req("/api/history"),
  pgn: () => ChessAPI._req("/api/pgn"),
  newGame: (body) =>
    ChessAPI._req("/api/new", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    }),
  move: (uci) =>
    ChessAPI._req("/api/move", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ move: uci }),
    }),
  load: (fen) =>
    ChessAPI._req("/api/load", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fen }),
    }),
  loadPgn: (pgn) =>
    ChessAPI._req("/api/load-pgn", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pgn }),
    }),
  post: (path, body) =>
    ChessAPI._req(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body ?? {}),
    }),
  aiMove: (body) => ChessAPI.post("/api/ai-move", body), // {depth} or {level}
  resign: () => ChessAPI.post("/api/resign"),
  offerDraw: (force) => ChessAPI.post("/api/offer-draw", { force }),
  takeback: () => ChessAPI.post("/api/takeback"),
  puzzle: (level, extra) => ChessAPI.post("/api/puzzle", { level, ...(extra || {}) }),
  solve: (move) => ChessAPI.post("/api/solve", { move }),
  analyze: (depth) => ChessAPI.post("/api/analyze", { depth }),
  analyzePosition: (depth) => ChessAPI.post("/api/analyze-position", { depth }),
  undo: () => ChessAPI._req("/api/undo", { method: "POST" }),
  flag: (color) =>
    ChessAPI._req("/api/flag", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ color }),
    }),
};
