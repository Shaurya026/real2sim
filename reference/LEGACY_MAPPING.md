# What the original archive contributed

| Original method | New implementation / purpose |
|---|---|
| `repair_chairs.py`, `fit_furniture.py` | Source-informed mesh replacement pattern generalized into typed table/box/cylinder edits in `blender/repair_scene.py` |
| `complete_surfaces.py` | Explicit fitted completion and provenance, rather than assuming hidden geometry is recovered |
| `export_interaction_glb.py` | Separate selected object visuals and portable relative assets in scene manifests |
| `fit_objects.py` | Keep inferred dimensions/pose distinct from observations; SAM3D proposal placement must be fitted |
| `validate_interactive_assets.py` | Per-object record and output validation; new pipeline adds immutable hashes and typed transform checks |
| `room2sim_paths.py` | Historical path adapter retained for reference; new pipeline resolves config-relative paths and confines package references |

Selected original files are preserved verbatim under `legacy_methods/` and are not imported or executed by the new CLI. Their old input/output assumptions are not implied to be compatible with the new pipeline.
