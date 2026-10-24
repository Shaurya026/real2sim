from __future__ import annotations
import argparse
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import sys
from .core import ROOT, digest, ffmpeg, read_json, run_command, write_json
from . import pipeline


def parser():
    p=argparse.ArgumentParser(description='Room2Sim: video → splats → repairs → objects → browser')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor')
    s=sub.add_parser('check-repo'); s.add_argument('--root',default=str(ROOT))
    s=sub.add_parser('restore-assets'); s.add_argument('archive')
    i=sub.add_parser('init'); i.add_argument('--config',required=True); i.add_argument('--run',required=True)
    for name in ('ingest','reconstruct','splat','repair','objects'):
        s=sub.add_parser(name); s.add_argument('--run',required=True)
        if name=='repair': s.add_argument('--patch')
    s=sub.add_parser('package'); s.add_argument('--run',required=True); s.add_argument('--output',required=True)
    s=sub.add_parser('run'); s.add_argument('--config',required=True); s.add_argument('--run',required=True); s.add_argument('--output',required=True)
    s=sub.add_parser('demo'); s.add_argument('--scene',choices=['desk','office','pantry'],default='desk'); s.add_argument('--output',required=True)
    s=sub.add_parser('serve'); s.add_argument('directory'); s.add_argument('--port',type=int,default=8080); s.add_argument('--host',default='127.0.0.1')
    s=sub.add_parser('validate'); s.add_argument('directory')
    s=sub.add_parser('mask'); s.add_argument('--image',required=True); s.add_argument('--polygon',required=True); s.add_argument('--output',required=True)
    s=sub.add_parser('import-demo'); s.add_argument('video'); s.add_argument('--output',required=True)
    return p


def main(argv=None):
    a=parser().parse_args(argv)
    try:
        if a.command=='check-repo':
            from .uploads import check_checkout
            report=check_checkout(a.root); print(json.dumps(report,indent=2))
            if report['status']!='ready': raise SystemExit(1)
        elif a.command=='restore-assets':
            from .uploads import restore_assets
            print(json.dumps(restore_assets(a.archive),indent=2))
        elif a.command=='doctor':
            try:
                ffmpeg_bin=ffmpeg()
            except RuntimeError:
                ffmpeg_bin=None
            status={'python':sys.version.split()[0],'viewer_built':(ROOT/'web/dist/index.html').exists(),
                'ffmpeg':ffmpeg_bin,'blender':shutil.which(os.environ.get('BLENDER_BIN','blender')),
                'ns_process':shutil.which(os.environ.get('NS_PROCESS_BIN','ns-process-data')),
                'ns_train':shutil.which(os.environ.get('NS_TRAIN_BIN','ns-train')),
                'ns_export':shutil.which(os.environ.get('NS_EXPORT_BIN','ns-export')),
                'sam3d_repo_configured':bool(os.environ.get('SAM3D_REPO')),
                'openai_key_configured':bool(os.environ.get('OPENAI_API_KEY'))}
            print(json.dumps(status,indent=2))
        elif a.command=='init':
            print(pipeline.new_run(a.config,a.run))
        elif a.command in ('ingest','reconstruct','splat','repair','objects'):
            fn=getattr(pipeline,'stage_'+a.command)
            fn(a.run,a.patch) if a.command=='repair' else fn(a.run)
        elif a.command=='package':
            print(pipeline.stage_package(a.run,a.output))
        elif a.command=='run':
            run=pipeline.new_run(a.config,a.run)
            cfg=pipeline.run_config(run)
            pipeline.stage_ingest(run)
            if not cfg.get('existing_splat'): pipeline.stage_reconstruct(run)
            pipeline.stage_splat(run)
            pipeline.stage_repair(run)
            pipeline.stage_objects(run)
            print(pipeline.stage_package(run,a.output))
        elif a.command=='demo':
            print(pipeline.package_demo(a.scene,a.output))
        elif a.command=='validate':
            print(json.dumps(pipeline.validate_package(a.directory),indent=2))
        elif a.command=='serve':
            directory=Path(a.directory).resolve()
            if not (directory/'index.html').is_file(): raise ValueError('Directory must contain a packaged viewer')
            handler=functools.partial(SimpleHTTPRequestHandler,directory=str(directory))
            server=ThreadingHTTPServer((a.host,a.port),handler)
            print(f'Open http://{a.host}:{a.port} (Ctrl+C to stop)',flush=True)
            server.serve_forever()
        elif a.command=='mask':
            from PIL import Image, ImageDraw
            from .core import vector
            image=Image.open(a.image)
            polygon=read_json(a.polygon)
            if not isinstance(polygon,list) or len(polygon)<3: raise ValueError('Polygon requires at least 3 pixel points')
            for point in polygon:
                vector(point,2,'polygon point')
                if not (0<=point[0]<image.width and 0<=point[1]<image.height): raise ValueError('Polygon point outside image')
            dest=Path(a.output)
            if dest.exists(): raise ValueError('Mask destination exists')
            dest.parent.mkdir(parents=True,exist_ok=True)
            mask=Image.new('L',image.size,0)
            ImageDraw.Draw(mask).polygon([tuple(v) for v in polygon],fill=255)
            mask.save(dest)
        elif a.command=='import-demo':
            video=Path(a.video).expanduser().resolve()
            if not video.is_file(): raise FileNotFoundError(video)
            out=Path(a.output).resolve(); out.mkdir(parents=True,exist_ok=False)
            run_command([ffmpeg(),'-nostdin','-i',video,'-an','-vf','scale=960:-2','-c:v','libx264','-crf','28','-preset','fast','-movflags','+faststart',out/'demo.mp4'],out/'transcode.log')
            run_command([ffmpeg(),'-nostdin','-i',video,'-vf','thumbnail=120,scale=960:-2','-frames:v','1',out/'poster.jpg'],out/'poster.log')
            write_json(out/'provenance.json',{'source_name':video.name,'source_sha256':digest(video),
                'scope':'supplied historical demo recording; not evidence of this pipeline execution'})
    except KeyboardInterrupt:
        return
    except (ValueError,RuntimeError,FileNotFoundError,FileExistsError,KeyError,ImportError) as exc:
        print(f'Error: {exc}',file=sys.stderr)
        raise SystemExit(1)


if __name__=='__main__': main()
