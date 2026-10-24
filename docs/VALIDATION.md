# Validation scope — 25 October 2026

## Newly completed checks

- **36 Python tests passed**: Gaussian cropping and finite values, path confinement, typed patch validation, config loading, staged offline import/repair/objects/package, receipt tampering, asset recovery, LFS placeholders, modified-asset preservation, frozen-config integrity, checksum coverage, and stale browser/review evidence.
- **16 JavaScript tests passed**: interaction bounds, finite placements, binary header boundaries, 228,043-Gaussian desk decoding, non-Gaussian rejection, malformed ASCII rows, and duplicate property rejection.
- Four office/reference GLBs passed SHA-256, file-size, embedded-dependency, and declared geometry-inventory checks. Triangle counts are 59,716 / 70,000 / 129,060 / 62,280.
- The early PLY was converted to GLB and rendered as a static scientific preview from its actual triangles. This is not a browser screenshot.
- The GitHub Pages artifact includes the office mesh reference, original pantry viewer, yellow-room player, and architecture walkthrough. Its static build and JavaScript syntax checks pass; the embedded office package passes checksum validation.
- Demo package validations and checkout asset checks are recorded in `validation-summary.json` and `package-validation.json`.

Run the checks from the repository root:

```bash
python3 -m unittest discover -s tests -v
node --test web/tests/*.test.mjs
python3 tools/check_mesh_site.py
python3 tools/build_pages.py --output _site
```

Use a new build output directory; builders preserve existing results.

## Not established by these checks

Browser rendering and interaction QA remain pending: localhost serving returns `PermissionError: Operation not permitted`, and the existing Chromium process cannot launch in this sandbox. Syntax and asset checks do not establish visual correctness or mobile/browser performance. The existing Playwright capture tool can be run on a suitable host.

Fresh COLMAP/Gaussian training, Blender repair execution, SAM 3D inference, live Astra requests, Isaac/PhysX execution, metric calibration, and policy training were not run. No paid provider call or dependency installation was made. Historical captures, metrics, and validation receipts are identified as supplied evidence rather than new execution.

The initial clone was blocked by DNS. The user subsequently supplied a genuine checkout at `real2sim-upstream`, with origin `https://github.com/Shaurya026/real2sim.git`, based on commit `47785b5`. Changes were reconciled on `improve-project-pages-and-guide`; the actual upstream README was retained as the presentation base. Authenticated push, PR creation, Pages settings and hosted deployment remain unverified.

## Compatibility

New runs contain a `run_config_sha256` integrity receipt. Old runs without that receipt must be initialized afresh. New browser evidence and Astra reviews bind to the package checksum inventory in addition to the scene manifest; regenerate older evidence before applying a review. Do not manually add hashes to old evidence to bypass these checks.

## Presentation revision

The README restores the original refined office image and uses the supplied `pipeline.png` diagram, linking to a separate workflow explanation. The gallery links to the original office mesh reference and the pantry/yellow-room interactive examples; rough geometry remains an explicit diagnostic option. Authors are credited professionally; team random.py and the second-place result link to the supplied award announcement. LinkedIn content could not be fetched here, so recognition follows the user-provided attribution.

GitHub Pages is configured for relevant default-branch pushes and manual runs, with checks before deployment. A genuine checkout is now present; publication and repository Pages settings are not established by the local build.

## Original scene gallery and object controls

Thirteen original archive assets pass byte-for-byte SHA-256 and size checks. The original pantry HTML and its media are preserved. Embedded animation checks establish finite, increasing track data and actual motion: the yellow-room chair clip is 9 seconds, and the pantry snack clip is 14 seconds. Corrupt/nonfinite and duplicate-time regressions are covered.

The original office `bottle_31` mesh is explicitly selectable and focusable. Its source triangles are used by executable Three.js tests for pointer selection, hidden-geometry restoration, camera focus, world-space lift through the source axis conversion, and exact reset. Multipart rotation/reset is also checked. Required object meshes in all three scenes are validated by name and nonempty geometry. Pantry bottles are one original mesh and are exposed as a group. These are kinematic edits, not live physics.

The browser QA helper covers the gallery, office bottle controls, yellow-room animation/navigation, original pantry tour/pickup, and pantry bottle movement/reset. An actual browser run is still blocked by this environment's Chromium process restrictions. Mathematical/asset tests do not establish visual rendering, texture visibility, or browser event behavior.

## Own-video guide and future work

The guide commands were checked against the actual CLI parser, and its inline JSON matches the supplied configuration. Offline integration tests run Astra crop application, manifest-based room reuse, fresh staged packaging, and placement/collider updates without GPU inference. Alignment preserves source assets and viewer bytes. Destination repository/ref injection and guide rendering are tested. This establishes local command contracts and data flow, not upstream installation compatibility or successful live GPT/Blender/SAM execution.

The Pages guide is generated from the Markdown guide. Future video-model-to-3D work is identified as a proposal, with primary research links, benefits, limitations, and an evaluation plan. No video-model backend has been integrated.

## README and destination-link revision

Restored the original project summary and richer README scene demonstrations, including the original office, chair and gripper screenshots and pantry result table. Public workflow links are relative. The site checker rejects the personal fork URLs in HTML and primary project documentation. README, summary, workflow and Pages document links were checked locally; the Pages build passed with a different destination repository. Publication remains a post-merge maintainer step.

## Incremental Astra refinement update

Astra shape proposals now explicitly distinguish static structure from movable repairs. Movable Blender groups are registered with local box proxies and resolved from the repair layer by the viewer. Package reuse retains existing reconstructed objects and repair bindings. Tests cover the response contract, duplicate ids, missing exported nodes, candidate assembly using a local Blender-output fixture, object retention, world placement, and legacy axis transforms. These are offline checks; the Blender-output fixture is not a Blender execution or live model result. No new API call, GPU inference or browser rendering is claimed. The original README Mermaid diagram and presentation sections are retained.
