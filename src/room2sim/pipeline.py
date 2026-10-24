from __future__ import annotations
import os
from pathlib import Path
import shutil
import time
import uuid
from copy import deepcopy
from .core import (ROOT, IDENTITY, clean_config, digest, executable, ffmpeg, inside,
                   load_config, read_json, resolve, run_command, transform, vector, write_json)
from .patches import validate_patch, repair_objects
from . import splats


def new_run(config, output):
    cfg = load_config(config)
    out = Path(output).resolve()
    # Each run is immutable with respect to its input configuration.
    out.mkdir(parents=True, exist_ok=False)
    write_json(out/'config.json', clean_config(cfg))
    write_json(out/'context.json', {'config_base':cfg['_base'], 'source_config_sha256':digest(config), 'run_config_sha256':digest(out/'config.json')})
    write_json(out/'state.json', {'version':1, 'stages':{}})
    return out


def run_config(run):
    context = read_json(Path(run)/'context.json')
    if context.get('run_config_sha256') != digest(Path(run)/'config.json'):
        raise RuntimeError('Run config changed or lacks an integrity receipt; start a new run')
    cfg = load_config(Path(run)/'config.json')
    cfg['_base'] = context['config_base']
    return cfg


def finish(run, stage, outputs, metadata=None):
    run = Path(run)
    state = read_json(run/'state.json')
    state['stages'][stage] = {'status':'complete', 'completed_unix':time.time(),
        'outputs': {str(Path(p).relative_to(run)):digest(p) for p in outputs}, 'metadata':metadata or {}}
    write_json(run/'state.json', state)


def verify_stage(run, stage):
    run = Path(run)
    receipt = read_json(run/'state.json')['stages'].get(stage)
    if not receipt:
        raise RuntimeError(f'Run stage {stage} first')
    for relative, sha in receipt['outputs'].items():
        p = inside(run, relative)
        if not p.is_file() or digest(p) != sha:
            raise RuntimeError(f'Stage {stage} output changed/missing: {relative}. Start a new run.')
    return receipt


def stage_ingest(run):
    run = Path(run).resolve()
    cfg = run_config(run)
    frames = run/'frames'
    frames.mkdir(exist_ok=False)
    sources, index = [], []
    limit = int(cfg['max_frames'])
    for i, name in enumerate(cfg['videos']):
        video = resolve(cfg['_base'], name)
        if not video.is_file():
            raise FileNotFoundError(f'Video not found: {video}')
        dest = frames/f'capture-{i:02d}'
        dest.mkdir()
        run_command([ffmpeg(), '-hide_banner', '-nostdin', '-i', video, '-an',
            '-vf', f"fps={cfg['fps']},scale='min(1600,iw)':-2", '-frames:v', limit,
            '-q:v', '2', dest/'frame-%06d.jpg'], run/'logs'/f'ingest-{i}.log')
        files = sorted(dest.glob('*.jpg'))
        if not files:
            raise RuntimeError(f'No frames extracted from {video}')
        for j, f in enumerate(files):
            target = frames/f'capture-{i:02d}-{f.name}'
            f.rename(target)
            index.append({'file':str(target.relative_to(run)), 'capture':i,
                          'sample_time_seconds':j/cfg['fps']})
        dest.rmdir()
        sources.append({'name':video.name, 'sha256':digest(video), 'frames':len(files)})
    write_json(run/'capture.json', {'sources':sources, 'frame_index':index,
        'sampling':'FFmpeg fps filter; sample times nominal, not original frame timestamps'})
    finish(run, 'ingest', [run/'capture.json', *sorted(frames.glob('*.jpg'))])


def stage_reconstruct(run):
    run = Path(run).resolve()
    cfg = run_config(run)
    verify_stage(run, 'ingest')
    data = run/'reconstruction'
    if data.exists():
        raise RuntimeError('reconstruction exists; use a new run to retry a failed reconstruction')
    cmd = [executable('NS_PROCESS_BIN','ns-process-data'), 'images', '--data', run/'frames', '--output-dir',data]
    receipt = run_command(cmd, run/'logs'/'colmap.log')
    if not (data/'transforms.json').is_file():
        raise RuntimeError('Nerfstudio did not produce transforms.json')
    transforms = read_json(data/'transforms.json')
    registered = len(transforms.get('frames',[]))
    extracted = len(read_json(run/'capture.json')['frame_index'])
    if registered < 3:
        raise RuntimeError('Fewer than 3 registered cameras; capture has insufficient reconstruction coverage')
    write_json(run/'coverage.json', {'registered':registered, 'extracted':extracted,
                                   'fraction':registered/extracted, 'command':receipt})
    finish(run, 'reconstruct', [data/'transforms.json',run/'coverage.json'])


