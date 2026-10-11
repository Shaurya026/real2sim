"""Adapter executed with SAM3D_PYTHON in Meta's upstream environment."""
import argparse
import json
from pathlib import Path
import sys

p = argparse.ArgumentParser()
p.add_argument('--repo', required=True)
p.add_argument('--config', required=True)
p.add_argument('--image', required=True)
p.add_argument('--mask', required=True)
p.add_argument('--output', required=True)
p.add_argument('--seed', type=int, default=42)
a = p.parse_args()
sys.path.insert(0, str(Path(a.repo).resolve()/'notebook'))
import numpy as np
from PIL import Image
import torch
from inference import Inference, load_image

if not torch.cuda.is_available():
    raise RuntimeError('SAM 3D Objects requires its configured CUDA environment')
image = load_image(a.image)
mask = np.array(Image.open(a.mask).convert('L')) > 127
if mask.shape != image.shape[:2] or not mask.any():
    raise ValueError('Mask must be nonempty, same size as image, white foreground on black')
out = Path(a.output)
out.mkdir(parents=True, exist_ok=True)
model = Inference(str(Path(a.config).resolve()), compile=False)
result = model(image, mask, seed=a.seed)
result['gs'].save_ply(str(out/'splat.ply'))
metadata = {'seed':a.seed, 'backend':'facebookresearch/sam-3d-objects',
            'coordinate_frame':'raw model output; placement explicitly configured, not automatically metric',
            'torch_version':torch.__version__, 'cuda':torch.version.cuda}
# Preserve inferred layout separately; never silently assume it aligns to COLMAP.
for key in ('rotation','translation','scale'):
    if key in result:
        value = result[key]
        metadata[key] = value.detach().cpu().tolist() if hasattr(value,'detach') else np.asarray(value).tolist()
(out/'inference.json').write_text(json.dumps(metadata, indent=2))
