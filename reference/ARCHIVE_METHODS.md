# Reconstruction methods

Room2Sim collects the working recipes behind several indoor reconstruction and manipulation demonstrations. The scenes use different input modalities. The best-looking outputs combine recovered camera geometry and real photographs with scene-specific fitted surfaces and objects; they are not fully automatic or surveyed replicas.

## Method matrix

| Method | Inputs and geometric evidence | Processing | Result and scope |
| --- | --- | --- | --- |
| RGB-D point fusion | TUM RGB images, registered depth and supplied motion-capture poses | Timestamp association, pose interpolation, back-projection, discontinuity filtering and voxel aggregation | Colored points; known-pose fusion rather than visual-only SLAM |
| RGB-D surface fusion | TUM or synthetic Redwood RGB-D frames, camera intrinsics and supplied poses | Open3D scalable TSDF integration, small-component removal and display-mesh decimation | Connected colored surfaces; unobserved surfaces can remain open |
| Surface-initialized Gaussians | Full-resolution reconstructed mesh, normals and colors | Estimate local sample spacing; orient thin anisotropic Gaussians along surface normals | Gaussian rasterization, without photometric training, densification or learned view-dependent color |
| Sparse-photo stereo experiments | AreaMapper RGB photos, calibration and ARCore poses | COLMAP camera refinement, CPU SGBM or normalized-correlation plane sweep, depth-consistency filtering and fusion | Experimental depth/mesh baselines; see the later solid reconstruction for the final output |
| Photo-textured solid reconstruction | AreaMapper photographs and image-supported camera estimates | COLMAP, OpenMVS multi-view depth, visibility-aware meshing/refinement, custom visible-face photo projection | Connected photographic surface; the low-resolution phone-depth stream is not fused into the final solid model |
| Video room reconstruction | RGB video, with no measured depth or supplied trajectory | Sharp-frame selection, COLMAP structure from motion, OpenMVS depth/mesh, fitted architecture and objects, calibrated texture projection | Navigable visual scene at an explicitly estimated scale |
| Image-to-object fitting | Four YCB can photographs, known relative viewing angles and published diameter | Annotated rim/crop fit, cylinder prior and photographic label projection | Independent visual mesh, collision cylinder and contact-tested pickup |
| Object interaction | Fitted object visual geometry, simplified colliders, assumed material properties | MuJoCo free-body simulation driven only through an authored gripper trajectory | Recorded contact-based pickup; selected chair motions instead use authored geometric animation |

Source recipes live in [`methods/`](../methods/). Input datasets, large intermediate caches and external reconstruction executables are separate dependencies.

## RGB-D baselines

[`methods/rgbd/`](../methods/rgbd/) contains timestamp association, point fusion, TSDF surfaces, viewer export and Gaussian initialization scripts. Registered TUM depth uses `depth / 5000`, while Redwood uses `depth / 1000`, in metres. Both use the documented registered-image projection with `fx = fy = 525`, `cx = 319.5`, `cy = 239.5` at 640 × 480.

The real TUM desk surface fuses 294 matched views at 6 mm voxel spacing; desk2 uses 318. The synthetic Redwood living-room sequence supplies clean depth and exact camera trajectories. Its visual cleanliness is supported by these inputs and should not be presented as evidence that ordinary RGB video provides equivalent measurements. Voxel spacing is an algorithm parameter, not an accuracy measurement.

Full meshes are retained separately from browser meshes capped at 450,000 triangles. The Gaussian initialization uses full reconstructed geometry and surface normals, not the reduced display mesh. A separate pretrained third-party reference was used locally for comparison; it is not a project reconstruction and is not redistributed here.

## AreaMapper methods

The 195844 capture has 13 photographs, with nine image-supported camera poses in the final solid output. Its recipes include CPU stereo matching, 256-hypothesis inverse-depth plane sweep, consistency filtering, and the later OpenMVS surface pipeline. The final custom texture projection replaced a defective texture atlas. The solid output has 4,097 shared vertices and 8,123 triangles.

The 210511 capture has 54 RGB/depth frames and ARCore poses. The initial TSDF recipe uses discontinuity-filtered 160 × 90 phone depth. Its low spatial sampling and inconsistent layers motivated an RGB multi-view rebuild. The final solid reconstruction supports all 54 photographs, reports 0.849 px mean sparse reprojection error, and contains 26,603 triangles. ARCore supplies approximate metric alignment, not independent surveyed accuracy.

