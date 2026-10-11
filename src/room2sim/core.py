from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    tmp.replace(path)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def resolve(base, value):
    p = Path(value).expanduser()
    return p.resolve() if p.is_absolute() else (Path(base) / p).resolve()


def inside(base, value):
    """Resolve a package reference without letting it escape the package."""
    base = Path(base).resolve()
    p = resolve(base, value)
    if not p.is_relative_to(base):
        raise ValueError(f'Path escapes package: {value}')
    return p


def vector(value, n, label, positive=False):
    if not isinstance(value, list) or len(value) != n or any(
        isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in value
    ):
        raise ValueError(f'{label} must contain {n} finite numbers')
    if positive and any(x <= 0 for x in value):
        raise ValueError(f'{label} must be positive')
    return value


def transform(value):
    vector(value['position'], 3, 'position')
    q = vector(value['quaternion'], 4, 'quaternion')
    if abs(sum(x*x for x in q) - 1) > .001:
        raise ValueError('quaternion must be normalized (xyzw)')
    if not isinstance(value['scale'], (int, float)) or isinstance(value['scale'], bool) or not math.isfinite(value['scale']) or value['scale'] <= 0:
        raise ValueError('scale must be finite and positive; only uniform splat scales are supported')
    return value


IDENTITY = {'position': [0, 0, 0], 'quaternion': [0, 0, 0, 1], 'scale': 1}


def run_command(argv, log, cwd=None, timeout=None):
    """No shell, streaming log, no credentials captured in command receipts."""
    log = Path(log)
    log.parent.mkdir(parents=True, exist_ok=True)
    start = time.time()
    print('Running:', ' '.join(map(str, argv)), flush=True)
    with log.open('w') as out:
        try:
            subprocess.run(list(map(str, argv)), stdout=out, stderr=subprocess.STDOUT,
                           cwd=cwd, timeout=timeout, check=True)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(f'Command failed. Inspect {log}') from exc
    return {'argv': list(map(str, argv)), 'seconds': round(time.time()-start, 3), 'log': log.name}


def executable(env, default):
    value = os.environ.get(env, default)
    found = shutil.which(value)
    if not found:
        raise RuntimeError(f'Missing {value}. Install it in the stage environment or set {env}. See docs/SETUP.md.')
    return found


def ffmpeg():
    if os.environ.get('FFMPEG_BIN'):
        return executable('FFMPEG_BIN', 'ffmpeg')
    if shutil.which('ffmpeg'):
        return shutil.which('ffmpeg')
    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise RuntimeError('FFmpeg is not on PATH. Set FFMPEG_BIN to your already installed executable, or provide imageio-ffmpeg. See requirements.txt.') from exc
    return imageio_ffmpeg.get_ffmpeg_exe()


def load_config(path):
    path = Path(path).resolve()
    cfg = read_json(path)
    if cfg.get('version') != 1:
        raise ValueError('Config version must be 1')
    if cfg.get('backend') != 'splatfacto':
        raise ValueError('This release implements splatfacto; other backends need their own adapter')
    if not isinstance(cfg.get('videos'), list) or not cfg['videos']:
        raise ValueError('At least one video is required')
    for k in ('fps', 'max_frames', 'iterations'):
        if not isinstance(cfg[k], (float, int)) or isinstance(cfg[k], bool) or not math.isfinite(cfg[k]) or cfg[k] <= 0:
            raise ValueError(f'{k} must be finite and positive')
    if cfg['max_frames'] != int(cfg['max_frames']) or cfg['iterations'] != int(cfg['iterations']):
        raise ValueError('max_frames and iterations must be integers')
    transform(cfg.get('room_transform', IDENTITY))
    cfg['_base'] = str(path.parent)
    cfg['_path'] = str(path)
    return cfg


def clean_config(cfg):
    return {k: v for k, v in cfg.items() if not k.startswith('_')}
