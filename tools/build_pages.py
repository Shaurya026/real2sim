"""Build the offline GitHub Pages mesh inspector. No network or dependencies.

python3 tools/build_pages.py --output _site
"""
import argparse
from pathlib import Path
import shutil
from check_mesh_site import check, ROOT
from render_guides import build_guides
from project_metadata import metadata
import json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'_site')
    p.add_argument('--repository',help='Optional destination owner/repo; otherwise use GITHUB_REPOSITORY or origin')
    p.add_argument('--ref',help='Optional source ref; otherwise use GITHUB_REF_NAME or commit')
    a=p.parse_args()
    source=(ROOT/'docs/mesh').resolve();target=a.output.resolve()
    if target==source or target.is_relative_to(source) or source.is_relative_to(target):
        p.error('Output must be separate from the source site')
    project=metadata(a.repository,a.ref)
    check(source)
    target.mkdir(parents=True,exist_ok=False)
    shutil.copytree(source,target,dirs_exist_ok=True)
    build_guides(target)
    (target/'project.json').write_text(json.dumps(project,indent=2)+'\n')
    (target/'.nojekyll').touch()
    print(f'GitHub Pages artifact ready: {target}')


if __name__=='__main__':
    main()
