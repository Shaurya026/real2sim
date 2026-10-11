"""Gaussian PLY validation/filtering using only the Python standard library.
Binary crop preserves entire records including all spherical harmonic properties.
"""
from pathlib import Path
import math
import struct
from .core import vector

REQUIRED = {'x','y','z','f_dc_0','f_dc_1','f_dc_2','opacity',
            'scale_0','scale_1','scale_2','rot_0','rot_1','rot_2','rot_3'}
TYPES = {'char':'b','int8':'b','uchar':'B','uint8':'B','short':'h','int16':'h',
         'ushort':'H','uint16':'H','int':'i','int32':'i','uint':'I','uint32':'I',
         'float':'f','float32':'f','double':'d','float64':'d'}


def load(path):
    with Path(path).open('rb') as f:
        lines=[]
        while True:
            line=f.readline()
            if not line or sum(map(len,lines))>65536:
                raise ValueError('Invalid or oversized PLY header')
            lines.append(line)
            if line.strip()==b'end_header': break
        header=b''.join(lines)
        body=f.read()
    if lines[0].strip()!=b'ply': raise ValueError('Not PLY')
    fmt=None; count=None; props=[]; element=None
    for raw in lines:
        row=raw.decode('ascii').split()
        if not row: continue
        if row[0]=='format': fmt=row[1]
        if row[0]=='element':
            if row[1]!='vertex': raise ValueError('Gaussian PLY must contain only a vertex element')
            element=row[1]; count=int(row[2])
        if row[0]=='property' and element=='vertex':
            if row[1] not in TYPES: raise ValueError('Unsupported Gaussian property type')
            props.append((row[2],row[1]))
    names=[p[0] for p in props]
    if len(set(names))!=len(names) or not REQUIRED.issubset(names):
        raise ValueError('Not Gaussian PLY: missing or duplicate properties')
    if not count or count<0: raise ValueError('Empty splat')
    if fmt in ('binary_little_endian','binary_big_endian'):
        record=struct.Struct(('<' if fmt=='binary_little_endian' else '>')+''.join(TYPES[t] for _,t in props))
        if len(body)!=count*record.size: raise ValueError('PLY length does not match vertex count')
        values=record.iter_unpack(body)
        rows=None
    elif fmt=='ascii':
        rows=body.splitlines()
        if len(rows)!=count: raise ValueError('ASCII PLY row count mismatch')
        record=None
        values=(tuple(map(float,r.split())) for r in rows)
    else: raise ValueError('Unsupported PLY format')
    return {'header':header,'body':body,'format':fmt,'count':count,'names':names,
            'record':record,'values':values,'rows':rows}


def inspect(path):
    data=load(path)
    ix=[data['names'].index(n) for n in ('x','y','z')]
    lo=[math.inf]*3; hi=[-math.inf]*3
    for row in data['values']:
        if len(row)!=len(data['names']) or any(not math.isfinite(x) for x in row):
            raise ValueError(f'{path}: invalid or nonfinite Gaussian')
        for i,index in enumerate(ix):
            lo[i]=min(lo[i],row[index]); hi[i]=max(hi[i],row[index])
    return {'gaussians':data['count'],'properties':data['names'],'bounds':[lo,hi]}


def check_region(region):
    lo=vector(region['min'],3,'min'); hi=vector(region['max'],3,'max')
    if any(a>=b for a,b in zip(lo,hi)): raise ValueError('region max must exceed min')
    return lo,hi


def crop(source,destination,regions,keep_inside=False):
    if Path(source).resolve()==Path(destination).resolve(): raise ValueError('Source splat is immutable')
    data=load(source)
    limits=[check_region(r) for r in regions]
    ix=[data['names'].index(n) for n in ('x','y','z')]
    records=[]
    for i,row in enumerate(data['values']):
        if len(row)!=len(data['names']) or any(not math.isfinite(v) for v in row): raise ValueError('Nonfinite or invalid Gaussian')
        selected=any(all(lo[j]<=row[k]<=hi[j] for j,k in enumerate(ix)) for lo,hi in limits)
        if selected==keep_inside:
            if data['record']:
                size=data['record'].size; records.append(data['body'][i*size:(i+1)*size])
            else: records.append(data['rows'][i]+b'\n')
    if not records: raise ValueError('Crop removes every Gaussian; refusing empty output')
    header=data['header'].replace(f"element vertex {data['count']}".encode(),f"element vertex {len(records)}".encode())
    dest=Path(destination); dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(header+b''.join(records))
    return {'input':data['count'],'output':len(records),'removed':data['count']-len(records),
            'region_frame':'source PLY coordinates; center-based selection, not segmentation'}
