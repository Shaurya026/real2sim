# Improvements backed by implementation and checks

The project developed from point and fragmented-mesh previews into continuous photographic rooms with separate movable objects. The changes below describe the implemented work and its evidence. They do not claim that missing observations were recovered as measurements.

## Connected surfaces from RGB-D observations

The initial TUM desk preview displayed 139,035 isolated points. TSDF integration connected depth observations into a triangle surface and retained full-resolution output separately from the browser mesh. Small disconnected components were removed, and browser geometry was reduced to 450,000 triangles. This addresses visible sampling gaps without implying that unseen backs or undersides were observed.

**Implementation:** [`build_surfaces.py`](../methods/rgbd/build_surfaces.py), [`build_surface_viewers.py`](../methods/rgbd/build_surface_viewers.py).

## Continuous walls and cleaner photographic surfaces

Raw video meshes contained irregular wall fragments, texture boundaries and projected furniture silhouettes. Fitted structural planes give walls, ceilings and tables continuous geometry. Calibrated projection, visibility rejection, robust color adjustment and feathered blending improve agreement between contributing photographs. Foreground exclusion removes chair and carton imagery from backgrounds when the corresponding solid objects are represented separately.

The blue-room completion retains 59,700 triangles and replaces or removes 157,293 raw scan triangles. That reduction records a change in representation, not a measured reconstruction-accuracy improvement. Twelve fitted structural planes and repaired furniture replace weak scan fragments. In the yellow room, photographed wall wear, glass tint, privacy-film bands and the door notice were restored after the initial completion looked too uniform. Carpet and blind completion reuse photographed materials; their unseen arrangements remain inferred.

**Implementation:** [`complete_surfaces.py`](../methods/video_1000021594/complete_surfaces.py), [`clean_carton_wall_residue.py`](../methods/video_1000021594/clean_carton_wall_residue.py), [`restore_photographic_walls.py`](../methods/video_1000021600/restore_photographic_walls.py), [`bake_surfaces.py`](../methods/video_1000021610_1611/bake_surfaces.py), [`complete_floor.py`](../methods/video_1000021610_1611/complete_floor.py), [`complete_blind.py`](../methods/video_1000021610_1611/complete_blind.py).

**Evidence:** [`completed_summary.json`](../evidence/video_1000021594/completed_summary.json), [`wall_texture_reference.json`](../evidence/video_1000021600/wall_texture_reference.json), [`floor_texture_reference.json`](../evidence/video_1000021610_1611/floor_texture_reference.json), [`blind_completion_reference.json`](../evidence/video_1000021610_1611/blind_completion_reference.json).

## Complete, independently movable chairs

Broken scan fragments were replaced with source-informed chair geometry. The moving office chairs separate seat, base and five wheels, allowing a roll-out, swivel and return with wheel rotation and moving contact shadows. The blue room has two animated chairs; the yellow room has one. Hidden chair structure and material details are fitted approximations.

The blue-room audit samples 121 poses per chair. It reports zero intersections with the checked tabletop and leg boxes, no overlap with the checked static chairs, and about 2 mm floor clearance in estimated scene scale. The yellow-room exported 9-second GLB animation has seven moving parts; 181 checked poses stay inside the room with about 2 mm minimum floor clearance. These are scoped geometric tests, not continuous collision proofs or rigid-body chair simulations.

**Implementation:** [`repair_chairs.py`](../methods/video_1000021594/repair_chairs.py), [`prepare_chair_motion.py`](../methods/video_1000021594/prepare_chair_motion.py), [`fit_furniture.py`](../methods/video_1000021600/fit_furniture.py), [`validate_chair_export.py`](../methods/video_1000021600/validate_chair_export.py).

**Evidence:** [`chair_motion_validation.json`](../evidence/video_1000021594/chair_motion_validation.json), [`chair_export_validation.json`](../evidence/video_1000021600/chair_export_validation.json).

## Continuous navigation and obstacle-aware tours

The viewers use interpolated viewpoints, eased scrolling, drag-to-look, keyboard walking and touch controls. Swept furniture checks limit movement through configured obstacles and allow sliding along them. Guided routes connect scene landmarks continuously and can be interrupted by the user. The original viewers also support source-frame comparison; that control is disabled in the bundled pantry demo because the raw source frames are omitted.

The yellow room's complete 26-second, seven-waypoint tour and pantry's 30-second, six-waypoint tour both report zero collisions and zero out-of-bounds samples against their configured proxy obstacles. Browser checks also cover controls, smooth presets, cancellation and WebGL errors. This validates the demo paths against the modeled environment; it does not establish a robot navigation map or physical clearance in the actual room.

