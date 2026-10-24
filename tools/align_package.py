"""Apply exported placements to a new package, with no SAM/API call or viewer replacement."""
import argparse
from copy import deepcopy
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from room2sim.core import read_json, write_json, digest, inside, transform, vector
from room2sim.pipeline import validate_package
from room2sim import splats


def align(package,placements,output,fit_colliders=False):
    source=Path(package).resolve();output=Path(output).resolve();placements=Path(placements).resolve()
    validate_package(source)
    if output.exists() or output.is_relative_to(source):raise ValueError('Use a fresh output outside the source package')
    edits=read_json(placements)
    if edits.get('version')!=1 or not isinstance(edits.get('objects'),list):raise ValueError('Use a version 1 placements export with an objects list')
    manifest=read_json(source/'scene.json');known={o['id']:o for o in manifest.get('objects',[])};seen=set()
    for edit in edits['objects']:
        identifier=edit.get('id')
        if identifier not in known or identifier in seen:raise ValueError('Unknown or duplicate object id in placements')
        seen.add(identifier);obj=known[identifier]
        obj['transform']=deepcopy(transform(edit['transform']))
        if fit_colliders:
            if obj.get('representation')!='splat' or not obj.get('asset'):raise ValueError('Automatic box fitting needs a selected Gaussian object asset')
            lo,hi=splats.inspect(inside(source,obj['asset']))['bounds']
            obj['collider']={'type':'box','center':[(a+b)/2 for a,b in zip(lo,hi)],'dimensions':[b-a for a,b in zip(lo,hi)]}
            obj.setdefault('provenance',{})['collider_fit']='AABB of Gaussian centers; approximate local interaction proxy'
        if 'collider' in edit:obj['collider']=deepcopy(edit['collider'])
        collider=obj['collider']
        if collider.get('type')!='box':raise ValueError('Only box interaction proxies are supported')
        vector(collider['dimensions'],3,'collider dimensions',positive=True);vector(collider.get('center',[0,0,0]),3,'collider center')
    manifest.setdefault('provenance',{})['manual_alignment']={'base_package_sha256':digest(source/'checksums.json'),
        'placements_sha256':digest(placements),'objects':sorted(seen),'status':'candidate; requires visual alignment and interaction checks'}
    output.mkdir(parents=True,exist_ok=False);shutil.copytree(source,output,dirs_exist_ok=True)
    write_json(output/'scene.json',manifest)
    evidence=output/'evidence/manual-alignment';evidence.mkdir(parents=True,exist_ok=True)
    write_json(evidence/'placements.json',edits)
    # Preserve this package's viewer bytes, including any already-reviewed fixes.
    hashes={str(p.relative_to(output)):digest(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name!='checksums.json'}
    write_json(output/'checksums.json',hashes)
    return validate_package(output)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('package','placements','output'):p.add_argument('--'+name,required=True)
    p.add_argument('--fit-colliders',action='store_true')
    a=p.parse_args()
    try:result=align(a.package,a.placements,a.output,a.fit_colliders)
    except (ValueError,FileNotFoundError,KeyError) as e:p.exit(1,f'Error: {e}\n')
    print(f'Created alignment candidate: {a.output}; validation: {result["status"]}')


if __name__=='__main__':main()
