# Prepare the changes for GitHub

The reviewed changes are now in the genuine `real2sim-upstream` checkout on `improve-project-pages-and-guide`, based on `47785b5` from `https://github.com/Shaurya026/real2sim.git`. Review and commit from that checkout. No commit, push or PR has been created automatically. The earlier `real2sim` directory and review bundle are preserved as local preparation artifacts; the instructions below describe applying those artifacts to another checkout if needed.

## Apply to a real clone

Once GitHub is reachable, replace OWNER/REPOSITORY with the intended destination and run from the parent workspace:

```bash
git clone https://github.com/OWNER/REPOSITORY.git real2sim-upstream
git -C real2sim-upstream switch -c improve-mesh-case-study
python3 real2sim/tools/apply_review.py \
  --target real2sim-upstream --manifest real2sim-review-manifest.json
```

The last command checks all changed files against the reviewed baseline without writing. If every preimage matches, repeat it with `--apply`. If the remote has differing code, the helper stops; reconcile those differences before copying the changes. The manifest describes a **local baseline comparison**, not a verified GitHub diff. Use the included text patch for review; the manifest also lists binary additions.

After applying, run inside the real checkout:

```bash
python3 -m unittest discover -s tests -v
node --test web/tests/*.test.mjs
python3 tools/check_mesh_site.py
git diff --check
git status --short
```

Review the source changes and added `docs/mesh` assets, then commit and push the feature branch using your normal Git identity. Open a pull request against the intended destination repository. If the destination is Shreya's repository rather than the supplied Shaurya URL, use that repository as the PR base. The destination URL has not been inferred or changed automatically.

A commit email linked to your GitHub account is needed for attribution. The README names both hackathon contributors; a README credit does not itself establish GitHub commit authorship.

## Included changes

- Revised README with real mesh evidence and credit to Shaurya Gupta and Shreya Sajal.
- Three verified case-study GLBs, an actual early-mesh preview, source hashes, and selected historical receipts.
- Offline mesh inspection page and a GitHub Pages workflow for default-branch updates and manual publication.
- Pipeline config, package checksum coverage, Astra evidence binding, and Gaussian parser integrity fixes.
- Regression tests, CI, browser QA helper, and verification/code-review documentation.

The new `docs/mesh` GLBs are ordinary tracked binary assets; each is below 100 MB. The existing larger `demo` assets remain under the project's release-asset workflow and `.gitignore` rules. `.gitattributes` classifies binaries and does not configure Git LFS.

Keep runtime folders (`inputs`, `runs`, `site`, `_site`, `.venv`, `node_modules`, `review-work`, `verification-work`) outside commits. Do not copy the entire parent workspace into Git.

## Demo asset recovery

If original demo assets are absent from a fresh clone, use the existing bundle and manifest:

```bash
python3 room2sim.py restore-assets real2sim-demo-assets.zip
python3 room2sim.py check-repo
python3 room2sim.py demo --scene desk --output site/desk
```

The restorer checks paths, sizes, and hashes before replacing only missing files or Git LFS placeholders. It refuses unrelated local bytes. The new mesh inspection page does not need this demo bundle; its own assets are included under `docs/mesh`.

See [Pages setup](PAGES.md) to publish the inspector after merge. The workflow has not been run remotely.
