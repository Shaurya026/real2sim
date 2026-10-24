# Room2Sim: Turning Real Spaces into Interactive 3D Environments

The results below describe the original scene demonstrations. For the current Gaussian/Astra/SAM implementation, see the [workflow](docs/WORKFLOW.md) and [own-video guide](docs/OWN_VIDEO.md).

## The idea

Room2Sim converts ordinary room videos and photographs into explorable 3D environments. Beyond a stitched visual tour, selected objects become separate entities that can move or participate in simulated pick-and-place interactions.

The goal is to reduce the effort needed to create a useful simulation of a real workspace, making it easier to demonstrate and develop robot interaction before testing in the physical environment.

## What we built

- Continuous 3D room viewers with guided tours, free navigation and collision-aware movement.
- Two office reconstructions with photographic wall textures and repaired furniture.
- Movable chairs with roll, swivel and wheel animation.
- Separate carton objects with simulated grasp, lift, transfer and placement.
- A pantry reconstructed from two videos, with a snack-packet pickup demonstration.
- An image-based can reconstruction using four views, with a contact-based grasp example.
- Portable GLB exports, simulation/export scripts, recorded demos and validation reports.

## How it works

1. **Prepare the capture.** Select sharp video frames and preserve the relationship to their source timestamps.
2. **Recover camera geometry.** Match image features and estimate camera intrinsics, positions and orientations using COLMAP/PyCOLMAP.
3. **Reconstruct surfaces.** Use multi-view stereo for RGB footage, or integrate available depth and poses through TSDF fusion for RGB-D datasets.
4. **Clean the environment.** Fit continuous structural surfaces, remove unreliable fragments, repair furniture and project source photographs onto geometry.
5. **Separate interactive objects.** Give selected objects individual meshes, transforms and simplified collision shapes.
6. **Add movement and simulation.** Use smooth camera paths, articulated chair animation and MuJoCo contact simulation for pickup examples.
7. **Export and check.** Package browser viewers and GLB assets; check geometry, navigation, interaction playback and video decoding.

## Improvements made

**Cleaner walls and fewer seams.** Continuous fitted surfaces replace fragmented wall meshes. Visibility checks, foreground exclusion, photographic material completion and blending reduce holes, texture boundaries and duplicated object silhouettes.

**Complete furniture.** Broken chair fragments are replaced with source-informed fitted geometry. Seats, bases and wheels can move together while retaining separate articulated parts.

**More coherent navigation.** Continuous camera paths, smooth transitions and collision checks improve movement through the reconstructed rooms.

**Objects that can interact.** Cartons and the snack packet are separate from the room. Their grasp examples are driven by contact and friction, rather than attaching the object directly to the gripper.

**Corrected cross-video alignment.** Identical printed artwork on different cartons caused a false connection between the pantry videos. Scene-specific pair exclusions and additional frames around the real camera turn repaired that connection.

## Demonstrated results

| Pantry reconstruction | Recorded result |
| --- | --- |
| Selected RGB frames | 214 |
| Registered views | 177 |
| Sparse 3D points | 31,701 |
| Mean reprojection error | Approximately 0.822 pixels |
| Dense reconstructed points | 2,205,365 |
| Clean exported GLB | 29 mesh nodes; 38,638 triangles |
| Recorded tour | Approximately 60 seconds |
| Simulated snack lift | Approximately 0.464 m at estimated scene scale |

The grasp test also includes a zero-friction negative control: the object fails to lift when friction is removed. This checks that the demonstrated pickup depends on the modeled contact interaction. It does not establish real-world grasp success.

## How simulation helps

A reconstructed environment provides a visual and geometric context for testing navigation, object placement and interaction sequences. It supports repeatable demonstrations, controlled changes to object properties and early inspection of collisions or unreachable placements without repeatedly rearranging the physical room.

The current prototype demonstrates authored movement and simulated grasp sequences. A future robot-training workflow would add a robot model, measured calibration, task definitions, policy training and evaluation against physical observations.

## What is reconstructed and what is estimated

Visible appearance comes from the captures. Camera poses and RGB-video depth are estimated from image correspondence. Hidden surfaces, some furniture geometry, material completion and room scale use explicit assumptions because the videos do not provide complete coverage or a measured reference dimension.

Chair motion is authored animation. Pickup uses rigid-body collision proxies with assumed physical parameters. The project has not been validated as a real-robot system or through an Isaac runtime.

## Demo and technical material

- [Interactive pantry scene](docs/mesh/pantry/viewer.html)
- [Recorded tour and snack pickup](docs/mesh/assets/pantry-tour.webm)
- [Detailed methods](reference/ARCHIVE_METHODS.md)
- [Improvements and supporting evidence](reference/ARCHIVE_IMPROVEMENTS.md)
- [Setup and reproduction](docs/OWN_VIDEO.md)
