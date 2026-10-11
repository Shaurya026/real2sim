"""Source-informed complete furniture for video 1000021600.

Chairs use smooth fitted geometry because narrow black legs/mesh have unreliable
multi-view support. Positions/size are fitted to calibrated photo landmarks.
Material colors are sampled from this video; hidden structure is approximate.
The desk has four individual legs and a continuous edge, with no apron rails.
"""
from room2sim_paths import project_path, input_path, browser_path, openmvs_path, ffmpeg_path
from pathlib import Path
import json, math, sys
import numpy as np
from PIL import Image

import cv2
P=Path(__file__).resolve().parent
MATS={'plastic':(42,43,43),'rubber':(23,24,24),'fabric':(38,39,42),'mesh':(47,48,49),'metal':(91,94,94),'table_edge':(203,203,200),'table_leg':(85,91,94),'folding_seat':(60,61,61),'frame':(65,66,63),'baseboard':(170,167,153)}
# Diffuse tones are taken from source photos without baking their perspective.
for key,frame,box in [('fabric',74,(200,730,380,835)),('folding_seat',34,(319,840,361,869)),('plastic',79,(441,473,532,559))]:
 im=np.asarray(Image.open(P/f'images/frame_{frame:04d}.jpg'))
 x0,y0,x1,y1=box;MATS[key]=tuple(np.median(im[y0:y1,x0:x1].reshape(-1,3),axis=0).astype(int))
