# -*- coding: utf-8 -*-
"""BLD 并行施工题 checks.py 共用工具（纯 Python，不依赖 bpy）。

用法（在 checks.run(ctx) 中）：
    from _bld_lib import Scene, ok, bad, png_size, load_manifest
    S = Scene.load(ctx, frames=[1, 120], islands_regex=r'_gear_', extra_py=None)
    if S.err: ...            # blender 不可用或 .blend 打不开：S.data 为 None
    S.coll('DN01')           # 集合内全部对象名（递归）
    S.objs_in('DN01', r'^DN01_col_\\d{3}$')   # 名称正则过滤
    S.bbox(names)            # 多对象世界包围盒并集 [[minx,miny,minz],[maxx,maxy,maxz]]
    S.at(frame, name)        # 某帧世界矩阵（需在 frames 中采样）
"""
import json, os, re, shutil, subprocess, pathlib, math

HERE = pathlib.Path(__file__).resolve().parent


def ok(detail=''):
    return {'verdict': 'pass', 'detail': str(detail)[:600]}


def bad(detail=''):
    return {'verdict': 'fail', 'detail': str(detail)[:600]}


def close(a, b, rel=0.03, abs_=0.1):
    """尺寸通用容差：±rel 或 ±abs_ 取大者。"""
    try:
        return abs(float(a) - float(b)) <= max(abs_, rel * abs(float(b)))
    except Exception:
        return False


def png_size(p):
    try:
        with open(p, 'rb') as f:
            h = f.read(24)
        if h[:8] != b'\x89PNG\r\n\x1a\n':
            return None
        return int.from_bytes(h[16:20], 'big'), int.from_bytes(h[20:24], 'big')
    except Exception:
        return None


def load_manifest(out):
    p = pathlib.Path(out) / 'manifest.json'
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return None


class Scene:
    def __init__(self, data, err=None):
        self.data, self.err = data, err
        self._all = {}
        if data:
            cols = data.get('collections', {})
            for k, v in cols.items():
                self._all[k] = v.get('all_objects', [])

    @classmethod
    def load(cls, ctx, frames=None, anim_regex=None, islands_regex=None, verts_regex=None, extra_py=None, timeout=1500):
        out = pathlib.Path(ctx['out'])
        blend = out / 'scene.blend'
        fake = os.environ.get('BLD_EXTRACT_JSON')  # 本地冒烟测试：直接读预制的导出 JSON
        if fake and os.path.exists(fake):
            return cls(json.loads(open(fake, encoding='utf-8').read()))
        cache = pathlib.Path(ctx['tmp']) / 'bld_extract.json'
        if cache.exists():
            try:
                return cls(json.loads(cache.read_text(encoding='utf-8')))
            except Exception:
                pass
        if not blend.exists():
            return cls(None, 'scene.blend missing')
        exe = shutil.which('blender') or os.environ.get('BLENDER_BIN')
        if not exe:
            return cls(None, 'blender not available')
        cfgp = pathlib.Path(ctx['tmp']) / 'bld_cfg.json'
        cfgp.write_text(json.dumps({'frames': frames or [], 'anim_regex': anim_regex, 'islands_regex': islands_regex,
                                    'verts_regex': verts_regex, 'extra_py': extra_py}), encoding='utf-8')
        script = pathlib.Path(ctx['tests']) / '_bld_extract.py'
        try:
            p = subprocess.run([exe, '-b', '--factory-startup', str(blend), '--python', str(script), '--', str(cache), str(cfgp)],
                               capture_output=True, text=True, timeout=timeout)
        except Exception as e:
            return cls(None, f'blender run failed: {e}')
        if not cache.exists():
            return cls(None, 'extract failed: ' + (p.stdout[-600:] + p.stderr[-600:]))
        return cls(json.loads(cache.read_text(encoding='utf-8')))

    # --- 查询 ---
    @property
    def objects(self):
        return self.data.get('objects', {}) if self.data else {}

    def has_coll(self, name):
        return name in self._all

    def coll(self, name):
        return list(self._all.get(name, []))

    def objs_in(self, cname, regex=None):
        r = re.compile(regex) if regex else None
        return [n for n in self.coll(cname) if (r.search(n) if r else True)]

    def count(self, cname, regex):
        return len(self.objs_in(cname, regex))

    def ob(self, name):
        return self.objects.get(name)

    def bbox(self, names):
        bs = [self.objects[n]['bbox_world'] for n in names if n in self.objects and self.objects[n].get('bbox_world')
              and self.objects[n].get('type') in ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT')]
        if not bs:
            return None
        return [[min(b[0][i] for b in bs) for i in range(3)], [max(b[1][i] for b in bs) for i in range(3)]]

    def coll_bbox(self, cname, regex=None):
        return self.bbox(self.objs_in(cname, regex))

    @staticmethod
    def center(bb):
        return [(bb[0][i] + bb[1][i]) / 2 for i in range(3)] if bb else None

    @staticmethod
    def size(bb):
        return [bb[1][i] - bb[0][i] for i in range(3)] if bb else None

    def at(self, frame, name):
        a = (self.data or {}).get('anim', {}).get(str(frame), {})
        return a.get(name)

    @staticmethod
    def loc(m):
        return [m[0][3], m[1][3], m[2][3]] if m else None

    @staticmethod
    def axis(m, i):
        """世界矩阵第 i 列（局部轴在世界中的方向，未归一化）。"""
        return [m[0][i], m[1][i], m[2][i]] if m else None

    @staticmethod
    def angle_z(m):
        """绕 Z 的朝向角（度），由局部 X 轴投影计算。"""
        return math.degrees(math.atan2(m[1][0], m[0][0])) if m else None

    def material_colors(self, name):
        mats = (self.data or {}).get('materials', {})
        return [mats.get(m, {}).get('base_color') for m in self.objects.get(name, {}).get('materials', [])]


def gate_group(results, items, failing_ids, group_pred, reason):
    """组级门槛：failing_ids 中任一 fail 时，把 group_pred(item) 为真的判定全部置 fail。"""
    if any(results.get(i, {}).get('verdict') == 'fail' for i in failing_ids):
        for it in items:
            if group_pred(it) and it['id'] not in failing_ids:
                results[it['id']] = {'verdict': 'fail', 'detail': reason, 'source': 'gate'}
    return results
