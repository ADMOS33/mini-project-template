// HTTP client helpers for the FastAPI server (chess/api/server.py).
// Every helper returns parsed JSON and throws Error(detail) on HTTP errors.

const ChessAPI = {
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
  newGame: () => ChessAPI._req("/api/new", { method: "POST" }),
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
  aiMove: (depth) =>
    ChessAPI._req("/api/ai-move", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ depth }),
    }),
  undo: () => ChessAPI._req("/api/undo", { method: "POST" }),
};
