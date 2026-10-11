"""Separate the room into named nodes and embed the demonstrated object motions."""
from room2sim_paths import project_path, input_path, browser_path, openmvs_path, ffmpeg_path
from pathlib import Path
import base64
import json
import struct
import io
import numpy as np
from PIL import Image

P = Path(__file__).resolve().parent


def export_interaction_glb(data):
    g = dict(asset=dict(version='2.0', generator='Source-textured room with fitted interactive objects'),
        scene=0, scenes=[dict(nodes=[0])], nodes=[dict(name='Room', children=[], rotation=[-2**-.5,0,0,2**-.5])],
        meshes=[], materials=[], textures=[], images=[], samplers=[dict(magFilter=9729,minFilter=9729,wrapS=33071,wrapT=33071)],
        bufferViews=[], accessors=[], extensionsUsed=['KHR_materials_unlit'], extras=dict(
            source='1000021594.mp4', metricScaleKnown=False,
            description='Photographic room with source-informed fitted furniture and closed cartons. Hidden surfaces are inferred.',
            animation='Chair motion is authored. Carton poses replay free-body MuJoCo contact dynamics under assumed physical parameters.'))
    chunks=[]; length=0; textures={}; nodes={}; pivots={}
    def chunk(raw, target=None):
        nonlocal length
        idx=len(g['bufferViews']); g['bufferViews'].append(dict(buffer=0,byteOffset=length,byteLength=len(raw),**({'target':target} if target else {})))
        raw += b'\0'*(-len(raw)%4); chunks.append(raw); length+=len(raw); return idx
    def accessor(values, kind, target=None):
        values=np.ascontiguousarray(values,dtype='<f4')
        entry=dict(bufferView=chunk(values.tobytes(),target),componentType=5126,count=len(values),type=kind)
        if kind in ('SCALAR','VEC3'):
            entry.update(min=np.atleast_1d(values.min(axis=0)).astype(float).tolist(),max=np.atleast_1d(values.max(axis=0)).astype(float).tolist())
        idx=len(g['accessors']);g['accessors'].append(entry);return idx
    export_groups=list(data['groups'])
    # The independent GLB includes the gripper so its pickup clip has the same
    # visible cause as the browser playback. Hide it in the default static pose.
    texture_io=io.BytesIO();Image.new('RGB',(8,8),(42,117,129)).save(texture_io,format='JPEG')
    plain_texture='data:image/jpeg;base64,'+base64.b64encode(texture_io.getvalue()).decode()
    faces=np.array([[0,2,1],[1,2,3],[4,5,6],[5,7,6],[0,1,4],[1,5,4],[2,6,3],[3,6,7],[0,4,2],[2,4,6],[1,3,5],[3,7,5]])
    for actor in data.get('interactions',{}).get('cartons',[]):
        for part in ('palm','left','right'):
            size=np.array(actor['gripper']['palmSize' if part=='palm' else 'fingerSize'])
            corners=np.array([[1 if n&(1<<i) else -1 for i in range(3)] for n in range(8)])*size/2
            xyz=corners[faces].reshape(-1,3).astype('<f4');uv=np.zeros((len(xyz),2),dtype='<f4')
            export_groups.append(dict(name=actor['id']+'_gripper_'+part,kind='added_gripper',hiddenByDefault=True,
                positions=base64.b64encode(xyz.tobytes()).decode(),uv=base64.b64encode(uv.tobytes()).decode(),texture=plain_texture))
    for idx, group in enumerate(export_groups):
        name=group.get('name',f"{group['kind']}_{idx}")
        xyz=np.frombuffer(base64.b64decode(group['positions']),dtype='<f4').reshape(-1,3)
        uv=np.frombuffer(base64.b64decode(group['uv']),dtype='<f4').reshape(-1,2).copy();uv[:,1]=1-uv[:,1]
        pivot=np.asarray(group.get('pivot',[0,0,0]),dtype='<f4');local=xyz-pivot
        triangles=local.reshape(-1,3,3)
        keep=np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]),axis=1)>1e-12
        local=triangles[keep].reshape(-1,3);uv=uv.reshape(-1,3,2)[keep].reshape(-1,2)
        tex=group['texture']
        if tex not in textures:
            ti=len(g['textures']);textures[tex]=ti
            g['images'].append(dict(bufferView=chunk(base64.b64decode(tex.split(',',1)[1])),mimeType='image/jpeg'))
            g['textures'].append(dict(source=ti,sampler=0))
        material=len(g['materials']);g['materials'].append(dict(name=name,doubleSided=True,pbrMetallicRoughness=dict(
            baseColorTexture=dict(index=textures[tex]),roughnessFactor=1,metallicFactor=0),extensions={'KHR_materials_unlit':{}}))
        mesh=len(g['meshes']);g['meshes'].append(dict(name=name,primitives=[dict(attributes=dict(
            POSITION=accessor(local,'VEC3',34962),TEXCOORD_0=accessor(uv,'VEC2',34962)),material=material)]))
        ni=len(g['nodes']);nodes[name]=ni;pivots[name]=pivot
        props={k:group[k] for k in ('kind','objectId','motionRole','wheelRadius','wheelAxis') if k in group}
        g['nodes'].append(dict(name=name,mesh=mesh,translation=pivot.tolist(),extras=props,**({'scale':[0,0,0]} if group.get('hiddenByDefault') else {})));g['nodes'][0]['children'].append(ni)
    animations=[]
    def animation(name, times, method):
        a=dict(name=name,channels=[],samplers=[],extras=dict(method=method));animations.append(a)
        ti=accessor(times,'SCALAR')
        def channel(group_name,path,values,kind):
            if group_name not in nodes: raise ValueError('Missing animation mesh '+group_name)
            si=len(a['samplers']);a['samplers'].append(dict(input=ti,output=accessor(values,kind),interpolation='LINEAR'))
            a['channels'].append(dict(sampler=si,target=dict(node=nodes[group_name],path=path)))
        return channel
    for actor in data.get('interactions',{}).get('cartons',[]):
        frames=actor['frames'];times=np.array([f['t'] for f in frames]);positions=np.array([f['block'] for f in frames]);q=np.array([f['quat'] for f in frames])[:,[1,2,3,0]]
        for i in range(1,len(q)):
            if q[i-1]@q[i]<0:q[i]*=-1
        channel=animation('Pick and place '+actor['label'],times,'Free-body MuJoCo contact playback; gripper trajectory and material parameters assumed')
        for name in actor['groups']:
            channel(name,'translation',positions,'VEC3');channel(name,'rotation',q,'VEC4')
        for part in ('palm','left','right'):
            name=actor['id']+'_gripper_'+part
            pq=np.array([f[part+'Quat'] for f in frames])[:,[1,2,3,0]]
            for i in range(1,len(pq)):
                if pq[i-1]@pq[i]<0:pq[i]*=-1
            channel(name,'translation',np.array([f[part] for f in frames]),'VEC3')
            channel(name,'rotation',pq,'VEC4');channel(name,'scale',np.ones((len(frames),3)),'VEC3')
    def smooth(t):t=np.clip(t,0,1);return t*t*t*(t*(t*6-15)+10)
    for actor in data.get('interactions',{}).get('chairs',[]):
        duration=actor.get('duration',9);times=np.linspace(0,duration,int(duration*60)+1);u=times/duration
        travel=np.where(u<.32,smooth(u/.32),np.where(u<.72,1,1-smooth((u-.72)/.28)))
        swivel=actor.get('seatYaw',.4)*np.where(u<.30,0,np.where(u<.48,smooth((u-.30)/.18),np.where(u<.58,1,np.where(u<.72,1-smooth((u-.58)/.14),0))))
        channel=animation('Roll and swivel '+actor['label'],times,'Authored furniture demonstration; no chair dynamics simulation')
        offset=np.array(actor['offset']);spec=actor['groups'];wheels={x['name']:x for x in actor.get('wheels',[])}
        for role in ('base','seat','wheels'):
            names=spec.get(role,[]); names=[names] if isinstance(names,str) else names
            for name in names:
                channel(name,'translation',pivots[name]+travel[:,None]*offset,'VEC3')
                if role=='seat':q=np.c_[np.zeros((len(times),2)),np.sin(swivel/2),np.cos(swivel/2)]
                elif role=='wheels':
                    wheel=wheels[name];axis=np.array(wheel.get('axis',wheel.get('wheelAxis')));radius=wheel.get('radius',wheel.get('wheelRadius',.034))
                    # Pure rolling: displacement = angle * (axis cross world-up) * radius.
                    angle=(offset@np.cross(axis,[0,0,1]))*travel/radius
                    q=np.c_[np.sin(angle/2)[:,None]*axis,np.cos(angle/2)]
                else:continue
                channel(name,'rotation',q,'VEC4')
    if animations:g['animations']=animations
    g['buffers']=[dict(byteLength=length)]
    header=json.dumps(g,separators=(',',':')).encode();header+=b' '*(-len(header)%4)
    binary=b''.join(chunks);body=struct.pack('<I4s',len(header),b'JSON')+header+struct.pack('<I4s',len(binary),b'BIN\0')+binary
    (P/'room.glb').write_bytes(struct.pack('<4sII',b'glTF',2,len(body)+12)+body)
    return dict(nodes=len(nodes),animation_clips=len(animations),bytes=len(body)+12)
