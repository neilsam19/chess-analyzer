from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parents[2]
UPLOADS_DIR = BASE_DIR / "uploads"
ARTIFACTS_DIR = BASE_DIR / "artifacts"
SCRIPTS_DIR = BASE_DIR / "scripts"

STOCKFISH_PATH = os.getenv("STOCKFISH_PATH")
