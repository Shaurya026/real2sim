"""Independent, read-only checks of exported interactive geometry and motion.

Run after export_completed.py. Writes only interactive_asset_validation.json;
never rebuilds the scene. This checks asset consistency, not Isaac compatibility
or a continuous-time collision guarantee.
"""
from room2sim_paths import project_path, input_path, browser_path, openmvs_path, ffmpeg_path
from pathlib import Path
import hashlib
import io
import json
import struct
import traceback
import numpy as np
from PIL import Image

P = Path(__file__).resolve().parent
COMPONENTS = {5120: 'i1', 5121: 'u1', 5122: '<i2', 5123: '<u2', 5125: '<u4', 5126: '<f4'}
WIDTHS = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT2': 4, 'MAT3': 9, 'MAT4': 16}


class GLB:
    def __init__(self, path):
        self.raw = path.read_bytes()
        magic, version, size = struct.unpack_from('<4sII', self.raw)
        assert magic == b'glTF' and version == 2 and size == len(self.raw), 'GLB header invalid'
        chunks = []
        pos = 12
        while pos < size:
            length, kind = struct.unpack_from('<I4s', self.raw, pos)
            assert length % 4 == 0 and pos + 8 + length <= size, 'Invalid GLB chunk extent'
            chunks.append((kind, self.raw[pos+8:pos+8+length]))
            pos += length + 8
        assert pos == size and [c[0] for c in chunks] == [b'JSON', b'BIN\0']
        self.g = json.loads(chunks[0][1])
        self.binary = chunks[1][1]
        assert self.g['asset']['version'] == '2.0'
        assert len(self.g['buffers']) == 1 and 'uri' not in self.g['buffers'][0]
        size = self.g['buffers'][0]['byteLength']
        assert size <= len(self.binary) <= size + 3
        for v in self.g['bufferViews']:
            assert v['buffer'] == 0
            assert v.get('byteOffset', 0) >= 0 and v['byteLength'] > 0
            assert v.get('byteOffset', 0) + v['byteLength'] <= size
        self.arrays = [self.accessor(i) for i in range(len(self.g['accessors']))]

    def view(self, index):
        v = self.g['bufferViews'][index]
        start = v.get('byteOffset', 0)
        return self.binary[start:start+v['byteLength']]

    def accessor(self, index):
        a = self.g['accessors'][index]
        assert 'sparse' not in a, 'Sparse accessors not supported in this exporter'
        v = self.g['bufferViews'][a['bufferView']]
        dtype = np.dtype(COMPONENTS[a['componentType']])
        width = WIDTHS[a['type']]
        packed = width * dtype.itemsize
        stride = v.get('byteStride', packed)
        offset = a.get('byteOffset', 0)
        assert a['count'] > 0 and stride >= packed
        assert offset % dtype.itemsize == 0 and (v.get('byteOffset', 0) + offset) % dtype.itemsize == 0
        assert offset + (a['count']-1)*stride + packed <= v['byteLength'], 'Accessor exceeds bufferView'
        out = np.ndarray((a['count'], width), dtype=dtype, buffer=self.view(a['bufferView']), offset=offset, strides=(stride, dtype.itemsize)).copy()
        assert np.isfinite(out).all(), f'Nonfinite accessor {index}'
        for key, f in [('min', np.min), ('max', np.max)]:
            if key in a:
                assert np.allclose(f(out, axis=0), a[key], atol=1e-6), f'Accessor {index} {key} differs'
        return out[:, 0] if width == 1 else out


def motion_curve(times, duration, profile, key):
    """Evaluate the published piecewise profile independently of the exporter."""
    assert profile['easing'] == 'quintic_smootherstep'
    knots = np.asarray(profile[key], dtype=float)
    assert np.all(np.diff(knots[:, 0]) > 0)
    normalized = np.clip(np.asarray(times, dtype=float) / duration, knots[0, 0], knots[-1, 0])
    segments = np.clip(np.searchsorted(knots[:, 0], normalized, side='right') - 1, 0, len(knots)-2)
    low, high = knots[segments], knots[segments+1]
    local = (normalized-low[:, 0]) / (high[:, 0]-low[:, 0])
    eased = 10*local**3 - 15*local**4 + 6*local**5
    return low[:, 1] + eased * (high[:, 1]-low[:, 1])