The separate 210712 mosaic contains a floor image and projection metadata. No common-frame transform or original RGB-D sequence was supplied, so it is not incorporated into the 210511 geometry.

## RGB video pipeline

1. **Select sharp frames.** Sample time windows and retain frames with strong Laplacian sharpness scores. Preserve source clip, timestamp, frame index and image filename.
2. **Recover cameras.** Extract SIFT features, match views, triangulate and bundle-adjust a shared camera model. Inspect disconnected components and ambiguous repeated objects before promoting a reconstruction.
3. **Estimate dense geometry.** Undistort registered photographs; run OpenMVS depth estimation, multi-view consistency fusion, visibility-aware meshing, refinement and texture generation. Inferred multi-view depth is distinct from sensor depth.
4. **Fit a scene frame.** Estimate upright axes and major planes from calibrated geometry and selected landmarks. Resolve the remaining monocular scale using an explicitly assumed object or table dimension.
5. **Complete useful surfaces.** Fit continuous walls, floor, ceiling, tables and source-informed furniture. Remove overlapping scan fragments where fitted objects replace them. Back faces and weakly observed regions use documented geometric priors.
6. **Bake source appearance.** Project original photographs through the calibrated cameras, reject occluded/foreground samples, blend supported views, and complete remaining gaps using photographed material samples or fitted colors.
7. **Export and navigate.** Preserve separate mesh groups, photographic textures and camera references. Export GLB with a Z-up-to-Y-up root transform and an offline WebGL viewer with continuous motion, room bounds and furniture avoidance.
8. **Validate.** Check geometry, texture references, animation samples and browser behavior. Sample complete tour paths against the configured obstacle proxies. Decode delivered video files after recording.

The scene recipes intentionally retain fitted anchors, masks, material references and configuration files. These values encode work specific to the captures; replacing the video path alone does not create a reliable automatic reconstruction of another room.

## Interaction and simulation

The blue room provides independent bottle and carton contact simulations plus two movable chairs. The pantry provides a rigid snack-packet pickup. MuJoCo commands the gripper palm trajectory and jaw actuators; the target object remains a free body. Positive trials and zero-friction negative controls distinguish a contact-supported pickup from an object attached to a gripper.

The browser plays recorded simulator poses. It does not solve physics live or contain a learned grasp policy, full robot-arm controller, reachability planner or closed-loop visual feedback. Chair roll/swivel clips are authored animations checked against selected geometric obstacles; caster dynamics are not simulated. The packet uses a rigid proxy rather than flexible packaging mechanics.

USD assets and an Isaac runner are included for interoperability where available. USD structure was checked, but Isaac Sim/PhysX execution and Isaac Lab training were not validated. MuJoCo success does not establish real-world robot success.

## Scale and evidence

| Scene | Scale source | Main evidence |
| --- | --- | --- |
| TUM / Redwood | Supplied depth scale and camera trajectory | RGB-D metadata and surface settings |
| AreaMapper | ARCore alignment | Capture audits and sparse-camera reports |
| YCB can | Published 66 mm diameter | `object_fit.json`, `physics_validation.json` |
| Blue room, video 1000021594 | Assumed 0.21 m bottle base-to-neck height | [`provenance.json`](../evidence/video_1000021594/provenance.json), [`carton_physics_validation.json`](../evidence/video_1000021594/carton_physics_validation.json) |
| Yellow room, video 1000021600 | Assumed 0.95 m counter height | [`provenance.json`](../evidence/video_1000021600/provenance.json), [`navigation_validation.json`](../evidence/video_1000021600/navigation_validation.json) |
| Pantry, videos 1000021610 + 1000021611 | Assumed 0.80 m coffee-table height | [`orientation.json`](../evidence/video_1000021610_1611/orientation.json), [`sparse_summary.json`](../evidence/video_1000021610_1611/sparse_summary.json) |

Reprojection error measures consistency in source images, not metric reconstruction accuracy. Contact clearances, tour speeds, dimensions and lift distances in monocular scenes inherit the scale assumption. Hidden geometry, object mass and friction are estimates unless a specific source measurement is documented.
