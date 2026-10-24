"""Resolve destination repository links without assuming an owner or default branch."""
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import quote
ROOT=Path(__file__).resolve().parents[1]

def git_output(*args):
    try:
        cp=subprocess.run(['git','-C',str(ROOT),*args],capture_output=True,text=True)
        return cp.stdout.strip() if cp.returncode==0 else ''
    except OSError:
        return ''


def metadata(repository=None,ref=None):
    repository=repository or os.environ.get('GITHUB_REPOSITORY')
    ref=ref or os.environ.get('GITHUB_REF_NAME')
    if not repository:
        origin=git_output('remote','get-url','origin')
        match=re.fullmatch(r'(?:https://github\.com/|git@github\.com:)([\w.-]+/[\w.-]+?)(?:\.git)?/?',origin)
        if match:repository=match[1]
    if repository and not re.fullmatch(r'[\w.-]+/[\w.-]+',repository):raise ValueError('Repository must be owner/name')
    if repository and not ref:
        ref=git_output('rev-parse','HEAD')
    ref=ref or 'HEAD'
    repo_url='https://github.com/'+repository if repository else None
    return {'repository':repository,'repository_url':repo_url,'source_ref':ref,
            'source_url':repo_url+'/blob/'+quote(ref,safe='')+'/' if repo_url else None}
