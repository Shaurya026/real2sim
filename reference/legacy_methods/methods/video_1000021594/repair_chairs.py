"""Source-informed fitted replacement chairs; all geometry is an explicit approximation.

The calibrated room provides positions and scale; silhouettes in frames 40, 50,
100, 110 and 120 constrain the two office chairs. Hidden parts are regularized
using their visible five-star bases, fabric seats, armrests and mesh backs.
No claim of recovered per-object geometry or measured dimensions is made.
"""
from room2sim_paths import project_path, input_path, browser_path, openmvs_path, ffmpeg_path
from pathlib import Path
import json, math
import numpy as np
from PIL import Image, ImageDraw
P=Path(__file__).resolve().parent
MATS={'plastic':(35,39,40),'rubber':(20,23,24),'fabric':(29,33,35),'mesh':(47,51,52),'metal':(118,124,126),'orange':(166,79,46),'table_edge':(211,212,209),'table_leg':(156,166,170)}
# The source colors are sampled to keep replacement appearance in the capture's palette.
source50=np.array(Image.open(P/'images/frame_0050.jpg'))
source100=np.array(Image.open(P/'images/frame_0100.jpg'))
source40=np.array(Image.open(P/'images/frame_0040.jpg'))
MATS['orange']=tuple(np.median(source50[1190:1240,550:660].reshape(-1,3),0).astype(int))
# Baked gentle lighting is required by the room's intentionally unlit photo renderer.
TW,TH=1536,1536;cell=48;atlas=Image.new('RGB',(TW,TH));draw=ImageDraw.Draw(atlas)
texels={};mi=0;rng=np.random.default_rng(20261010)
for material,color in MATS.items():
 for shade in range(24):
  x=(mi%32)*cell;y=(mi//32)*cell;factor=.52+shade/23*.72
  block=np.empty((cell,cell,3));block[:]=np.array(color)*factor
  noise=rng.normal(0,.48,(cell,cell,1));block+=noise
  yy,xx=np.mgrid[:cell,:cell]
  if material in ['fabric','orange']:block+=((xx%3==0)|(yy%4==0))[:,:,None]*1.8
  if material=='mesh':block+=(((xx%4)<2)&((yy%4)<2))[:,:,None]*11-4
  atlas.paste(Image.fromarray(block.clip(0,255).astype('u1')),(x,y));texels[(material,shade)]=((x+cell/2)/TW,1-(y+cell/2)/TH);mi+=1
atlas.save(P/'chair_materials.jpg',quality=98,subsampling=0)

class Builder:
 def __init__(self):self.v=[];self.uv=[];self.roles=[];self.role='static'
 def tri(self,a,b,c,mat='plastic',norm=None,shade=None):
  a,b,c=map(lambda v:np.asarray(v,float),(a,b,c));n=np.cross(b-a,c-a);l=np.linalg.norm(n)
  if l<1e-10:return
  n=n/l if norm is None else np.asarray(norm)/np.linalg.norm(norm)
  brightness=.55+.30*max(0,n@np.array([-.28,.2,.938]))+.15*max(0,n[2])
  si=int(np.clip((brightness-.52)/.72*23,0,23)) if shade is None else int(shade)
  u,v=texels[(mat,si)];self.v.extend([a,b,c]);self.roles.extend([self.role]*3);self.uv.extend([[u-.009,v-.009],[u+.009,v-.009],[u,v+.009]])
 def quad(self,a,b,c,d,mat='plastic',norm=None,shade=None):self.tri(a,b,c,mat,norm,shade);self.tri(a,c,d,mat,norm,shade)
 def box(self,lo,hi,mat):
  lo=np.array(lo);hi=np.array(hi);v=np.array([[x,y,z] for z in [lo[2],hi[2]] for y in [lo[1],hi[1]] for x in [lo[0],hi[0]]])
  for ids in [[0,2,3,1],[4,5,7,6],[0,1,5,4],[2,6,7,3],[0,4,6,2],[1,3,7,5]]:self.quad(*v[ids],mat)
 def tube(self,path,rad,mat='plastic',sides=12,closed=False,aspect=1):
  path=np.array(path,float);rings=[]
  for i,p in enumerate(path):
   tangent=path[(i+1)%len(path)]-path[(i-1)%len(path)] if closed else path[min(i+1,len(path)-1)]-path[max(0,i-1)]
   tangent/=np.linalg.norm(tangent);u=np.cross(tangent,[0,0,1])
   if np.linalg.norm(u)<.01:u=np.cross(tangent,[0,1,0])
   u/=np.linalg.norm(u);v=np.cross(tangent,u);rr=rad[i] if isinstance(rad,(list,np.ndarray)) else rad
   rings.append([p+rr*(u*math.cos(t)+v*math.sin(t)*aspect) for t in np.linspace(0,2*np.pi,sides,endpoint=False)])
  for i in range(len(path) if closed else len(path)-1):
   j=(i+1)%len(path)
   for k in range(sides):self.quad(rings[i][k],rings[i][(k+1)%sides],rings[j][(k+1)%sides],rings[j][k],mat)
  if not closed:
   for k in range(sides):self.tri(path[0],rings[0][(k+1)%sides],rings[0][k],mat);self.tri(path[-1],rings[-1][k],rings[-1][(k+1)%sides],mat)
 def cushion(self,c,sizes,mat='fabric',power=4):
  c=np.array(c);rx,ry,h=sizes;N=72;rings=[]
  for phi in np.linspace(-np.pi/2,np.pi/2,13):
   # Rounded box/cushion profile with a broad, gently domed top.
   t=np.linspace(0,2*np.pi,N,endpoint=False);f=np.cos(phi)**.32
   xx=np.sign(np.cos(t))*abs(np.cos(t))**(2/power)*rx*f
   yy=np.sign(np.sin(t))*abs(np.sin(t))**(2/power)*ry*f
   rings.append(np.c_[xx,yy,np.full(N,h*np.sin(phi))]+c)
  for k in range(len(rings)-1):
   for j in range(N):self.quad(rings[k][j],rings[k][(j+1)%N],rings[k+1][(j+1)%N],rings[k+1][j],mat)
 def wheel(self,c,angle):
  c=np.array(c);axis=np.array([math.cos(angle),math.sin(angle),0]);self.tube([c-axis*.026,c+axis*.026],.034,'rubber',18)
  self.tube([c-axis*.028,c+axis*.028],.013,'plastic',16)
 def back(self,orange=False):
  # Local front is +Y. Curved mesh frame approximately follows the real chair silhouette.
  def surface(x,z):return np.array([x,-.215-.10*(z-.54)+.28*x*x,z])
  ts=np.linspace(0,2*np.pi,112,endpoint=False);outline=[]
  for t in ts:
   x=.218*np.sign(np.cos(t))*abs(np.cos(t))**.5
   z=.785+.245*np.sign(np.sin(t))*abs(np.sin(t))**.5
   outline.append(surface(x,z))
  self.tube(outline,.019 if not orange else .025,'plastic' if not orange else 'orange',12,True,1.10)
  # Smooth inset, closed front/rear skins; mesh appearance is sampled, unseen detail inferred.
  from scipy.spatial import Delaunay
  xz=np.array([[p[0],p[2]] for p in outline])
  interior=[]
  for z in np.linspace(.548,1.022,35):
   for x in np.linspace(-.21,.21,35):
    if (abs(x/.218)**4+abs((z-.785)/.245)**4)<.95:interior.append([x,z])
  xz=np.vstack([xz,np.array(interior)]);vertices=np.array([surface(x,z) for x,z in xz]);triangles=Delaunay(xz).simplices
  for ids in triangles:self.tri(*vertices[ids],'orange' if orange else 'mesh',norm=[0,1,.08])
  # Lumbar support and the rear support stem are visible in the low angle source.
  if not orange:
   path=[surface(x,.655)+[0,-.020,0] for x in np.linspace(-.20,.20,30)]
   self.tube(path,.035,'plastic',12,False,.7)
   self.tube([[0,-.16,.37],[0,-.225,.46],[0,-.262,.62]], [.035,.033,.029],'plastic',16)
   self.tube([surface(-.17,.553),surface(.17,.553)],.025,'metal',16)
  else:self.tube([[0,-.12,.35],[0,-.24,.56]],.022,'metal',16)
 def office(self,orange=False):
  self.role='chair_seat'
  self.cushion([0,0,.445],[.232,.225,.042],'orange' if orange else 'fabric')
  self.cushion([0,0,.407],[.216,.204,.017],'plastic')
  self.role='chair_base'
  self.tube([[0,0,.14],[0,0,.382]], [.031,.036],'plastic',24)
  self.tube([[0,0,.21],[0,0,.368]],.020,'metal',24)
  for j in range(5):
   a=2*np.pi*j/5+.2;direction=np.array([np.cos(a),np.sin(a),0]);path=[np.array([0,0,.15])+direction*.035,np.array([0,0,.115])+direction*.16,np.array([0,0,.082])+direction*.29]
   self.tube(path,[.029,.026,.020],'plastic',12,False,.64);self.role=f'chair_wheel_{j}';self.wheel(direction*.30+[0,0,.015],a+np.pi/2);self.role='chair_base'
  self.role='chair_seat'
  for sign in [-1,1]:
   self.tube([[sign*.204,-.08,.425],[sign*.253,-.09,.47],[sign*.259,-.075,.652]], [.017,.018,.019],'plastic',12)
   self.cushion([sign*.256,.015,.666],[.033,.158,.019],'plastic')
  self.back(orange)
  # Small tilt knob and height lever distinguish the source's real chair hardware.
  self.tube([[.14,-.04,.381],[.244,-.04,.365]],.012,'plastic',12)
  self.tube([[-.10,-.10,.385],[-.10,-.16,.366]],.026,'plastic',16)
  self.role='static'
 def save(self,name,center,angle):
  xyz=np.array(self.v);a=angle;R=np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1]]);xyz=xyz@R.T+center
  np.savez_compressed(P/f'chair_{name}.npz',xyz=xyz.astype('f4'),uv=np.array(self.uv,'f4'))
  return {'name':name,'geometry':f'chair_{name}.npz','texture':'chair_materials.jpg','triangles':len(xyz)//3,'kind':'fitted_chair','center':list(center),'yaw':angle,'bounds':[xyz.min(0).tolist(),xyz.max(0).tolist()]}

def main():
 chairs=[]
 # The blue-wall chair faces the table (-X). The glass-wall chair faces +X.
 for name,center,angle,orange in [('blue_wall',[.36,-.79,-.02],np.pi/2,False),('glass_wall',[-.81,-.70,-.02],-np.pi/2,False),('orange_front',[-.015,-1.52,-.02],0,True)]:
  b=Builder();b.office(orange);chairs.append(b.save(name,center,angle))
 # White laminate thickness and metal table support follow the visible under-table frame.
 table=Builder();corners=np.array([[-.73,.31,.75],[.27,.31,.75],[.34,-1.28,.75],[-.66,-1.28,.75]])
 for i in range(4):
  j=(i+1)%4;table.quad(corners[i],corners[j],corners[j]-[0,0,.024],corners[i]-[0,0,.024],'table_edge')
 table.quad(*(corners-[0,0,.024]),'table_leg')
 leg_bounds=[]
 for i,point in enumerate(corners):
  toward=corners.mean(0)-point;toward/=np.linalg.norm(toward);center=point+toward*.095;lo=center+[-.023,-.023,0];hi=center+[.023,.023,0];lo[2]=-.04;hi[2]=.723;table.box(lo,hi,'table_leg');leg_bounds.append({'min':(lo-.015).tolist(),'max':(hi+.015).tolist(),'name':'table_leg_'+str(i)})
 # The four legs and continuous underside are sufficient here. In the browser's
 # capture renderer, extra hidden apron rails caused thin raster artifacts through
 # the broad tabletop even though their vertices are below it; omit those inferred rails.
 # Recess the vertical edge's upper rim very slightly beneath the separately owned
 # tabletop. This avoids subpixel shared-edge flicker without adding a duplicate top.
 for i,vertex in enumerate(table.v):
  if abs(vertex[2]-.75)<1e-6:
   vertex=vertex.copy();toward=corners.mean(0)[:2]-vertex[:2];toward/=np.linalg.norm(toward);vertex[:2]+=toward*.0006;vertex[2]-=.0006;table.v[i]=vertex
 support=table.save('table_support',[0,0,0],0);support['kind']='fitted_table_support'
 # Volumes are separated by height to preserve the adjacent tabletop and packages.
 volumes=[
  {'name':'blue_wall_chair','min':[.29,-1.20,.04],'max':[.90,-.35,1.09]},
  {'name':'blue_wall_chair_under_table','min':[-.01,-1.17,.01],'max':[.88,-.36,.58]},
  {'name':'glass_wall_chair','min':[-1.31,-1.13,.025],'max':[-.70,-.27,1.06]},
  {'name':'glass_wall_chair_under_table','min':[-1.28,-1.15,.01],'max':[-.46,-.26,.58]},
  {'name':'orange_chair','min':[-.39,-1.94,.0],'max':[.40,-1.30,1.08]},
  {'name':'orange_under_table','min':[-.39,-1.66,.0],'max':[.40,-1.09,.56]},
 ]
 report={'method':'Source-informed fitted curved office-chair models replacing unstable dark/thin scan fragments','inferred_geometry':True,'metric_scale_known':False,'sources':['frame_0040.jpg','frame_0050.jpg','frame_0100.jpg','frame_0110.jpg','frame_0120.jpg','frame_0150.jpg'],'fit_evidence':{'blue_wall_back_top_world_approx':[.52,-.98,1.02],'glass_wall_back_top_raycast_world':[-1.051,-.783,.957],'orange':'Partially visible cushion/back; placement and hidden structure regularized from room layout, lower confidence'},'parts':['rounded fabric cushion','curved mesh insert and continuous back frame','lumbar support','armrests','gas lift','five-star rolling base','casters'],'groups':chairs,'furniture_supports':[support],'support_exclusion_volumes':leg_bounds,'exclusion_volumes':volumes,'limitations':['Chair surfaces are fitted approximations, not recovered exact meshes.','The orange chair is only partly seen, so its hidden geometry and placement are especially uncertain.','Mesh fabric is visually represented by sampled/patterned material, without individual fabric holes.','Chairs are static visual geometry, not articulated or validated collision assets.']}
 (P/'chair_repair.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':main()
