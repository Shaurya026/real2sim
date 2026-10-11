# Room2Sim review and fix task

Use GPT-6 Astra to review the supplied scene package and its browser evidence. Read the README, scene manifest, patch schema, capture logs and relevant source frames first. Inspect table edges, room/splat occlusion, object placement, duplicate originals, uncovered background, movement/reset and loading errors.

Report which findings are observed, inferred or still uncertain. Do not claim physical calibration or robot training. Do not guess a source-PLY crop volume from a screenshot.

For geometry, produce a version-1 typed patch using the existing table/box/cylinder/remove_mesh/crop_splats operations. Apply it only to a new candidate package. For browser issues, edit the relevant viewer files in a separate candidate checkout. Do not change input media, original artifacts, credentials or attribution. Do not install dependencies; assume the runner provides the environments described in docs/SETUP.md.

Run the relevant Python contracts, JavaScript parser/interaction tests, package validation and browser capture when the environment supports them. Review the full hybrid browser output from multiple viewpoints after changes. Keep before/after evidence. Stop when the evidenced issues are resolved, or record the specific remaining missing measurement/environment dependency. Do not promote or publish a candidate without an explicit user request.