TW,TH,CELL=1536,1536,48
atlas=Image.new('RGB',(TW,TH));texels={};mi=0;rng=np.random.default_rng(1600)
for material,color in MATS.items():
 for shade in range(32):
  x=(mi%32)*CELL;y=(mi//32)*CELL;factor=.47+shade/31*.83
  block=np.broadcast_to(np.array(color)*factor,(CELL,CELL,3)).copy();yy,xx=np.mgrid[:CELL,:CELL]
  block+=rng.normal(0,.6,(CELL,CELL,1))
  if material=='fabric':block+=(((xx%3==0)|(yy%3==0))*1.5)[:,:,None]
  if material=='folding_seat':block+=np.sin(yy*.7)[:,:,None]*.6
  atlas.paste(Image.fromarray(block.clip(0,255).astype('u1')),(x,y));texels[(material,shade)]=((x+CELL/2)/TW,1-(y+CELL/2)/TH);mi+=1
# Dedicated photograph patches occupy the unused atlas area. Perspective is
# removed with source seat corners; diffuse level comes from a low-glare view.
PHOTO_REGIONS={};material_evidence=[]
for mat,frame,quad,xy in [
 ('fabric',74,[[165,734],[401,705],[510,785],[273,899]],(0,640)),
 ('folding_seat',82,[[165,610],[180,455],[395,454],[536,603]],(544,640))]:
 source=np.asarray(Image.open(P/f'images/frame_{frame:04d}.jpg'))
 target=np.array([[0,0],[511,0],[511,511],[0,511]],dtype='f4')
 H=cv2.getPerspectiveTransform(np.asarray(quad,dtype='f4'),target)
 patch=cv2.warpPerspective(source,H,(512,512),flags=cv2.INTER_CUBIC).astype('f4')
 median=np.median(patch[40:-40,40:-40].reshape(-1,3),0)
 gain=np.array(MATS[mat])/np.maximum(median,1);patch*=gain
 # Broadly darken only the fitted cushion rim so photographed top texture meets
 # its curved side material without a hard ring or pasted rectangular patch.
 yy,xx=np.mgrid[:512,:512];u=(xx-255.5)/255.5;v=(yy-255.5)/255.5
 if mat=='fabric':patch*=np.clip(1-.16*(np.maximum(abs(u),abs(v))**5),.84,1)[:,:,None]
 atlas.paste(Image.fromarray(patch.clip(0,255).astype('u1')),xy)
 PHOTO_REGIONS[mat]=(xy[0],xy[1],512,512)
 material_evidence.append({'material':mat,'photograph':f'frame_{frame:04d}.jpg','source_quad':quad,'tone_reference':{'fabric':{'frame':'frame_0074.jpg','crop':[200,730,380,835]},'folding_seat':{'frame':'frame_0034.jpg','crop':[319,840,361,869]}}[mat],'target_median_rgb':list(map(int,MATS[mat])),'method':'Rectified source photograph detail, exposure matched to lower-glare view; fitted UV mapping'})
atlas.save(P/'furniture_materials.jpg',quality=98,subsampling=0)
(P/'furniture_material_reference.json').write_text(json.dumps({'materials':material_evidence,'limitations':'Real photographed appearance mapped onto approximated chair geometry; hidden sides retain sampled material colors.'},indent=2))

class Builder:
 def __init__(self):self.v=[];self.uv=[];self.roles=[];self.role='static'
 def tri(self,a,b,c,mat='plastic',norm=None):
  a,b,c=map(lambda v:np.asarray(v,float),(a,b,c));n=np.cross(b-a,c-a);l=np.linalg.norm(n)
  if l<1e-11:return
  n=n/l if norm is None else np.asarray(norm)/np.linalg.norm(norm)
  light=np.array([-.28,.25,.927]);brightness=.65+.36*max(0,n@light)+.10*max(0,n[2]);shade=int(np.clip((brightness-.47)/.83*31,0,31))
  u,v=texels[(mat,shade)];self.v.extend([a,b,c]);self.roles.extend([self.role]*3)
  if mat in PHOTO_REGIONS and (mat=='folding_seat' or n[2]>.20):
   x0,y0,w,h=PHOTO_REGIONS[mat];points=np.asarray([a,b,c]);rx,ry=(.235,.226) if mat=='fabric' else (.212,.209)
   uu=np.clip(points[:,0]/(2*rx)+.5,0,1);vv=np.clip(.5-points[:,1]/(2*ry),0,1)
   self.uv.extend(np.c_[(x0+2+uu*(w-4))/TW,1-(y0+2+vv*(h-4))/TH])
  else:self.uv.extend([[u-.008,v-.008],[u+.008,v-.008],[u,v+.008]])
 def quad(self,a,b,c,d,mat='plastic',norm=None):self.tri(a,b,c,mat,norm);self.tri(a,c,d,mat,norm)
 def box(self,lo,hi,mat='plastic'):
  lo=np.asarray(lo);hi=np.asarray(hi);v=np.array([[x,y,z] for z in [lo[2],hi[2]] for y in [lo[1],hi[1]] for x in [lo[0],hi[0]]])
  for ids in [[0,2,3,1],[4,5,7,6],[0,1,5,4],[2,6,7,3],[0,4,6,2],[1,3,7,5]]:self.quad(*v[ids],mat)
 def tube(self,path,rad,mat='plastic',sides=16,closed=False,aspect=1):
  path=np.asarray(path,float);rings=[]
  for i,p in enumerate(path):
   tangent=path[(i+1)%len(path)]-path[(i-1)%len(path)] if closed else path[min(i+1,len(path)-1)]-path[max(0,i-1)]
   tangent/=np.linalg.norm(tangent);u=np.cross(tangent,[0,0,1])
   if np.linalg.norm(u)<.01:u=np.cross(tangent,[0,1,0])
   u/=np.linalg.norm(u);v=np.cross(tangent,u);rr=rad[i] if isinstance(rad,(list,np.ndarray)) else rad
   rings.append([p+rr*(u*np.cos(t)+v*np.sin(t)*aspect) for t in np.linspace(0,2*np.pi,sides,endpoint=False)])
  for i in range(len(path) if closed else len(path)-1):
   j=(i+1)%len(path)
   for k in range(sides):self.quad(rings[i][k],rings[i][(k+1)%sides],rings[j][(k+1)%sides],rings[j][k],mat)
  if not closed:
   for k in range(sides):self.tri(path[0],rings[0][(k+1)%sides],rings[0][k],mat);self.tri(path[-1],rings[-1][k],rings[-1][(k+1)%sides],mat)
 def cushion(self,c,sizes,mat='fabric',power=4):
  c=np.asarray(c);rx,ry,h=sizes;N=64;rings=[]
  for phi in np.linspace(-np.pi/2,np.pi/2,13):
   t=np.linspace(0,2*np.pi,N,endpoint=False);f=np.cos(phi)**.32
   rings.append(np.c_[np.sign(np.cos(t))*abs(np.cos(t))**(2/power)*rx*f,np.sign(np.sin(t))*abs(np.sin(t))**(2/power)*ry*f,np.full(N,h*np.sin(phi))]+c)
  for k in range(len(rings)-1):
   for j in range(N):self.quad(rings[k][j],rings[k][(j+1)%N],rings[k+1][(j+1)%N],rings[k+1][j],mat)
 def wheel(self,c,angle):
  c=np.asarray(c);axis=np.array([np.cos(angle),np.sin(angle),0]);self.tube([c-axis*.025,c+axis*.025],.030,'rubber',20);self.tube([c-axis*.027,c+axis*.027],.011,'plastic',16)
 def office(self):
  # Local front is +Y; five-star base, curved seat, adjustable arms, mesh back.
  self.role='chair_seat'
  self.cushion([0,0,.448],[.235,.226,.042],'fabric')
  self.cushion([0,0,.410],[.216,.206,.018],'plastic')
  self.role='chair_base'
  self.tube([[0,0,.132],[0,0,.382]],[.030,.035],'plastic',24)
  for j in range(5):
   a=j*2*np.pi/5+.25;d=np.array([np.cos(a),np.sin(a),0]);self.tube([d*.03+[0,0,.14],d*.17+[0,0,.104],d*.28+[0,0,.070]],[.027,.024,.019],'plastic',16,aspect=.57)
   # A vertical caster stem remains with the base as the tire rolls/swivels.
   self.tube([d*.282+[0,0,.052],d*.282+[0,0,.078]],.010,'plastic',16)
   self.role=f'chair_wheel_{j}';self.wheel(d*.282+[0,0,.032],a+.4);self.role='chair_base'
  self.role='chair_seat'
  for s in [-1,1]:
   self.tube([[s*.205,-.08,.425],[s*.252,-.08,.48],[s*.252,-.07,.648]],[.021,.020,.017],'plastic',16)
   self.cushion([s*.255,.014,.658],[.039,.122,.017],'plastic')
  def surf(x,z):return np.array([x,-.185-.095*(z-.54)+.27*x*x,z])
  # Width increases gently toward the top, as visible in frames 74/77/92.
  def width(z):return .166+.061*np.clip((z-.525)/.455,0,1)
  def inside(x,z):return abs(x)<width(z)*((max(0,1-abs((z-.76)/.235)**8))**.15)
  outline=[]
  for t in np.linspace(0,2*np.pi,120,endpoint=False):
   z=.762+.242*np.sign(np.sin(t))*abs(np.sin(t))**.35;x=width(z)*np.sign(np.cos(t))*abs(np.cos(t))**.5;outline.append(surf(x,z))
  self.tube(outline,.018,'plastic',16,True,1.15)
  # Real openings avoid an opaque black rectangle over the glass background.
  wire=.0017
  for z in np.arange(.535,.994,.009):
   xs=np.linspace(-width(z)+.004,width(z)-.004,30)
   for a,b in zip(xs[:-1],xs[1:]):
    if inside((a+b)/2,z):self.quad(surf(a,z-wire/2),surf(b,z-wire/2),surf(b,z+wire/2),surf(a,z+wire/2),'mesh',[0,1,.08])
  for x in np.arange(-.218,.22,.009):
   zs=np.linspace(.532,.995,52)
   for a,b in zip(zs[:-1],zs[1:]):
    if inside(x,(a+b)/2):self.quad(surf(x-wire/2,a),surf(x+wire/2,a),surf(x+wire/2,b),surf(x-wire/2,b),'mesh',[0,1,.08])
  # Central tapered support, visible through the mesh; approximate hidden rear.
  zs=np.linspace(.54,.99,20)
  for z0,z1 in zip(zs[:-1],zs[1:]):
   w0=.049-.017*(z0-.54)/.45;w1=.049-.017*(z1-.54)/.45
   self.quad(surf(-w0,z0)+[0,-.008,0],surf(w0,z0)+[0,-.008,0],surf(w1,z1)+[0,-.008,0],surf(-w1,z1)+[0,-.008,0],'plastic',[0,1,0])
  self.tube([[0,-.15,.366],[0,-.215,.44],[0,-.247,.66]],[.031,.030,.037],'plastic',20)
  self.tube([[.12,-.045,.38],[.242,-.045,.36]],.011,'plastic',12)
  self.role='static'
 def folding(self):
  # Source folding chair: thin pressed seat and continuous tubular X legs.
  for s in [-1,1]:
   self.tube([[s*.225,.275,.014],[s*.225,.11,.32],[s*.225,-.166,.72],[s*.225,-.295,.89]],.0115,'plastic',20)
   self.tube([[s*.193,-.284,.014],[s*.193,-.12,.28],[s*.193,.176,.461]],.0105,'plastic',20)
   self.tube([[s*.21,-.025,.386],[s*.21,-.025,.421]],.019,'plastic',18)
   for x,y in [(s*.225,.275),(s*.193,-.284)]:self.tube([[x,y,.014],[x,y,.03]],.014,'rubber',16)
  # Bent U brace lies below the seat and is clearly visible in source frame 82.
  path=[[-.225,.207,.134],[-.225,.231,.102],[-.20,.245,.09],[.20,.245,.09],[.225,.231,.102],[.225,.207,.134]]
  self.tube(path,.009,'plastic',16)
  self.tube([[-.20,-.177,.442],[.20,-.177,.442]],.008,'plastic',16)
  # Seat sheet, curved lateral edges with a slight pressed recess. Build paired
  # surfaces with continuous edge so it never looks like broken scan triangles.
  nx,ny=48,40
  def seat(x,y):
   # Round only the four sheet corners; keep the source's pressed side ridges.
   dx=max(0,abs(x)-.187);dy=max(0,abs(y)-.184);radius=np.hypot(dx,dy)
   if radius>.025:
    x=np.sign(x)*(.187+dx*.025/radius);y=np.sign(y)*(.184+dy*.025/radius)
   ridge=.014*np.exp(-((abs(x)-.17)/.025)**2);dish=-.006*(1-(x/.211)**2)*(1-(y/.209)**2)
   return np.array([x,y,.468+ridge+dish])
  xs=np.linspace(-.212,.212,nx);ys=np.linspace(-.209,.209,ny)
  for i in range(nx-1):
   for j in range(ny-1):
    a,b,c,d=seat(xs[i],ys[j]),seat(xs[i+1],ys[j]),seat(xs[i+1],ys[j+1]),seat(xs[i],ys[j+1])
    self.quad(a,b,c,d,'folding_seat');self.quad(d-[0,0,.007],c-[0,0,.007],b-[0,0,.007],a-[0,0,.007],'plastic')
  perimeter=[seat(x,-.209) for x in xs]+[seat(.212,y) for y in ys]+[seat(x,.209) for x in xs[::-1]]+[seat(-.212,y) for y in ys[::-1]]
  for a,b in zip(perimeter,perimeter[1:]+perimeter[:1]):self.quad(a,a-[0,0,.007],b-[0,0,.007],b,'plastic')
  # Backrest has a convex face and curved lower edge, not a rectangular cushion.
  nu,nv=48,30
  def back(u,v,offset=0):
   x=.215*u;top=.971-.045*abs(u)**5;bottom=.767+.040*(1-u*u)
   z=bottom*(1-v)+top*v;y=-.285-.11*(z-.72)+.075*u*u+offset
   return np.array([x,y,z])
  us=np.linspace(-1,1,nu);vs=np.linspace(0,1,nv)
  for i in range(nu-1):
   for j in range(nv-1):
    a,b,c,d=[back(u,v) for u,v in [(us[i],vs[j]),(us[i+1],vs[j]),(us[i+1],vs[j+1]),(us[i],vs[j+1])]]
    self.quad(a,b,c,d,'plastic',norm=[0,1,.1]);self.quad(d-[0,.014,0],c-[0,.014,0],b-[0,.014,0],a-[0,.014,0],'plastic',norm=[0,-1,0])
  perimeter=[back(u,0) for u in us]+[back(1,v) for v in vs]+[back(u,1) for u in us[::-1]]+[back(-1,v) for v in vs[::-1]]
  for a,b in zip(perimeter,perimeter[1:]+perimeter[:1]):self.quad(a,b,b-[0,.014,0],a-[0,.014,0],'plastic')
 def save(self,name,center=(0,0,0),yaw=0,size=(1,1,1),kind='fitted_furniture'):
  a=yaw;R=np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1]])
  xyz=(np.asarray(self.v)*size)@R.T+center
  path=P/f'furniture_{name}.npz';np.savez_compressed(path,xyz=xyz.astype('f4'),uv=np.asarray(self.uv,'f4'))
  return {'name':name,'geometry':path.name,'texture':'furniture_materials.jpg','triangles':len(xyz)//3,'kind':kind,'center':list(center),'yaw':yaw,'scale':list(size),'bounds':[xyz.min(0).tolist(),xyz.max(0).tolist()]}

def main():
 anchors_path=P/'furniture_anchors.json'
 anchors=json.loads(anchors_path.read_text()) if anchors_path.exists() else None
 groups=[];chair_static=[];wheel_metadata=[]
 for name in ['office_chair','folding_chair']:
  b=Builder();b.office() if name=='office_chair' else b.folding()
  if anchors:
   a=anchors[name]
   # Placement comes from furniture_anchors.json; the stool includes a
   # 25 mm leftward clearance allowance for its outside tubular supports.
   if 'z_profile' in a:
    profile=np.asarray(a['z_profile']);v=np.asarray(b.v);v[:,2]=np.interp(v[:,2],profile[:,0],profile[:,1]);b.v=list(v)
   combined=b.save(name,a['center'],a['yaw'],a.get('scale',[1,1,1]));chair_static.append(combined)
   if name=='office_chair':
    for role,suffix in [('chair_base','base'),('chair_seat','seat')]:
     mask=np.asarray(b.roles)==role;part=Builder();part.v=list(np.asarray(b.v)[mask]);part.uv=list(np.asarray(b.uv)[mask]);part.roles=list(np.asarray(b.roles)[mask])
     group=part.save(name+'_'+suffix,a['center'],a['yaw'],a.get('scale',[1,1,1]),kind='fitted_chair');group.update(motionRole=role,pivot=a['center'],seatPivot=[a['center'][0],a['center'][1],.515]);groups.append(group)
    # Wheel geometry is regenerated directly in world coordinates: circular
    # cross sections and a fixed floor clearance avoid bobbing from the general
    # chair's anisotropic fit and vertical profile remapping.
    yaw=a['yaw'];Rz=np.array([[np.cos(yaw),-np.sin(yaw),0],[np.sin(yaw),np.cos(yaw),0],[0,0,1]]);sizes=np.asarray(a.get('scale',[1,1,1]));root=np.asarray(a['center'])
    for j in range(5):
     theta=j*2*np.pi/5+.25;direction=np.array([np.cos(theta),np.sin(theta),0]);center=root+(direction*.282*sizes)@Rz.T;center[:2]=root[:2]+.990*(center[:2]-root[:2]);center[2]=.034
     axis=np.array([2**-.5,-2**-.5,0]) # Axles perpendicular to scripted rollout; allows no-slip straight rolling.
     wheel=Builder();wheel.tube([center-axis*.021,center+axis*.021],.032,'rubber',32);wheel.tube([center-axis*.023,center+axis*.023],.0105,'plastic',24)
     g=wheel.save(f'office_chair_wheel_{j}',kind='fitted_chair');g.update(motionRole='chair_wheel',pivot=center.tolist(),wheelAxis=axis.tolist(),wheelRadius=.032);groups.append(g)
     wheel_metadata.append({'name':g['name'],'pivot':center.tolist(),'axis':axis.tolist(),'radius':.032,'contact':[float(center[0]),float(center[1]),.002]})
    # Keep a static combined chair for older comparison/export callers, but it
    # is deliberately absent from the live render groups to prevent duplication.
    office_groups=[g for g in groups if g['name'].startswith('office_chair_')];parts=[np.load(P/g['geometry']) for g in office_groups];combined_xyz=np.concatenate([g['xyz'] for g in parts]);combined_uv=np.concatenate([g['uv'] for g in parts]);np.savez_compressed(P/'furniture_office_chair.npz',xyz=combined_xyz,uv=combined_uv);combined['triangles']=len(combined_xyz)//3;combined['bounds']=[combined_xyz.min(0).tolist(),combined_xyz.max(0).tolist()]
   else:groups.append(combined)
  else:b.save(name+'_local')
 if not anchors:
  print('Local chair meshes ready; furniture_anchors.json required for calibrated placement.');return
 corners=np.asarray(anchors['table']['corners']);floor=float(anchors.get('floor_z',0));table=Builder()
 for i in range(4):
  j=(i+1)%4;table.quad(corners[i],corners[j],corners[j]-[0,0,.025],corners[i]-[0,0,.025],'table_edge')
 table.quad(*(corners-[0,0,.025]),'table_leg');leg_bounds=[]
 for i,p in enumerate(corners):
  inward=corners.mean(0)-p;inward/=np.linalg.norm(inward);c=p+inward*.064;lo=c+[-.023,-.023,0];hi=c+[.023,.023,0];lo[2]=floor+.002;hi[2]=p[2]-.026;table.box(lo,hi,'table_leg');leg_bounds.append({'min':(lo-.02).tolist(),'max':(hi+.02).tolist(),'name':'desk_leg_'+str(i)})
 for i,v in enumerate(table.v):
  if abs(v[2]-corners[0,2])<1e-7:
   v=v.copy();v[2]-=.0008;table.v[i]=v
 groups.append(table.save('desk_support',kind='fitted_table_support'))
 # Partition framing is anchored to the reconstructed envelope. The single
 # intermediate side post is independently ray-fit from three registered views.
 L=json.loads((P/'surface_layout.json').read_text());W=L['room']['width'];DEP=L['room']['depth'];GH=L['room']['glass_height']
 frame=Builder()
 for y in [0,-.815,-DEP]:frame.box([W-.026,y-.027,0],[W+.008,y+.027,GH+.038],'frame')
 frame.box([W-.027,-DEP-.025,GH-.031],[W+.01,.025,GH+.038],'frame')
 frame.box([W-.028,-DEP,.001],[W+.013,0,.048],'frame')
 for x in [0,W]:frame.box([x-.028,-DEP-.014,0],[x+.028,-DEP+.027,GH+.038],'frame')
 frame.box([0,-DEP-.014,GH-.031],[W,-DEP+.027,GH+.038],'frame')
 frame.box([0,-DEP-.014,.001],[W,-DEP+.032,.048],'frame')
 # Door's inset rectangular leaf: only one vertical edge is visible in source,
 # so use the captured perimeter rather than duplicating reflected bars.
 frame.box([.073,-DEP+.017,.059],[.099,-DEP+.033,GH-.090],'frame')
 frame.box([.073,-DEP+.017,GH-.115],[W-.073,-DEP+.033,GH-.086],'frame')
 frame.box([W-.099,-DEP+.017,.059],[W-.073,-DEP+.033,GH-.090],'frame')
 frame.box([.073,-DEP+.017,.059],[W-.073,-DEP+.034,.089],'frame')
 groups.append(frame.save('glass_frame',kind='fitted_frame'))
 skirting=Builder();skirting.box([.002,-DEP,.003],[.018,-.005,.066],'baseboard');skirting.box([.003,-.016,.003],[W-.02,.001,.066],'baseboard')
 groups.append(skirting.save('baseboard',kind='fitted_frame'))
 exclusions=[]
 for g in chair_static:
  lo,hi=np.asarray(g['bounds']);lo-=np.array([.07,.07,.01]);hi+=np.array([.07,.07,.06]);exclusions.append({'name':g['name'],'min':lo.tolist(),'max':hi.tolist()})
 report={'method':'Calibrated source-informed regularized furniture models','inferred_geometry':True,'metric_scale_known':False,'groups':groups,'static_compatibility':chair_static,'material_reference':'furniture_material_reference.json','support_exclusion_volumes':leg_bounds,'exclusion_volumes':exclusions,'sources':['frame_0034.jpg','frame_0036.jpg','frame_0074.jpg','frame_0077.jpg','frame_0079.jpg','frame_0082.jpg','frame_0092.jpg'],'fit':anchors,'frame_fit':{'side_post_y':-.815,'ray_samples':{'frame_0034':{'pixel':[362,400],'y':-.8024},'frame_0036':{'pixel':[381,300],'y':-.8196},'frame_0038':{'pixel':[458,450],'y':-.8219}},'method':'Camera rays intersect fitted glass X plane; end framing follows room envelope','door_leaf':'Regularized rectangle; dimensions approximate'},'limitations':['Chairs are complete fitted approximations, not exact recovered meshes.','Hidden components and chair dimensions are regularized from their visible silhouettes.','The mesh back has geometric openings; its individual threads are approximated.','Chair rolling and swiveling are presentation animation; no dynamics or collision validation is claimed.']}
 # Export moving-part contract. Geometry is world-space; transforms belong to
 # the viewer. Circular tires retain constant floor contact during spin.
 wheels=[{'center':w['contact'],'radius':w['radius']} for w in wheel_metadata]
 base=next(g for g in groups if g['name']=='office_chair_base');seat=next(g for g in groups if g['name']=='office_chair_seat');pivot=anchors['office_chair']['center']
 motion={'pivot':pivot,'seatPivot':[pivot[0],pivot[1],.515],'offset':[-.30,-.30,0],'duration':9,'seatYaw':.45,'groups':{'base':['office_chair_base'],'seat':['office_chair_seat'],'wheels':[w['name'] for w in wheel_metadata]},'baseBounds':base['bounds'],'seatBounds':seat['bounds'],'bounds':next(g for g in chair_static if g['name']=='office_chair')['bounds'],'wheelContacts':wheels,'wheels':wheel_metadata,'motion_type':'Scripted visual rolling and swiveling; no rigid-body physics claim','source_geometry':'Source-informed fitted approximation, scale estimated; caster axle alignment regularized for scripted straight rolling'}
 motion['wheelProfile']={'method':'rolling_distance_over_radius','axes_aligned_to_motion':True}
 motion['profile']={'easing':'quintic_smootherstep','travel':[[0,0],[.32,1],[.72,1],[1,0]],'swivel':[[0,0],[.30,0],[.48,1],[.58,1],[.72,0],[1,0]]}
 def profile_at(keys,t):
  for (a,va),(b,vb) in zip(keys,keys[1:]):
   if t<=b:
    u=np.clip((t-a)/(b-a),0,1);q=6*u**5-15*u**4+10*u**3;return va+(vb-va)*q
  return keys[-1][1]
 # Conservative swept geometry bounds are a navigation aid only, not contact
 # simulation. They include both rolling base and independently swiveling top.
 base_xyz=np.concatenate([np.load(P/g['geometry'])['xyz'] for g in groups if g.get('motionRole') in ['chair_base','chair_wheel']]);motion['baseBounds']=[base_xyz.min(0).tolist(),base_xyz.max(0).tolist()];seat_xyz=np.load(P/seat['geometry'])['xyz'];seat_pivot=np.asarray(motion['seatPivot']);swept_min=np.full(3,np.inf);swept_max=np.full(3,-np.inf)
 for tt in np.linspace(0,1,101):
  shift=np.asarray(motion['offset'])*profile_at(motion['profile']['travel'],tt);angle=motion['seatYaw']*profile_at(motion['profile']['swivel'],tt);Rz=np.array([[np.cos(angle),-np.sin(angle),0],[np.sin(angle),np.cos(angle),0],[0,0,1]])
  transformed=[base_xyz+shift,(seat_xyz-seat_pivot)@Rz.T+seat_pivot+shift]
  for xyz in transformed:swept_min=np.minimum(swept_min,xyz.min(0));swept_max=np.maximum(swept_max,xyz.max(0))
 motion['collisionEnvelope']={'min':swept_min.tolist(),'max':swept_max.tolist(),'purpose':'Conservative navigation exclusion during scripted chair motion; not physics validation'}
 (P/'chair_motion.json').write_text(json.dumps(motion,indent=2));report['chair_motion']='chair_motion.json'
 (P/'furniture.json').write_text(json.dumps(report,indent=2));print(json.dumps({'groups':[(x['name'],x['triangles']) for x in groups],'triangles':sum(x['triangles'] for x in groups)},indent=2))
if __name__=='__main__':main()
