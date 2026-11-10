# -*- coding: utf-8 -*-
"""在 Blender 内运行：blender -b scene.blend --python _bld_extract.py -- <out.json> <cfg.json>
导出通用场景数据，供各题 checks.py 做确定性测量。任何单项异常只记录，不中断。

cfg.json（均可省略）：
  frames:        [int,...]      需要采样世界矩阵的帧（动画题）
  anim_regex:    "regex"        只对名称匹配的对象逐帧采样（默认：有动画/约束/父级动画的对象）
  islands_regex: "regex"        对名称匹配的网格对象计算连通块数（大网格 >300k 顶点跳过）
  verts_regex:   "regex"        对名称匹配的网格对象导出评估后世界坐标顶点（最多 20000 个/对象，供精细测量）
  extra_py:      "python code"  额外代码，可读写字典 EXTRA（在 bpy 环境中执行），结果写入 out['extra']
"""
import bpy, sys, json, re, math, traceback
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else '/tmp/bld_extract.json'
cfg = {}
if len(argv) > 1:
    try:
        cfg = json.load(open(argv[1], encoding='utf-8'))
    except Exception:
        cfg = {}
errors = []
scene = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get()


def mat(m):
    return [[round(m[i][j], 6) for j in range(4)] for i in range(4)]


def _box(pts):
    return [[round(min(p[i] for p in pts), 5) for i in range(3)], [round(max(p[i] for p in pts), 5) for i in range(3)]]


def eval_mesh_stats(ob):
    """v0.2: exact world bbox + vertex/face counts of the EVALUATED geometry (modifiers, geometry nodes, curves, text).
    The v0.1 bbox transformed the 8 local bound_box corners, which overestimates rotated non-box objects."""
    ev = ob.evaluated_get(dg)
    try:
        me = ev.to_mesh()
    except Exception:
        me = None
    if me is None:
        return None
    try:
        n = len(me.vertices)
        if n == 0:
            return {'bbox': None, 'n_verts': 0, 'n_faces': len(me.polygons)}
        mw = ev.matrix_world
        try:
            import numpy as np
            co = np.empty(n * 3, dtype=np.float64)
            me.vertices.foreach_get('co', co)
            co = co.reshape(n, 3)
            m = np.array([[mw[i][j] for j in range(4)] for i in range(4)])
            w = co @ m[:3, :3].T + m[:3, 3]
            lo, hi = w.min(axis=0), w.max(axis=0)
            box = [[round(float(x), 5) for x in lo], [round(float(x), 5) for x in hi]]
        except ImportError:
            box = _box([mw @ v.co for v in me.vertices])
        return {'bbox': box, 'n_verts': n, 'n_faces': len(me.polygons)}
    finally:
        ev.to_mesh_clear()


def wbbox(ob):
    try:
        if ob.type in ('MESH', 'CURVE', 'SURFACE', 'FONT', 'META', 'CURVES', 'POINTCLOUD', 'VOLUME'):
            st = eval_mesh_stats(ob)
            if st and st['bbox']:
                return st['bbox']
        ev = ob.evaluated_get(dg)
        return _box([ev.matrix_world @ Vector(c) for c in ev.bound_box])
    except Exception:
        return None


def islands(ob):
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    try:
        n = len(me.vertices)
        if n == 0 or n > 300000:
            return None if n else 0
        parent = list(range(n))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        for e in me.edges:
            a, b = find(e.vertices[0]), find(e.vertices[1])
            if a != b:
                parent[a] = b
        return len({find(i) for i in range(n)})
    finally:
        ev.to_mesh_clear()