def stage_splat(run):
    run = Path(run).resolve()
    cfg = run_config(run)
    source = cfg.get('existing_splat')
    dest = run/'appearance'
    dest.mkdir(exist_ok=False)
    metadata = {}
    if source:
        p = resolve(cfg['_base'],source)
        splats.inspect(p)
        shutil.copy2(p,dest/'room.ply')
        metadata = {'backend':'existing Gaussian PLY', 'source_name':p.name, 'source_sha256':digest(p)}
    else:
        verify_stage(run,'reconstruct')
        train = [executable('NS_TRAIN_BIN','ns-train'),'splatfacto','--data',run/'reconstruction',
                 '--output-dir',run/'training','--max-num-iterations',int(cfg['iterations']),'--vis','tensorboard']
        run_command(train,run/'logs'/'splatfacto.log')
        configs = list((run/'training').rglob('config.yml'))
        if len(configs) != 1:
            raise RuntimeError('Expected exactly one training config in this isolated run')
        run_command([executable('NS_EXPORT_BIN','ns-export'),'gaussian-splat','--load-config',configs[0],
                     '--output-dir',dest],run/'logs'/'export.log')
        plys = list(dest.glob('*.ply'))
        if len(plys) != 1:
            raise RuntimeError('Expected one exported Gaussian PLY')
        plys[0].rename(dest/'room.ply')
        metadata = {'backend':'splatfacto','iterations':cfg['iterations'],
                    'config':str(configs[0].relative_to(run))}
    metadata.update(splats.inspect(dest/'room.ply'))
    write_json(dest/'receipt.json',metadata)
    finish(run,'splat',[dest/'room.ply',dest/'receipt.json'])


def stage_repair(run, patch_path=None):
    run = Path(run).resolve()
    cfg = run_config(run)
    verify_stage(run,'splat')
    path = patch_path or cfg.get('repairs')
    patch_file = Path(patch_path).resolve() if patch_path else resolve(cfg['_base'],path) if path else None
    patch = validate_patch(read_json(patch_file)) if path else {'version':1,'operations':[]}
    dest = run/'repairs'
    dest.mkdir(exist_ok=False)
    write_json(dest/'patch.json',patch)
    regions = [o for o in patch['operations'] if o['kind']=='crop_splats']
    receipt = splats.crop(run/'appearance'/'room.ply',dest/'room.ply',regions) if regions else None
    if not regions:
        shutil.copy2(run/'appearance'/'room.ply',dest/'room.ply')
    mesh_ops = [o for o in patch['operations'] if o['kind']!='crop_splats']
    if mesh_ops or cfg.get('existing_mesh'):
        cmd = [executable('BLENDER_BIN','blender'),'--background','--python-exit-code','1','--python',
               ROOT/'blender'/'repair_scene.py','--','--patch',dest/'patch.json','--output',dest]
        if cfg.get('existing_mesh'):
            cmd.extend(['--source',resolve(cfg['_base'],cfg['existing_mesh'])])
        run_command(cmd,run/'logs'/'blender.log')
        if not (dest/'repairs.glb').is_file():
            raise RuntimeError('Blender did not produce a mesh; inspect logs')
    write_json(dest/'crop-receipt.json',{'crop':receipt,'source_sha256':digest(run/'appearance'/'room.ply')})
    finish(run,'repair',[p for p in dest.iterdir() if p.is_file()])


def validate_objects(objects, base):
    if not isinstance(objects,list) or len(objects)>16:
        raise ValueError('objects must be a list of at most 16 selected objects')
    ids=set()
    import re
    for obj in objects:
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',obj.get('id','')) or obj['id'] in ids:
            raise ValueError('Object ids must be unique safe names')
        ids.add(obj['id'])
        transform(obj['transform'])
        vector(obj['collider']['dimensions'],3,'collider dimensions',positive=True)
        vector(obj['collider'].get('center',[0,0,0]),3,'collider center')
        if obj['collider'].get('type')!='box':
            raise ValueError('This viewer implements box interaction proxies')
        for key in ('image','mask'):
            if not resolve(base,obj[key]).is_file():
                raise FileNotFoundError(f"{obj['id']}: missing {key}: {obj[key]}")
    return objects


