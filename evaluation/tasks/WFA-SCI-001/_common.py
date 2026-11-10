import json, os
LOG = os.environ.get("WFS_LOG_DIR", "/logs/verifier")


def emit(reward, extra):
    out = {"reward": float(reward)}
    out.update({k: float(v) for k, v in extra.items() if isinstance(v, (int, float, bool)) and v is not None})
    os.makedirs(LOG, exist_ok=True)
    open(os.path.join(LOG, "reward.json"), "w").write(json.dumps(out))
    open(os.path.join(LOG, "reward.txt"), "w").write(f"{float(reward)}\n")
    print(json.dumps(out))
