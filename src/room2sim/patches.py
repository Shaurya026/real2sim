"""Typed edits accepted from a human or review model. Never execute generated code."""
import re
import math
from .core import vector, transform, IDENTITY


def validate_patch(patch):
    if patch.get('version') != 1 or not isinstance(patch.get('operations'), list):
        raise ValueError('Patch needs version=1 and operations list')
    if len(patch['operations']) > 64:
        raise ValueError('Maximum 64 operations per patch')
    ids = set()
    for op in patch['operations']:
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', op.get('id', '')) or op['id'] in ids:
            raise ValueError('Operation ids must be unique safe names')
        ids.add(op['id'])
        kind = op.get('kind')
        if kind == 'crop_splats':
            lo = vector(op['min'], 3, 'min')
            hi = vector(op['max'], 3, 'max')
            if any(a >= b for a, b in zip(lo, hi)):
                raise ValueError('Crop min must be below max')
        elif kind in ('table', 'box', 'cylinder'):
            if 'interactive' in op and not isinstance(op['interactive'], bool):
                raise ValueError('interactive must be a boolean')
            vector(op['position'], 3, 'position')
            vector(op['dimensions'], 3, 'dimensions', positive=True)
            if any(x > 100 for x in op['dimensions']):
                raise ValueError('Repair dimensions exceed 100 world units')
            vector(op['color'], 3, 'color')
            if any(x < 0 or x > 1 for x in op['color']):
                raise ValueError('color channels must be in [0,1]')
            vector(op['rotation'], 3, 'rotation Euler radians')
        elif kind == 'remove_mesh':
            if not isinstance(op.get('name'), str) or not op['name']:
                raise ValueError('remove_mesh needs an exact mesh name')
        else:
            raise ValueError(f'Unsupported operation: {kind}')
        if not isinstance(op.get('reason'), str) or not op['reason'].strip():
            raise ValueError('Every edit requires a reason')
    return patch


def repair_objects(patch, existing=()):
    """Register explicitly movable Blender repair groups, in browser coordinates."""
    validate_patch(patch)
    ids = {obj['id'] for obj in existing}
    objects = []
    for op in patch['operations']:
        if op['kind'] not in ('table', 'box', 'cylinder') or not op.get('interactive', False):
            continue
        if op['id'] in ids:
            raise ValueError(f"Repair object id already exists: {op['id']}")
        ids.add(op['id'])
        x, y, z = (angle / 2 for angle in op['rotation'])
        sx, sy, sz = math.sin(x), math.sin(y), math.sin(z)
        cx, cy, cz = math.cos(x), math.cos(y), math.cos(z)
        objects.append({'id': op['id'], 'label': op['id'].replace('_', ' '),
            'representation': 'mesh', 'node': op['id'], 'node_source': 'repairs',
            'transform': {'position': list(op['position']), 'scale': 1,
                'quaternion': [sx*cy*cz+cx*sy*sz, cx*sy*cz-sx*cy*sz,
                               cx*cy*sz+sx*sy*cz, cx*cy*cz-sx*sy*sz]},
            'collider': {'type': 'box', 'center': [0,0,0], 'dimensions': list(op['dimensions'])},
            'background_removed': False,
            'provenance': {'backend': 'typed Blender repair', 'operation_id': op['id'],
                'scope': 'candidate geometry and interaction proxy; background separation requires visual review'}})
    return objects