def stage_objects(run):
    run = Path(run).resolve()
    cfg = run_config(run)
    verify_stage(run,'repair')
    spec_path = cfg.get('objects')
    specs = []
    base = cfg['_base']
    if spec_path:
        spec_file = resolve(base,spec_path)
        base = spec_file.parent
        specs = validate_objects(read_json(spec_file)['objects'],base)
    imported=[]
    previous=cfg.get('existing_objects_package')
    if previous:
        previous=resolve(cfg['_base'],previous)
        validate_package(previous)
        imported=deepcopy(read_json(previous/'scene.json').get('objects',[]))
    additions=repair_objects(read_json(run/'repairs'/'patch.json'), imported)
    retained_ids={obj['id'] for obj in imported+additions}
    if any(obj['id'] in retained_ids for obj in specs):
        raise ValueError('New SAM object id collides with a retained or repaired object')
    dest = run/'objects'
    dest.mkdir(exist_ok=False)
    results=[]
    for obj in imported:
        if obj.get('asset'):
            source=inside(previous,obj['asset'])
            obj['asset']=str(Path('objects')/'imported'/obj['id']/source.name)
            target=inside(run,obj['asset']);target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,target)
        obj.setdefault('provenance',{})['reused_package_sha256']=digest(previous/'checksums.json')
        results.append(obj)
    results.extend(additions)
    for obj in specs:
        out = dest/obj['id']
        repo = Path(os.environ.get('SAM3D_REPO','')).expanduser()
        model = Path(os.environ.get('SAM3D_CONFIG','')).expanduser()
        if not (repo/'notebook'/'inference.py').is_file() or not model.is_file():
            raise RuntimeError('Set SAM3D_REPO and SAM3D_CONFIG to a configured upstream checkout and checkpoint YAML')
        cmd=[executable('SAM3D_PYTHON','python'),ROOT/'backends'/'sam3d_infer.py',
             '--repo',repo.resolve(),'--config',model.resolve(),'--image',resolve(base,obj['image']),
             '--mask',resolve(base,obj['mask']),'--output',out,'--seed',obj.get('seed',42)]
        run_command(cmd,run/'logs'/f"sam3d-{obj['id']}.log",cwd=repo.resolve())
        stats=splats.inspect(out/'splat.ply')
        result={k:v for k,v in obj.items() if k not in ('image','mask')}
        result.update({'asset':str((out/'splat.ply').relative_to(run)), 'representation':'splat',
            'provenance':{'backend':'SAM 3D Objects','image_sha256':digest(resolve(base,obj['image'])),
                          'mask_sha256':digest(resolve(base,obj['mask'])), 'statistics':stats},
            'background_removed': bool(obj.get('background_removed',False))})
        results.append(result)
    write_json(dest/'objects.json',{'objects':results})
    finish(run,'objects',[p for p in dest.rglob('*') if p.is_file()],{'selected_objects':len(results)})


def copy_asset(source, package, relative):
    dest = inside(package,relative)
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,dest)
    return relative


def stage_package(run, output):
    run=Path(run).resolve()
    cfg=run_config(run)
    verify_stage(run,'repair')
    verify_stage(run,'objects')
    out=Path(output).resolve()
    out.mkdir(parents=True,exist_ok=False)
    room={'representation':'splat', 'asset':copy_asset(run/'repairs'/'room.ply',out,'assets/room.ply'),
          'transform':cfg.get('room_transform',IDENTITY)}
    if (run/'repairs'/'repairs.glb').exists():
        room['mesh']=copy_asset(run/'repairs'/'repairs.glb',out,'assets/repairs.glb')
    objects=read_json(run/'objects'/'objects.json')['objects']
    for obj in objects:
        if obj.get('asset'):
            source=inside(run,obj['asset'])
            obj['asset']=copy_asset(source,out,f"assets/objects/{obj['id']}{source.suffix}")
    manifest={'version':1,'title':cfg.get('title','Reconstructed room'), 'world':{'up':'+Y','units':cfg.get('units','uncalibrated'),
              'metric_scale_verified':False}, 'room':room,'objects':objects,
              'camera':cfg.get('camera',{'position':[3,2,3],'target':[0,0,0]}),
              'provenance':{'config':clean_config(cfg),'stages':read_json(run/'state.json')['stages']},
              'limitations':['SAM 3D poses require manual alignment','Browser interactions are kinematic; no physics training',
                              'AABB removal selects Gaussian centers and may leave boundary fragments or holes']}
    if cfg.get('viewer_colliders'):
        manifest['colliders']=cfg['viewer_colliders']
    write_json(out/'scene.json',manifest)
    copy_asset(run/'repairs'/'patch.json',out,'evidence/repair-patch.json')
    finalize_package(out)
    finish(run,'package',[out/'scene.json'] if out.is_relative_to(run) else [],{'package':str(out)})
    return out


