"""Check original GLB animation buffers without a browser or GPU."""
import json
import math
from pathlib import Path
import struct


def check_animations(path):
    raw=Path(path).read_bytes()
    if len(raw)<28 or struct.unpack_from('<4sII',raw)!=(b'glTF',2,len(raw)):
        raise ValueError('Invalid animated GLB')
    length,kind=struct.unpack_from('<I4s',raw,12)
    if kind!=b'JSON':raise ValueError('Missing GLB JSON')
    doc=json.loads(raw[20:20+length]);offset=20+length
    size,kind=struct.unpack_from('<I4s',raw,offset)
    if kind!=b'BIN\0' or offset+8+size!=len(raw):raise ValueError('Missing or invalid binary animation chunk')
    binary=raw[offset+8:]
    def accessor(index):
        a=doc['accessors'][index];view=doc['bufferViews'][a['bufferView']]
        if a.get('componentType')!=5126 or 'sparse' in a or view.get('buffer',0)!=0:
            raise ValueError('Animation needs embedded float32 accessors')
        width={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']];record=struct.Struct('<'+'f'*width)
        stride=view.get('byteStride',record.size);start=view.get('byteOffset',0)+a.get('byteOffset',0);count=a['count']
        end=start+(count-1)*stride+record.size
        if count<=0 or stride<record.size or start<0 or end>len(binary) or end>view.get('byteOffset',0)+view['byteLength']:
            raise ValueError('Animation accessor exceeds its buffer view')
        rows=[record.unpack_from(binary,start+i*stride) for i in range(count)]
        if any(not math.isfinite(v) for row in rows for v in row):raise ValueError('Nonfinite animation track')
        return rows
    reports=[]
    for animation in doc.get('animations',[]):
        duration=0;motion=False
        for sampler in animation['samplers']:
            times=[r[0] for r in accessor(sampler['input'])];values=accessor(sampler['output'])
            if times[0]<0 or any(a>=b for a,b in zip(times,times[1:])):raise ValueError('Animation times must increase')
            multiplier=3 if sampler.get('interpolation')=='CUBICSPLINE' else 1
            if len(values)!=len(times)*multiplier:raise ValueError('Animation value count mismatch')
            duration=max(duration,times[-1]);motion|=any(any(abs(a-b)>1e-6 for a,b in zip(values[0],row)) for row in values[1:])
        for channel in animation['channels']:
            if not 0<=channel['sampler']<len(animation['samplers']):raise ValueError('Invalid animation sampler')
            target=channel['target']
            if not 0<=target['node']<len(doc['nodes']) or target['path'] not in ('translation','rotation','scale','weights'):
                raise ValueError('Invalid animation target')
        if duration<=0 or not motion:raise ValueError('Animation has no motion')
        reports.append({'name':animation.get('name','Unnamed'),'seconds':duration,'channels':len(animation['channels'])})
    if not reports:raise ValueError('Expected original scene animation')
    return reports
