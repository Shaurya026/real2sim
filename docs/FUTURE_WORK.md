# Future work: video models for 3D and world modeling

The next method we plan to investigate is **video-model-assisted 3D reconstruction**. This is a research direction, not an implemented backend, completed benchmark, or demonstrated robot capability in this repository.

## Proposed experiment

Use the same captured room as the current baseline. Investigate either a video-conditioned geometry model that predicts spatial/depth representations, or a video model that proposes additional viewpoints followed by explicit 3D reconstruction. Preserve the original observations and identify generated content separately. Export a mesh or Gaussian representation, align it to the capture, and compare it with the existing pipeline.

These are different outputs: an image/video generator may produce plausible views without yielding a reusable 3D mesh, while a geometry model explicitly predicts spatial structure. [V3D](https://arxiv.org/abs/2403.06738) explores video-diffusion priors with geometry consistency and downstream mesh/Gaussian reconstruction. [Sora3R](https://arxiv.org/abs/2503.21082) studies video-prior-based inference of dynamic pointmaps. They motivate experiments; their reported results are not results of this project.

## Where video modeling could help world modeling

A useful world model should represent how a scene persists and changes over time, ideally conditioned on camera motion or actions. Video priors could help propose temporal transitions, scene completions, or varied visual conditions. A spatial reconstruction could provide persistent object locations, explicit geometry, and a coordinate frame in which to inspect those proposals.

That combination could support scenario prototyping, visual data augmentation, or candidate rollouts for later evaluation. It does not establish causally correct dynamics, collision geometry, or calibrated robot observations/actions. Interactive video-world generation also has documented consistency and control limits; see [DeepMind's Genie 3 discussion](https://deepmind.google/blog/genie-3-a-new-frontier-for-world-models/). Our proposed use is an experiment, not a claim of compatibility with a specific model/service.

## Potential benefits and limitations

| Aspect | Potential benefit to test | Limitation or failure to measure |
| --- | --- | --- |
| Temporal information | Use relationships across frames to reduce independent-view inconsistencies | Camera/object motion may be entangled; errors can drift over a sequence |
| Missing observations | Propose plausible occluded surfaces or new views | Plausible content can invent walls, objects, openings, or hidden structure |
| Appearance variation | Explore lighting, viewpoints, and scenario variations | Textures or object identity may change across views; generated pixels are not new measurements |
| Dynamic scenes | Propose object-motion sequences or time-varying geometry | Attractive motion need not obey contact, mass, friction, or conservation |
| Spatial structure | Convert proposals into explicit pointmaps, splats, or surfaces | Consistent-looking video does not guarantee metric scale, topology, or a stable mesh |
| Development effort | Reduce manual setup for some scene proposals | Inference/fine-tuning, geometry extraction, and repair can add substantial compute and dependencies |
| World-model use | Produce candidate futures or synthetic observations for evaluation | Controllability, repeatability, uncertainty, and real-world transfer require independent tests |

The benefits in this table are hypotheses for our experiment. We should report failures alongside improvements and keep observed versus generated regions distinguishable.

## How we would evaluate it

1. Keep a capture-only baseline and a fixed set of held-out **real** frames; never use generated frames as the held-out truth.
2. Compare reprojection/novel-view appearance, object identity, cross-view geometry, and long-sequence drift.
3. Check any available measured distances, openings, and object extents. Report scale ambiguity where no measurement exists.
4. Inspect mesh connectivity, missing/duplicated surfaces, collider alignment, object removal, and reset repeatability.
5. Record time, VRAM, manual corrections, checkpoint/seed, and per-region provenance.
6. Before robotics claims, evaluate collision/contact behavior and action-conditioned outcomes in a target simulator and against independent real observations where available.

The first comparison will be the original office mesh reference and the pantry/yellow-room captures. We have not yet selected or integrated a video-model backend. A strong visual example alone would not be sufficient to promote it into the verified pipeline.
