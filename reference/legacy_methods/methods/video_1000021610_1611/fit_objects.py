"""Photograph-textured pantry object proxies, with explicitly inferred hidden faces.

Local objects have +Z up, +X right, front toward -Y. Object anchors (base center,
yaw, optional full size) are supplied by calibrated room fitting. No new image
generation is used: recognizable labels and front panels come from the videos.
"""
from room2sim_paths import project_path, input_path, browser_path, openmvs_path, ffmpeg_path
from pathlib import Path
import json, math, sys
import numpy as np
from PIL import Image, ImageDraw

import cv2

P = Path(__file__).resolve().parent
ATLAS = 2560
atlas = Image.new('RGB', (ATLAS, ATLAS), (70, 70, 68))
patches = {}; evidence = []
COLORS = {'black':(32,34,34),'metal':(82,85,84),'silver':(151,155,153),
          'cardboard':(149,125,91),'cardboard_dark':(115,95,69),
          'white':(208,211,204),'foam':(205,208,196),'blue':(35,65,116),
          'cap':(48,59,120),'glass':(155,164,158),'red':(147,35,36),
          'wood':(179,156,112),'paper':(222,222,208),'water':(80,95,96)}

def photo(name, file, quad, slot, tone=None):
    source_path=P/file if '/' in file else P/'diagnostics'/file
    source = np.asarray(Image.open(source_path))
    x,y,size=slot if isinstance(slot,tuple) else ((slot%4)*512,(slot//4)*512,508)
    H = cv2.getPerspectiveTransform(np.asarray(quad,'f4'),np.asarray([[0,0],[size-1,0],[size-1,size-1],[0,size-1]],'f4'))
    patch = cv2.warpPerspective(source,H,(size,size),flags=cv2.INTER_CUBIC)
    if tone is not None:
        med=np.median(patch.reshape(-1,3),axis=0); patch=np.clip(patch.astype(float)*np.array(tone)/np.maximum(med,1),0,255).astype('u1')
    padded=np.pad(patch,((2,2),(2,2),(0,0)),mode='edge')
    atlas.paste(Image.fromarray(padded),(x,y));patches[name]=(x+2,y+2,size,size)
    evidence.append({'name':name,'source':str(source_path.relative_to(P)),'source_quad':quad,'operation':'Planar rectification of an observed material or object face.'})

def uvtex(name, uv):
    x,y,w,h=patches[name]; a=np.asarray(uv,float)
    return np.c_[(x+1+a[:,0]*(w-2))/ATLAS,1-(y+1+(1-a[:,1])*(h-2))/ATLAS]

def make_atlas():
    # All image corner orders are top-left, top-right, bottom-right, bottom-left.
    photo('coffee_front','images/1000021610_0110.jpg',[[165,549],[690,560],[634,1196],[184,1196]],0)
    photo('coffee_side','object_1610_24.6.jpg',[[343,351],[399,326],[399,451],[338,481]],1)
    photo('cooler_lid','object_1611_28.0.jpg',[[10,399],[492,400],[719,593],[57,651]],2)
    photo('cooler_front','object_1611_28.0.jpg',[[42,970],[719,880],[719,1168],[82,1268]],3)
    photo('carton_front','packet_44.jpg',[[0,971],[718,947],[718,1278],[0,1278]],4)
    photo('cardboard','packet_42.jpg',[[90,140],[605,156],[611,442],[77,435]],5)
    photo('packet_front','packet_42.jpg',[[333,470],[485,567],[291,829],[171,682]],6)
    photo('dispenser_front','images/1000021610_0106.jpg',[[188,279],[395,322],[347,1003],[157,994]],7)
    photo('bottle_cover','object_1610_133.7.jpg',[[34,442],[221,441],[230,752],[41,775]],8)
    photo('table_wood','object_1610_133.7.jpg',[[277,577],[520,579],[701,672],[460,667]],9)
    photo('table_dark','object_1611_51.0.jpg',[[188,977],[580,989],[655,1229],[127,1228]],10)
    photo('supplies_front','object_1611_51.0.jpg',[[439,752],[565,762],[567,811],[438,805]],11)
    photo('bottle_label','object_1610_133.7.jpg',[[282,513],[303,513],[303,540],[281,541]],12)
    photo('foam_side','object_1611_28.0.jpg',[[183,1006],[576,977],[622,1183],[197,1221]],13)
    photo('cola_label','object_1611_32.6.jpg',[[303,577],[358,550],[424,646],[363,670]],(1024,1792,252))
    photo('dispenser_side','images/1000021610_0106.jpg',[[56,297],[186,279],[155,994],[61,964]],(1280,1792,252))
    photo('floor_bingo','images/1000021610_0010.jpg',[[117,626],[310,638],[301,846],[92,844]],(1536,1792,252))
    photo('floor_parle','images/1000021610_0010.jpg',[[145,477],[314,480],[312,624],[142,618]],(1792,1792,252))
    photo('jug_plastic','object_1610_129.jpg',[[421,866],[667,865],[709,1274],[397,1274]],(2048,0,508))
    photo('water_bottle_body','images/1000021610_0133.jpg',[[521,312],[546,313],[550,397],[518,402]],(2048,512,508))
    # Small sampled-color patches carry smooth directional shading on inferred
    # sides. They deliberately do not invent unseen brand text or photographs.
    yy,xx=np.mgrid[:24,:24];rng=np.random.default_rng(1611)
    for i,(name,color) in enumerate(COLORS.items()):
        for j in range(24):
            idx=i*24+j;x=1024+(idx%42)*24;y=1536+(idx//42)*24
            a=np.broadcast_to(np.array(color)*(.55+j*.032),(24,24,3)).copy()
            a+=rng.normal(0,.7,(24,24,1))
            atlas.paste(Image.fromarray(np.clip(a,0,255).astype('u1')),(x,y))
            patches[f'{name}_{j}']=(x+2,y+2,20,20)
    atlas.save(P/'object_materials.jpg',quality=96,subsampling=0)
    (P/'object_material_reference.json').write_text(json.dumps({'materials':evidence,'hidden_surfaces':'Closed fitted geometry with source-sampled colors or neighboring photographed material; no recovered metric dimensions. Snack back and foil shape are inferred.'},indent=2))

class Mesh:
    def __init__(self): self.v=[];self.uv=[]
    def tri(self,a,b,c,mat='black',uv=None):
        v=np.asarray([a,b,c],float); n=np.cross(v[1]-v[0],v[2]-v[0]);l=np.linalg.norm(n)
        if l<1e-12:return
        if uv is None:
            light=np.array([-.22,-.34,.914]);shade=int(np.clip((.73+.34*max(0,(n/l)@light)-.55)/.032,0,23));mat=f'{mat}_{shade}';uv=[[.35,.35],[.65,.35],[.5,.65]]
        self.v.extend(v);self.uv.extend(uvtex(mat,uv))
    def quad(self,a,b,c,d,mat='black',uv=None):
        if uv is None:self.tri(a,b,c,mat);self.tri(a,c,d,mat)
        else:self.tri(a,b,c,mat,[uv[i] for i in [0,1,2]]);self.tri(a,c,d,mat,[uv[i] for i in [0,2,3]])
    def panel(self,a,b,c,d,texture): self.quad(a,b,c,d,texture,[[0,0],[1,0],[1,1],[0,1]])
    def box(self,lo,hi,mat='black',front=None,top=None):
        x0,y0,z0=lo;x1,y1,z1=hi
        self.quad([x0,y0,z0],[x0,y1,z0],[x1,y1,z0],[x1,y0,z0],mat)
        if top:self.panel([x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1],top)
        else:self.quad([x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1],mat)
        if front:self.panel([x0,y0,z0],[x1,y0,z0],[x1,y0,z1],[x0,y0,z1],front)
        else:self.quad([x0,y0,z0],[x1,y0,z0],[x1,y0,z1],[x0,y0,z1],mat)
        self.quad([x1,y1,z0],[x0,y1,z0],[x0,y1,z1],[x1,y1,z1],mat)
        self.quad([x0,y1,z0],[x0,y0,z0],[x0,y0,z1],[x0,y1,z1],mat)
        self.quad([x1,y0,z0],[x1,y1,z0],[x1,y1,z1],[x1,y0,z1],mat)
    def lathe(self,profile,mat='black',center=(0,0,0),sides=48,texture=None,full=False):
        center=np.asarray(center);rings=[]
        for z,r in profile:
            a=np.linspace(-math.pi/2,3*math.pi/2,sides,endpoint=False)
            rings.append(np.c_[r*np.cos(a),r*np.sin(a),np.full(sides,z)]+center)
        zmin,zmax=profile[0][0],profile[-1][0]
        for i in range(len(rings)-1):
            for j in range(sides):
                k=(j+1)%sides
                if texture and (full or j<12 or j>=36):
                    u0=j/sides if full else ((j+12)%sides)/24;u1=(j+1)/sides if full else ((j+13)%sides)/24
                    v0=(profile[i][0]-zmin)/(zmax-zmin);v1=(profile[i+1][0]-zmin)/(zmax-zmin)
                    self.quad(rings[i][j],rings[i][k],rings[i+1][k],rings[i+1][j],texture,[[u0,v0],[u1,v0],[u1,v1],[u0,v1]])
                else:self.quad(rings[i][j],rings[i][k],rings[i+1][k],rings[i+1][j],mat)
        for j in range(sides):
            k=(j+1)%sides
            self.tri(center+[0,0,zmin],rings[0][k],rings[0][j],mat)
            self.tri(center+[0,0,zmax],rings[-1][j],rings[-1][k],mat)
    def tube(self,a,b,r,mat='metal',sides=12):
        a,b=np.asarray(a),np.asarray(b);d=b-a;d/=np.linalg.norm(d);u=np.cross(d,[0,0,1.]);
        if np.linalg.norm(u)<.01:u=np.cross(d,[0,1.,0])
        u/=np.linalg.norm(u);v=np.cross(d,u);q=np.linspace(0,2*math.pi,sides,endpoint=False)
        ring=[r*(np.cos(t)*u+np.sin(t)*v) for t in q]
        for j in range(sides):k=(j+1)%sides;self.quad(a+ring[j],a+ring[k],b+ring[k],b+ring[j],mat);self.tri(a,a+ring[k],a+ring[j],mat);self.tri(b,b+ring[j],b+ring[k],mat)
    def save(self,name,anchor,nominal):
        xyz=np.asarray(self.v,float); scale=np.asarray(anchor.get('size',nominal))/nominal
        a=anchor.get('yaw',0);R=np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1.]])
        xyz=(xyz*scale)@R.T+anchor['center']; file=f'object_{name}.npz'
        np.savez_compressed(P/file,xyz=xyz.astype('f4'),uv=np.asarray(self.uv,'f4'))
        out={'name':name,'geometry':file,'texture':'object_materials.jpg','triangles':len(xyz)//3,'kind':'fitted_object','bounds':[xyz.min(0).tolist(),xyz.max(0).tolist()],'center':anchor['center'],'yaw':a,'nominalSize':list(nominal),'source':'Observed video object; fitted complete geometry; hidden sides inferred.'}
        if name=='snack_packet':out.update(kind='interactive_object',pivot=(np.array(anchor['center'])+np.array([0,0,nominal[2]*.5])*scale).tolist())
        return out

def table(w,d,h,wood=False):
    m=Mesh();m.box([-w/2,-d/2,h-.036],[w/2,d/2,h],'wood' if wood else 'black',top='table_wood' if wood else 'table_dark')
    r=.016
    for x in [-w/2+.045,w/2-.045]:
        for y in [-d/2+.045,d/2-.045]:m.box([x-r,y-r,.015],[x+r,y+r,h-.035]);m.lathe([(0,.023),(.015,.023)],center=[x,y,0])
        m.box([x-r,-d/2+.04,.21],[x+r,d/2-.04,.237])
    m.box([-w/2+.04,d/2-.057,.20],[w/2-.04,d/2-.025,.228])
    m.box([-w/2+.04,-d/2+.025,h-.10],[w/2-.04,-d/2+.055,h-.036])
    return m

def coffee_machine():
    w,d,h=.56,.48,.84;m=Mesh();m.box([-w/2,-d/2,.035],[w/2,d/2,h-.015],front='coffee_front')
    for x in [-w/2+.045,w/2-.045]:
        for y in [-d/2+.045,d/2-.045]:m.lathe([(0,.018),(.038,.018)],'black',center=[x,y,0],sides=16)
    m.box([-w/2-.006,-d/2-.002,h-.015],[w/2+.006,d/2+.004,h],'metal')
    m.panel([-w/2-.001,d/2,.19],[-w/2-.001,-d/2,.19],[-w/2-.001,-d/2,h-.04],[-w/2-.001,d/2,h-.04],'coffee_side')
    m.box([-w/2+.04,-d/2-.095,.025],[w/2-.035,-d/2+.10,.058],'silver')
    for x in np.arange(-.17,.19,.012):m.box([x,-d/2-.079,.058],[x+.003,-d/2+.045,.060],'black')
    # Mouth and controls stay in their observed photograph; the separate tray
    # supplies real depth without duplicating its grille on the vertical face.
    return m,(w,d,h)

def dispenser():
    w,d,h=.36,.36,1.40;m=Mesh();m.box([-w/2,-d/2,.028],[w/2,d/2,.92],'white',front='dispenser_front')
    m.box([-w/2-.015,-d/2-.015,.9],[w/2+.015,d/2+.015,.935],'white')
    m.panel([-w/2-.0005,d/2,.03],[-w/2-.0005,-d/2,.03],[-w/2-.0005,-d/2,.91],[-w/2-.0005,d/2,.91],'dispenser_side')
    # The blue floor basin surrounds the dispenser rather than being a pedestal.
    m.box([-.245,-.245,0],[.245,.24,.025],'blue')
    m.box([-.245,-.245,0],[.245,-.231,.13],'blue')
    m.box([-.245,.225,0],[.245,.24,.13],'blue')
    for x in [-.245,.230]:m.box([x,-.24,0],[x+.015,.235,.13],'blue')
    m.lathe([(.936,.125),(.95,.144),(.985,.151),(1.33,.15),(1.375,.125)],'black',texture='bottle_cover')
    m.lathe([(1.375,.038),(1.40,.037)],'cap')
    return m,(w,d,h)

def bin_blue():
    m=Mesh();m.lathe([(0,.195),(.018,.204),(.08,.214),(.25,.225),(.48,.231),(.61,.216)],'blue')
    for z in [.08,.36,.57]:m.lathe([(z,.225 if z<.5 else .223),(z+.012,.226 if z<.5 else .224)],'blue')
    m.lathe([(.612,.227),(.63,.238),(.645,.228)],'black')
    for x in [-.239,.239]:m.box([x-.008,-.04,.42],[x+.008,.04,.49],'black')
    return m,(.48,.48,.65)

def carton():
    w,d,h=.62,.43,.35;t=.008;m=Mesh()
    m.box([-w/2,-d/2,0],[w/2,d/2,t],'cardboard')
    # Empty bottom texture: clean neighboring cardboard; packet never baked in.
    m.panel([-w/2+t,-d/2+t,t+.0002],[w/2-t,-d/2+t,t+.0002],[w/2-t,d/2-t,t+.0002],[-w/2+t,d/2-t,t+.0002],'cardboard')
    m.box([-w/2,-d/2,0],[w/2,-d/2+t,h],'cardboard',front='carton_front')
    m.box([-w/2,d/2-t,0],[w/2,d/2,h],'cardboard')
    for x in [-w/2,w/2-t]:m.box([x,-d/2,0],[x+t,d/2,h],'cardboard')
    # The two open side flaps are observed; no invented closed box top.
    for s in [-1,1]:
        x=s*w/2;out=x+s*.15;z=h-.09
        m.quad([x,-d/2,h],[x,d/2,h],[out,d/2,z],[out,-d/2,z],'cardboard')
        m.quad([out,-d/2,z-.003],[out,d/2,z-.003],[x,d/2,h-.003],[x,-d/2,h-.003],'cardboard_dark')
    for x in np.arange(-w/2,w/2,.01):m.box([x,-d/2-.0008,h-.002],[x+.004,-d/2+.004,h+.0006],'cardboard_dark')
    return m,(w,d,h)

def packet():
    m=Mesh();w,d,h=.17,.245,.047;nx,ny=24,32
    def p(u,v,top=True):
        # Closed pillow-like wrapper, tapered heat-sealed ends, slight folds.
        width=w*(.88+.12*np.sin(math.pi*v));x=(u-.5)*width;y=(v-.5)*d
        puff=np.sin(math.pi*u)**.5*np.sin(math.pi*v)**.43
        z=.007+(h-.009)*puff if top else .003+.003*puff
        if top:z+=.0018*np.sin(22*u+5*v)*np.sin(math.pi*u)*np.sin(math.pi*v)
        return [x,y,z]
    for i in range(nx):
        for j in range(ny):
            u0,u1=i/nx,(i+1)/nx;v0,v1=j/ny,(j+1)/ny
            m.quad(p(u0,v0),p(u1,v0),p(u1,v1),p(u0,v1),'packet_front',[[u0,v0],[u1,v0],[u1,v1],[u0,v1]])
            m.quad(p(u0,v1,False),p(u1,v1,False),p(u1,v0,False),p(u0,v0,False),'red')
    edges=[[(i/nx,0),((i+1)/nx,0)] for i in range(nx)]+[[(1,i/ny),(1,(i+1)/ny)] for i in range(ny)]+[[((i+1)/nx,1),(i/nx,1)] for i in range(nx)]+[[(0,(i+1)/ny),(0,i/ny)] for i in range(ny)]
    for (u,v),(s,t) in edges:m.quad(p(u,v),p(u,v,False),p(s,t,False),p(s,t),'red')
    return m,(w,d,h)

def cooler():
    w,d,h=.76,.54,.48;t=.046;m=Mesh()
    m.box([-w/2,-d/2,0],[w/2,d/2,.046],'foam')
    m.box([-w/2,-d/2,0],[w/2,-d/2+t,h-.05],'foam',front='cooler_front')
    m.box([-w/2,d/2-t,0],[w/2,d/2,h-.05],'foam')
    for x in [-w/2,w/2-t]:m.box([x,-d/2,0],[x+t,d/2,h-.05],'foam')
    # Source lid rests horizontally, slid back to expose the iced bottles.
    m.box([-w/2-.009,-d/2+.26,h-.05],[w/2+.009,d/2+.26,h],'foam',top='cooler_lid')
    rng=np.random.default_rng(42)
    for i in range(7):
        x=-.27+(i%4)*.175;y=-.15+(i//4)*.18
        b=Mesh();b.lathe([(0,.031),(.04,.034),(.15,.033),(.195,.018),(.22,.016)],'water',sides=24)
        b.lathe([(.052,.034),(.14,.034)],'red',sides=24,texture='cola_label',full=True)
        b.lathe([(.218,.018),(.239,.018)],'red',sides=24)
        angle=(-1 if i%2 else 1)*(.26+.12*(i%3));R=np.array([[1,0,0],[0,np.cos(angle),-np.sin(angle)],[0,np.sin(angle),np.cos(angle)]])
        m.v.extend(np.array(b.v)@R.T+np.array([x,y,.055]));m.uv.extend(b.uv)
    # Small source-observed ice fragments remain inside the hollow cooler.
    for i in range(28):
        x=rng.uniform(-.30,.30);y=rng.uniform(-.20,.18);z=rng.uniform(.06,.10)
        m.box([x,y,z],[x+.025,y+.02,z+.018],'glass')
    return m,(w,d,h)

def bottles():
    m=Mesh()
    for i in range(11):
        x=-.27+(i%6)*.105;y=-.055+(i//6)*.105
        m.lathe([(0,.024),(.015,.032),(.13,.031),(.168,.020),(.190,.012)],'glass',center=[x,y,0],sides=24,texture='water_bottle_body')
        for z in [.033,.052,.074]:m.lathe([(z,.032),(z+.004,.0325)],'glass',center=[x,y,0],sides=24)
        m.lathe([(.085,.032),(.13,.032)],'blue',center=[x,y,0],sides=24,texture='bottle_label',full=True)
        m.lathe([(.186,.014),(.207,.014)],'cap',center=[x,y,0],sides=24)
    return m,(.64,.19,.21)

def supplies():
    m=Mesh()
    for x in [-.14,0,.14]:m.box([x-.065,-.05,0],[x+.065,.06,.075],'paper',front='supplies_front',top='supplies_front')
    m.box([.045,-.012,.075],[.182,.115,.18],'paper',front='supplies_front',top='supplies_front')
    # Nested paper bowls with a visible concave center and rounded thin rim.
    for i in range(5):
        z=i*.004
        m.lathe([(z,.04),(z+.022,.066),(z+.027,.069),(z+.029,.067),(z+.024,.064),(z+.005,.038)],'paper',center=[-.20,-.17,0],sides=48)
    return m,(.46,.33,.18)

def floor_cooler():
    m=Mesh();m.box([-.36,-.25,0],[.36,.25,.43],'foam',front='foam_side')
    m.box([-.37,-.26,.43],[.37,.26,.47],'foam',top='cooler_lid')
    return m,(.74,.52,.47)

def slim_bins():
    m=Mesh()
    for x,closed in [(-.17,True),(.17,False)]:
        m.lathe([(0,.123),(.025,.138),(.56,.139),(.59,.14)],'silver',center=[x,0,0])
        m.lathe([(.555,.142),(.59,.145)],'black',center=[x,0,0])
        if closed:m.lathe([(.59,.145),(.61,.147),(.618,.139)],'silver',center=[x,0,0])
        else:
            m.lathe([(.57,.139),(.592,.143),(.6,.139),(.60,.127),(.57,.127)],'black',center=[x,0,0])
    return m,(.64,.30,.62)

def bulk_jugs():
    m=Mesh()
    for x,mat in [(-.18,'glass'),(.18,'blue')]:
        m.lathe([(0,.116),(.018,.137),(.32,.137),(.39,.122),(.43,.035),(.48,.029)],mat,center=[x,0,0],texture='jug_plastic' if mat=='glass' else None)
        for z in [.08,.14,.24,.32]:m.lathe([(z,.14),(z+.012,.141)],mat,center=[x,0,0])
        m.lathe([(.473,.031),(.502,.030)],'black',center=[x,0,0])
    return m,(.65,.29,.51)

def coffee_supplies():
    m=Mesh()
    m.box([-.14,-.14,0],[.14,.13,.015],'cardboard')
    for x,y,n in [(-.083,.042,18),(0,.077,24),(.081,.07,29)]:
        h=.085+n*.0045
        m.lathe([(0,.023),(h-.075,.023),(h,.038)],'paper',center=[x,y,0],sides=32)
        for k in range(n):
            z=.045+k*.0045;m.lathe([(z,.030),(z+.0018,.031)],'paper',center=[x,y,0],sides=24)
        m.lathe([(h-.002,.038),(h+.001,.038),(h+.002,.033),(h-.004,.033)],'paper',center=[x,y,0],sides=32)
    # One empty cup in front as observed on the service table.
    m.lathe([(0,.023),(.077,.037),(.080,.038),(.081,.033),(.075,.032),(.010,.019)],'paper',center=[.07,-.10,0],sides=40)
    return m,(.28,.28,.23)

def floor_cartons():
    m=Mesh();w,d=.43,.40
    m.box([-.43,-.20,0],[0,.20,.39],'cardboard')
    m.box([-.425,-.202,.391],[.005,.202,.79],'cardboard',front='floor_bingo')
    m.box([.018,.16,0],[.438,.58,.33],'cardboard')
    # Two folded top leaves and packing tape on the right-hand sealed box.
    m.box([.018,.159,.33],[.226,.581,.335],'cardboard')
    m.box([.230,.159,.33],[.438,.581,.335],'cardboard')
    m.box([.218,.155,.06],[.24,.161,.337],'wood')
    m.box([.218,.158,.337],[.24,.58,.338],'wood')
    # Parle box on top is open in the source and uses that specific photograph.
    m.box([-.40,-.16,.793],[-.02,.185,.801],'cardboard')
    m.box([-.40,-.16,.793],[-.02,-.152,1.105],'cardboard',front='floor_parle')
    m.box([-.40,.177,.793],[-.02,.185,1.105],'cardboard')
    for x in [-.40,-.028]:m.box([x,-.16,.793],[x+.008,.18,1.105],'cardboard')
    m.quad([-.40,-.16,1.105],[-.02,-.16,1.105],[-.02,-.29,1.125],[-.40,-.29,1.125],'cardboard')
    return m,(.88,.87,1.125)

FACTORIES={'coffee_machine':coffee_machine,'dispenser':dispenser,'blue_bin':bin_blue,
           'snack_carton':carton,'snack_packet':packet,'ice_cooler':cooler,'water_bottles':bottles,'tabletop_supplies':supplies,
           'floor_cooler':floor_cooler,'slim_bins':slim_bins,'bulk_jugs':bulk_jugs,'coffee_supplies':coffee_supplies,
           'floor_cartons':floor_cartons}
TABLES={'coffee_table':(.91,.57,.82,False),'bottle_table':(1.06,.38,1.03,True),
        'cooler_table':(.86,.62,.73,False),'carton_table':(1.06,.56,.75,False)}

def main():
    make_atlas();anchors_path=P/'object_anchors.json';groups=[]
    anchors=json.loads(anchors_path.read_text()) if anchors_path.exists() else {}
    if 'objects' in anchors:anchors=anchors['objects']
    for name,factory in FACTORIES.items():
        m,size=factory();anchor=anchors.get(name,{'center':[0,0,0],'yaw':0})
        if anchor.get('omit'):continue
        groups.append(m.save(name,anchor,np.array(size)))
    for name,(w,d,h,wood) in TABLES.items():
        anchor=anchors.get(name,{'center':[0,0,0],'yaw':0})
        if anchor.get('omit'):continue
        groups.append(table(w,d,h,wood).save(name,anchor,np.array([w,d,h])))
    result={'groups':groups,'coordinate_frame':'Calibrated room anchors when object_anchors.json supplied; otherwise unplaced local assets. Front is -Y, +Z up.','placed':anchors_path.exists(),'method':'Manually fitted closed proxies with real video face textures. Hidden geometry inferred.'}
    (P/'objects.json').write_text(json.dumps(result,indent=2));print(json.dumps({'placed':result['placed'],'groups':len(groups),'triangles':sum(g['triangles'] for g in groups)}))

if __name__=='__main__':main()
