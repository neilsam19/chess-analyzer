from .config import UPLOADS_DIR, ARTIFACTS_DIR

def ensure_dirs():
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