def quaternion_error(a, b):
    return float(np.max(np.minimum(np.linalg.norm(a-b, axis=1), np.linalg.norm(a+b, axis=1))))


def validate():
    glb = GLB(P / 'room.glb')
    g = glb.g
    report = {'passed': False, 'asset': 'room.glb', 'sha256': hashlib.sha256(glb.raw).hexdigest(), 'bytes': len(glb.raw)}
    names = {n['name']: i for i, n in enumerate(g['nodes'])}
    assert len(names) == len(g['nodes']), 'Duplicate node names'
    scene = g['scenes'][g.get('scene', 0)]
    visited = set()
    def walk(i, chain):
        assert 0 <= i < len(g['nodes']) and i not in chain, 'Invalid node hierarchy'
        assert i not in visited, 'Node occurs twice in scene tree'
        visited.add(i)
        node = g['nodes'][i]
        for prop, width in [('translation', 3), ('scale', 3), ('rotation', 4), ('matrix', 16)]:
            if prop in node:
                assert len(node[prop]) == width and np.isfinite(node[prop]).all()
        if 'rotation' in node:
            assert abs(np.linalg.norm(node['rotation'])-1) < 1e-6
        for child in node.get('children', []):
            walk(child, chain + [i])
    for root in scene['nodes']:
        walk(root, [])
    assert len(visited) == len(g['nodes']), 'Unreachable node'
    assert np.allclose(g['nodes'][names['Room']]['rotation'], [-2**-.5, 0, 0, 2**-.5]), 'Unexpected Z-up to glTF-Y-up conversion'
    images = []
    for image in g['images']:
        assert image['mimeType'] in ('image/jpeg', 'image/png') and 'bufferView' in image
        raw = glb.view(image['bufferView'])
        with Image.open(io.BytesIO(raw)) as im:
            assert im.format == ('JPEG' if image['mimeType'] == 'image/jpeg' else 'PNG')
            dims = im.size
            im.verify()
        with Image.open(io.BytesIO(raw)) as im:
            im.load()
        images.append({'bytes': len(raw), 'dimensions': list(dims)})
    for texture in g['textures']:
        assert 0 <= texture['source'] < len(g['images'])
        if 'sampler' in texture:
            assert 0 <= texture['sampler'] < len(g['samplers'])
    for mat in g['materials']:
        pbr = mat.get('pbrMetallicRoughness', {})
        tex = pbr.get('baseColorTexture')
        if tex:
            assert 0 <= tex['index'] < len(g['textures'])
    count = 0
    min_area = float('inf')
    for node in g['nodes']:
        if 'mesh' not in node:
            continue
        assert 0 <= node['mesh'] < len(g['meshes'])
        for prim in g['meshes'][node['mesh']]['primitives']:
            assert prim.get('mode', 4) == 4
            xyz = glb.arrays[prim['attributes']['POSITION']]
            uv = glb.arrays[prim['attributes']['TEXCOORD_0']]
            assert xyz.shape[1] == 3 and uv.shape == (len(xyz), 2)
            assert 0 <= prim['material'] < len(g['materials'])
            indices = glb.arrays[prim['indices']] if 'indices' in prim else np.arange(len(xyz))
            assert indices.min() >= 0 and indices.max() < len(xyz) and len(indices) % 3 == 0
            tri = xyz[indices].astype(np.float64).reshape(-1, 3, 3)
            area = np.linalg.norm(np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]), axis=1)*.5
            assert (area > 0).all(), f'Degenerate mesh triangles: {node["name"]}'
            count += len(tri)
            min_area = min(min_area, float(area.min()))
    report.update(mesh_nodes=sum('mesh' in x for x in g['nodes']), triangles=count,
        minimum_triangle_area_m2=min_area, images=images,
        buffers_accessors_images_valid=True, all_mesh_triangles_finite_nondegenerate=True)
    # New objects must retain the source NPZ appearance and their prescribed pivot.
    chair_data = json.loads((P / 'chair_motion.json').read_text())
    carton_data = json.loads((P / 'cartons.json').read_text())
    replacement = chair_data['replacementGroups'] + carton_data['groups']
    geometry_errors = []
    for group in replacement:
        assert group['name'] in names, f'Missing node {group["name"]}'
        node = g['nodes'][names[group['name']]]
        pivot = np.asarray(group['pivot'])
        assert np.allclose(node.get('translation', [0, 0, 0]), pivot, atol=1e-7)
        prim = g['meshes'][node['mesh']]['primitives'][0]
        exported = glb.arrays[prim['attributes']['POSITION']] + np.asarray(node['translation'])
        exported_uv = glb.arrays[prim['attributes']['TEXCOORD_0']]
        source = np.load(P / group['geometry'])
        xyz = source['xyz'].reshape(-1, 3, 3)
        uv = source['uv'].reshape(-1, 3, 2)
        keep = np.linalg.norm(np.cross(xyz[:, 1]-xyz[:, 0], xyz[:, 2]-xyz[:, 0]), axis=1) > 1e-12
        xyz, uv = xyz[keep], uv[keep]
        # Final float32 rebasing can collapse preexisting near-zero-area slivers.
        local_source = xyz.astype('<f4') - np.asarray(pivot, dtype='<f4')
        surviving = np.linalg.norm(np.cross(local_source[:, 1]-local_source[:, 0], local_source[:, 2]-local_source[:, 0]), axis=1) > 1e-12
        expected = xyz[surviving].reshape(-1, 3)
        expected_uv = uv[surviving].reshape(-1, 2).copy()
        expected_uv[:, 1] = 1 - expected_uv[:, 1]
        assert exported.shape == expected.shape and exported_uv.shape == expected_uv.shape
        error = float(np.max(np.abs(exported-expected)))
        assert error < 5e-7 and np.allclose(exported_uv, expected_uv, atol=1e-7)
        geometry_errors.append(error)
    # 'blue_wall' is also the name of a legitimate static room plane.
    assert not any(name in names and g['nodes'][names[name]].get('extras', {}).get('kind') != 'fitted_plane' for name in chair_data['replaces']), 'Unsplit moving chair duplicated in GLB'
    report['source_geometry_max_error_m'] = max(geometry_errors)
    clips = {}
    clip_summary = []
    for clip in g.get('animations', []):
        channels = {}
        for channel in clip['channels']:
            s = clip['samplers'][channel['sampler']]
            assert s.get('interpolation', 'LINEAR') == 'LINEAR'
            t, value = glb.arrays[s['input']], glb.arrays[s['output']]
            assert t.ndim == 1 and np.all(np.diff(t) > 0) and t[0] == 0
            assert len(value) == len(t)
            target = channel['target']
            assert 0 <= target['node'] < len(g['nodes'])
            path = target['path']
            assert path in ('translation', 'rotation', 'scale')
            assert value.shape[1] == (4 if path == 'rotation' else 3)
            if path == 'rotation':
                assert np.max(np.abs(np.linalg.norm(value, axis=1)-1)) < 2e-6
            key = (g['nodes'][target['node']]['name'], path)
            assert key not in channels
            channels[key] = (t, value)
        assert clip['name'] not in clips
        clips[clip['name']] = channels
        clip_summary.append({'name': clip['name'], 'channels': len(channels), 'duration_s': float(max(t[-1] for t, v in channels.values()))})
    assert len(clips) == len(chair_data['actors']) + len(json.loads((P / 'carton_playbacks.json').read_text()))
    chair_errors = []
    for actor in chair_data['actors']:
        clip = clips['Roll and swivel ' + actor['label']]
        errors = []
        for role in ('base', 'seat', 'wheels'):
            for name in actor['groups'].get(role, []):
                times, translation = clip[(name, 'translation')]
                assert abs(times[-1]-actor['duration']) < 1e-6
                travel = motion_curve(times, actor['duration'], actor['profile'], 'travel')
                rest = np.asarray(g['nodes'][names[name]]['translation'])
                expected = rest + travel[:, None]*np.asarray(actor['offset'])
                err = float(np.max(np.abs(translation-expected)))
                assert err < 3e-6
                errors.append(err)
                if role == 'base':
                    continue
                rt, actual_q = clip[(name, 'rotation')]
                assert np.array_equal(rt, times)
                if role == 'seat':
                    angle = actor['seatYaw']*motion_curve(times, actor['duration'], actor['profile'], 'swivel')
                    axis = np.array([0, 0, 1])
                else:
                    wheel = next(x for x in actor['wheels'] if x['name'] == name)
                    axis = np.asarray(wheel['axis'])
                    assert abs(np.linalg.norm(axis)-1) < 1e-6
                    displacement = travel[:, None]*np.asarray(actor['offset'])
                    angle = (displacement @ np.cross(axis, [0, 0, 1]))/wheel['radius']
                expected_q = np.column_stack([np.sin(angle/2)[:, None]*axis, np.cos(angle/2)])
                err = quaternion_error(actual_q, expected_q)
                assert err < 3e-6
                errors.append(err)
        chair_errors.append({'id': actor['id'], 'maximum_transform_error': max(errors), 'profile_samples_checked': len(times)})
    carton_errors = []
    for actor in json.loads((P / 'carton_playbacks.json').read_text()):
        clip = clips['Pick and place ' + actor['label']]
        frames = actor['frames']
        expected_times = np.array([x['t'] for x in frames])
        targets = [(name, 'block', 'quat') for name in actor['groups']]
        targets += [(actor['id']+'_gripper_'+part, part, part+'Quat') for part in ('palm', 'left', 'right')]
        errors = []
        for name, key, qkey in targets:
            t, positions = clip[(name, 'translation')]
            assert np.allclose(t, expected_times, atol=1e-6)
            expected = np.array([x[key] for x in frames])
            error = float(np.max(np.abs(positions-expected)))
            assert error < 3e-6
            errors.append(error)
            expected_q = np.array([x[qkey] for x in frames])[:, [1, 2, 3, 0]]
            error = quaternion_error(clip[(name, 'rotation')][1], expected_q)
            assert error < 3e-6
            errors.append(error)
            if '_gripper_' in name:
                assert g['nodes'][names[name]]['scale'] == [0, 0, 0]
                assert np.array_equal(clip[(name, 'scale')][1], np.ones_like(positions))
        carton_errors.append({'id': actor['id'], 'maximum_transform_error': max(errors), 'frames_checked': len(frames), 'gripper_parts_checked': 3})
    from export_carton_usd import validate as validate_usd
    usd = validate_usd()
    report.update(passed=True, animation_clips=clip_summary, chair_animation_checks=chair_errors,
        carton_animation_checks=carton_errors, all_animation_times_strictly_increasing=True,
        all_animation_quaternions_unit=True, usd=usd, isaac_runtime_tested=False,
        limitations=['GLB structure and motion checked against source assets and metadata; browser appearance is checked separately.',
            'Chair motion is authored, not a dynamic simulation. Existing chair_motion_validation.json contains sampled collision checks.',
            'Carton animation replays the separate MuJoCo simulation. These asset checks do not validate its physics assumptions.',
            'Dimensions and physical parameters are estimates; hidden geometry is source-informed completion. Isaac runtime not tested.'])
    return report


if __name__ == '__main__':
    try:
        result = validate()
    except Exception as exc:
        result = {'passed': False, 'error': str(exc), 'traceback': traceback.format_exc()}
    (P / 'interactive_asset_validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('images', 'usd')}, indent=2))
    if not result['passed']:
        raise SystemExit(1)
