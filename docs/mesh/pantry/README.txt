TWO-VIDEO PANTRY RECONSTRUCTION

Inputs: user-supplied 1000021610.mp4 and 1000021611.mp4 (not included)

Open viewer.html in a desktop browser for the complete offline interactive scene.
Use Guided tour, or drag to look and WASD/arrows to walk; Q/E change height.
Pick up snack plays the recorded contact simulation. Pause, inspect and reset
are available. Room cutaway and Overview expose the complete object layout.

room_tour_demo.webm: browser-friendly recording of the tour and pickup.
room.glb: named room/object meshes and the pickup animation, with embedded textures.
Video: 59.92 seconds, 1440x1000, 25 fps.
GLB: 29 meshes, 38,638 triangles, 1 animation.

HOW IT WAS BUILT
214 sharp frames were extracted from the two portrait RGB videos. COLMAP
registered 177 views into one coordinate system with 31,701 sparse points.
Identical Bingo artwork on different cartons initially caused false matches;
those cross-zone links were excluded and 28 additional turn frames repaired
the real camera connection. Mean sparse reprojection error is about 0.822px.
The corrected multi-view stereo pass fused 2,205,365 points. This inferred
depth comes from image correspondence; the input did not contain measured
depth, LiDAR, tracked camera poses or a known physical dimension.

The clean demo fits continuous room surfaces to that geometry. Wall signs,
object fronts, the blind and material detail use actual video photographs.
Objects are separate solid fitted meshes. The white column has its own
geometry. Background object silhouettes are excluded before texture baking.
The weakly observed blind and carpet are completed using photographed material.
The original workspace also retains the raw photogrammetric reference.
It is omitted from this repository. Its COLMAP-to-viewer transform is:
viewer_position = scale * R * raw_position + origin.

WHAT IS ESTIMATED
Scale assumes the coffee table is 0.80m high. Hidden faces, some furniture
dimensions, unseen carpet arrangement and boundary completion are inferred.
This is a photo-informed demo, not a surveyed digital twin. The exterior office
and moving person are not reconstructed as part of the fitted pantry.

PICKUP
Only the gripper is commanded in MuJoCo. The packet is a free rigid body,
held by contact/friction without an attachment or object-pose overrides.
It lifts about 0.464m and returns to the carton. A zero-friction control fails
to lift it. Packet mass (40g), friction and scale are assumed; real flexible
packaging behavior is not modeled. This scene was not runtime-tested in Isaac.

CHECKS
The complete video files were decoded after export. Browser controls, continuous
tour clearance, pickup playback and reset were exercised. GLB geometry and
animation samples are finite and contain no degenerate triangles. Detailed
reports and calibration notes are included in ../../evidence/video_1000021610_1611/.

REPOSITORY DEMO
The source-photo comparison control is disabled because original capture frames
are omitted. The embedded photographic textures still show the captured room.
The GLB and WebM are original project outputs; other than this viewer UI and
portable path notation, this copy does not alter the recorded results.
