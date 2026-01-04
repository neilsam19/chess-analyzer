from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class EvalData(BaseModel):
    cp: Optional[int]
    mate: Optional[int]


class MoveData(BaseModel):
    san: str
    uci: str


class Position(BaseModel):
    ply: int
    fullmove: int
    side_to_move: str
    mover: Optional[str]
    move: Optional[MoveData]
    fen: str
    eval: Optional[EvalData]
    pv_uci: List[str]
    pv_san: Optional[List[str]] = None


class EngineAnalysis(BaseModel):
    game_id: str
    headers: Dict[str, str]
    white: str
    black: str
    result: str
    engine: Dict[str, Any]
    positions: List[Position]


class TurningPoint(BaseModel):
    ply: int
    fullmove: int
    mover: str
    played: Optional[MoveData]
    eval_before_cp: Optional[int]
    eval_after_cp: Optional[int]
    delta_cp_white_pov: int
    best_move_uci: str
    position_fen: str


class Insights(BaseModel):
    top_turning_points: List[TurningPoint]


class AnalysisResponse(BaseModel):
    run_id: str
    engine: EngineAnalysis
    insights: Insights
