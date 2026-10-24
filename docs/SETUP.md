# Required existing environments

For a complete own-video walkthrough, see [the execution guide](OWN_VIDEO.md).

The project assumes dependencies are already installed. It never installs packages, downloads checkpoints or accepts licenses automatically. Ask the person executing it to provide the paths/environment for these prerequisites.

| Stage | Prerequisites to provide | Configuration |
|---|---|---|
| Demo packaging / serving | Python 3.10+ | `python3 room2sim.py ...`; no Python packages needed |
| Frame extraction | FFmpeg with H.264/MOV decode and JPEG encode | On PATH or `FFMPEG_BIN` |
| Masks | Pillow | `requirements.txt` |
| Camera recovery | COLMAP and Nerfstudio `ns-process-data` | `NS_PROCESS_BIN` if outside PATH |
| Room Gaussians | CUDA-enabled PyTorch, gsplat, Nerfstudio | `NS_TRAIN_BIN`, `NS_EXPORT_BIN`; `requirements-reconstruction.txt` records the supplied desk stack |
| Blender repairs | Blender 4.2+ (Eevee Next and glTF exporter) | `BLENDER_BIN` |
| SAM 3D Objects | Configured Meta upstream checkout, CUDA extensions, accepted SAM License and checkpoints | `SAM3D_REPO`, `SAM3D_CONFIG`, `SAM3D_PYTHON` |
| Viewer rebuilding | Node 18+ and Three.js **0.170.0** already available | `web/package.json`; `THREE_MODULE_ROOT` can point to an existing Three.js package |
| Browser evidence | Node Playwright plus an available Chromium/Chrome | `agents/package.json`; optional `PLAYWRIGHT_MODULE`, `BROWSER_BIN` |
| Astra API review | Python OpenAI SDK and account access to `gpt-6-astra` | `requirements-review.txt`; `OPENAI_API_KEY`, optional `OPENAI_REVIEW_MODEL` |

Run `python3 room2sim.py doctor` to check the local stage executables and whether credential variables are configured. It prints only key presence, never key values. GPU availability and checkpoint health must be checked in each provider environment; `doctor` is not a GPU compatibility test.

Run with source directly, without installing the project:

```bash
python3 room2sim.py --help
```

Executable paths may point into separate environments; the orchestration process does not need to import Nerfstudio or SAM 3D. Sample declarations, to be replaced with your existing paths:

```bash
export FFMPEG_BIN=/existing/tools/ffmpeg
export NS_PROCESS_BIN=/existing/nerfstudio/bin/ns-process-data
export NS_TRAIN_BIN=/existing/nerfstudio/bin/ns-train
export NS_EXPORT_BIN=/existing/nerfstudio/bin/ns-export
export BLENDER_BIN=/existing/blender
export SAM3D_PYTHON=/existing/sam3d/bin/python
export SAM3D_REPO=/existing/sam-3d-objects
export SAM3D_CONFIG=/existing/sam-3d-objects/checkpoints/hf/pipeline.yaml
```

`SAM3D_PYTHON` must run with the upstream environment variables and shared libraries configured. The adapter passes `cwd=SAM3D_REPO` and imports its notebook inference API. Use upstream's environment and checkpoint setup; do not combine its dependencies with the historical Splatfacto stack. Pin your upstream checkout commit and preserve the checkpoint source/license before distributing results.

Official references:

- [Nerfstudio Splatfacto](https://docs.nerf.studio/nerfology/methods/splat.html) and [Gaussian export](https://docs.nerf.studio/reference/cli/ns_export.html).
- [SAM 3D Objects](https://github.com/facebookresearch/sam-3d-objects) and [upstream setup](https://github.com/facebookresearch/sam-3d-objects/blob/main/doc/setup.md).
- [GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra) and [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

No provider invocation, GPU job, or paid review was performed during code creation. No installations are needed to serve the included prebuilt demos. Keep credentials in your environment, outside source control and browser assets.
