# -*- coding: utf-8 -*-
"""CDC-C-X06 grader-side Blender export (run as: blender -b scene.blend --python x06_blend_dump.py -- MODE OUT ARGS_JSON).
MODE dump   : per-frame export used by checks.py (B06, M02, M05-M08, G01-G08 engineering clauses).
MODE render : low-sample re-render of given film frames (M04, M09) with a given roll_T34_frames value.
Film frame i == scene frame (frame_start + i). Shot k is always measured through camera CAM_Sk.
Never raises on scene content problems: everything is caught and reported in the JSON ('errors')."""
import bpy, json, math, sys, time, traceback
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from bpy_extras.object_utils import world_to_camera_view

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
MODE, OUT = argv[0], argv[1]
ARGS = json.loads(argv[2]) if len(argv) > 2 else {}
T0 = time.time()
ERR = []

SHOTS = {'S1': (0, 149), 'S2': (150, 269), 'S3': (270, 449), 'S4': (450, 539), 'S5': (540, 659), 'S6': (660, 899)}
FINGER_KW = ('finger', 'thumb', 'index', 'middle', 'ring', 'pinky', 'little', 'f_index', 'f_middle', 'f_ring', 'f_pinky')
FAMILIES = ['CHAINRING', 'CRANK', 'REAR_COG', 'REAR_WHEEL', 'FRONT_WHEEL', 'BIKE', 'QUICK_LINK', 'COURIER', 'MECHANIC',
            'WATCH', 'HELMET', 'WINDOW', 'COURIER_RIG', 'MECHANIC_RIG', 'OLD_CHAIN', 'PARTS_TRAY', 'REPAIR_STAND']


def err(tag):
    ERR.append(tag + ': ' + traceback.format_exc()[-400:])


def fam(name, base):
    return name == base or name.startswith(base + '.')


def pick_scene():
    for s in bpy.data.scenes:
        if 'CAM_S1' in s.objects and 'CHAIN' in s.objects:
            return s
    for s in bpy.data.scenes:
        if 'CAM_S1' in s.objects:
            return s
    return bpy.context.scene


sc = pick_scene()
try:
    bpy.context.window_manager  # noqa
    if bpy.context.window is not None:
        bpy.context.window.scene = sc
except Exception:
    pass
FS = sc.frame_start
US = sc.unit_settings.scale_length or 1.0
HAS_ROLL = 'roll_T34_frames' in sc.keys()


def set_roll(v):
    if HAS_ROLL:
        try:
            cur = sc['roll_T34_frames']
            sc['roll_T34_frames'] = type(cur)(v) if isinstance(cur, (int, float)) else v
        except Exception:
            sc['roll_T34_frames'] = v


def dg():
    return bpy.context.evaluated_depsgraph_get() if bpy.context.scene == sc else sc.view_layers[0].depsgraph


def goto(f):
    sc.frame_set(FS + int(f))
    d = dg()
    try:
        d.update()
    except Exception:
        pass
    return d


def m2l(m):
    return [round(float(m[i][j]), 6) for i in range(4) for j in range(4)]


def v2l(v, n=6):
    return [round(float(x), n) for x in v]


def side_of(name, x_local):
    n = name.lower().replace('-', '.').replace('_', '.').replace(' ', '.')
    if n.endswith('.l') or '.l.' in n or 'left' in n:
        return 'L'
    if n.endswith('.r') or '.r.' in n or 'right' in n:
        return 'R'
    return 'L' if x_local > 0 else 'R'


def is_finger(name):
    n = name.lower()
    return any(k in n for k in FINGER_KW) and 'palm' not in n and 'metacarp' not in n


