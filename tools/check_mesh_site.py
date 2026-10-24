"""Verify self-contained case-study assets and recorded geometry statistics."""
import json
import re
import struct
from pathlib import Path
import sys
from import_case_study import inspect_glb, sha
from check_scene_animations import check_animations
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from room2sim.pipeline import validate_package


def check(root=ROOT/'docs/mesh'):
    root=Path(root).resolve()
    # Public source documents must remain usable before a destination is published.
    for doc in [ROOT/'README.md', ROOT/'PROJECT_SUMMARY.md', ROOT/'docs/WORKFLOW.md', ROOT/'docs/PAGES.md']:
        if re.search(r'https?://shaurya026\.github\.io/',doc.read_text(),re.I):
            raise ValueError(f'Personal Pages URL in project documentation: {doc.name}')
    inventory=json.loads((root/'assets.json').read_text())
    for asset in inventory['assets']:
        p=(root/asset['file']).resolve()
        if not p.is_relative_to(root):
            raise ValueError('Asset escapes site')
        if sha(p)!=asset['sha256'] or p.stat().st_size!=asset['bytes']:
            raise ValueError(f'Asset differs: {p.name}')
        actual=inspect_glb(p)
        for key in ('triangles','vertices','meshes','embedded_images','nodes'):
            if actual[key]!=asset[key]:
                raise ValueError(f'Geometry inventory mismatch: {p.name}: {key}')
    for name in ['index.html','analysis.html','workflow.html','inspector.js','style.css',
                 'guide.html','future.html','manual.css','manual.js','project.json','project-links.js',
                 'room-player.js','room-player.css','object-controls.js','interaction-specs.json','package.json','booth/index.html',
                 'pantry/index.html','pantry/viewer.html','pantry/objects.html','original-assets.json',
                 'assets/pipeline.png','assets/office-preview.png',
                 'assets/rough-preview.png','assets/geometry-preview.png',
                 'evidence/historical-status.json','evidence/gaussian-evaluation.json',
                 'vendor/three.module.js','vendor/THREE-LICENSE.txt',
                 'vendor/addons/controls/OrbitControls.js','vendor/addons/loaders/GLTFLoader.js',
                 'vendor/addons/utils/BufferGeometryUtils.js']:
        if not (root/name).is_file():
            raise ValueError(f'Missing static site file: {name}')
    originals=json.loads((root/'original-assets.json').read_text())['assets']
    for item in originals:
        asset=(root/item['path']).resolve()
        if not asset.is_relative_to(root) or not asset.is_file():
            raise ValueError('Invalid original asset path')
        if asset.stat().st_size!=item['bytes'] or sha(asset)!=item['sha256']:
            raise ValueError(f'Original asset changed: {item["path"]}')
    interactive={}
    for scene,spec in json.loads((root/'interaction-specs.json').read_text()).items():
        asset=(root/spec['asset']).resolve()
        if not asset.is_relative_to(root):raise ValueError('Interactive asset escapes site')
        raw=asset.read_bytes();doc=json.loads(raw[20:20+struct.unpack_from('<I',raw,12)[0]])
        nodes={n.get('name'):n for n in doc['nodes']}
        for item in spec['objects']:
            for name in item['names']:
                node=nodes.get(name)
                if node is None or 'mesh' not in node or any(x==0 for x in node.get('scale',[1,1,1])):
                    raise ValueError(f'Interactive object missing or hidden: {scene}: {name}')
                primitives=doc['meshes'][node['mesh']]['primitives']
                if not primitives or any(doc['accessors'][p['attributes']['POSITION']]['count']<=0 for p in primitives):
                    raise ValueError(f'Interactive object has no geometry: {name}')
        interactive[scene]=[item['label'] for item in spec['objects']]
    animations={'yellow_room':check_animations(root/'booth/room.glb'),
                'pantry':check_animations(root/'pantry/room.glb')}
    class Links(HTMLParser):
        def __init__(self):super().__init__();self.targets=[]
        def handle_starttag(self,tag,attrs):
            self.targets.extend(v for k,v in attrs if k in ('href','src','poster') and v)
    for page in root.rglob('*.html'):
        content=page.read_text()
        if re.search(r'https?://(?:shaurya026\.github\.io(?:/|[\"\s])|github\.com/shaurya026/real2sim(?:/|[\"\s]))',content,re.I):
            raise ValueError(f'Personal fork link in public page: {page.relative_to(root)}')
        parser=Links();parser.feed(content)
        for target in parser.targets:
            url=urlsplit(target)
            if url.scheme or url.netloc or not url.path:continue
            destination=(page.parent/unquote(url.path)).resolve()
            if not destination.is_relative_to(root) or not destination.exists():
                raise ValueError(f'Broken page link: {page.relative_to(root)}: {target}')
    environment = validate_package(root/'environment')
    return {'status':'passed','original_assets':len(originals),'scene_animations':animations,'interactive_objects':interactive,'refined_environment':environment,'artifacts':len(inventory['assets']),
            'triangles':[a['triangles'] for a in inventory['assets']],
            'scope':'SHA-256 and GLB metadata; visual quality and browser behavior checked separately'}


if __name__=='__main__':
    print(json.dumps(check(sys.argv[1] if len(sys.argv)>1 else ROOT/'docs/mesh'),indent=2))
