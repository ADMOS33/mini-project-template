"""Negamax search with alpha-beta pruning over the engine's legal moves.

``best_move(board, depth)`` returns ``(move, score, nodes)`` where ``score``
is in centipawns from the side to move's perspective and ``nodes`` is the
number of nodes visited. Mate is ±MATE_SCORE adjusted by the remaining depth,
so a faster mate scores higher.
"""

from __future__ import annotations

from chess.ai.evaluation import MATE_SCORE, VALUES, evaluate
from chess.engine.board import Board
from chess.engine.move import Move
from chess.engine.movegen import apply_move, is_square_attacked, legal_moves
from chess.engine.pieces import PieceType

_INF = MATE_SCORE * 2


def _move_order_key(board: Board, move: Move) -> int:
    """Ordering key: captures first (MVV-LVA), then promotions.

    An en-passant capture (empty destination on the ep square) counts as a
    pawn capture.
    """
    victim = board.piece_at(move.to_sq)
    if victim is None and move.to_sq == board.ep_square:
        piece = board.piece_at(move.from_sq)
        if piece is not None and piece.type is PieceType.PAWN:
            victim_type = PieceType.PAWN
        else:
            victim_type = None
    else:
        victim_type = victim.type if victim is not None else None
    key = 0
    if victim_type is not None:
        attacker = board.piece_at(move.from_sq)
        key = 10 * VALUES[victim_type] - (VALUES[attacker.type] if attacker else 0)
    if move.promotion is not None:
        key += 10_000 + VALUES[move.promotion]
    return key


def _ordered_moves(board: Board) -> list[Move]:
    """Legal moves, best-ordered first (captures MVV-LVA, promotions)."""
    return sorted(legal_moves(board), key=lambda m: _move_order_key(board, m), reverse=True)


def negamax(board: Board, depth: int, alpha: int, beta: int) -> tuple[int, int]:
    """``(best score for the side to move, nodes visited)`` at ``depth``.

    Checkmate scores ``-MATE_SCORE - depth`` (adjusted by remaining depth);
    stalemate scores 0.
    """
    nodes = 1
    if depth == 0:
        return evaluate(board), nodes
    moves = _ordered_moves(board)
    if not moves:
        if is_square_attacked(board, board.king_square(board.turn), board.turn.opposite):
            return -MATE_SCORE - depth, nodes  # checkmated
        return 0, nodes  # stalemate
    best = -_INF
    for move in moves:
        child_score, child_nodes = negamax(apply_move(board, move), depth - 1, -beta, -alpha)
        nodes += child_nodes
        score = -child_score  # negamax: the child score is from the opponent's view
        if score > best:
            best = score
        if best > alpha:
            alpha = best
        if alpha >= beta:
            break
    return best, nodes


def best_move(board: Board, depth: int = 3) -> tuple[Move, int, int]:
    """``(best move, score for the side to move, nodes visited)`` at ``depth``."""
    if depth < 1:
        raise ValueError(f"depth must be >= 1, got {depth}")
    best: Move | None = None
    best_score = -_INF
    alpha = -_INF
    nodes = 0
    for move in _ordered_moves(board):
        child_score, child_nodes = negamax(apply_move(board, move), depth - 1, -_INF, -alpha)
        nodes += 1 + child_nodes
        score = -child_score  # negamax: child score is from the opponent's view
        if score > best_score:
            best_score = score
            best = move
        if score > alpha:
            alpha = score
    if best is None:
        raise ValueError("no legal move available")
    return best, best_score, nodes
