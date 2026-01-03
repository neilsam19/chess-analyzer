import io
import json
import hashlib
import chess
import chess.pgn
import chess.engine

PGN_TEXT = """[Event "?"]
[Site "?"]
[Date "????.??.??"]
[Round "?"]
[White "?"]
[Black "?"]
[Result "*"]

1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. Be3 e5 7. Nf3 Be7 8. h3 Be6 9. Ng5 Bd7 10. Bc4 O-O 11. a4 Nc6 12. O-O Rc8 13. Ba2 h6 14. Nf3 Be6 15. Bd5 Bxd5 16. exd5 Nb4 17. a5 Rxc3 18. bxc3 Nbxd5 19. c4 Nxe3 20. fxe3 Qc7 21. Nd2 Qc5 22. Qf3 d5 23. Kh1 e4 24. Qe2 Rc8 25. Rfb1 Rc7 26. c3 Qd6 27. cxd5 Qxd5 28. Rb3 Bd6 29. g4 h5 30. Qg2 hxg4 31. hxg4 Nxg4 32. Qxg4 Qxd2 33. Qg2 Qxe3 34. Rd1 Rc5 35. Qg4 Qh6+ 36. Kg2 Rg5
"""
# Change this to your Stockfish path
STOCKFISH_PATH = "stockfish-windows-x86-64-sse41-popcnt.exe"  # e.g. r"C:\path\to\stockfish.exe" on Windows

# Output file
OUTPUT_FILE = "game_analysis.json"

# Engine configuration
DEPTH = 16                        # increase for stronger, slower evals
MULTIPV = 1                       # set to 2 or 3 if you want alternatives
EVAL_EVERY_PLY = True             # Set to False to evaluate only after Black's moves

def extract_score(score: chess.engine.PovScore) -> dict:
    """Extract score as raw data (from White's POV)."""
    s = score.pov(chess.WHITE)
    if s.is_mate():
        return {
            "cp": None,
            "mate": s.mate()
        }
    return {
        "cp": s.score(mate_score=100000),
        "mate": None
    }

def score_to_display_str(eval_dict: dict) -> str:
    """Convert eval dict to human-readable string."""
    if eval_dict["mate"] is not None:
        return f"M{eval_dict['mate']}"
    return f"{eval_dict['cp']/100:.2f}"

def main():
    game = chess.pgn.read_game(io.StringIO(PGN_TEXT))
    board = game.board()

    # Extract game metadata
    headers = game.headers
    white_player = headers.get("White", "?")
    black_player = headers.get("Black", "?")
    result = headers.get("Result", "*")

    # Generate game ID from PGN text
    game_id = hashlib.md5(PGN_TEXT.encode()).hexdigest()[:16]

    # Initialize output structure
    output = {
        "game_id": game_id,
        "white": white_player,
        "black": black_player,
        "result": result,
        "engine": {
            "name": "Stockfish",
            "depth": DEPTH,
            "multipv": MULTIPV
        },
        "positions": []
    }

    # Add initial position (before any moves)
    output["positions"].append({
        "ply": 0,
        "fullmove": 1,
        "side_to_move": "white",
        "move": None,
        "fen": board.fen(),
        "eval": None,
        "pv": []
    })

    with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as engine:
        # Configure engine
        engine.configure({
            "Threads": 4,
            "Hash": 256,
        })

        print(f"Analyzing game: {game_id}")
        print(f"{white_player} vs {black_player}")
        print("=" * 60)

        for move in game.mainline_moves():
            # Capture move info before pushing
            san = board.san(move)
            uci = move.uci()

            # Push the move
            board.push(move)
            ply = board.ply()
            fullmove = board.fullmove_number
            side_to_move = "white" if board.turn == chess.WHITE else "black"

            # Determine if we should evaluate this position
            should_eval = EVAL_EVERY_PLY or (ply % 2 == 0)  # Every ply or only after Black

            if should_eval:
                # Analyze position
                infos = engine.analyse(board, chess.engine.Limit(depth=DEPTH), multipv=MULTIPV)
                info = infos[0]

                # Extract eval
                eval_data = extract_score(info["score"])

                # Extract PV (principal variation)
                pv_moves = info.get("pv", [])
                pv_san = []
                pv_board = board.copy()
                for pv_move in pv_moves[:8]:  # First 8 half-moves
                    pv_san.append(pv_board.san(pv_move))
                    pv_board.push(pv_move)

                # Print progress
                eval_str = score_to_display_str(eval_data)
                side_moved = "Black" if (ply % 2 == 0) else "White"
                print(f"Move {fullmove} {side_moved} {san}: eval={eval_str}  PV: {' '.join(pv_san[:5])}")
            else:
                eval_data = None
                pv_san = []

            # Add position to output
            position_entry = {
                "ply": ply,
                "fullmove": fullmove,
                "side_to_move": side_to_move,
                "move": {
                    "san": san,
                    "uci": uci
                },
                "fen": board.fen(),
                "eval": eval_data,
                "pv": pv_san
            }
            output["positions"].append(position_entry)

    # Write JSON output
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    print("=" * 60)
    print(f"Analysis complete! Output saved to: {OUTPUT_FILE}")
    print(f"Total positions analyzed: {len([p for p in output['positions'] if p['eval'] is not None])}")

if __name__ == "__main__":
    main()
