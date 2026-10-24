# Stage execution and contracts

For a complete own-video walkthrough, see [the execution guide](OWN_VIDEO.md).

All commands below run from the repository root. Config video/asset paths are relative to the config file, not the caller's current directory. Command-line `--patch` is relative to your current directory. Outputs must use fresh destinations to preserve sources and failed-run evidence.

## Input and reconstruction

`init` freezes config JSON and its original path base, records the saved config hash, and rejects later config mutation. Older runs without the integrity receipt need a fresh initialization. `ingest` extracts JPEG frames at configured FPS, with a per-video `max_frames` limit and nominal sampling times. Review the frames before continuing: moving people, blur, reflections and cuts can break reconstruction. Videos of unrelated rooms belong in separate runs; do not concatenate them into one reconstruction.

`reconstruct` invokes `ns-process-data images`, then records registered camera count against extracted frames. A minimum of three cameras is a sanity check, not a quality threshold. `splat` either imports a validated existing Gaussian PLY or invokes Splatfacto optimization and Gaussian export. The default office config performs a fresh reconstruction; the desk config uses the supplied existing PLY.

For an import-only desk path without extracting video again:

```bash
python3 room2sim.py init --config configs/desk.json --run runs/desk-import
python3 room2sim.py splat --run runs/desk-import
python3 room2sim.py repair --run runs/desk-import
python3 room2sim.py objects --run runs/desk-import
python3 room2sim.py package --run runs/desk-import --output site/desk-import
```

## Blender repair

Inspect the browser environment, determine a poor table's position/dimensions, and create a repair patch from `configs/repair.example.json`. Patch `table`, `box` and `cylinder` operations have browser/glTF +Y-up coordinates; `rotation` is Euler XYZ radians, and color is RGB 0–1. Each repair has an id and reason. `remove_mesh` requires the exact imported mesh name.

```bash
python3 room2sim.py repair --run runs/office-v1 --patch configs/your-repair.json
```

Blender exports `repairs.glb`, saves `scene.blend` and captures **mesh-only** preview images. The browser composes the mesh in the world frame alongside the room splat. Do not interpret the Blender images as a full Gaussian scene review.

Adding a replacement mesh does not erase a bad Gaussian table. To remove one, add a `crop_splats` operation with source-PLY `min`/`max` bounds to the same patch. Bounds are applied **before** `room_transform`. Cropping preserves every retained vertex's SH, scale, rotation and opacity values. It removes Gaussian centers in a volume; it is not learned segmentation. Wide/anisotropic Gaussians can leave fragments across the boundary, and hidden background may be missing. Tight fit, alternate-view review and measured scene alignment remain necessary.

An existing mesh can be supplied with config `existing_mesh`. It must already be in the browser/glTF world frame. Blender imports/exports it with the usual glTF axis conversion; its coordinates must match the fitted room transform.

## SAM 3D selected objects

Choose a few objects and source frames. Make white-on-black PNG masks with the exact source-frame size. Any existing segmentation tool can generate them; this repo also provides a deterministic polygon helper:

```bash
# polygon.json is [[pixel_x,pixel_y], ...] with at least three points.
python3 room2sim.py mask --image runs/office-v1/frames/capture-00-frame-000020.jpg \
  --polygon configs/carton-polygon.json --output inputs/carton-mask.png
```

Copy `configs/objects.example.json` to your own object spec. Set the real image/mask paths and fit each output's `transform` and local `collider`. Add `"objects": "your-objects.json"` to the pipeline config **before init**. The object spec paths are relative to the object spec file. Then run `objects` in the configured SAM environment.

The adapter uses upstream `Inference(config, compile=False)`, `inference(image, mask, seed=...)` and `output['gs'].save_ply(...)`. It exports actual inferred object Gaussians and preserves inferred rotation/translation/scale as metadata. It does not assume those single-view estimates align with the COLMAP room.

Fit `transform.position`, normalized `transform.quaternion` in **xyzw** order and positive uniform `transform.scale` to place the object in the browser world. Fit `collider.dimensions` and `center` in the object's local PLY coordinates; the viewer applies the same rigid transform and uniform scale to both. Confirm alignment from multiple source/render views.

Room-object duplicates must be removed separately in the repair stage. `background_removed` is an operator declaration and is displayed in the UI; it is not an automatic ghost-removal test. The pipeline never invents missing background behind a moved object. When needed, use Blender surfaces to fill justified geometry and mark that completion as authored.

Empty object specs produce a valid static environment. The example object spec is not enabled by default because no masks or measured placements were supplied.

## Package, interaction and recovery

Packages contain relative assets, a `scene.json` manifest, original patch evidence, stage receipts and `checksums.json`. `validate` checks paths stay in the package, asset presence, Gaussian attributes/finite numbers, GLB headers and file hashes. It does not claim collision or visual accuracy.

The browser supports kinematic transforms, rotated box bounds, inter-object overlap rejection, optional authored world AABB obstacles and placement export. Static room meshes are not automatically collision geometry. Walk mode is free camera exploration. Browser depth uses approximate Gaussian center depth against mesh depth; verify mixed occlusion visually, especially around transparent surfaces.

Each stage records outputs by hash. Dependencies must pass receipt checks before the next stage. A failed stage can leave useful partial output and logs; use a **new run** when rerunning that stage. This release does not automatically delete outputs, resume training, change config mid-run or recover failed GPU jobs. Completed later stages can be invoked individually. An existing portable package can always be reopened independently of the original run paths.

The historical archive methods in `reference/legacy_methods` retain scene-specific assumptions and are reference material. The new pipeline calls only its own adapters, not those scripts.
