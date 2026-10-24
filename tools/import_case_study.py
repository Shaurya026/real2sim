"""Import the historical office meshes without training or claiming a new run.

Usage: python3 tools/import_case_study.py --source ../room-to-robot
Only Python's standard library is required. The early Open3D PLY is converted
losslessly in topology to a vertex-colored GLB; position precision becomes float32.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ply_to_glb(source, destination):
    """Read exactly the supplied Open3D triangle layout; reject other layouts."""
    with Path(source).open('rb') as f:
        lines = []
        while len(b''.join(lines)) < 65536:
            line = f.readline()
            if not line:
                raise ValueError('Truncated PLY header')
            lines.append(line)
            if line.strip() == b'end_header':
                break
        else:
            raise ValueError('Oversized PLY header')
        rows = [line.decode('ascii').strip() for line in lines]
        expected = ['property double '+n for n in ('x','y','z','nx','ny','nz')]
        expected += ['property uchar '+n for n in ('red','green','blue')]
        if rows[:2] != ['ply', 'format binary_little_endian 1.0']:
            raise ValueError('Expected little-endian Open3D PLY')
        vi = next(i for i, r in enumerate(rows) if r.startswith('element vertex '))
        fi = next(i for i, r in enumerate(rows) if r.startswith('element face '))
        count, faces = int(rows[vi].split()[-1]), int(rows[fi].split()[-1])
        if rows[vi+1:fi] != expected or rows[fi+1:] != ['property list uchar uint vertex_indices', 'end_header']:
            raise ValueError('Unsupported vertex or face layout')
        if count <= 0 or faces <= 0:
            raise ValueError('Mesh must contain vertices and faces')
        vertex = struct.Struct('<6d3B')
        positions, normals, colors, indices = bytearray(), bytearray(), bytearray(), bytearray()
        lo, hi = [math.inf]*3, [-math.inf]*3
        for _ in range(count):
            row = vertex.unpack(f.read(vertex.size))
            if not all(math.isfinite(x) for x in row[:6]):
                raise ValueError('Nonfinite mesh vertex')
            positions.extend(struct.pack('<3f', *row[:3]))
            normals.extend(struct.pack('<3f', *row[3:6]))
            # glTF vertex colors are linear; the input Open3D colors are sRGB.
            linear = [v/255/12.92 if v/255 <= .04045 else ((v/255+.055)/1.055)**2.4 for v in row[6:]]
            colors.extend(struct.pack('<3f', *linear))
            for j in range(3):
                lo[j], hi[j] = min(lo[j], row[j]), max(hi[j], row[j])
        for _ in range(faces):
            if f.read(1) != b'\x03':
                raise ValueError('Only triangle faces are supported')
            face = f.read(12)
            if len(face) != 12 or max(struct.unpack('<3I', face)) >= count:
                raise ValueError('Invalid triangle index')
            indices.extend(face)
        if f.read(1):
            raise ValueError('Unexpected trailing mesh data')
    chunks = [positions, normals, colors, indices]
    offset, views = 0, []
    for chunk in chunks:
        views.append({'buffer':0, 'byteOffset':offset, 'byteLength':len(chunk)})
        offset += len(chunk)
    gltf = {'asset':{'version':'2.0','generator':'Real2Sim historical mesh importer'},
        'buffers':[{'byteLength':offset}], 'bufferViews':views,
        'accessors':[
            {'bufferView':0,'componentType':5126,'count':count,'type':'VEC3','min':lo,'max':hi},
            {'bufferView':1,'componentType':5126,'count':count,'type':'VEC3'},
            {'bufferView':2,'componentType':5126,'count':count,'type':'VEC3'},
            {'bufferView':3,'componentType':5125,'count':faces*3,'type':'SCALAR'}],
        'materials':[{'name':'Captured vertex colors','doubleSided':True,
            'pbrMetallicRoughness':{'metallicFactor':0,'roughnessFactor':1}}],
        'meshes':[{'primitives':[{'attributes':{'POSITION':0,'NORMAL':1,'COLOR_0':2},'indices':3,'material':0,'mode':4}]}],
        # Source is Z up. glTF is Y up: [x,y,z] becomes [x,z,-y].
        'nodes':[{'name':'Early observed surface','mesh':0,'rotation':[-math.sqrt(.5),0,0,math.sqrt(.5)]}],
        'scenes':[{'nodes':[0]}], 'scene':0}
    text = json.dumps(gltf, separators=(',',':'), allow_nan=False).encode()
    text += b' ' * (-len(text)%4)
    binary = b''.join(chunks)
    binary += b'\0' * (-len(binary)%4)
    raw = struct.pack('<4sII',b'glTF',2,12+8+len(text)+8+len(binary))
    raw += struct.pack('<I4s',len(text),b'JSON')+text+struct.pack('<I4s',len(binary),b'BIN\0')+binary
    Path(destination).write_bytes(raw)
    return {'vertices':count,'triangles':faces,'conversion':'Open3D Z-up PLY to Y-up GLB; same topology, float32 positions and normals; sRGB colors decoded to linear'}


def inspect_glb(path):
    raw = Path(path).read_bytes()
    if len(raw)<20 or struct.unpack_from('<4sII',raw) != (b'glTF',2,len(raw)):
        raise ValueError(f'Invalid GLB: {path}')
    size, kind = struct.unpack_from('<I4s',raw,12)
    if kind != b'JSON' or 20+size>len(raw):
        raise ValueError('Invalid JSON chunk')
    doc = json.loads(raw[20:20+size])
    triangles, vertices = 0, 0
    for mesh in doc.get('meshes',[]):
        for primitive in mesh['primitives']:
            if primitive.get('mode',4)!=4:
                raise ValueError('Expected triangle primitives')
            n = doc['accessors'][primitive['attributes']['POSITION']]['count']
            vertices += n
            elements = doc['accessors'][primitive['indices']]['count'] if 'indices' in primitive else n
            if elements%3:
                raise ValueError('Invalid triangle count')
            triangles += elements//3
    external = [x['uri'] for key in ('buffers','images') for x in doc.get(key,[]) if 'uri' in x and not x['uri'].startswith('data:')]
    if external:
        raise ValueError(f'GLB has external dependencies: {external}')
    return {'vertices':vertices,'triangles':triangles,'meshes':len(doc.get('meshes',[])),
            'embedded_images':sum('bufferView' in x for x in doc.get('images',[])),
            'nodes':[n.get('name','Unnamed') for n in doc.get('nodes',[]) if 'mesh' in n]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    args = parser.parse_args()
    dest = ROOT/'docs/mesh/assets'
    dest.mkdir(parents=True,exist_ok=True)
    assets = []
    specs = [
        ('rough','Early depth-fused surface','outputs/da3_v2_final_geometry/observed_room.ply','rough-room.glb'),
        ('repaired','Textured room + Blender repair','outputs/realism/room-repaired.glb','room-repaired.glb'),
        ('chair','Authored Blender chair','outputs/realism/chair-repaired.glb','chair-repaired.glb')]
    for identifier, title, relative, filename in specs:
        source, target = args.source/relative, dest/filename
        conversion = ply_to_glb(source,target) if source.suffix=='.ply' else None
        if conversion is None:
            shutil.copy2(source,target)
        assets.append({'id':identifier,'title':title,'file':'assets/'+filename,
            'source':relative,'source_sha256':sha(source),'sha256':sha(target),'bytes':target.stat().st_size,
            **inspect_glb(target), **({'conversion':conversion['conversion']} if conversion else {})})
    office = ROOT/'docs/mesh/environment/assets/room.glb'
    if office.is_file():
        assets.insert(0,{'id':'office','title':'First office · original mesh','file':'environment/assets/room.glb',
            'source':'room2sim_repository.zip / demo/office_interactions/room.glb',
            'source_sha256':sha(office),'sha256':sha(office),'bytes':office.stat().st_size,**inspect_glb(office)})
    evidence = ROOT/'docs/mesh/evidence'
    evidence.mkdir(exist_ok=True)
    for filename in ('asset-validation.json','texture-audit.json','chair-pose-fit.json'):
        shutil.copy2(args.source/'outputs/realism'/filename,evidence/filename)
    shutil.copy2(args.source/'outputs/status.json',evidence/'historical-status.json')
    shutil.copy2(args.source/'outputs/gaussian/sousvide_v2/evaluation.json',evidence/'gaussian-evaluation.json')
    shutil.copy2(args.source/'outputs/realism/realism-comparison-298.jpg',dest/'comparison.jpg')
    shutil.copy2(args.source/'outputs/browser/geometry.png',dest/'geometry-preview.png')
    vendor = ROOT/'docs/mesh/vendor'
    shutil.copytree(ROOT/'web/dist/vendor',vendor,dirs_exist_ok=True)
    report = {'version':1,'scope':'Historical local assets; imported and structurally checked, not regenerated by the new pipeline.',
        'metric_scale_verified':False,'sam3d_executed':False,'astra_execution_verified':False,
        'assets':assets}
    (ROOT/'docs/mesh/assets.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
