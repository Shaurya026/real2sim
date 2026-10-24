"""Compare/apply this review to a real Git clone, preserving unrelated edits.

Default is read-only. --apply copies only manifest-listed files after checking all
preimages. A differing remote file must be reconciled manually, never overwritten.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def confined(root,relative):
    p=(root/relative).resolve()
    if not p.is_relative_to(root) or p==root:
        raise ValueError(f'Invalid manifest path: {relative}')
    return p


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--target',type=Path,required=True)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--apply',action='store_true')
    a=p.parse_args();target=a.target.resolve()
    cp=subprocess.run(['git','-C',str(target),'rev-parse','--show-toplevel'],capture_output=True,text=True)
    if cp.returncode or Path(cp.stdout.strip()).resolve()!=target:
        p.error('Target must be the root of a real Git checkout')
    if target==ROOT:
        p.error('Target must be a separate upstream checkout')
    manifest=json.loads(a.manifest.read_text());changes=[];conflicts=[]
    for item in manifest['files']:
        source=confined(ROOT,item['path']);dest=confined(target,item['path'])
        if not source.is_file() or sha(source)!=item['sha256']:
            raise ValueError(f'Review source changed: {item["path"]}')
        if dest.is_file() and sha(dest)==item['sha256']:
            continue
        if dest.exists() and (not dest.is_file() or sha(dest)!=item['base_sha256']):
            conflicts.append(item['path']);continue
        if not dest.exists() and item['base_sha256'] is not None:
            conflicts.append(item['path']);continue
        changes.append((source,dest))
    if conflicts:
        raise SystemExit('Upstream differs from the reviewed local baseline. Reconcile first:\n'+'\n'.join(conflicts))
    print(f'{len(changes)} files can be applied; all preimages match the reviewed baseline.')
    if a.apply:
        for source,dest in changes:
            dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
        print('Review files copied. Inspect git diff and run checks before committing.')
    else:
        print('Read-only check. Add --apply to copy these files.')


if __name__=='__main__':
    main()
