# Attribution and distribution

This project retains supplied room-capture assets, the TUM desk splat and selected original archive methods. No blanket license is assigned to supplied media or the original archive. Choose a license for your project-owned code before publishing, while keeping third-party terms intact.

- `demo/desk` derives from the supplied `tum_desk_test_01-comparison` capture and trained Gaussian export. Preserve its metadata and consult TUM dataset terms: https://cvg.cit.tum.de/data/datasets/rgbd-dataset.
- `demo/office`, `demo/pantry`, their previews and the pantry recording derive from `room2sim_repository.zip`. Original notes are in `reference/ARCHIVE_THIRD_PARTY.md` and `reference/ARCHIVE_ATTRIBUTION.txt`. Room scale includes fitted assumptions; photographed packaging/signage remain their owners' property.
- `demo/media/supplied-demo.mov` is the user's supplied `random_py_demo_2.mov`, preserved as historical evidence. Public redistribution rights are not inferred from local access.
- Three.js 0.170.0 is MIT licensed. Every built viewer retains `vendor/THREE-LICENSE.txt`; its source was reused from an existing local cache to build the included offline viewer, without a download/install.
- The Gaussian review shader, PLY parser and sorter are project code; no external splat renderer is vendored.
- Nerfstudio, gsplat, COLMAP, FFmpeg, Blender, Playwright and the OpenAI SDK retain their upstream licenses. GPU/backend environments and weights are not bundled.
- SAM 3D Objects code/checkpoints use Meta's SAM License: https://github.com/facebookresearch/sam-3d-objects/blob/main/LICENSE. Obtain access and follow the pinned upstream setup separately; no weights are included.

The original proposal mentions SOUS VIDE and 3DGruT. They are reference alternatives, not bundled implementations or dependencies of this release. YCB assets are not included in the new demo selection.

## Historical office mesh case study

`docs/mesh/assets` derives from the supplied `room-to-robot` workspace: a Depth Anything depth-fused surface, captured-video texture atlas, and authored Blender chair/floor repair. The GLB source hashes and conversion receipt are in `docs/mesh/assets.json`. Original output receipts and selected historical images are retained in `docs/mesh/evidence` and `docs/mesh/assets`. These are supplied project assets, not newly generated SAM 3D results.

The inspection page vendors Three.js 0.170.0 and three required addon modules from the same existing viewer distribution. Its MIT notice is retained at `docs/mesh/vendor/THREE-LICENSE.txt`. NumPy and Matplotlib are optional local tools for rendering the static early-mesh preview; they are not bundled or required by the inspector.

## Original scene gallery

The pantry viewer, original recording, original screenshots, yellow-room GLB, and image-derived YCB can assets are preserved from `room2sim_repository.zip`; entry paths and hashes are recorded in `docs/mesh/original-assets.json`. The original pantry viewer is embedded without source changes. The gallery, yellow-room player, and optional object controls are new presentation code. `docs/mesh/scene-attribution.txt` preserves the archive's attribution, including CC BY 4.0 attribution for the YCB-derived can asset and grasp screenshot. Original GLBs are unchanged; object edits happen in browser memory.
