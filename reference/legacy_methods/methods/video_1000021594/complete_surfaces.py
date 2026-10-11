"""Calibrated room surfaces with foreground-aware, feathered photo projection."""
from room2sim_paths import project_path, input_path, browser_path, openmvs_path, ffmpeg_path
from pathlib import Path
import sys,json,numpy as np

import pycolmap as pc,cv2,open3d as o
from PIL import Image
P=Path(__file__).resolve().parent;rot=json.loads((P/'orientation.json').read_text());R=np.array(rot['R']);scale=rot['scale'];origin=np.array(rot['origin']);r=pc.Reconstruction(P/'selected_sparse');cams=[]
for im in r.images.values():
 if not im.has_pose:continue
 T=im.cam_from_world().inverse().matrix();cams.append(dict(name=im.name,c=r.cameras[im.camera_id],T=T,eye=R@T[:,3]*scale+origin))
# Add unique cameras from the registered, similarity-aligned second video pass.
known={c['name'] for c in cams}
r2=pc.Reconstruction(P/'secondary/selected_sparse')
for im in r2.images.values():
 if not im.has_pose or im.name in known:continue
 T=im.cam_from_world().inverse().matrix();cams.append(dict(name=im.name,c=r2.cameras[im.camera_id],T=T,eye=R@T[:,3]*scale+origin))
mesh=o.io.read_triangle_mesh(str(P/'mvs/refined.ply'));V=np.asarray(mesh.vertices)@R.T*scale+origin;mesh.vertices=o.utility.Vector3dVector(V);rayScene=o.t.geometry.RaycastingScene(nthreads=8);rayScene.add_triangles(o.t.geometry.TriangleMesh.from_legacy(mesh))
# Structural corners calibrated from repeated video edges; see surface_layout.json.
A=[.28351,.07325]; B=[.52946,.05942]; C=[.2462,.5404]; E=[C[0]+B[0]-A[0],C[1]+B[1]-A[1]]
def vertical(a,b):return [[*a,0],[*b,0],[*b,3.1],[*a,3.1]]
def normal(a,b):
 d=np.array(b)-a;n=np.array([-d[1],d[0],0.]);return (n/np.linalg.norm(n)).tolist()
specs=[
 ('table',[[-.73,.31,.75],[.27,.31,.75],[.34,-1.28,.75],[-.66,-1.28,.75]],[0,0,1],1200,1600,[209,211,215],[176,50,25,110,45,183]),
 ('column_side',vertical(A,C),normal(A,C),384,1536,[198,198,189],[176,25,50,110]),
 ('column_front',vertical(B,A),normal(B,A),256,1536,[203,204,196],[25,50,176,40]),
 ('column_right',vertical(E,B),normal(E,B),384,1536,[195,197,190],[55,65,110,75]),
 ('column_back',vertical(C,E),normal(C,E),256,1536,[190,193,185],[110,115,105,100]),
 ('blue_wall',vertical([1.25,-2.3],[1.25,1.20]),[-1,0,0],1536,1536,[40,82,111],[58,59,75,65,55,50,85,110]),
 ('screen',[[1.187,-2.16,1.09],[1.187,-.42,1.09],[1.187,-.42,2.38],[1.187,-2.16,2.38]],[-1,0,0],1400,1040,[215,216,212],[58,59,60,65,75]),
 ('back_wall',vertical([-1.56,1.03],[1.25,1.20]),[.06,-.998,0],1400,1536,[193,195,187],[25,176,0,110,10,45]),
 ('left_glass',vertical([-1.56,1.03],[-1.56,-2.3]),[1,0,0],1400,1536,[170,180,179],[121,110,130,0,10,160]),
 ('front_glass',vertical([-1.56,-2.3],[1.25,-2.3]),[0,1,0],1400,1536,[170,180,179],[140,145,146,139,90,85,95]),
 ('floor',[[-1.56,-2.3,-.04],[1.25,-2.3,-.04],[1.25,1.20,-.04],[-1.56,1.03,-.04]],[0,0,1],1024,1024,[95,97,95],[17,100,75,90]),
 ('ceiling',[[-1.56,-2.3,3.1],[1.25,-2.3,3.1],[1.25,1.20,3.1],[-1.56,1.03,3.1]],[0,0,-1],768,768,[201,203,197],[65,25,110,0])]
(P/'surface_layout.json').write_text(json.dumps(dict(column_front_inner=A,column_front_outer=B,column_rear_inner=C,column_rear_outer_inferred=E,method='Column vertical edge intersections fitted across frames 0025,0050,0176; rear face inferred; outer room boundaries fitted to scan planes'),indent=2))

# Use only interior object geometry as an occluder. The noisy wall scan must not punch
# random holes into its own replacement. Exact fitted planes are tested separately.
T=np.asarray(mesh.triangles);cent=V[T].mean(1)
inside=(cent[:,0]>-1.42)&(cent[:,0]<1.03)&(cent[:,1]>-2.1)&(cent[:,1]<.99)&(cent[:,2]>.05)&(cent[:,2]<2.1)
for name,cs,nn,*_ in specs:
 if name in ['floor','ceiling']:continue
 cs=np.array(cs);nn=np.array(nn);a=cs[1]-cs[0];b=cs[3]-cs[0];d=cent-cs[0];u=d@a/(a@a);v=d@b/(b@b)
 inside &= ~((np.abs(d@nn)<.24)&(u>-.1)&(u<1.1)&(v>-.1)&(v<1.1))