def rig_info(rig):
    """finger chains / wrist / head / eye / hips bones of an armature object."""
    B = rig.data.bones
    fing = [b for b in B if is_finger(b.name) and b.use_deform]
    if len(fing) < 8:
        fing = [b for b in B if is_finger(b.name) and not b.name.lower().startswith(('mch', 'org', 'ik', 'vis'))]
    fset = {b.name for b in fing}
    chains = []
    for b in fing:
        if b.parent is None or b.parent.name not in fset:
            ch = [b.name]
            cur = b
            while True:
                kids = [c for c in cur.children if c.name in fset]
                if not kids:
                    break
                cur = max(kids, key=lambda c: len(c.children_recursive))
                ch.append(cur.name)
            chains.append({'bones': ch, 'side': side_of(b.name, b.head_local.x), 'root_parent': b.parent.name if b.parent else None})
    # wrist per side: first ancestor of chain roots that is not a finger/palm bone
    wrist = {}
    for c in chains:
        p = B[c['bones'][0]].parent
        while p is not None and ('palm' in p.name.lower() or is_finger(p.name)):
            p = p.parent
        if p is not None:
            wrist.setdefault(c['side'], []).append(p.name)
    wrist = {s: max(set(v), key=v.count) for s, v in wrist.items()}
    for b in B:  # rigs without fingers: hand/wrist bones by name
        n = b.name.lower()
        if ('hand' in n or 'wrist' in n) and not is_finger(b.name) and 'ik' not in n and not n.startswith(('mch', 'org')):
            wrist.setdefault(side_of(b.name, b.head_local.x), b.name)

    def pick(pred, prefer_deform=True):
        c = [b for b in B if pred(b.name.lower())]
        d = [b for b in c if b.use_deform]
        return (d or c)

    heads = pick(lambda n: (n == 'head' or n.endswith('head') or n.endswith('head.x') or n.startswith('head')) and 'top' not in n and 'end' not in n)
    eyes = pick(lambda n: 'eye' in n and 'lid' not in n and 'brow' not in n and 'lash' not in n)
    hips = pick(lambda n: any(k in n for k in ('hips', 'pelvis', 'torso', 'root', 'cog')))
    roots = [b for b in B if b.parent is None]
    return {'chains': chains, 'wrist': wrist, 'head': heads[0].name if heads else None,
            'eyes': [b.name for b in eyes[:2]], 'hips': (hips[0].name if hips else (roots[0].name if roots else None)),
            'n_bones': len(B)}


def bone_local_angle(rig, pb):
    """rotation angle (deg) of the evaluated pose bone relative to its rest pose, in parent space."""
    b = pb.bone
    if pb.parent is not None:
        loc = pb.parent.matrix.inverted() @ pb.matrix
        rest = b.parent.matrix_local.inverted() @ b.matrix_local
    else:
        loc, rest = pb.matrix, b.matrix_local
    q = (rest.inverted() @ loc).to_quaternion()
    return math.degrees(q.angle if q.angle <= math.pi else 2 * math.pi - q.angle), q


# ---------------- chain links ----------------
def chain_links(d):
    """returns (source, {key: (matrix_world, mesh_key)}) for the largest of the three link sources."""
    srcs = {}
    inst = {}
    try:
        for i in d.object_instances:
            if not i.is_instance or i.parent is None:
                continue
            if fam(i.parent.original.name, 'CHAIN') or (i.parent.original.parent and fam(i.parent.original.parent.name, 'CHAIN')):
                ob = i.object
                if ob.original is not None and fam(ob.original.name, 'QUICK_LINK'):
                    continue
                key = 'i' + '.'.join(str(x) for x in i.persistent_id if x != 0x7fffffff)
                inst[key] = (i.matrix_world.copy(), ob)
    except Exception:
        err('instances')
    srcs['instances'] = inst
    desc = {}
    for o in sc.objects:
        if fam(o.name, 'CHAIN') and o.type in ('MESH', 'EMPTY', 'CURVE'):
            for c in o.children_recursive:
                if c.type == 'MESH' and not fam(c.name, 'QUICK_LINK'):
                    oe = c.evaluated_get(d)
                    desc['o' + c.name] = (oe.matrix_world.copy(), oe)
    srcs['descendants'] = desc
    coll = {}
    for cn, cobj in bpy.data.collections.items():
        if fam(cn, 'CHAIN'):
            for c in cobj.all_objects:
                if c.type == 'MESH' and not fam(c.name, 'QUICK_LINK') and not fam(c.name, 'CHAIN') and c.name in sc.objects:
                    oe = c.evaluated_get(d)
                    coll['o' + c.name] = (oe.matrix_world.copy(), oe)
    srcs['collection'] = coll
    best = max(srcs, key=lambda k: len(srcs[k]))
    return best, srcs[best], {k: len(v) for k, v in srcs.items()}


