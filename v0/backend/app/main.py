from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.analyze import router as analyze_router
from app.init_dirs import ensure_dirs

app = FastAPI(title="Chess Analysis v0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # v0 only; tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def _startup():
    ensure_dirs()

@app.get("/health")
def health():
    return {"status": "ok"}

# Include API routes
app.include_router(analyze_router, prefix="/api")

# Serve frontend
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
