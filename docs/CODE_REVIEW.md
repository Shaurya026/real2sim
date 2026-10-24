# Workflow and code review

Reviewed on 25 October 2026 against the local `room2sim-pipeline` source copied into `real2sim`. The workspace contained no Git metadata for these folders. `git clone https://github.com/Shaurya026/real2sim.git` failed with a DNS resolution error, and the web fetch failed. This review therefore does not establish parity with the current remote branch or a remote commit. No changes have been pushed.

## Does the code implement the proposed workflow?

It implements the main building blocks, with explicit configuration and human alignment between them. It does **not** currently provide a verified, autonomous end-to-end real-to-simulation system.

| Component | Evidence in code | Finding |
| --- | --- | --- |
| Video sampling | `stage_ingest` in `src/room2sim/pipeline.py` | FFmpeg extracts configured frames and records source hashes. Sampling timestamps are nominal. |
| Camera recovery | `stage_reconstruct` | Uses Nerfstudio's COLMAP path; checks at least three registered cameras. That minimum is a sanity check, not reconstruction quality validation. |
| Gaussian splatting | `stage_splat`, `src/room2sim/splats.py` | Actual Splatfacto train/export commands or a validated existing Gaussian PLY. Higher-order SH attributes survive crops. |
| Blender repair | `stage_repair`, `blender/repair_scene.py` | Deterministic tables/boxes/cylinders and exact mesh removal; optional source GLB. Browser +Y-up is converted to Blender +Z-up. No automatic Gaussian-to-mesh reconstruction stage. |
| GPT-6 Astra | `agents/review.py`, `agents/capture.mjs` | Separate evidence-driven Responses API reviewer, strict JSON schema, typed edits, isolated candidates. `run` does not call Astra. The reviewer supports splat-room candidates; the historical mesh-only demos cannot be repaired through `apply`. |
| SAM 3D | `stage_objects`, `backends/sam3d_infer.py` | Uses upstream `Inference(config, compile=False)` and `model(image, mask, seed)`, then `result['gs'].save_ply`. The adapter exports Gaussians and layout metadata, not a triangle mesh. |
| Full scene assembly | `stage_package`, `web/app.js` | Packages splats and meshes with relative assets, hashes, object poses and box proxies. Poses and duplicate removal require manual verification. |
| Interactive inspection | `web/`, `docs/mesh/` | Gaussian/GLB environment controls plus the new standalone mesh inspector. Kinematic movement and box checks are not rigid-body simulation. |

The SAM call signature and PLY export were checked against the [official upstream quickstart](https://github.com/facebookresearch/sam-3d-objects) and [single-object example](https://github.com/facebookresearch/sam-3d-objects/blob/main/notebook/demo_single_object.ipynb). The reviewer request structure was compared with [OpenAI's structured outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs). This is contract inspection; no live provider execution was performed.

## Important configuration behavior

`configs/office.json` has no `repairs` or `objects` entries. `repair` copies the room appearance without running Blender, and `objects` emits an empty selection. This is intentional optional-stage behavior, but presenting the default command as a completed Astra/Blender/SAM 3D result would be misleading.

To use the full configured path, provide a reviewed repair patch, real frame/mask pairs, a configured SAM environment, and capture-specific object alignment before initializing a new run. Astra reviews an already packaged candidate in a separate loop. If you need review before object generation, use a preliminary static-room run, review it, then initialize a fresh configured run using the accepted repair patch and existing splat. Automatic candidate promotion back into a run is not implemented.

A SAM-generated object does not erase the corresponding room Gaussians. The `background_removed` field records an operator assertion, not a segmentation test. Cropping is center-based AABB removal; it can remove background or leave boundary fragments. Hidden surfaces remain inferred or absent.

## Fixed during this review

| Issue | Impact | Change and regression coverage |
| --- | --- | --- |
| Frozen config not integrity checked | Editing `run/config.json` silently changed the recipe for later stages | Initialization stores its hash; loading a run rejects modified or unreceipted configs. Existing old runs need a new initialization. |
| Missing entries accepted in package checksums | An omitted asset or browser file could bypass checksum coverage | Require manifest, referenced assets, camera views, and present HTML/JS/CSS files in the inventory before checking hashes. |
| Review bound only to manifest | A package could keep the same `scene.json` while replacing assets or viewer bytes and updating checksums | Capture records manifest and checksum-inventory hashes; prepare and apply reject mismatches. Older captures/reviews need regeneration. |
| Malformed ASCII Gaussian rows | Missing/short rows could fail with an opaque indexing error | Validate row counts, property widths, and finite values before decoding. Reject duplicate property names. Source and prebuilt parser synchronized. |

The new test cases exercise changed package bytes with the same manifest, stale screenshot bindings, missing hash coverage, config mutation, and malformed PLY input. Existing crop, path, upload, and packaging tests still pass.

## Historical case versus current implementation

The original `room-to-robot` output contains actual splats, depth-fused surfaces, textured meshes, Blender source, USD exports, and saved validation receipts. Its chair was authored and fitted in Blender. Its object segmentation used SAM masks lifted to Gaussian membership. **SAM segmentation is not SAM 3D inference.** The saved status explicitly sets `sam3d_ran` to false.

The historical depth fusion, video atlas bake, detailed chair fitting, Bullet contacts, USD/Isaac handoff, and FiGS scripts belong to that earlier asset workspace. They are not recreated by the portable pipeline adapters. The new case-study importer preserves results for inspection and records their origin; it does not claim to reproduce them.

## Remaining verification and engineering gaps

- Execute a fresh camera/Gaussian/Blender/SAM run on a suitable configured GPU host, then retain run receipts and before/after images.
- Execute the live Astra call and verify the resulting scene visually; schema validation alone does not establish geometry quality.
- Complete browser QA for both viewers. This host refuses localhost binding and Chromium launch. The page has passed syntax/build/asset checks, not browser rendering checks.
- Implement and validate object triangle-mesh export if required downstream. A Gaussian PLY is not a collision mesh.
- Add measured scale, physically checked colliders and simulator execution before asserting robotics readiness. Isaac Sim and policy training remain unverified.
- Pin external environment/checkpoint versions for reproducible GPU runs. External object/repair specs remain input files rather than immutable snapshots; preserve them with your run evidence.

Review scope included the active CLI/orchestrator, config and path utilities, Gaussian loader/cropper, patch schema, SAM adapter, Blender script, review/candidate tools, browser viewer/shader/sorter/interaction code, asset-restoration tools, existing tests, configs and documentation. Vendored Three.js and archived reference methods were not re-audited as new project code.
