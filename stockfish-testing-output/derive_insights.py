import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


MATE_BIG = 100000  # numeric stand-in for mate for ordering/threshold logic


def eval_to_numeric_cp(eval_obj: Optional[Dict[str, Any]]) -> Optional[int]:
    """
    Convert {"cp": int|None, "mate": int|None} (White POV) into a single numeric value for comparisons.
    - cp stays cp
    - mate becomes +/- MATE_BIG (sign indicates who is mating)
    """
    if eval_obj is None:
        return None
    mate = eval_obj.get("mate")
    cp = eval_obj.get("cp")
    if mate is not None:
        return MATE_BIG if mate > 0 else -MATE_BIG
    return cp


def mover_from_ply(ply: int) -> str:
    # After a move is played, ply increments. Odd ply => White just moved; even => Black just moved.
    return "white" if (ply % 2 == 1) else "black"


def compute_turning_points(positions: List[Dict[str, Any]], min_abs_delta_cp: int = 100) -> List[Dict[str, Any]]:
    """
    Returns list of turning points with deltas between consecutive evaluated positions.
    Assumes eval numeric is White POV (positive good for White).
    """
    # Keep only evaluated positions in chronological order (skip ply 0 eval=None)
    eval_positions = [p for p in positions if p.get("eval") is not None]

    tps = []
    prev = None
    for p in eval_positions:
        if prev is None:
            prev = p
            continue
        cp_prev = eval_to_numeric_cp(prev["eval"])
        cp_now = eval_to_numeric_cp(p["eval"])
        if cp_prev is None or cp_now is None:
            prev = p
            continue

        delta = cp_now - cp_prev  # White POV delta
        if abs(delta) >= min_abs_delta_cp:
            ply = p["ply"]
            mover = p.get("mover") or mover_from_ply(ply)

            tp = {
                "ply": ply,
                "fullmove": p.get("fullmove"),
                "mover": mover,
                "side_to_move": p.get("side_to_move"),
                "played": p.get("move"),
                "fen": p.get("fen"),
                "eval_before_cp": cp_prev,
                "eval_after_cp": cp_now,
                "delta_cp_white_pov": delta,
                "pv_uci": p.get("pv_uci", []),
                "best_move_uci": (p.get("pv_uci", [None])[0] if p.get("pv_uci") else None),
            }
            tps.append(tp)
        prev = p

    # Sort by absolute impact, descending (keep stable info too)
    tps.sort(key=lambda x: abs(x["delta_cp_white_pov"]), reverse=True)
    return tps


def delta_from_mover_pov(delta_white_pov: int, mover: str) -> int:
    """
    Convert delta (White POV) to delta from mover's POV:
    - if White moved, mover POV == White POV
    - if Black moved, mover POV == -(White POV)
    Positive means mover improved their situation; negative means mover worsened.
    """
    return delta_white_pov if mover == "white" else -delta_white_pov


def find_first_critical_mistake(
    positions: List[Dict[str, Any]],
    min_drop_mover_cp: int = 150,
    decided_threshold_cp: int = 150,
    recovery_threshold_cp: int = 100,
    lookahead_plies: int = 12,
) -> Optional[Dict[str, Any]]:
    """
    Earliest 'irreversible' mistake heuristic:
    - mover makes a sizeable drop from their POV (<= -min_drop_mover_cp)
    - eval crosses into 'decided' territory for the opponent (|eval_after| >= decided_threshold_cp in opponent-favored direction)
    - and does not recover past recovery_threshold in the opposite direction for lookahead window

    All evals are White POV.
    """
    eval_positions = [p for p in positions if p.get("eval") is not None]
    # Build quick ply -> index map
    ply_to_index = {p["ply"]: i for i, p in enumerate(eval_positions)}

    for i in range(1, len(eval_positions)):
        prev = eval_positions[i - 1]
        cur = eval_positions[i]

        cp_prev = eval_to_numeric_cp(prev["eval"])
        cp_cur = eval_to_numeric_cp(cur["eval"])
        if cp_prev is None or cp_cur is None:
            continue

        delta_white = cp_cur - cp_prev
        ply = cur["ply"]
        mover = cur.get("mover") or mover_from_ply(ply)
        delta_mover = delta_from_mover_pov(delta_white, mover)

        # mover made things worse for themselves significantly
        if delta_mover > -min_drop_mover_cp:
            continue

        # Did the eval cross into "decided for opponent" territory?
        # If mover is White, opponent is Black => decided if cp_cur <= -decided_threshold_cp
        # If mover is Black, opponent is White => decided if cp_cur >= +decided_threshold_cp
        if mover == "white":
            if cp_cur > -decided_threshold_cp:
                continue
        else:
            if cp_cur < decided_threshold_cp:
                continue

        # Check "no meaningful recovery" in next lookahead window
        end = min(i + lookahead_plies, len(eval_positions) - 1)
        window = eval_positions[i:end + 1]
        cps = [eval_to_numeric_cp(p["eval"]) for p in window if eval_to_numeric_cp(p["eval"]) is not None]
        if not cps:
            continue

        if mover == "white":
            # recovery would be cp rising back above -recovery_threshold_cp (i.e., not so bad for White)
            if max(cps) > -recovery_threshold_cp:
                continue
        else:
            # recovery would be cp dropping back below +recovery_threshold_cp (i.e., not so good for White anymore)
            if min(cps) < recovery_threshold_cp:
                continue

        # This qualifies as first critical mistake
        return {
            "ply": ply,
            "fullmove": cur.get("fullmove"),
            "mover": mover,
            "played": cur.get("move"),
            "fen": cur.get("fen"),
            "eval_before_cp": cp_prev,
            "eval_after_cp": cp_cur,
            "delta_cp_white_pov": delta_white,
            "delta_cp_mover_pov": delta_mover,
            "best_move_uci": (cur.get("pv_uci", [None])[0] if cur.get("pv_uci") else None),
            "pv_uci": cur.get("pv_uci", []),
        }

    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True, help="engine_artifact.json")
    ap.add_argument("--out", default="insights.json")
    ap.add_argument("--tp-threshold", type=int, default=100, help="Turning point threshold in cp (abs delta).")
    args = ap.parse_args()

    data = json.loads(Path(args.in_path).read_text(encoding="utf-8"))
    positions = data["positions"]

    turning_points = compute_turning_points(positions, min_abs_delta_cp=args.tp_threshold)
    first_critical = find_first_critical_mistake(positions)

    # Keep also a time-ordered turning point list for UI (sort by ply)
    turning_points_by_time = sorted(turning_points, key=lambda x: x["ply"])

    out = {
        "game_id": data.get("game_id"),
        "source_engine_artifact": Path(args.in_path).name,
        "turning_points": turning_points_by_time,
        "top_turning_points": turning_points[:10],  # by magnitude
        "first_critical_mistake": first_critical,
    }

    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {args.out} | turning_points={len(turning_points_by_time)} | first_critical={'yes' if first_critical else 'no'}")


if __name__ == "__main__":
    main()
