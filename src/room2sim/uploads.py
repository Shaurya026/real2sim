"""Check a downloaded checkout and restore separately distributed demo assets."""
import json
from pathlib import Path
import shutil
import tempfile
import zipfile
from .core import ROOT, digest, inside, read_json

LFS_PREFIX = b'version https://git-lfs.github.com/spec/v1'
VIEWER_FILES = ['index.html','app.js','gaussians.js','ply.js','sort-worker.js','interaction.js','style.css',
                'vendor/three.module.js','vendor/THREE-LICENSE.txt',
                'vendor/addons/controls/OrbitControls.js','vendor/addons/loaders/GLTFLoader.js',
                'vendor/addons/utils/BufferGeometryUtils.js']


def pointer(path):
    with Path(path).open('rb') as f:
        return f.read(len(LFS_PREFIX)) == LFS_PREFIX


def check_checkout(root=ROOT):
    root=Path(root).resolve()
    if not (root/'room2sim.py').exists() and (root/'room2sim-pipeline/room2sim.py').exists():
        root=root/'room2sim-pipeline'
    required=['room2sim.py','pyproject.toml','src/room2sim/cli.py','src/room2sim/pipeline.py',
        'src/room2sim/uploads.py','blender/repair_scene.py','backends/sam3d_infer.py',
        'agents/review.py','agents/fix_browser.py','agents/capture.mjs','configs/office.json',
        'configs/desk.json','demo/desk/scene.json','demo/desk/poses.json',
        'demo/office/scene.json','demo/pantry/scene.json', 'assets-manifest.json']
    required += ['web/dist/'+name for name in VIEWER_FILES]
    missing=[name for name in required if not (root/name).is_file()]
    assets=[]
    if (root/'assets-manifest.json').is_file():
        for item in read_json(root/'assets-manifest.json')['assets']:
            p=inside(root,item['path'])
            status='missing' if not p.is_file() else 'lfs_pointer' if pointer(p) else 'ok' if digest(p)==item['sha256'] else 'hash_mismatch'
            assets.append({'path':item['path'],'required':item['required'],'status':status})
    blocking_assets=[a for a in assets if a['required'] and a['status']!='ok']
    return {'root':str(root),'status':'ready' if not missing and not blocking_assets else 'incomplete',
            'missing_code':missing,'assets':assets,
            'next':'Restore real2sim-demo-assets.zip with restore-assets, or materialize tracked assets using your existing Git LFS setup. site/ is generated, not uploaded.'}


def restore_assets(archive, root=ROOT):
    """Prevalidate every source before replacing only missing files/LFS pointers."""
    root=Path(root).resolve();manifest=read_json(root/'assets-manifest.json')
    expected={a['path']:a for a in manifest['assets']}
    restored=[]
    with tempfile.TemporaryDirectory(prefix='room2sim-assets-') as tmp:
        temp=Path(tmp)
        with zipfile.ZipFile(archive) as z:
            for info in z.infolist():
                if info.is_dir():continue
                if info.filename not in expected:raise ValueError(f'Unexpected archive entry: {info.filename}')
                item=expected[info.filename]
                if info.file_size!=item['bytes']:raise ValueError(f'Size mismatch: {info.filename}')
                dest=inside(temp,info.filename);dest.parent.mkdir(parents=True,exist_ok=True)
                with z.open(info) as source,dest.open('wb') as target:shutil.copyfileobj(source,target)
                if digest(dest)!=item['sha256']:raise ValueError(f'Hash mismatch: {info.filename}')
            missing=[a['path'] for a in manifest['assets'] if a['required'] and not (temp/a['path']).is_file()]
            if missing:raise ValueError('Asset archive is missing required assets: '+', '.join(missing))
        # Refuse unrelated/modified local bytes, preserve identical assets.
        for name in expected:
            staged=inside(temp,name);current=inside(root,name)
            if not staged.exists():continue
            if current.exists() and not pointer(current) and digest(current)!=expected[name]['sha256']:
                raise ValueError(f'Existing asset differs: {name}. Move it aside before restoring.')
        for name in expected:
            staged=inside(temp,name);current=inside(root,name)
            if not staged.exists():continue
            if current.exists() and not pointer(current):continue
            current.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(staged,current);restored.append(name)
    return {'restored':restored,'checkout':check_checkout(root)}
