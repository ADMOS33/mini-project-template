"""Game review (V9): per-ply evaluation, centipawn loss and labels.

For each ply: evaluation before/after the move (from the mover's perspective,
searched at ``depth``), the centipawn loss, and a label:

- ``meilleur`` (loss <= BEST_CP), ``excellent`` (<= EXCELLENT_CP),
  ``bon`` (< INACCURACY_CP), ``imprécision ?!`` (>= INACCURACY_CP),
  ``erreur ?`` (>= ERROR_CP), ``gaffe ??`` (>= BLUNDER_CP)
- ``brillant !!`` overrides: the engine's best move AND the mover gave up
  material (sacrifice) without losing evaluation.

Thresholds are constants (see README "Décisions"). Accuracy per player:
mean of per-ply ``max(0, 100 - loss)``.
"""

from __future__ import annotations

from chess.ai.evaluation import VALUES, evaluate
from chess.ai.search import best_move
from chess.engine.board import Board
from chess.engine.fen import board_from_fen
from chess.engine.game import Game
from chess.engine.movegen import apply_move
from chess.engine.san import move_to_san

BEST_CP = 5
EXCELLENT_CP = 25
INACCURACY_CP = 50
ERROR_CP = 100
BLUNDER_CP = 300

LABEL_BEST = "meilleur"
LABEL_EXCELLENT = "excellent"
LABEL_GOOD = "bon"
LABEL_INACCURACY = "imprécision ?!"
LABEL_ERROR = "erreur ?"
LABEL_BLUNDER = "gaffe ??"
LABEL_BRILLIANT = "brillant !!"


def _score_stm(board: Board) -> int:
    """Static evaluation from the side to move's perspective (centipawns)."""
    s = evaluate(board)
    return s if board.turn.value == "w" else -s


def _material(board: Board, color: str) -> int:
    return sum(
        VALUES[p.type] for p in board.squares if p is not None and p.color.value == color
    )


def _label(loss: int) -> str:
    if loss >= BLUNDER_CP:
        return LABEL_BLUNDER
    if loss >= ERROR_CP:
        return LABEL_ERROR
    if loss >= INACCURACY_CP:
        return LABEL_INACCURACY
    if loss <= BEST_CP:
        return LABEL_BEST
    if loss <= EXCELLENT_CP:
        return LABEL_EXCELLENT
    return LABEL_GOOD


def analyze_game(game: Game, depth: int = 2) -> dict:
    """Analyze every ply of ``game``; returns a JSON-serializable report."""
    from chess.ai.search import negamax, _INF

    fens = game.position_fens()
    plies: list[dict] = []
    losses: dict[str, list[int]] = {"w": [], "b": []}
    for i, move in enumerate(game.moves):
        board = board_from_fen(fens[i])
        mover = board.turn.value
        eval_before = _score_stm(board)
        # engine's best move at this position (for the brilliant label)
        engine_best, engine_score, _nodes = best_move(board, depth)
        child = apply_move(board, move)
        # evaluation after the move, still from the mover's perspective
        eval_after = -_score_stm(child)
        mat_before = _material(board, mover)
        # a sacrifice = the mover's material drops after the opponent's best reply
        from chess.engine.movegen import legal_moves as _legal_moves

        if _legal_moves(child):
            reply = best_move(child, depth)[0]
            mat_final = _material(apply_move(child, reply), mover)
        else:
            mat_final = mat_before  # game over (mate/stalemate): nothing captured
        # searched evaluation of the position before (mover to move)
        searched_before, _ = negamax(board, depth, -_INF, _INF)
        searched_after, _ = negamax(child, depth, -_INF, _INF)
        # mover's evaluation after the move = - (opponent's score in child)
        loss = max(0, searched_before + searched_after)
        sacrificed = mat_final < mat_before
        is_best = move.to_uci() == engine_best.to_uci() and loss <= BEST_CP
        label = LABEL_BRILLIANT if (is_best and sacrificed) else _label(loss)
        plies.append(
            {
                "ply": i + 1,
                "uci": move.to_uci(),
                "san": move_to_san(board, move),
                "color": mover,
                "eval_before": eval_before,
                "eval_after": eval_after,
                "loss": loss,
                "best_move": engine_best.to_uci(),
                "sacrifice": sacrificed,
                "label": label,
            }
        )
        losses[mover].append(loss)
    accuracy = {
        c: round(100 - min(100, sum(v) / len(v)), 1) if v else 100.0
        for c, v in losses.items()
    }
    return {"depth": depth, "plies": plies, "accuracy": accuracy}