def verts(ob, cap=20000):
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    try:
        mw = ev.matrix_world
        vs = me.vertices
        step = max(1, len(vs) // cap)
        return [[round(c, 4) for c in (mw @ vs[i].co)] for i in range(0, len(vs), step)]
    finally:
        ev.to_mesh_clear()


out = {'blender_version': bpy.app.version_string, 'file': bpy.data.filepath}
try:
    us = scene.unit_settings
    r = scene.render
    out['scene'] = {'name': scene.name, 'unit_system': us.system, 'length_unit': us.length_unit, 'scale_length': us.scale_length,
                    'frame_start': scene.frame_start, 'frame_end': scene.frame_end, 'fps': r.fps, 'fps_base': r.fps_base,
                    'res': [r.resolution_x, r.resolution_y, r.resolution_percentage], 'engine': r.engine,
                    'camera': scene.camera.name if scene.camera else None}
except Exception:
    errors.append(traceback.format_exc()[-400:])


def walk(c, parent=None, acc=None):
    acc = acc if acc is not None else {}
    acc[c.name] = {'parent': parent, 'children': [x.name for x in c.children], 'objects': [o.name for o in c.objects],
                   'all_objects': [o.name for o in c.all_objects], 'hide_render': getattr(c, 'hide_render', False)}
    for ch in c.children:
        walk(ch, c.name, acc)
    return acc


try:
    out['collections'] = walk(scene.collection)
except Exception:
    errors.append(traceback.format_exc()[-400:])

isl_re = re.compile(cfg['islands_regex']) if cfg.get('islands_regex') else None
vrt_re = re.compile(cfg['verts_regex']) if cfg.get('verts_regex') else None
objs = {}
for ob in scene.objects:
    try:
        d = {'type': ob.type, 'parent': ob.parent.name if ob.parent else None,
             'collections': [c.name for c in ob.users_collection], 'matrix_world': mat(ob.matrix_world),
             'location': [round(x, 5) for x in ob.matrix_world.translation], 'rotation_euler': [round(x, 6) for x in ob.rotation_euler],
             'rotation_mode': ob.rotation_mode, 'scale': [round(x, 5) for x in ob.scale], 'dimensions': [round(x, 5) for x in ob.dimensions],
             'bbox_world': wbbox(ob), 'hide_render': ob.hide_render,
             'animated': bool(ob.animation_data and (ob.animation_data.action or ob.animation_data.drivers)),
             'constraints': [c.type for c in ob.constraints], 'modifiers': [m.type for m in ob.modifiers],
             'materials': [s.material.name for s in getattr(ob, 'material_slots', []) if s.material]}
        if ob.type in ('MESH', 'CURVE', 'SURFACE', 'FONT', 'META'):
            st = eval_mesh_stats(ob) or {}
            d['n_verts'] = st.get('n_verts', len(ob.data.vertices) if ob.type == 'MESH' else 0)
            d['n_faces'] = st.get('n_faces', len(ob.data.polygons) if ob.type == 'MESH' else 0)
            if ob.type == 'MESH':
                d['n_verts_raw'] = len(ob.data.vertices)
                d['n_faces_raw'] = len(ob.data.polygons)
        if ob.type == 'MESH':
            if isl_re and isl_re.search(ob.name):
                d['islands'] = islands(ob)
            if vrt_re and vrt_re.search(ob.name):
                d['verts_world'] = verts(ob)
        elif ob.type == 'CAMERA':
            d['lens'] = ob.data.lens
            d['sensor_width'] = ob.data.sensor_width
        elif ob.type == 'LIGHT':
            d['light'] = {'type': ob.data.type, 'energy': ob.data.energy, 'color': list(ob.data.color)}
        elif ob.type == 'EMPTY':
            d['empty_display'] = ob.empty_display_type
        objs[ob.name] = d
    except Exception:
        errors.append(f'{ob.name}: ' + traceback.format_exc()[-300:])
out['objects'] = objs

# v0.2: instanced geometry (collection instances, particle/geometry-nodes instances) is invisible in scene.objects
try:
    inst = []
    for oi in dg.object_instances:
        if not oi.is_instance:
            continue
        src = oi.object
        mw = oi.matrix_world.copy()
        pts = [mw @ Vector(c) for c in src.bound_box]
        inst.append({'instancer': oi.parent.name if oi.parent else None, 'object': src.name, 'type': src.type,
                     'location': [round(x, 5) for x in mw.translation], 'bbox_world': _box(pts)})
        if len(inst) >= 5000:
            errors.append('instances capped at 5000')
            break
    out['instances'] = inst
except Exception:
    errors.append('instances: ' + traceback.format_exc()[-300:])

try:
    mats = {}
    for m in bpy.data.materials:
        col = None
        try:
            linked = False
            if m.use_nodes:
                for n in m.node_tree.nodes:
                    if n.type == 'BSDF_PRINCIPLED':
                        col = [round(x, 4) for x in n.inputs['Base Color'].default_value]
                        linked = n.inputs['Base Color'].is_linked  # v0.2: texture/node-driven colour -> default is not the look
                        break
            if col is None:
                col = [round(x, 4) for x in m.diffuse_color]
        except Exception:
            pass
        mats[m.name] = {'base_color': col, 'base_color_linked': linked, 'users': m.users}
    out['materials'] = mats
except Exception:
    errors.append(traceback.format_exc()[-400:])

frames = cfg.get('frames') or []
if frames:
    are = re.compile(cfg['anim_regex']) if cfg.get('anim_regex') else None

    def is_anim(ob):
        p = ob
        while p is not None:
            if p.animation_data or p.constraints:
                return True
            p = p.parent
        return False
    sel = [ob for ob in scene.objects if (are.search(ob.name) if are else is_anim(ob))]
    anim = {}
    cur = scene.frame_current
    for f in frames:
        try:
            scene.frame_set(int(f))
            anim[str(f)] = {ob.name: mat(ob.matrix_world) for ob in sel}
        except Exception:
            errors.append(f'frame {f}: ' + traceback.format_exc()[-300:])
    scene.frame_set(cur)
    out['anim'] = anim
    out['anim_objects'] = [ob.name for ob in sel]

EXTRA = {}
if cfg.get('extra_py'):
    try:
        exec(cfg['extra_py'], {'bpy': bpy, 'EXTRA': EXTRA, 'scene': scene, 'dg': bpy.context.evaluated_depsgraph_get(),
                               'Vector': Vector, 'math': math})
    except Exception:
        errors.append('extra_py: ' + traceback.format_exc()[-800:])
out['extra'] = EXTRA
out['errors'] = errors[:200]
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f)
print('BLD_EXTRACT_OK', OUT, len(objs))
