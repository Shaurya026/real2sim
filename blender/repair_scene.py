"""Run inside Blender 4.2+: deterministic primitive repairs, GLB export and views.
Input manifest and patch have already been validated by the orchestration CLI.
Coordinates in patch: browser/glTF +Y up; converted into Blender +Z up here.
"""
import argparse
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Vector, Euler, Matrix

p = argparse.ArgumentParser()
p.add_argument('--patch', required=True)
p.add_argument('--output', required=True)
p.add_argument('--source')
a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
out = Path(a.output).resolve()
out.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
if a.source:
    bpy.ops.import_scene.gltf(filepath=str(Path(a.source).resolve()))
patch = json.loads(Path(a.patch).read_text())
# Browser vector [x,y,z] → Blender [x,-z,y]. Export reverses this mapping.
C = Matrix(((1,0,0), (0,0,-1), (0,1,0)))


def material(name, color):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*color, 1)
    m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .7
    return m


def box(name, center, dimensions, mat, parent):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.object
    o.name = name
    o.parent = parent
    o.location = C @ Vector(center)
    o.scale = (dimensions[0], dimensions[2], dimensions[1])
    o.data.materials.append(mat)
    return o


created = []
for op in patch['operations']:
    if op['kind'] == 'remove_mesh':
        matches = [o for o in bpy.data.objects if o.name == op['name'] and o.type == 'MESH']
        if not matches:
            raise RuntimeError(f"Mesh not found: {op['name']}")
        for o in matches:
            bpy.data.objects.remove(o, do_unlink=True)
        continue
    if op['kind'] == 'crop_splats':
        continue
    parent = bpy.data.objects.new(op['id'], None)
    bpy.context.collection.objects.link(parent)
    parent.location = C @ Vector(op['position'])
    parent.rotation_euler = (C @ Euler(op['rotation'], 'XYZ').to_matrix() @ C.transposed()).to_euler()
    mat = material(op['id'] + '_material', op['color'])
    x, y, z = op['dimensions']
    if op['kind'] == 'table':
        # Origin at table volume center; tabletop at top, four legs below.
        thick = min(.06, y*.12)
        leg = min(.07, x*.12, z*.12)
        box(op['id'] + '_top', [0, y/2-thick/2, 0], [x, thick, z], mat, parent)
        for ix in (-1,1):
            for iz in (-1,1):
                box(f"{op['id']}_leg_{ix}_{iz}", [ix*(x/2-leg), -thick/2, iz*(z/2-leg)],
                    [leg, y-thick, leg], mat, parent)
    elif op['kind'] == 'box':
        box(op['id'] + '_mesh', [0,0,0], [x,y,z], mat, parent)
    elif op['kind'] == 'cylinder':
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=1, depth=1)
        o = bpy.context.object
        o.name = op['id'] + '_mesh'
        o.parent = parent
        o.scale = (x/2, z/2, y)
        o.data.materials.append(mat)
    created.append(op['id'])
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
if meshes:
    bpy.ops.export_scene.gltf(filepath=str(out/'repairs.glb'), export_format='GLB', export_yup=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'scene.blend'))
    # Mesh-only previews: full hybrid browser review must be captured separately.
    corners = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    lo = Vector([min(c[i] for c in corners) for i in range(3)])
    hi = Vector([max(c[i] for c in corners) for i in range(3)])
    center = (lo+hi)/2
    radius = max((hi-lo).length, 1)
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x = 960
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.world.color = (.15,.15,.15)
    for i, direction in enumerate(((1,-1,.8),(-1,-1,.8),(1,1,.8))):
        bpy.ops.object.camera_add(location=center+Vector(direction).normalized()*radius*1.3)
        cam = bpy.context.object
        cam.rotation_euler = (center-cam.location).to_track_quat('-Z','Y').to_euler()
        scene.camera = cam
        bpy.ops.object.light_add(type='AREA', location=cam.location)
        bpy.context.object.data.energy = 1500
        bpy.context.object.data.shape = 'DISK'
        bpy.context.object.data.size = radius
        scene.render.filepath = str(out/f'mesh-review-{i}.png')
        bpy.ops.render.render(write_still=True)
(out/'receipt.json').write_text(json.dumps({'created':created, 'mesh_count':len(meshes),
    'blender_version':bpy.app.version_string, 'preview_scope':'mesh only, not full Gaussian environment'}, indent=2))
