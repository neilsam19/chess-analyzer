from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.runner import run_analysis

router = APIRouter()

@router.post("/analyze")
async def analyze(pgn: UploadFile = File(...)):
    """
    Accepts a PGN file upload and runs the full analysis pipeline.
    Returns combined engine + insights data.
    """
    if not pgn.filename.lower().endswith((".pgn", ".txt")):
        raise HTTPException(status_code=400, detail="Upload a .pgn file")

    pgn_bytes = await pgn.read()
    if len(pgn_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        return await run_analysis(pgn_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
