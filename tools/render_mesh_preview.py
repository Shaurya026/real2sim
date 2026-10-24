"""Optional scientific rendering of the historical early mesh (NumPy/Matplotlib).
No model or GPU is used. Run against the source Open3D PLY, not a Gaussian PLY.
"""
import argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    with a.source.open('rb') as f:
        header=[]
        while True:
            line=f.readline()
            if not line:raise ValueError('Missing PLY header')
            header.append(line.decode('ascii').strip())
            if line.strip()==b'end_header':break
        count=int(next(x for x in header if x.startswith('element vertex ')).split()[-1])
        faces=int(next(x for x in header if x.startswith('element face ')).split()[-1])
        dtype=np.dtype([('position','<f8',(3,)),('normal','<f8',(3,)),('color','u1',(3,))])
        vertices=np.fromfile(f,dtype=dtype,count=count)
        indices=np.fromfile(f,dtype=np.dtype([('count','u1'),('indices','<u4',(3,))]),count=faces)
    if not np.all(indices['count']==3):raise ValueError('Expected triangle faces')
    points=vertices['position'];triangles=points[indices['indices']]
    color=vertices['color'][indices['indices']].mean(axis=1)/255
    fig=plt.figure(figsize=(12,8),facecolor='#e4e8df');ax=fig.add_subplot(111,projection='3d',facecolor='#e4e8df')
    ax.add_collection3d(Poly3DCollection(triangles,facecolors=color,edgecolors='none',rasterized=True))
    center=(points.min(axis=0)+points.max(axis=0))/2;span=np.max(np.ptp(points,axis=0))*.51
    ax.set_xlim(center[0]-span,center[0]+span);ax.set_ylim(center[1]-span,center[1]+span);ax.set_zlim(center[2]-span,center[2]+span)
    ax.set_box_aspect((1,1,1));ax.view_init(elev=25,azim=-55);ax.set_axis_off()
    fig.text(.06,.92,'REAL2SIM  /  EARLY OBSERVED SURFACE',fontsize=12,color='#276342',family='monospace')
    fig.text(.06,.075,f'{count:,} vertices  /  {faces:,} triangles  /  scale unverified',fontsize=10,color='#455b4a',family='monospace')
    fig.subplots_adjust(left=0,right=1,bottom=.07,top=.95)
    fig.savefig(a.output,dpi=120,facecolor=fig.get_facecolor());plt.close(fig)
    print(a.output)


if __name__=='__main__':main()
