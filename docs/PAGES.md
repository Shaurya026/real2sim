# Publish the Real2Sim scene gallery

The project pages live in `docs/mesh/`. They use original project media and scene assets, with locally bundled viewer libraries. No inference backend or API key is required.

## Experiences

| Path | Content |
| --- | --- |
| `/` | Gallery: office environment and mesh reference, pantry, and yellow room |
| `/environment/` | Textured office with walk/orbit modes, bottle/carton controls, reset and placement export |
| `/analysis.html#office` | Original first-office mesh with bottle/carton controls, plus the later room and early-surface references |
| `/pantry/` | Original pantry viewer plus a separate object-controls mode for bottles, snack packet, and carton |
| `/booth/` | Yellow room with the original animated GLB, chair/folding-chair controls, timeline, cutaway, and free camera inspection |
| `/workflow.html` | Separate architecture walkthrough with the supplied pipeline diagram |

The gallery features the office, pantry and yellow room as interactive environments. The office also has a separate mesh-analysis view. The office environment supports walk mode (WASD and Q/E, drag to look, Esc to exit), orbit inspection, bottle/carton selection, movement, reset and placement export.

The original pantry HTML, recording, model, and screenshots are copied byte-for-byte from `room2sim_repository.zip`. The yellow-room GLB is also unchanged; its player is new. `original-assets.json` records archive entry paths, sizes, and hashes. The gallery video uses `preload="none"`; scene geometry loads when an example is opened.

## Local preview

From the repository root:

```bash
python3 tools/check_mesh_site.py
python3 -m http.server 8080 --bind 127.0.0.1 --directory docs/mesh
```

Open http://127.0.0.1:8080. The pantry viewer embeds its original renderer and scene. The yellow-room player and office inspector use local Three.js modules. HTTP hosting is required for module/fetch-based pages.

## GitHub Pages

Publish from the destination repository after merge. Until its first successful deployment, the README uses downloadable examples and local-preview instructions; it does not advertise a contributor fork as the project website. After deployment, add the returned URL to the destination repository About panel and optionally replace the short README setup note with that link.

1. Merge the source and `docs/mesh` assets into the default branch.
2. In **Settings → Pages → Build and deployment**, choose **GitHub Actions**.
3. Relevant default-branch pushes run **Publish project pages**, or select it under **Actions → Run workflow**.
4. Use GitHub's returned deployment URL. The address depends on the destination repository and its Pages settings.

The workflow validates assets and source logic, builds `_site`, uploads the static artifact, and deploys through the `github-pages` environment. Pull requests run checks without deployment. Pages settings and hosted availability are not verified from the restricted development workspace.

To build the same artifact locally:

```bash
python3 tools/build_pages.py --output _site
```

Use a fresh destination. The page source includes its scene assets; no downloaded demo bundle is needed for this build. Raw captures, checkpoints, credentials, and runtime folders are excluded.

## Validation

The site checker verifies four office mesh inventories and the required named object geometry, the retained office package, original-asset hashes, embedded GLB animation tracks, and local page links. Original screenshots/recordings are historical evidence. Static checks do not establish browser rendering or real-robot behavior.

With an existing Playwright/Chromium installation:

```bash
node tools/check_mesh_browser.mjs verification-work/mesh-browser
```

The helper checks the office inspector and yellow-room animation, plus the gallery and pantry page. It uses file-backed HTTPS routes and installs no dependencies. `PLAYWRIGHT_MODULE` and `BROWSER_BIN` may point to existing installations. Browser execution remains subject to the host environment.

## Source and attribution

See [original-assets.json](mesh/original-assets.json), [scene attribution](mesh/scene-attribution.txt), and [third-party notices](../THIRD_PARTY.md). The YCB can model and original grasp screenshot retain their dataset attribution; the gallery focuses on the office reference, pantry, and yellow room.

## Bottle visibility and controls

The office bottle is the original `bottle_31` node. It is explicitly listed in the object selector, with a focus action that frames its actual geometry and restores visibility. Move/lift/turn/reset edits operate in world coordinates, preserving the source Z-up to glTF Y-up root conversion. The previous office editor URL also exposes the bottle now.

In Pantry, choose **Object controls** to edit the water-bottle group, snack packet, or carton. The original water bottles form one mesh, so they move as a group. The separate original tour and recorded pickup remain unchanged. These edits are kinematic, with no live contact simulation.

## Open your deployment

Open **Actions → Publish project pages → the latest successful run → deployment URL**, or use the website configured in this repository's About panel. GitHub supplies the actual address; do not copy another contributor's personal Pages URL into a fork's README.

Scene and guide navigation uses relative paths. The build resolves repository/source links from `GITHUB_REPOSITORY` and `GITHUB_REF_NAME` in Actions, or the local origin/commit when available. To preview a destination explicitly:

```bash
python3 tools/build_pages.py --output _site-preview --repository OWNER/REPOSITORY --ref BRANCH
```

Replace the uppercase values with the destination. The emitted `project.json` affects only links, not credentials or scene content. With no repository metadata, the local source uses internal guide links rather than linking to a particular contributor's fork. Both project paths and custom Pages domains retain relative navigation.

The new **Your own video** (`guide.html`) and **Future work** (`future.html`) pages are rendered from `docs/OWN_VIDEO.md` and `docs/FUTURE_WORK.md` during the build. Run `python3 tools/render_guides.py` after editing those files if serving `docs/mesh` directly. Source guides and Pages output share the same content.
