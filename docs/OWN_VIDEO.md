# Use your own video: reconstruction, Astra review, and SAM 3D

This guide follows the current code, from a local room video to an editable browser package. Work from the repository root. The examples use `my-room`; choose new names for later attempts.

GitHub Pages hosts examples and this guide. It does not upload videos, keep API keys, run Blender, or provide GPU inference. Run the commands on your workstation or a configured GPU server; then serve the resulting package locally or host its static files.

## 1. Choose a machine and separate the environments

| Environment | What runs there | Requirements |
| --- | --- | --- |
| Pipeline | CLI, package validation, masks | Python 3.10+; Pillow for masks; FFmpeg or imageio-ffmpeg |
| Reconstruction | COLMAP, `ns-process-data`, `ns-train`, `ns-export` | Compatible NVIDIA/CUDA/PyTorch/gsplat/Nerfstudio installation |
| Blender | Typed geometry repairs and GLB export | Blender 4.2+ executable, with its own bundled Python |
| SAM 3D Objects | Selected image/mask inference | Upstream Linux/CUDA environment, checkpoint access, and sufficient VRAM |
| Review | Offline request preparation and the explicit Astra call | Separate Python environment with the OpenAI SDK |
| Browser evidence | Screenshots and object-control checks | Node 18+ with Playwright and an installed Chromium/Chrome |

Meta's official SAM 3D setup specifies Linux and an NVIDIA GPU with at least 32 GB VRAM. A laptop that can display the gallery is not necessarily able to run that backend. Use the [official SAM environment/checkpoint instructions](https://github.com/facebookresearch/sam-3d-objects/blob/main/doc/setup.md); keep its dependencies separate from Nerfstudio.

