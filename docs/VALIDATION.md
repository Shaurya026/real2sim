# Validation scope

Code creation checks completed locally:

- 9 Python tests: lossless Gaussian cropping, finite attribute checks, empty/in-place edit rejection, path confinement, patch operation validation, relative config handling, offline staged import→repair→objects→package, checksum tamper detection and stale-review rejection.
- 5 JavaScript tests: box contact/overlap behavior, finite placements, binary header/payload boundary parsing, full supplied desk PLY decoding as 228,043 anisotropic Gaussians, and non-Gaussian rejection.
- Python compilation and JavaScript syntax checks.
- Offline viewer build using cached Three.js 0.170.0 bytes, without an installation or network request after the user's instruction.
- Desk, office and pantry package validation: relative references, Gaussian/GLB asset structure and checksums.

Pending runtime checks:

- Browser launch and screenshots: blocked by the current workspace sandbox. Localhost serving returns EPERM; Chrome launch aborts under the restricted process environment. The capture script is included to run on the target machine. No browser success evidence is fabricated.
- Fresh video camera recovery/Gaussian optimization: not executed; requires the runner's existing CUDA/Nerfstudio/COLMAP environment.
- Blender repair/render: not executed; requires an existing Blender executable.
- SAM 3D inference: not executed; requires the configured upstream environment, licensed checkpoints and selected masks.
- Live GPT review/fix: not executed; requires the runner's API configuration. No paid call was made.

A dependency installation attempt before the user's no-install instruction could not reach package servers. No further installation attempts were made. The project runs its standard-library tests directly from source and includes prebuilt demo viewers.

Historical screenshots and recordings are clearly labelled as supplied archive/user outputs. They are not evidence of running the new adapters. This release has no robot policy training or physical dynamics validation.
