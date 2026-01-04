import argparse
import hashlib
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chess
import chess.engine
import chess.pgn


def extract_eval_white_pov(score: chess.engine.PovScore) -> Dict[str, Optional[int]]:
    """
    Returns eval from White POV as raw centipawns or mate.
    - cp: integer centipawns (positive = White better)
    - mate: integer (positive = White mates in N, negative = Black mates in N)
    """
    s = score.pov(chess.WHITE)
    if s.is_mate():
        return {"cp": None, "mate": s.mate()}
    return {"cp": s.score(mate_score=100000), "mate": None}


def pv_to_uci_list(pv_moves: List[chess.Move]) -> List[str]:
    return [m.uci() for m in pv_moves]


def pv_uci_to_san(pv_uci: List[str], start_fen: str, max_halfmoves: int = 8) -> List[str]:
    """
    Convert PV UCI moves to SAN for display, given the starting FEN.
    Safe to treat SAN as derived display data.
    """
    board = chess.Board(start_fen)
    out = []
    for uci in pv_uci[:max_halfmoves]:
        mv = chess.Move.from_uci(uci)
        if mv not in board.legal_moves:
            break
        out.append(board.san(mv))
        board.push(mv)
    return out


def read_pgn_text(pgn_path: Optional[str], pgn_text: Optional[str]) -> str:
    if pgn_text:
        return pgn_text

    if not pgn_path:
        raise SystemExit("Provide --pgn PATH or --pgn-text STRING")

    text = Path(pgn_path).read_text(encoding="utf-8", errors="replace")

    # If user passed raw moves without headers, add minimal headers so parser is happy
    if "[Event" not in text:
        text = (
            '[Event "?"]\n[Site "?"]\n[Date "????.??.??"]\n[Round "?"]\n'
            '[White "?"]\n[Black "?"]\n[Result "*"]\n\n'
            + text.strip()
            + "\n"
        )
    return text


def parse_first_game(pgn_text: str) -> chess.pgn.Game:
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise SystemExit("Could not parse PGN (no game found).")
    return game


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pgn", help="Path to a .pgn file (uses first game inside).")
    ap.add_argument("--pgn-text", help="Inline PGN text (headers optional).")
    ap.add_argument("--stockfish", required=True, help="Path to Stockfish executable.")
    ap.add_argument("--out", default="engine_artifact.json", help="Output JSON path.")
    ap.add_argument("--depth", type=int, default=16)
    ap.add_argument("--multipv", type=int, default=1)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--hash", dest="hash_mb", type=int, default=256)
    ap.add_argument("--eval-every-ply", action="store_true", help="Evaluate after every ply.")
    ap.add_argument("--eval-after-black-only", action="store_true", help="Evaluate only after Black moves.")
    ap.add_argument("--pv-sans", action="store_true", help="Also store pv_san (derived, optional).")

    args = ap.parse_args()

    if args.eval_every_ply and args.eval_after_black_only:
        raise SystemExit("Choose only one: --eval-every-ply OR --eval-after-black-only")

    pgn_text = read_pgn_text(args.pgn, args.pgn_text)
    game = parse_first_game(pgn_text)
    board = game.board()

    headers = dict(game.headers)
    white_player = headers.get("White", "?")
    black_player = headers.get("Black", "?")
    result = headers.get("Result", "*")

    game_id = hashlib.md5(pgn_text.encode("utf-8", errors="replace")).hexdigest()[:16]

    output: Dict[str, Any] = {
        "game_id": game_id,
        "headers": headers,
        "white": white_player,
        "black": black_player,
        "result": result,
        "engine": {
            "name": "Stockfish",
            "depth": args.depth,
            "multipv": args.multipv,
        },
        "positions": [],
    }

    # Initial position (ply 0)
    output["positions"].append({
        "ply": 0,
        "fullmove": 1,
        "side_to_move": "white",
        "mover": None,
        "move": None,
        "fen": board.fen(),
        "eval": None,
        "pv_uci": [],
        **({"pv_san": []} if args.pv_sans else {}),
    })

    with chess.engine.SimpleEngine.popen_uci(args.stockfish) as engine:
        engine.configure({
            "Threads": args.threads,
            "Hash": args.hash_mb,
        })

        for move in game.mainline_moves():
            # mover is side BEFORE pushing
            mover = "white" if board.turn == chess.WHITE else "black"
            san = board.san(move)
            uci = move.uci()

            board.push(move)
            ply = board.ply()
            fullmove = board.fullmove_number
            side_to_move = "white" if board.turn == chess.WHITE else "black"

            should_eval = True
            if args.eval_after_black_only:
                # after Black moves => ply even
                should_eval = (ply % 2 == 0)

            eval_data = None
            pv_uci: List[str] = []
            pv_san: List[str] = []

            if should_eval:
                infos = engine.analyse(
                    board,
                    chess.engine.Limit(depth=args.depth),
                    multipv=args.multipv
                )
                info = infos[0]
                eval_data = extract_eval_white_pov(info["score"])

                pv_moves = info.get("pv", [])
                pv_uci = pv_to_uci_list(pv_moves[:12])  # keep some room; trim later in UI if needed

                if args.pv_sans:
                    pv_san = pv_uci_to_san(pv_uci, start_fen=board.fen(), max_halfmoves=8)

            pos_entry: Dict[str, Any] = {
                "ply": ply,
                "fullmove": fullmove,
                "side_to_move": side_to_move,
                "mover": mover,
                "move": {"san": san, "uci": uci},
                "fen": board.fen(),
                "eval": eval_data,
                "pv_uci": pv_uci,
            }
            if args.pv_sans:
                pos_entry["pv_san"] = pv_san

            output["positions"].append(pos_entry)

    Path(args.out).write_text(json.dumps(output, indent=2), encoding="utf-8")
    analyzed = sum(1 for p in output["positions"] if p.get("eval") is not None)
    print(f"Wrote {args.out} | game_id={game_id} | analyzed_positions={analyzed}/{len(output['positions'])}")


if __name__ == "__main__":
    main()
