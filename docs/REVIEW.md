# Separate GPT environment for review and fixing

For a complete own-video walkthrough, see [the execution guide](OWN_VIDEO.md).

The primary pipeline builds scenes. `agents/` independently captures browser evidence, prepares GPT-6 Astra requests, proposes repairs and produces candidate outputs. Live API calls are explicit commands and require the runner's own environment/account. No keys are accepted through config JSON or exposed to the browser.

`capture.mjs PACKAGE OUTPUT` uses an already installed Playwright and browser. It loads the environment, records up to four scene viewpoints, moves the first selected object, captures it again, resets it and records console errors/reset agreement. This checks browser functionality, not measured geometry, physical dynamics or ghost-free editing. `PLAYWRIGHT_MODULE` may point to an existing Playwright package; `BROWSER_BIN` may point to existing Chrome. `ROOM2SIM_FILE_ROUTES=1` uses Playwright file-backed request routing instead of a localhost server.

`review.py prepare` binds the current package manifest and checksum-inventory hashes, screenshots, console evidence, Gaussian bounds, source frames and exact mesh node names into an offline request folder. `call` sends one Responses API request with strict JSON schema output to `gpt-6-astra` by default. Configure another model only explicitly through `OPENAI_REVIEW_MODEL` if your account requires it. Refusal or incomplete output does not produce an applied patch. Uncertain coordinates should produce an uncertain verdict and no operations.

`review.py apply` checks both the reviewed scene and package inventory hashes, validates typed operations and writes an isolated candidate package. Shape operations (`table`, `box`, `cylinder`) include an explicit `interactive` boolean in model responses. Set it to false for structural surfaces and true for simple props intended to move. Applying a movable repair registers its exported Blender group as a selectable object with local box bounds; the viewer resolves it from the repair layer and supports movement/reset. Older human patches without this flag remain static. Adding a mesh does not remove overlapping Gaussians: justified source-coordinate crops are separate operations.

It supports splat rooms with optional repair meshes; supplied archive mesh demos are for historical comparison. It preserves the base package. Capture and review the candidate again before promoting it manually.

For browser implementation issues, rather than scene geometry:

```bash
python3 agents/fix_browser.py propose --evidence review-work/before --output review-work/browser-proposal
python3 agents/fix_browser.py apply --proposal review-work/browser-proposal/proposal.json \
  --output review-work/browser-candidate
```

The code fixer can change only seven named browser source files. It records source hashes, rejects stale proposals, writes a separate candidate and runs JavaScript syntax checks. It does not modify the live project, run generated shell commands, install dependencies or deploy anything. A candidate still needs review, an offline build using already installed Three.js, parser/interaction tests and fresh browser captures before manually adopting its changes.

If working directly inside a GPT/Codex coding environment, use [the separate review prompt](../agents/CODEX_REVIEW_PROMPT.md). Provide the repo and evidence folder. Scope code edits to the viewer and validated Blender operation schema, preserve provenance, rerun relevant checks and document unresolved issues.

A candidate application or syntax pass is not a visual review pass. Keep before/after screenshot sets, source-frame comparisons, operation reasons, model identity, API usage and manual alignment changes together. Repeat only as needed; the tools contain no autonomous paid-call loop.

Older captures and reviews without package bindings must be regenerated. Changes to package assets or viewer code require a fresh capture and review, even when `scene.json` stays identical.

Package reuse retains existing SAM objects and movable repairs without repeating inference. New object ids must be distinct. Regenerate evidence and requests after changing the viewer or response schema. The model proposes candidate repairs; before/after source comparison and interaction checks still determine whether they improve the scene.