def finalize_package(out):
    out=Path(out)
    if not (ROOT/'web'/'dist'/'index.html').is_file():
        raise RuntimeError('Prebuilt viewer is missing. Upload web/dist/ or rebuild with your existing Three.js: node web/build.mjs (no installation is performed)')
    shutil.copytree(ROOT/'web'/'dist',out,dirs_exist_ok=True)
    # checksum assets and manifest; viewer bundle is included too
    hashes={str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='checksums.json'}
    write_json(out/'checksums.json',hashes)
    validate_package(out)


def validate_package(out):
    out=Path(out).resolve()
    manifest=read_json(out/'scene.json')
    if manifest['version']!=1:
        raise ValueError('Unknown scene version')
    room=manifest['room']
    transform(room.get('transform',IDENTITY))
    assets=[]
    if room.get('asset'):
        assets.append((room['asset'],room['representation']))
    if room.get('mesh'):
        assets.append((room['mesh'],'mesh'))
    for obj in manifest.get('objects',[]):
        transform(obj['transform'])
        vector(obj['collider']['dimensions'],3,'collider dimensions',positive=True)
        if obj.get('asset'):
            assets.append((obj['asset'],obj['representation']))
    for path,representation in assets:
        p=inside(out,path)
        if not p.is_file():
            raise ValueError(f'Missing asset {path}. Restore demo assets or provide the configured source.')
        from .uploads import pointer
        if pointer(p):
            raise ValueError(f'{path} is a Git LFS pointer, not the asset. Materialize it with your existing Git LFS setup or restore-assets.')
        if representation=='splat':
            splats.inspect(p)
        elif representation=='mesh':
            import struct
            raw=p.read_bytes()
            if len(raw)<12:raise ValueError(f'Truncated GLB: {path}')
            magic,version,length=struct.unpack('<4sII',raw[:12])
            if magic!=b'glTF' or version!=2 or length!=len(raw):
                raise ValueError(f'Invalid GLB: {path}')
    hashes = read_json(out/'checksums.json')
    if not isinstance(hashes, dict):
        raise ValueError('checksums.json must be a file-to-SHA256 object')
    required_hashes = {'scene.json', *(path for path, _ in assets)}
    if manifest.get('camera_views'):
        required_hashes.add(manifest['camera_views'])
    # A present browser bundle must be covered too; tiny data-only fixtures remain valid.
    required_hashes.update(str(p.relative_to(out)) for p in out.rglob('*')
                           if p.is_file() and p.suffix in ('.js', '.html', '.css'))
    missing_hashes = required_hashes - hashes.keys()
    if missing_hashes:
        raise ValueError('Missing checksums for: ' + ', '.join(sorted(missing_hashes)))
    for relative,sha in hashes.items():
        p=inside(out,relative)
        if not p.is_file() or digest(p)!=sha:
            raise ValueError(f'Checksum mismatch: {relative}')
    return {'status':'passed','assets':len(assets),'files':len(hashes)}


def package_demo(name, output):
    src=ROOT/'demo'/name
    manifest=read_json(src/'scene.json')
    from .uploads import pointer
    asset=inside(src,manifest['room']['asset'])
    if not asset.is_file() or pointer(asset):
        raise ValueError(f'Demo asset missing or stored as an LFS pointer: {asset.relative_to(ROOT)}. Run check-repo and restore-assets before packaging.')
    out=Path(output).resolve()
    out.mkdir(parents=True,exist_ok=False)
    shutil.copytree(src,out,dirs_exist_ok=True)
    finalize_package(out)
    return out
