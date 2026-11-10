#!/usr/bin/env python3
"""Harbor reward for comp-dream5-network-inference: fraction of the 35 official DREAM5 methods (excl. community) beaten on overall score."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V  # noqa: E402
from _common import emit, LOG  # noqa: E402

sub = sys.argv[1]
if not os.path.isdir(sub):
    emit(0.0, {"valid": 0})
    sys.exit(0)
out = V.score_dir(sub)
board = V.load_board()
out.update(V.rank(out["overall"], board))
json.dump(out, open(os.path.join(LOG, "details.json"), "w"), ensure_ascii=False, indent=1)
if not out.get("complete"):
    emit(0.0, {"valid": 0, "overall": out["overall"]})
    sys.exit(0)
methods = [float(r["overall"]) for r in board if r["kind"] != "community"]
beaten = sum(1 for v in methods if v < out["overall"] - 1e-9)
emit(beaten / len(methods), {"valid": 1, "overall": out["overall"], "aupr_score": out["aupr_score"], "auroc_score": out["auroc_score"],
                             "rank_among_35_methods": int(out["rank_among_35_methods"].split("/")[0]), "official_methods": len(methods)})