**Implementation:** scene `viewer_template.html` files, [`plan_tour.py`](../methods/video_1000021610_1611/plan_tour.py), and scene `check_navigation.py` scripts.

**Evidence:** [`blue-room navigation`](../evidence/video_1000021594/navigation_validation.json), [`yellow-room navigation`](../evidence/video_1000021600/navigation_validation.json), [`pantry navigation`](../evidence/video_1000021610_1611/navigation_validation.json).

## Contact-supported carton and packet pickup

The top blue-room carton was separated from the static reconstruction and fitted as a closed object using visible corners and source-photo faces. Its supporting parcel was closed as well, so lifting the target reveals a solid supporting lid. Overlapping original scan triangles were removed to prevent a duplicate carton from remaining behind. The pantry similarly contains an independent packet and an open supporting carton.

| Check | Blue-room carton | Pantry packet |
| --- | --- | --- |
| MuJoCo maximum lift | 0.3857 m | 0.4643 m |
| Assumed mass | 0.6 kg | 0.04 kg |
| Positive-trial friction coefficient | 0.8 | 0.8 |
| Both-finger contact steps during carry | 1,849 | 1,849 |
| Object pose overrides / attachment constraints | 0 / 0 | 0 / 0 |
| Zero-friction control | Fails pickup; about 0.5 mm maximum lift | Fails pickup; about 1.8 mm maximum lift |

Distances inherit estimated scene scale. The trajectory is authored, environmental contacts use approximate proxies, and the packet is modeled as rigid. Very small final placement errors in the deterministic simulation are not real-world positioning-accuracy claims.

**Implementation:** [`fit_cartons.py`](../methods/video_1000021594/fit_cartons.py), [`simulate_carton.py`](../methods/video_1000021594/simulate_carton.py), [`configure_packet.py`](../methods/video_1000021610_1611/configure_packet.py), [`simulate_packet.py`](../methods/video_1000021610_1611/simulate_packet.py).

**Evidence:** [`carton_physics_validation.json`](../evidence/video_1000021594/carton_physics_validation.json), [`packet_physics_validation.json`](../evidence/video_1000021610_1611/packet_physics_validation.json).

## Repairing a false match between the two pantry videos

Identical printed artwork on two physically different cartons created a false camera connection. The initial problematic cross-clip image pair shared 127 reconstructed tracks. The corrected recipe excludes these known cross-zone matches while retaining genuine overlap. It also extracts 28 additional sharp frames around the real camera turn to restore temporal coverage.

After correction, the false pair shares zero 3D tracks. A genuine pair across the turn shares 65 tracks. The resulting joint model registers 177 of 214 selected images, with 31,701 sparse points and 0.8217 px mean reprojection error. OpenMVS fuses 2,205,365 dense points. The clean GLB contains 29 mesh nodes, 38,638 triangles, 11 embedded images and one pickup animation.

This repair uses scene-specific temporal zones and inspection of the repeated cartons; it is not a general automatic repeated-pattern detector. The rejected initial model is retained in the original workspace for diagnosis and is excluded from the final scene representation.

**Implementation:** [`reconstruct_corrected.py`](../methods/video_1000021610_1611/reconstruct_corrected.py), [`promote_corrected.py`](../methods/video_1000021610_1611/promote_corrected.py), [`check_match_bridge.py`](../methods/video_1000021610_1611/check_match_bridge.py).

**Evidence:** [`corrected_bridge_validation.json`](../evidence/video_1000021610_1611/corrected_bridge_validation.json), [`sparse_summary.json`](../evidence/video_1000021610_1611/sparse_summary.json), [`mvs_summary.json`](../evidence/video_1000021610_1611/mvs_summary.json), [`export_validation.json`](../evidence/video_1000021610_1611/export_validation.json).

## Deliverable validation

The scene export checks validate finite geometry and animation samples, triangle validity, embedded texture data and object transforms. Interaction checks exercise playback, pause, inspect and reset in the actual viewer. The recorded pantry tour contains 1,498 fully decoded frames at 25 fps, lasting 59.92 seconds. Browser-friendly WebM and MP4 copies were independently decoded after export.

The evidence JSON files record checks run on the original scenes. Packaging those reports does not mean that every experiment was rerun from scratch while preparing this repository. These checks make the demos reviewable within the recorded assumptions. They do not turn inferred surfaces into observations, authored motion into a learned policy, or a schema-valid USD export into an Isaac-tested robot task.
