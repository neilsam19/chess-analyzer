from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .init_dirs import ensure_dirs
from .pipeline import run_pipeline

app = FastAPI(title="Chess Analysis v0")

# Allow frontend dev server later
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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

@app.post("/api/analyze")
async def analyze(pgn: UploadFile = File(...)):
    if not pgn.filename.lower().endswith((".pgn", ".txt")):
        raise HTTPException(status_code=400, detail="Upload a .pgn file")

    pgn_bytes = await pgn.read()
    if len(pgn_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        return run_pipeline(pgn_bytes)
    except Exception as e:
        # For v0, surface error; later we’ll log nicely
        raise HTTPException(status_code=500, detail=str(e))