MESH_BVH = {}


def bvh_of_mesh_obj(ob):
    """BVH in object-local coords for an evaluated mesh object (cached by data pointer)."""
    try:
        me = ob.data
        if me is None or not hasattr(me, 'vertices'):
            return None
        k = me.as_pointer()
        if k not in MESH_BVH:
            vs = [v.co.copy() for v in me.vertices]
            ps = [tuple(p.vertices) for p in me.polygons]
            MESH_BVH[k] = BVHTree.FromPolygons(vs, ps) if ps else None
        return MESH_BVH[k]
    except Exception:
        return None


def world_bvh(ob, d):
    """BVH in world coords of an evaluated object's mesh."""
    try:
        oe = ob.evaluated_get(d)
        me = oe.to_mesh()
        mw = oe.matrix_world
        vs = [mw @ v.co for v in me.vertices]
        ps = [tuple(p.vertices) for p in me.polygons]
        oe.to_mesh_clear()
        return BVHTree.FromPolygons(vs, ps) if ps else None
    except Exception:
        return None


def signed_local(bvh, mw, p):
    """(distance, inside) of world point p to a local-space BVH placed at mw."""
    inv = mw.inverted()
    lp = inv @ p
    r = bvh.find_nearest(lp)
    if r[0] is None:
        return 1e9, False
    loc, nor = r[0], r[1]
    dist = (mw @ loc - p).length
    return dist, (lp - loc).dot(nor) < 0


def signed_world(bvh, p):
    r = bvh.find_nearest(p)
    if r[0] is None:
        return 1e9, False
    return (r[0] - p).length, (p - r[0]).dot(r[1]) < 0


def proj(cam, co):
    v = world_to_camera_view(sc, cam, co)
    return [round(v.x, 5), round(v.y, 5), round(v.z, 4)]


def bbox_world(oe):
    return [oe.matrix_world @ Vector(c) for c in oe.bound_box]