For reconstruction, follow the [official Nerfstudio installation](https://docs.nerf.studio/quickstart/installation.html), including its compatible PyTorch/CUDA and COLMAP prerequisites. [Splatfacto](https://docs.nerf.studio/nerfology/methods/splat.html) is the implemented room backend. `requirements-reconstruction.txt` records a historical stack, not a universal installer for every GPU or current upstream release. Record the versions and source revisions you actually use.

The orchestration process calls stage executables by path. It does not need all those Python dependencies in one environment. If your stages use different machines, copy the complete run/package plus needed source inputs and preserve configured paths; this CLI does not schedule remote jobs automatically.

## 2. Create the lightweight pipeline and review environments

These are first-time setup commands for the person running the project. No tool installs anything automatically.

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m venv .venv-review
.venv-review/bin/python -m pip install -r requirements-review.txt
```

Keep the pipeline environment active for the `python3` commands below. Windows users should use a Linux GPU host/WSL configuration compatible with the upstream backends and adjust activation/executable paths. The upstream SAM setup is not a native macOS workflow.

For first-time browser evidence setup:

```bash
cd agents
npm install
npx playwright install chromium
cd ..
```

If Playwright/Chrome are already installed, use `PLAYWRIGHT_MODULE`/`BROWSER_BIN` instead. The prebuilt scene viewer itself does not require an npm build. Browser capture is optional until you need Astra image review or browser QA.

## 3. Configure executables and credentials

```bash
cp .env.example .env
```

Edit `.env` with your actual paths. For example, point `NS_TRAIN_BIN` at the `ns-train` executable inside the reconstruction environment, and `SAM3D_PYTHON` at Python inside Meta's configured environment. Set `REVIEW_PYTHON` to the absolute path of `.venv-review/bin/python`. Quote values containing spaces.

| Variable | Meaning |
| --- | --- |
| `FFMPEG_BIN` | Existing FFmpeg executable; unset it to allow the imageio-ffmpeg fallback |
| `NS_PROCESS_BIN`, `NS_TRAIN_BIN`, `NS_EXPORT_BIN` | Existing Nerfstudio executables |
| `BLENDER_BIN` | Blender executable, not a Python interpreter |
| `SAM3D_PYTHON` | Python from the configured SAM 3D environment |
| `SAM3D_REPO` | Absolute upstream checkout containing `notebook/inference.py` |
| `SAM3D_CONFIG` | Absolute checkpoint pipeline YAML, commonly `checkpoints/hf/pipeline.yaml` |
| `REVIEW_PYTHON` | Shell helper for the separate OpenAI SDK environment |
| `OPENAI_API_KEY` | Your OpenAI API credential, used only by explicit review calls |
| `OPENAI_REVIEW_MODEL` | Requested review model, default `gpt-6-astra`; your account must have access |
| `PLAYWRIGHT_MODULE`, `BROWSER_BIN` | Optional existing browser tool paths; omit or unset unused entries |

Load the file explicitly in each new terminal:

```bash
set -a
. ./.env
set +a
python3 room2sim.py doctor
```

The scripts do not automatically load dotenv files. `.env` is ignored by Git. Keep keys out of JSON configs, browser files, screenshots, and published packages. ChatGPT access does not configure this script's API credential.

Check the external tools before spending time on a run:

```bash
"$NS_PROCESS_BIN" --help
"$NS_TRAIN_BIN" --help
"$NS_EXPORT_BIN" --help
"$BLENDER_BIN" --version
"$SAM3D_PYTHON" -c 'import torch; print(torch.__version__, torch.version.cuda); print("CUDA available:", torch.cuda.is_available()); assert torch.cuda.is_available()'
"$REVIEW_PYTHON" -c 'import openai; print(openai.__version__)'
```

`doctor` reports executable availability and whether variables are set; it does not authenticate to OpenAI, verify checkpoint access, or certify GPU compatibility. Obtain/download the gated SAM checkpoint in its upstream environment before continuing. Keep upstream runtime library variables active when calling that interpreter.

## 4. Prepare your capture and configuration

Record one mostly static room with overlap, camera translation, varied viewpoints, and object close-ups. Avoid cuts between unrelated rooms, motion blur, moving people, and relying on reflective/textureless surfaces. Capture a known distance if you need metric scale; monocular reconstruction does not establish it automatically.

Put the video at `inputs/my-room.mp4`. The supplied configuration is `configs/my-video.json`:

```json
{
  "version": 1,
  "title": "My room — first reconstruction",
  "backend": "splatfacto",
  "videos": ["../inputs/my-room.mp4"],
  "fps": 2,
  "max_frames": 240,
  "iterations": 15000,
  "units": "uncalibrated",
  "room_transform": {"position":[0,0,0],"quaternion":[-0.7071067811865476,0,0,0.7071067811865476],"scale":1},
  "camera": {"position":[3,2,3],"target":[0,0,0]}
}
```

`fps` is extraction sampling rate. `max_frames` is a per-video limit, so these defaults retain approximately the first two minutes at 2 fps; adjust them for your capture. `iterations` is the Splatfacto training target, not an Astra setting. The sample room transform is a provisional Z-up to Y-up conversion, not a guarantee about your reconstructed axes. Inspect orientation and camera framing in the browser before judging the result.

All config paths resolve relative to the config file. Object image/mask paths later resolve relative to their object spec. CLI file arguments resolve from the current working directory.

## 5. Reconstruct a first, static room

```bash
python3 room2sim.py init --config configs/my-video.json --run runs/my-room-v1
python3 room2sim.py ingest --run runs/my-room-v1
python3 room2sim.py reconstruct --run runs/my-room-v1
python3 room2sim.py splat --run runs/my-room-v1
python3 room2sim.py repair --run runs/my-room-v1
python3 room2sim.py objects --run runs/my-room-v1
python3 room2sim.py package --run runs/my-room-v1 --output site/my-room-v1
python3 room2sim.py validate site/my-room-v1
python3 room2sim.py serve site/my-room-v1
```

Open http://127.0.0.1:8080. Stop the server with Ctrl+C before reusing the terminal. On a remote host, forward the server port to your workstation.

This first config intentionally has no `repairs` or `objects`. Those two stages record an unchanged room and empty object list, so they need neither Blender nor SAM inference. This gives you a baseline to inspect before adding repairs. It is not evidence that GPT or SAM ran.

Check these outputs before moving on:

- `runs/my-room-v1/capture.json`: extracted frames and source hashes.
- `runs/my-room-v1/coverage.json`: registered cameras and coverage fraction; the three-camera minimum is only a sanity check.
- `runs/my-room-v1/appearance/room.ply`: actual Gaussian output.
- `runs/my-room-v1/logs/`: FFmpeg, COLMAP, training, and export logs.
- `site/my-room-v1/scene.json`: room transform and portable package references.

`init` freezes and hashes its config. Do not edit `runs/.../config.json` or rerun completed stages into their existing directories. A failed stage can leave partial evidence; use a fresh run when retrying. Preserve the source config and any external patch/object specs with your experiment notes.

## 6. Ask GPT-6 Astra to review and propose repairs

Choose representative original frames under `runs/my-room-v1/frames/`. The example below uses the guaranteed first extracted frame; select a sharper, more informative frame if needed.

```bash
node agents/capture.mjs site/my-room-v1 review-work/my-room/before
"$REVIEW_PYTHON" agents/review.py prepare --package site/my-room-v1 \
  --evidence review-work/my-room/before --output review-work/my-room/request \
  --source-images runs/my-room-v1/frames/capture-00-frame-000001.jpg
```

These commands capture/prepare evidence without calling the model. Inspect `request.json`, the copied images, and `response.schema.json`. Preparation binds the package hashes, source frames, Gaussian bounds, browser evidence, and available mesh names. Review images must be PNG/JPEG/WebP, no larger than 8 MiB each, with at most eight images total.

The next command makes the explicit paid API call:

```bash
"$REVIEW_PYTHON" agents/review.py call review-work/my-room/request
```

The implementation sends a Responses API request with images and strict structured output. See [official OpenAI structured outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs). It uses the configured model, disables SDK retries, and saves the review, typed patch, and API receipt. Model/account access and actual response quality must be checked on your account.

Read `review.json` before applying it. A `pass` verdict needs no repair. An `uncertain` verdict means coordinates/evidence are insufficient; improve the evidence rather than inventing a crop. Only a `repair` verdict with nonempty validated operations can be applied:

```bash
"$REVIEW_PYTHON" agents/review.py apply --package site/my-room-v1 \
  --review review-work/my-room/request/review.json --output site/my-room-reviewed
python3 room2sim.py validate site/my-room-reviewed
python3 room2sim.py serve site/my-room-reviewed
```

A mesh operation invokes `BLENDER_BIN`; a crop-only patch does not. Supported operations are table/box/cylinder creation, exact-name mesh removal, and Gaussian crops. For each proposed table/box/cylinder, Astra explicitly chooses `interactive`: true registers a movable repair with a local box proxy; false keeps structural geometry static. The viewer exposes movable Blender groups alongside existing objects. Human patches without this field remain static. Adding a repair does not erase its Gaussian ghost; removal needs a separately justified crop. This is constrained scene editing, not arbitrary GPT-authored Python execution or automatic detailed mesh sculpting.

Capture the candidate again, then prepare a fresh review if needed:

```bash
node agents/capture.mjs site/my-room-reviewed review-work/my-room/after
```

A valid package/patch is not a visual pass. Compare multiple viewpoints against source frames. `apply` supports Gaussian room packages; the historical mesh-only gallery scenes are not inputs for this workflow. If Astra returned `pass`, keep `site/my-room-v1` and use that package instead of `site/my-room-reviewed` in the next section.

## 7. Add manual Blender repairs when needed

For a human-authored patch, copy `configs/repair.example.json` to a new scene-specific file. Fit the position, dimensions, and rotation to the scene; do not apply the example table at its template coordinates.

Primitive repairs use browser/glTF +Y-up coordinates and Euler XYZ radians. Crops use source PLY coordinates before `room_transform`. Adding a mesh does not remove the old Gaussian object. Wide crops may destroy background; missing background needs separately justified completion.

The initial repair stage has already completed. To try another patch, create a fresh imported-room run using the approved package:

```bash
python3 tools/config_from_package.py --package site/my-room-reviewed \
  --video inputs/my-room.mp4 --output configs/my-room-repair-v2.json
python3 room2sim.py init --config configs/my-room-repair-v2.json --run runs/my-room-repair-v2
python3 room2sim.py splat --run runs/my-room-repair-v2
python3 room2sim.py repair --run runs/my-room-repair-v2 --patch configs/my-repair.json
python3 room2sim.py objects --run runs/my-room-repair-v2
python3 room2sim.py package --run runs/my-room-repair-v2 --output site/my-room-repair-v2
```

Create and review `configs/my-repair.json` before that block. `config_from_package.py` reads the actual manifest paths, preserves the room transform, and carries the approved mesh and existing objects forward. Reused objects retain their assets and do not invoke SAM again; new SAM object ids must be distinct. Skip `ingest`/`reconstruct` for this staged import; running the convenience `run` command would extract video again. The room is imported, not retrained. If an existing mesh is present, `repair` imports/exports it through Blender even with an empty patch.

If you use this optional repair candidate, substitute `site/my-room-repair-v2` for the room package in the following steps.

## 8. Select an object and create its mask

SAM 3D Objects accepts one image and a foreground mask per selected object. A mask is a same-size, white-foreground/black-background PNG. This is separate from automatic 2D segmentation: the repository includes a polygon helper, not an automatic text-prompt mask service.

Create the input directory first:

```bash
mkdir -p inputs/my-room
```

Inspect the chosen source frame, then create `inputs/my-room/bottle-polygon.json` with at least three image-pixel points. Use actual coordinates inside that frame, not this explanatory notation: `[[x1,y1],[x2,y2],[x3,y3], ...]`.

```bash
python3 room2sim.py mask --image runs/my-room-v1/frames/capture-00-frame-000001.jpg \
  --polygon inputs/my-room/bottle-polygon.json --output inputs/my-room/bottle-mask.png
cp configs/my-video-objects.example.json configs/my-room-objects.json
```

If you choose another source frame, update both the mask command and the object's `image` field. Inspect the mask overlay/alignment before inference. The adapter rejects empty masks and mismatched image dimensions.

Edit `configs/my-room-objects.json`. The template defines a `bottle` id, source image, mask, seed, a provisional pose/scale, and a provisional box collider. Those coordinates are not a fitted result. Keep `background_removed` false until you have actually checked room-object separation.

## 9. Run SAM in a fresh imported-room run

```bash
python3 tools/config_from_package.py --package site/my-room-reviewed \
  --video inputs/my-room.mp4 --objects configs/my-room-objects.json \
  --output configs/my-room-with-objects.json
python3 room2sim.py init --config configs/my-room-with-objects.json --run runs/my-room-objects-v1
python3 room2sim.py splat --run runs/my-room-objects-v1
python3 room2sim.py repair --run runs/my-room-objects-v1
python3 room2sim.py objects --run runs/my-room-objects-v1
python3 room2sim.py package --run runs/my-room-objects-v1 --output site/my-room-objects-v1
python3 room2sim.py serve site/my-room-objects-v1
```

The `objects` command invokes `SAM3D_PYTHON` in `SAM3D_REPO` with the configured checkpoint YAML. It runs inference for every selected object and saves `objects/bottle/splat.ply`, `inference.json`, source hashes, and statistics. The maximum is 16 selected objects per spec.

This adapter exports inferred Gaussians, not a final triangle mesh. The inferred layout metadata does not establish alignment with COLMAP. If the object is missing from view, check its package asset, selector entry, source-relative pose, scale, and camera before concluding inference failed. The gallery's bespoke bottle controls are separate from the generic viewer used for your new package.

## 10. Fit placement and proxies without rerunning SAM

Select the object in the generated viewer. Move/lift/rotate it, compare multiple source views, and export `placements.json`. Save that download at `review-work/my-room/placements.json`. To change scale, edit the selected object's positive uniform `transform.scale` in that export; the viewer's buttons do not scale objects.

Apply it into a fresh package:

```bash
python3 tools/align_package.py --package site/my-room-objects-v1 \
  --placements review-work/my-room/placements.json --fit-colliders \
  --output site/my-room-aligned-v1
python3 room2sim.py validate site/my-room-aligned-v1
python3 room2sim.py serve site/my-room-aligned-v1
```

This helper preserves source assets and viewer bytes, records the placements, and refreshes candidate checksums. It makes no inference or API call. `--fit-colliders` estimates local AABBs from Gaussian centers; inspect them with **Show bounds**, because they are approximate interaction proxies, not physical collision meshes. For a custom fit, add a local box `collider` to an object's placement entry; it overrides the estimated box. A degenerate box must be fitted manually.

Transforms use world position, normalized xyzw quaternion, and positive uniform scale. Collider center/dimensions are local to the object asset, before that transform. Reset returns to the placements in the currently loaded package, so reopening an alignment candidate makes the accepted placement its new reset baseline.

Clean motion also requires removal of the captured object from the room. Otherwise moving the SAM object exposes a duplicate. `background_removed` is an operator declaration, not an automated test. Review a room crop/repair first, or return to a fresh room-repair candidate and preserve the already-generated object evidence. Hidden surfaces and physical scale remain separate validation tasks.

## 11. Review, share, and troubleshoot

Capture your final candidate and compare it against the original frames. A new Astra call is optional and explicit; changed package bytes require a fresh capture and request. Keep the reviewed package, masks, configs, source frames, model/checkpoint versions, and operation receipts together.

Share only the self-contained package, and serve it over HTTP. You can copy an approved package under the static Pages source and link it deliberately before rebuilding; the gallery does not automatically publish arbitrary runs. Check that captures, credentials, and unwanted private imagery are not in the shared files.

| Symptom | Check or next step |
| --- | --- |
| `Missing ns-train` or another executable | Load `.env`; point the variable at the executable in its own environment |
| CUDA/SAM import error or out of memory | Verify the upstream environment, driver/extensions, checkpoint, and GPU capacity; this CLI has no CPU fallback |
| Too few registered cameras | Inspect sharpness, overlap, translation, reflections, and `logs/colmap.log`; recapture before trusting a scene |
| Output destination already exists | Use a new run/output/request name; do not delete or edit immutable receipts to force a retry |
| Browser shows no room | Serve over HTTP, inspect console errors, orientation, camera, asset paths, and file sizes |
| Object invisible or unusually large | Inspect PLY statistics, object pose and uniform scale; fit placement/proxy rather than retraining the room |
| Original object remains after moving | The room was not cleaned; propose a reviewed source-coordinate crop or repair |
| `Run config changed` / stale review | Start a new run, or recapture/reprepare evidence; do not add fake hashes to old evidence |
| Astra authentication, access, or billing error | Check the runner's API account, key, requested model, and usage; do not put the key in browser code |
| `uncertain`, refusal, or incomplete review | Improve source evidence/coordinates or reduce scope; no repair is applied automatically |
| Mask rejected | Check exact frame dimensions, white foreground, nonempty content, and image path |
| Collider fit is poor | Edit the local box and inspect multiple views; Gaussian-center bounds are only proxies |

## What has been checked

The commands, config-relative paths, CLI flags, stage dependencies, and import/alignment helpers are checked against the local implementation. Automated tests exercise offline import, typed candidate edits, configuration reuse, placement alignment, checksum preservation, and failure cases. This is an on-paper/offline contract check; it is not a fresh GPU reconstruction, live Astra/SAM/Blender run, or visual browser pass. Hardware, installed backend versions, source video quality, provider access, and final scene alignment must still be verified on the runner.

For the planned alternative approach, see [Future work: video models for 3D and world modeling](FUTURE_WORK.md).
