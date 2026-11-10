#!/usr/bin/env python3
"""Harbor reward for comp-capri-scoring: fraction of the 13 eligible real CAPRI scorer groups beaten on enrichment
(n_acc_models10, then n_med_models10)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V  # noqa: E402
from _common import emit, LOG  # noqa: E402

sub = sys.argv[1]
if not os.path.isdir(sub):
    emit(0.0, {"valid": 0})
    sys.exit(0)
truth = V.load_truth()
agg, per, invalid = V.score_submission(sub, truth)
G = V.load_groups()
elig = {u: v[1] for u, v in G.items() if v[1]['n_targets_submitted'] >= V.MIN_TARGETS_ELIGIBLE}
key = lambda x: (x['n_acc_models10'], x['n_med_models10'])
mine = key(agg)
json.dump({'aggregate': agg, 'per_target': per, 'invalid_ids_in_top10': invalid,
           'field': {u: key(v) for u, v in elig.items()}}, open(os.path.join(LOG, "details.json"), "w"), indent=1)
if agg['n_targets_submitted'] == 0:
    emit(0.0, {"valid": 0})
    sys.exit(0)
beaten = sum(1 for v in elig.values() if key(v) < mine)
better = sum(1 for v in elig.values() if key(v) > mine)
emit(beaten / len(elig), {"valid": 1, "n_acc_models10": agg['n_acc_models10'], "n_med_models10": agg['n_med_models10'],
                          "hits10": agg['hits10'], "mean_dockq_top1": agg['mean_dockq_top1'], "rank": better + 1, "field_size": len(elig) + 1})