def main_dump():
    out = {'mode': 'dump', 'version': bpy.app.version_string, 'file_version': list(bpy.data.version),
           'scene': sc.name, 'frame_start': FS, 'frame_end': sc.frame_end, 'fps': sc.render.fps / (sc.render.fps_base or 1),
           'unit_scale': US, 'res': [sc.render.resolution_x, sc.render.resolution_y], 'engine': sc.render.engine,
           'has_roll': HAS_ROLL, 'scenes': [s.name for s in bpy.data.scenes], 'objects': {}, 'frames': {}}
    set_roll(0)
    for o in bpy.data.objects:
        e = {'type': o.type, 'parent': o.parent.name if o.parent else None, 'parent_bone': o.parent_bone or None,
             'in_scene': o.name in sc.objects, 'data': o.data.name if o.data else None,
             'mods': [[m.type, getattr(getattr(m, 'object', None), 'name', None)] for m in getattr(o, 'modifiers', [])],
             'cons': [[c.type, getattr(getattr(c, 'target', None), 'name', None), getattr(c, 'subtarget', '')] for c in o.constraints],
             'materials': [s.material.name for s in getattr(o, 'material_slots', []) if s.material]}
        if o.type == 'MESH':
            e['n_verts'] = len(o.data.vertices)
            e['vgroups'] = [g.name for g in o.vertex_groups][:400]
        if o.type == 'LIGHT':
            L = o.data
            e['light'] = {'type': L.type, 'energy': L.energy, 'soft': float(getattr(L, 'shadow_soft_size', 0) or 0),
                          'size': float(getattr(L, 'size', 0) or 0), 'angle': float(getattr(L, 'angle', 0) or 0)}
        out['objects'][o.name] = e
    # materials (G08 engineering clause)
    mats = {}
    for m in bpy.data.materials:
        if m.users == 0:
            continue
        info = {'use_nodes': bool(m.use_nodes), 'bsdf': [], 'tex_inputs': []}
        if m.use_nodes and m.node_tree:
            for n in m.node_tree.nodes:
                if n.type.startswith('BSDF') or n.type in ('PRINCIPLED_VOLUME', 'SUBSURFACE_SCATTERING'):
                    info['bsdf'].append(n.type)
                    for s in n.inputs:
                        if s.is_linked and s.name in ('Base Color', 'Roughness', 'Normal', 'Metallic', 'Color', 'Specular IOR Level', 'Coat Normal'):
                            info['tex_inputs'].append(s.name)
                if n.type == 'OUTPUT_MATERIAL' and n.inputs.get('Displacement') and n.inputs['Displacement'].is_linked:
                    info['tex_inputs'].append('Displacement')
        mats[m.name] = info
    out['materials'] = mats
    w = sc.world
    wi = {'present': w is not None, 'nodes': [], 'strength': None}
    if w and w.use_nodes and w.node_tree:
        wi['nodes'] = sorted({n.type for n in w.node_tree.nodes})
        for n in w.node_tree.nodes:
            if n.type == 'BACKGROUND':
                wi['strength'] = float(n.inputs['Strength'].default_value)
                wi['bg_linked'] = n.inputs['Color'].is_linked
    out['world'] = wi
    rinfo = {'engine': sc.render.engine}
    try:
        rinfo['cycles_samples'] = sc.cycles.samples
        rinfo['cycles_denoise'] = bool(sc.cycles.use_denoising)
    except Exception:
        pass
    try:
        rinfo['comp_denoise'] = bool(sc.use_nodes and sc.node_tree and any(n.type == 'DENOISE' for n in sc.node_tree.nodes))
    except Exception:
        pass
    out['render'] = rinfo
    # rigs
    rigs = {}
    for rn in ('MECHANIC_RIG', 'COURIER_RIG'):
        r = bpy.data.objects.get(rn)
        if r is not None and r.type == 'ARMATURE':
            try:
                rigs[rn] = rig_info(r)
            except Exception:
                err('rig ' + rn)
    out['rigs'] = rigs
    # finger vertex indices on MECHANIC meshes (for interpenetration)
    fingers_all = {b for c in rigs.get('MECHANIC_RIG', {}).get('chains', []) for b in c['bones']}
    finger_vidx = {}
    for o in sc.objects:
        if o.type == 'MESH' and any(m.type == 'ARMATURE' and m.object is not None and m.object.name == 'MECHANIC_RIG' for m in o.modifiers):
            gi = {g.index: g.name for g in o.vertex_groups}
            idx = []
            for v in o.data.vertices:
                best = max(v.groups, key=lambda g: g.weight, default=None)
                if best is not None and best.weight >= 0.5 and gi.get(best.group) in fingers_all:
                    idx.append(v.index)
            finger_vidx[o.name] = idx
    out['finger_vcount'] = {k: len(v) for k, v in finger_vidx.items()}
    # scene objects per family
    famobjs = {f: [o for o in sc.objects if fam(o.name, f)] for f in FAMILIES}
    cams = {k: sc.objects.get(f'CAM_S{k[1]}') for k in SHOTS}
    ev = ARGS.get('events', {})

    # ---------------- frame plan (priority groups; stop the low-priority ones when over budget) ----------------
    budget = float(ARGS.get('budget', 1200))
    hard = float(ARGS.get('hard', budget + 250))  # stop everything (JSON still written) before the caller's timeout
    dense = set()
    def add(a, b, step=1):
        for f in range(max(0, a), min(899, b) + 1, step):
            dense.add(f)
    add(540, 661)  # S5 + match cut
    add(655, 700)
    lj = ev.get('link_join_start', 300); lc = ev.get('link_click', 400); ch = ev.get('chain_hand_contact', 280)
    add(min(lj, lc) - 3, 449)
    add(ch - 12, ch + 20)
    add(270, 449, 3)
    add(145, 152)
    add(0, 149, 6); add(150, 269, 3); add(450, 539, 3); add(660, 899, 2)  # minimum coverage for every item
    for k in ('watch_check', 'courier_turn', 'pedal_start'):
        if k in ev:
            add(ev[k] - 8, ev[k] + 8)
    groups = [sorted(dense)]
    mid = set(range(150, 270)) | set(range(450, 540)) | set(range(660, 900, 2)) | set(range(0, 150, 3))
    groups.append(sorted(mid - dense))
    rest = set(range(660, 900)) | set(range(270, 450))
    groups.append(sorted(rest - dense - mid))
    S3_CONTACT = set(range(270, 450, 3)) | set(range(min(lj, lc) - 3, 450)) | set(range(ch - 12, ch + 21))
    PEN = set(range(270, 450, 3))
    S1_VIS = set(range(0, 150, 3))
    truncated = []
    fdat = out['frames']
    finger_tips = {}
    mr = bpy.data.objects.get('MECHANIC_RIG')
    if mr is not None and 'MECHANIC_RIG' in rigs:
        for c in rigs['MECHANIC_RIG']['chains']:
            finger_tips[c['bones'][-1]] = c['side']
    track_bones = {}
    for rn, ri in rigs.items():
        names = set()
        for c in ri['chains']:
            names.update(c['bones'])
        names.update(ri['wrist'].values())
        for k in ('head', 'hips'):
            if ri.get(k): names.add(ri[k])
        names.update(ri.get('eyes', []))
        track_bones[rn] = sorted(names)
    courier_fam = {o.name for o in sc.objects if fam(o.name, 'COURIER') or fam(o.name, 'HELMET') or fam(o.name, 'WATCH')}
    r = bpy.data.objects.get('COURIER_RIG')
    if r is not None:
        courier_fam |= {c.name for c in r.children_recursive}
    window_fam = {o.name for o in sc.objects if fam(o.name, 'WINDOW')}
    ql_parts = []
    for o in famobjs['QUICK_LINK']:
        ql_parts.append(o)
        ql_parts += [c for c in o.children_recursive]
    ql_parts = list({o.name: o for o in ql_parts}.values())

    for gidx, frames in enumerate(groups):
        for f in frames:
            if (time.time() - T0 > budget and gidx > 0) or time.time() - T0 > hard:
                truncated.append(f)
                continue
            try:
                d = goto(f)
                F = {}
                shot = next(k for k, (a, b) in SHOTS.items() if a <= f <= b)
                F['shot'] = shot
                objs = {}
                for fa, lst in famobjs.items():
                    for o in lst:
                        oe = o.evaluated_get(d)
                        e = {'m': m2l(oe.matrix_world)}
                        if fa in ('COURIER', 'WATCH', 'WINDOW', 'CHAINRING', 'MECHANIC', 'HELMET') and o.type in ('MESH', 'CURVE', 'FONT'):
                            bb = bbox_world(oe)
                            e['bb'] = [v2l([min(v[i] for v in bb) for i in range(3)], 4), v2l([max(v[i] for v in bb) for i in range(3)], 4)]
                        if fa in ('CHAINRING', 'REAR_COG', 'REAR_WHEEL', 'FRONT_WHEEL'):
                            lb = [Vector(v) for v in oe.bound_box]
                            ext = [max(v[i] for v in lb) - min(v[i] for v in lb) for i in range(3)]
                            ax = min(range(3), key=lambda i: ext[i])
                            e['ax'] = v2l(oe.matrix_world.to_3x3().col[ax].normalized(), 5)
                            e['c'] = v2l(oe.matrix_world @ (sum(lb, Vector()) / 8), 5)
                        objs[o.name] = e
                F['obj'] = objs
                cams_f = {}
                for k, cam in cams.items():
                    a, b = SHOTS[k]
                    if cam is None or not (a - 2 <= f <= b + 2):
                        continue
                    ce = cam.evaluated_get(d)
                    cd = ce.data
                    c = {'m': m2l(ce.matrix_world)}
                    if cam.type == 'CAMERA':
                        dof = cd.dof
                        fd = dof.focus_distance
                        if dof.focus_object is not None:
                            fd = (dof.focus_object.evaluated_get(d).matrix_world.translation - ce.matrix_world.translation).length
                        c.update(lens=cd.lens, sensor=cd.sensor_width, ctype=cd.type, dof=bool(dof.use_dof), fstop=dof.aperture_fstop, focus=fd)
                        pts = {}
                        for o in famobjs['CHAINRING'] + famobjs['WATCH'] + famobjs['COURIER']:
                            pts[o.name] = proj(ce, o.evaluated_get(d).matrix_world.translation)
                        c['proj'] = pts
                        bbp = {}
                        for o in famobjs['COURIER'] + famobjs['WINDOW']:
                            if o.name in objs and 'bb' in objs[o.name]:
                                lo, hi = objs[o.name]['bb']
                                cs = [Vector((x, y, z)) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
                                bbp[o.name] = [proj(ce, v) for v in cs]
                        c['bbproj'] = bbp
                        if k in ('S5', 'S6') and 655 <= f <= 665:
                            rim = {}
                            for o in famobjs['CHAINRING']:
                                oe = o.evaluated_get(d)
                                lb = [Vector(v) for v in oe.bound_box]
                                ext = [max(v[i] for v in lb) - min(v[i] for v in lb) for i in range(3)]
                                ax = min(range(3), key=lambda i: ext[i])  # thin axis = axle (local)
                                r_loc = max(ext) / 2
                                cen = sum(lb, Vector()) / 8
                                u = [i for i in range(3) if i != ax]
                                ptsr = []
                                for j in range(16):
                                    t = 2 * math.pi * j / 16
                                    lp = cen.copy(); lp[u[0]] += r_loc * math.cos(t); lp[u[1]] += r_loc * math.sin(t)
                                    ptsr.append(proj(ce, oe.matrix_world @ lp))
                                rim[o.name] = {'centre': proj(ce, oe.matrix_world @ cen), 'rim': ptsr}
                            c['rim'] = rim
                    cams_f[k] = c
                F['cam'] = cams_f
                bones = {}
                for rn, names in track_bones.items():
                    rig = bpy.data.objects[rn].evaluated_get(d)
                    mw = rig.matrix_world
                    bd = {}
                    for bn in names:
                        pb = rig.pose.bones.get(bn)
                        if pb is None:
                            continue
                        ang, q = bone_local_angle(rig, pb)
                        R = (mw @ pb.matrix).to_3x3()
                        bd[bn] = {'h': v2l(mw @ pb.head, 5), 't': v2l(mw @ pb.tail, 5), 'ang': round(ang, 3),
                                  'q': v2l(q, 5), 'x': v2l(R.col[0].normalized(), 4), 'y': v2l(R.col[1].normalized(), 4), 'z': v2l(R.col[2].normalized(), 4)}
                    bones[rn] = bd
                F['bones'] = bones
                need_links = 270 <= f <= 449 or 540 <= f <= 661 or f % 30 == 0
                if need_links:
                    src, links, counts = chain_links(d)
                    F['link_src'] = src
                    F['link_counts'] = counts
                    F['links'] = {k: v2l(m.translation, 5) for k, (m, ob) in links.items()}
                    if f in S3_CONTACT or (f % 30 == 0):
                        # fingertip distances to chain / quick link (G01, G02)
                        lk = list(links.items())
                        lpos = [m.translation for k, (m, ob) in lk]
                        qbvh = [(o.name, world_bvh(o, d)) for o in famobjs['QUICK_LINK'] if o.type == 'MESH']
                        qpos = [o.evaluated_get(d).matrix_world.translation for o in famobjs['QUICK_LINK']]
                        tips = {}
                        rig = bpy.data.objects['MECHANIC_RIG'].evaluated_get(d) if mr is not None else None
                        for bn, sd in finger_tips.items():
                            pb = rig.pose.bones.get(bn) if rig else None
                            if pb is None:
                                continue
                            p = rig.matrix_world @ pb.tail
                            dq = min([signed_world(b, p)[0] for n, b in qbvh if b] or [1e9])
                            order = sorted(range(len(lpos)), key=lambda i: (lpos[i] - p).length)[:3]
                            dl = 1e9
                            for i in order:
                                m, ob = lk[i][1]
                                bv = bvh_of_mesh_obj(ob)
                                dl = min(dl, signed_local(bv, m, p)[0] if bv else (lpos[i] - p).length)
                            # links adjacent to the quick link
                            dadj = 1e9
                            if qpos:
                                adj = sorted(range(len(lpos)), key=lambda i: min((lpos[i] - q).length for q in qpos))[:2]
                                for i in adj:
                                    m, ob = lk[i][1]
                                    bv = bvh_of_mesh_obj(ob)
                                    dadj = min(dadj, signed_local(bv, m, p)[0] if bv else (lpos[i] - p).length)
                            tips[bn] = {'side': sd, 'p': v2l(p, 5), 'd_ql': round(dq, 5), 'd_chain': round(dl, 5), 'd_adj': round(dadj, 5)}
                        F['tips'] = tips
                        F['ql'] = {o.name: m2l(o.evaluated_get(d).matrix_world) for o in ql_parts}
                    if f in PEN and finger_vidx and mr is not None:
                        # interpenetration depth: finger modelled as capsules around the finger bones (radius = median
                        # distance of the finger-weighted vertices to their bone); depth = radius - distance of
                        # link / REAR_COG / CHAINRING vertices to the bone segment
                        rig = bpy.data.objects['MECHANIC_RIG'].evaluated_get(d)
                        segs = {}
                        for bn in fingers_all:
                            pb = rig.pose.bones.get(bn)
                            if pb is not None:
                                segs[bn] = (rig.matrix_world @ pb.head, rig.matrix_world @ pb.tail)

                        def sdist(p, a, b):
                            ab = b - a
                            t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.dot(ab), 1e-12)))
                            return (a + ab * t - p).length
                        rad = {}
                        for on, idx in finger_vidx.items():
                            oe = bpy.data.objects[on].evaluated_get(d)
                            me = oe.to_mesh()
                            if len(me.vertices) == len(bpy.data.objects[on].data.vertices):
                                gi = {g.index: g.name for g in bpy.data.objects[on].vertex_groups}
                                mw = oe.matrix_world
                                for vi in idx:
                                    v = bpy.data.objects[on].data.vertices[vi]
                                    bn = gi.get(max(v.groups, key=lambda g: g.weight).group)
                                    if bn in segs:
                                        rad.setdefault(bn, []).append(sdist(mw @ me.vertices[vi].co, *segs[bn]))
                            oe.to_mesh_clear()
                        rad = {k: sorted(v)[len(v) // 2] for k, v in rad.items() if v}
                        pts = []
                        lk = list(links.items())
                        cen = [(a + b) / 2 for a, b in segs.values()]
                        for k, (m, ob) in lk:
                            if cen and min((m.translation - c).length for c in cen) < 0.06:
                                pts.append(m.translation.copy())
                                try:
                                    pts += [m @ v.co for v in ob.data.vertices]
                                except Exception:
                                    pass
                        for o in famobjs['REAR_COG'] + famobjs['CHAINRING']:
                            if o.type != 'MESH':
                                continue
                            oe = o.evaluated_get(d)
                            me = oe.to_mesh(); mw = oe.matrix_world
                            for v in me.vertices:
                                p = mw @ v.co
                                if cen and min((p - c).length for c in cen) < 0.06:
                                    pts.append(p)
                            oe.to_mesh_clear()
                        pen = 0.0
                        for bn, (a, b) in segs.items():
                            r0 = rad.get(bn)
                            if not r0:
                                continue
                            for p in pts:
                                pen = max(pen, r0 - sdist(p, a, b))
                        F['pen'] = round(pen, 5)
                        F['pen_n'] = [len(rad), len(pts)]
                if f in S1_VIS and cams.get('S1') is not None and famobjs['COURIER']:
                    cam = cams['S1'].evaluated_get(d)
                    o0 = cam.matrix_world.translation
                    vis_in = False; vis_any = False
                    win_bbs = [objs[n]['bb'] for n in window_fam if n in objs and 'bb' in objs[n]]
                    wproj = []
                    for lo, hi in win_bbs:
                        cs = [Vector((x, y, z)) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
                        pp = [proj(cam, v) for v in cs]
                        wproj.append((min(p[0] for p in pp), max(p[0] for p in pp), min(p[1] for p in pp), max(p[1] for p in pp)))
                    for o in famobjs['COURIER']:
                        if o.name not in objs or 'bb' not in objs[o.name]:
                            continue
                        lo, hi = objs[o.name]['bb']
                        cen = Vector([(lo[i] + hi[i]) / 2 for i in range(3)])
                        hs = Vector([(hi[i] - lo[i]) / 4 for i in range(3)])
                        samples = [cen] + [cen + Vector((sx * hs.x, sy * hs.y, sz * hs.z)) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
                        for p in samples:
                            pp = proj(cam, p)
                            if pp[2] <= 0 or not (0 <= pp[0] <= 1 and 0 <= pp[1] <= 1):
                                continue
                            dvec = (p - o0); dist = dvec.length; dvec.normalize()
                            org = o0.copy(); ok = False
                            for _ in range(12):
                                hit, loc, nor, ii, hob, hm = sc.ray_cast(d, org, dvec, distance=dist - (org - o0).length + 0.05)
                                if not hit:
                                    break
                                hn = hob.original.name if hob.original else hob.name
                                if hn in courier_fam or fam(hn, 'COURIER'):
                                    ok = True; break
                                if hn in window_fam:
                                    org = loc + dvec * 0.002; continue
                                break
                            if ok:
                                vis_any = True
                                if any(a <= pp[0] <= b and c <= pp[1] <= e for a, b, c, e in wproj):
                                    vis_in = True
                    F['s1_vis'] = [vis_any, vis_in]
                fdat[str(f)] = F
            except Exception:
                err(f'frame {f}')
                if len(ERR) > 40:
                    break
    out['truncated'] = truncated[:50]
    out['n_truncated'] = len(truncated)
    out['elapsed'] = round(time.time() - T0, 1)
    out['errors'] = ERR[:40]
    return out


def main_render():
    """MODE render: ARGS = {'jobs': [{'roll': int, 'frames': [[film_frame, 'CAM_Sk'], ...]}, ...], 'dir': path,
    'w': 640, 'h': 360, 'engine': 'CYCLES'|'SCENE', 'samples': 16}"""
    import os
    out = {'mode': 'render', 'files': {}, 'errors': ERR, 'engine_scene': sc.render.engine}
    r = sc.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = ARGS.get('w', 640), ARGS.get('h', 360), 100
    r.image_settings.file_format = 'PNG'
    r.image_settings.color_mode = 'RGB'
    r.use_sequencer = False
    if ARGS.get('engine', 'CYCLES') == 'CYCLES':
        r.engine = 'CYCLES'
        try:
            sc.cycles.device = 'CPU'
            sc.cycles.samples = max(1, min(int(sc.cycles.samples or 16), int(ARGS.get('samples', 16))))
            sc.cycles.use_adaptive_sampling = True
            sc.cycles.use_denoising = True
            sc.cycles.max_bounces = min(sc.cycles.max_bounces, 6)
        except Exception:
            err('cycles setup')
    out['engine_used'] = r.engine
    for m in sc.timeline_markers:
        m.camera = None
    for job in ARGS['jobs']:
        set_roll(job.get('roll', 0))
        for f, cn in job['frames']:
            try:
                cam = sc.objects.get(cn)
                if cam is None:
                    ERR.append(f'{cn} missing'); continue
                sc.camera = cam
                sc.frame_set(FS + int(f))
                p = os.path.join(ARGS['dir'], f'rr_{job.get("roll", 0)}_{int(f):04d}.png')
                r.filepath = p
                bpy.ops.render.render(write_still=True, scene=sc.name)
                if os.path.exists(p):
                    out['files'][f'{job.get("roll", 0)}:{int(f)}'] = p
            except Exception:
                err(f'render {f}')
    out['elapsed'] = round(time.time() - T0, 1)
    return out


try:
    res = main_dump() if MODE == 'dump' else main_render()
except Exception:
    res = {'fatal': traceback.format_exc()[-1500:], 'errors': ERR}
with open(OUT, 'w') as fh:
    json.dump(res, fh)
print('X06DUMP_DONE', OUT)