om=o.geometry.TriangleMesh(o.utility.Vector3dVector(V),o.utility.Vector3iVector(T[inside]));rayScene=o.t.geometry.RaycastingScene(nthreads=8);rayScene.add_triangles(o.t.geometry.TriangleMesh.from_legacy(om))
# The replacement chairs prevent their original broken silhouettes being baked onto walls.
if (P/'chair_repair.json').exists():
 furniture=json.loads((P/'chair_repair.json').read_text())
 for g in furniture['groups']:
  vv=np.load(P/g['geometry'])['xyz'].reshape(-1,3);tt=np.arange(len(vv)).reshape(-1,3)
  fm=o.geometry.TriangleMesh(o.utility.Vector3dVector(vv),o.utility.Vector3iVector(tt));rayScene.add_triangles(o.t.geometry.TriangleMesh.from_legacy(fm))
cam_by_name={c['name']:c for c in cams}
# Conservative opaque supports for the stacked cartons. Their backs are not visible.
foreground_boxes=[([-1.50,-.04,-.04],[-.26,.89,1.39]),([-1.49,-.04,-.04],[-1.00,.67,1.94])]


def fill_missing(rgb,valid,fallback):
 # Harmonic completion at multiple scales: boundary colors continue smoothly through
 # unsupported areas. This does not synthesize object detail.
 H,W=valid.shape
 if valid.sum()<20:return np.broadcast_to(np.array(fallback,dtype='f4'),rgb.shape).copy()
 levels=[];w,h=W,H
 while min(w,h)>24:levels.append((w,h));w=max(1,w//2);h=max(1,h//2)
 result=np.full((h,w,3),np.median(rgb[valid],axis=0),dtype='f4')
 for w,h in [(w,h)]+levels[::-1]:
  v=cv2.resize(valid.astype('f4'),(w,h),interpolation=cv2.INTER_AREA)
  weighted=cv2.resize(rgb*valid[:,:,None],(w,h),interpolation=cv2.INTER_AREA)
  target=weighted/np.maximum(v[:,:,None],1e-5);fixed=v>.5
  result=cv2.resize(result,(w,h),interpolation=cv2.INTER_LINEAR);result[fixed]=target[fixed]
  for _ in range(45):
   blurred=cv2.blur(result,(3,3));result[~fixed]=blurred[~fixed]
 return result

def visibility(pts,c,name):
 dr=pts-c['eye'];dist=np.linalg.norm(dr,axis=1);rays=np.c_[np.broadcast_to(c['eye'],(len(pts),3)),dr/dist[:,None]].astype('f4');hit=rayScene.cast_rays(o.core.Tensor(rays))['t_hit'].numpy();ok=hit>=dist-.10
 for lo,hi in foreground_boxes:
  aa=(np.array(lo)-c['eye'])/np.where(np.abs(dr)>1e-9,dr,1e-9);bb=(np.array(hi)-c['eye'])/np.where(np.abs(dr)>1e-9,dr,1e-9);near=np.minimum(aa,bb).max(1);far=np.maximum(aa,bb).min(1)
  ok &= ~((far>np.maximum(near,0))&(near<.99)&(near>0))
 for other,cs,nn,*_ in specs:
  if other==name or other in ['floor','ceiling']:continue
  cs=np.array(cs);nn=np.array(nn);den=dr@nn;tt=((cs[0]-c['eye'])@nn)/np.where(np.abs(den)>1e-8,den,1e-8);q=c['eye']+tt[:,None]*dr-cs[0];a=cs[1]-cs[0];b=cs[3]-cs[0];u=q@a/(a@a);v=q@b/(b@b)
  ok &= ~((tt>0)&(tt<.985)&(u>.002)&(u<.998)&(v>.002)&(v<.998))
 if name=='table':
  vv=dr;ta=(.75-c['eye'][2])/vv[:,2];tb=(1.04-c['eye'][2])/vv[:,2];lo=np.maximum(0,np.minimum(ta,tb));hi=np.minimum(1,np.maximum(ta,tb));t=-np.sum(vv[:,:2]*c['eye'][:2],axis=1)/np.maximum(np.sum(vv[:,:2]**2,axis=1),1e-9);t=np.clip(t,lo,hi);xy=c['eye'][:2]+t[:,None]*vv[:,:2];ok &= ~((lo<=hi)&(np.linalg.norm(xy,axis=1)<.065))
 return ok

report=[]
previous={e['name']:e for e in json.loads((P/'completion.json').read_text())['planes']} if (P/'completion.json').exists() else {}
for name,corners,normal,W,H,fallback,preferred in specs:
 if len(sys.argv)>1 and name not in sys.argv[1:] and name in previous:
  report.append(previous[name]);continue
 corners=np.array(corners);normal=np.array(normal);normal=normal/np.linalg.norm(normal)
 u,v=np.meshgrid(np.linspace(0,1,W,dtype='f4'),np.linspace(1,0,H,dtype='f4'));points=((1-u)*(1-v))[...,None]*corners[0]+(u*(1-v))[...,None]*corners[1]+(u*v)[...,None]*corners[2]+((1-u)*v)[...,None]*corners[3];pts=points.reshape(-1,3);raw=(pts-origin)@R/scale;center=corners.mean(0)
 candidates=[]
 for c in cams:
  dr=c['eye']-center;dist=np.linalg.norm(dr);cos=dr@normal/dist
  if cos<.08:continue
  score=cos/(dist+.2)
  n=int(c['name'][6:10]);score+=12/(1+preferred.index(n)) if n in preferred else 0
  candidates.append((score,c))
 candidates=sorted(candidates,key=lambda q:q[0],reverse=True)[:12]
 acc=np.zeros((H,W,3),dtype='f4');weights=np.zeros((H,W),dtype='f4');validOut=np.zeros((H,W),bool);sources=[]
 for rank,(score,c) in enumerate(candidates):
  T=c['T'];camxyz=(raw-T[:,3])@T[:,:3];proj=c['c'].img_from_cam(camxyz);proj=np.nan_to_num(proj,nan=-1e5,posinf=-1e5,neginf=-1e5);edge=np.minimum.reduce([proj[:,0]-5,714-proj[:,0],proj[:,1]-5,1274-proj[:,1]]);valid=(edge>0)&(camxyz[:,2]>0);inds=np.flatnonzero(valid)
  if not len(inds):continue
  valid[inds]=visibility(pts[inds],c,name);valid=valid.reshape(H,W)
  # Erode unreliable silhouettes, then feather over physical/image boundaries.
  valid=cv2.erode(valid.astype('u1'),np.ones((5,5),np.uint8))>0
  if valid.sum()<50:continue
  img=np.array(Image.open(P/'images'/c['name']));rgb=cv2.remap(img,proj[:,0].reshape(H,W).astype('f4'),proj[:,1].reshape(H,W).astype('f4'),cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT).astype('f4')
  if name=='blue_wall':
   # The screen has a separate surface: reject its white pixels and foreground
   # clutter from the paint atlas instead of blurring those silhouettes into it.
   blue=(rgb[:,:,2]-rgb[:,:,0]>12)&(rgb[:,:,1]-rgb[:,:,0]>4)
   valid &= blue
  feather=cv2.distanceTransform(valid.astype('u1'),cv2.DIST_L2,5);w=np.minimum(feather/50,1)**2*np.minimum(np.maximum(edge.reshape(H,W),0)/80,1)
  # Earlier anchor retains detail; later frames fill coverage with broad soft overlap.
  overlap=valid&(weights>.05)&(feather>10)
  if overlap.sum()>300:
   ref=acc[overlap]/weights[overlap,None];diff=ref-rgb[overlap];good=np.linalg.norm(diff,axis=1)<65
   if good.sum()>100:rgb=np.clip(rgb+np.clip(np.median(diff[good],axis=0),-24,24),0,255)
  w*=np.maximum(1-weights,0);acc+=rgb*w[:,:,None];weights+=w;validOut|=valid;sources.append(c['name'])
 rgb=acc/np.maximum(weights[:,:,None],1e-8);valid=weights>1e-5
 texture=fill_missing(rgb,valid,fallback)
 # A constant ceiling/floor avoids treating specular lights as physical cutouts.
 # Their appearance is explicitly completed rather than photo-recovered.
 if name=='floor':
  texture[:]=[93,96,98]
 if name=='ceiling':texture[:]=[201,203,197]
 if name.startswith('column_'):
  zz=points[:,:,2];fade=np.clip((.95-zz)/.18,0,1);texture=texture*(1-fade[:,:,None])+np.array([195,197,190])[None,None,:]*fade[:,:,None];texture[zz<.13]=[117,24,38]
 Image.fromarray(np.clip(texture,0,255).astype('u1')).save(P/f'completion_{name}.jpg',quality=94)
 xyz=corners[[0,1,2,0,2,3]].astype('f4');uv=np.array([[0,0],[1,0],[1,1],[0,0],[1,1],[0,1]],dtype='f4');np.savez_compressed(P/f'completion_{name}.npz',xyz=xyz,uv=uv)
 entry=dict(name=name,corners=corners.tolist(),normal=normal.tolist(),calibration_supported_texel_fraction=float(validOut.mean()),photographic_texel_fraction=0.0 if name in ['floor','ceiling'] else float(validOut.mean()),texture=f'completion_{name}.jpg',geometry=f'completion_{name}.npz',sources=sources);report.append(entry);print(name,round(validOut.mean(),3),sources,flush=True)
(P/'completion.json').write_text(json.dumps(dict(method='Calibrated structural planes; foreground-aware reprojection, robust color offsets, feathered multi-view texture fusion and smooth harmonic completion',inferred_geometry=True,unknown_texture_regions='Smooth color continuation, not recovered object detail',planes=report),indent=2))
