"""Reuse an approved Gaussian package in a fresh run without retraining the room."""
import argparse
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from room2sim.core import read_json, write_json, inside, IDENTITY
from room2sim.pipeline import validate_package


def create(package,video,output,objects=None):
    package=Path(package).resolve();video=Path(video).resolve();output=Path(output).resolve()
    validate_package(package)
    if output.exists():raise ValueError('Config destination exists; choose a new file')
    if not video.is_file():raise ValueError('Provide the original local video path')
    manifest=read_json(package/'scene.json');room=manifest['room']
    if room['representation']!='splat':raise ValueError('Use your own Gaussian room package; archive mesh demos are not reconstruction inputs')
    def relative(p):return os.path.relpath(p,output.parent)
    cfg={'version':1,'title':manifest.get('title','My room')+' — reusable room','backend':'splatfacto',
         'videos':[relative(video)],'fps':2,'max_frames':240,'iterations':15000,
         'units':manifest.get('world',{}).get('units','uncalibrated'),
         'room_transform':room.get('transform',IDENTITY),
         'camera':manifest.get('camera',{'position':[3,2,3],'target':[0,0,0]}),
         'existing_splat':relative(inside(package,room['asset']))}
    if room.get('mesh'):cfg['existing_mesh']=relative(inside(package,room['mesh']))
    if manifest.get('objects'):cfg['existing_objects_package']=relative(package)
    if objects:
        objects=Path(objects).resolve()
        if not objects.is_file():raise ValueError('Object spec must exist before initializing the new run')
        if read_json(objects).get('version')!=1:raise ValueError('Object spec version must be 1')
        cfg['objects']=relative(objects)
    write_json(output,cfg)
    return cfg


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('package','video','output'):p.add_argument('--'+name,required=True)
    p.add_argument('--objects')
    a=p.parse_args()
    try:create(a.package,a.video,a.output,a.objects)
    except (ValueError,FileNotFoundError,KeyError) as e:p.exit(1,f'Error: {e}\n')
    print(f'Wrote {a.output}; import with init → splat → repair → objects → package. Skip ingest/reconstruct.')


if __name__=='__main__':main()
