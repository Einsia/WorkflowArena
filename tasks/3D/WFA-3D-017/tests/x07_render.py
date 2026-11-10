# -*- coding: utf-8 -*-
"""CDC-C-X07 M17 re-render (2026-10-25): blender -b scene.blend --python x07_render.py -- cfg.json
cfg: {"props": {...}, "frames": [film frames], "w": 320, "h": 180, "samples": 16, "dir": "...", "out": "...json",
      "engine": null | "CYCLES"}
Renders the 3D scene (sequencer off, compositor as authored) at film frame f = scene frame f + frame_start."""
import bpy, json, os, sys, time, traceback

argv = sys.argv[sys.argv.index("--") + 1:]
cfg = json.load(open(argv[0]))
sc = bpy.context.scene
res = {"frames": {}, "errors": []}
try:
    for k, v in cfg.get("props", {}).items():
        if k in sc.keys():
            sc[k] = v
    r = sc.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = int(cfg["w"]), int(cfg["h"]), 100
    r.use_sequencer = False
    r.image_settings.file_format = 'PNG'
    r.image_settings.color_mode = 'RGB'
    if cfg.get("engine"):
        r.engine = cfg["engine"]
    res["engine"] = r.engine
    if r.engine == 'CYCLES':
        c = sc.cycles
        c.device = 'CPU'
        c.samples = int(cfg.get("samples", 16))
        try:
            c.use_adaptive_sampling = True
            c.use_denoising = True
            c.denoiser = 'OPENIMAGEDENOISE'
        except Exception:
            pass
        try:
            c.time_limit = float(cfg.get("time_limit", 60))
        except Exception:
            pass
    elif 'EEVEE' in r.engine:
        try:
            sc.eevee.taa_render_samples = int(cfg.get("samples", 16))
        except Exception:
            pass
    for f in cfg["frames"]:
        t0 = time.time()
        sc.frame_set(int(f) + sc.frame_start)
        fp = os.path.join(cfg["dir"], f"rr_{int(f):04d}.png")
        r.filepath = fp
        try:
            bpy.ops.render.render(write_still=True)
            res["frames"][str(f)] = fp if os.path.exists(fp) else "ERR no file written"
        except Exception as e:
            res["frames"][str(f)] = f"ERR {type(e).__name__}: {e}"
        res.setdefault("seconds", {})[str(f)] = round(time.time() - t0, 1)
except Exception:
    res["errors"].append(traceback.format_exc()[-800:])
json.dump(res, open(cfg["out"], "w"))
print("X07RENDER_OK")
