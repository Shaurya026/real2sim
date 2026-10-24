#!/usr/bin/env python3
"""Compare this reference project with a cloned/downloaded uploaded repo. Read-only."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EXCLUDE={'.git','.venv','__pycache__','node_modules','inputs','runs','site','review-work','_site','verification-work'}
ASSET_SUFFIXES={'.ply','.glb','.mov','.webm','.mp4'}


def is_pointer(path):
    prefix=b'version https://git-lfs.github.com/spec/v1'
    with path.open('rb') as f:return f.read(len(prefix))==prefix


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()


def compare(source,target):
    source=Path(source).resolve();target=Path(target).resolve()
    if not target.is_dir():raise ValueError('Target must be a local clone or extracted GitHub ZIP')
    if not (target/'room2sim.py').exists() and (target/'room2sim-pipeline/room2sim.py').exists():target=target/'room2sim-pipeline'
    result={'target':str(target),'upload_missing':[],'replace_changed':[],'same':[],
            'assets_missing':[],'assets_lfs_pointer':[],'assets_changed':[]}
    for p in sorted(source.rglob('*')):
        rel=p.relative_to(source)
        if not p.is_file() or any(x in EXCLUDE or x.endswith('.egg-info') for x in rel.parts):continue
        dest=target/rel;name=rel.as_posix();asset=p.suffix in ASSET_SUFFIXES
        if not dest.is_file():result['assets_missing' if asset else 'upload_missing'].append(name)
        elif asset and is_pointer(dest):result['assets_lfs_pointer'].append(name)
        elif sha(p)!=sha(dest):result['assets_changed' if asset else 'replace_changed'].append(name)
        else:result['same'].append(name)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',required=True);p.add_argument('--source',default=str(ROOT));p.add_argument('--output')
    a=p.parse_args();result=compare(a.source,a.target)
    if a.output:Path(a.output).write_text(json.dumps(result,indent=2)+'\n')
    for key in ('upload_missing','replace_changed','assets_missing','assets_lfs_pointer','assets_changed'):
        print(f'\n{key} ({len(result[key])})')
        for name in result[key]:print('  '+name)
    print(f"\nAlready identical: {len(result['same'])} files")
if __name__=='__main__':main()
