import json
import subprocess
from pathlib import Path
from uuid import uuid4

from .config import UPLOADS_DIR, ARTIFACTS_DIR, SCRIPTS_DIR, STOCKFISH_PATH


def run_pipeline(pgn_bytes: bytes) -> dict:
    """
    Saves PGN, runs:
      1) analyze_game.py -> engine_artifact.json
      2) derive_insights.py -> insights.json
    Returns combined payload for the frontend.
    """
    run_id = uuid4().hex

    # File paths for this run
    pgn_path = UPLOADS_DIR / f"{run_id}.pgn"
    engine_path = ARTIFACTS_DIR / f"{run_id}.engine.json"
    insights_path = ARTIFACTS_DIR / f"{run_id}.insights.json"

    pgn_path.write_bytes(pgn_bytes)

    analyze_py = SCRIPTS_DIR / "analyze_game.py"
    derive_py = SCRIPTS_DIR / "derive_insights.py"

    # ---- 1) Analyze PGN with Stockfish (adjust args to match YOUR script) ----
    # IMPORTANT: you must align these CLI args to what analyze_game.py expects.
    cmd1 = [
        "python",
        str(analyze_py),
        "--pgn",
        str(pgn_path),
        "--stockfish",
        STOCKFISH_PATH,
        "--out",
        str(engine_path),
    ]
    subprocess.run(cmd1, check=True)

    # ---- 2) Derive turning points (adjust args to match YOUR script) ----
    cmd2 = [
        "python",
        str(derive_py),
        "--in",
        str(engine_path),
        "--out",
        str(insights_path),
    ]
    subprocess.run(cmd2, check=True)

    engine = json.loads(engine_path.read_text(encoding="utf-8"))
    insights = json.loads(insights_path.read_text(encoding="utf-8"))

    return {
        "run_id": run_id,
        "engine": engine,
        "insights": insights,
    }
