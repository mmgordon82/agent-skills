---
name: airgap
description: "Use only when the user says a target is offline or air-gapped: build it without public fetches (mirrors, sensible pins, vendored assets), then prove it — run it isolated (Docker --network none, netns, Playwright offline) and audit that it contacts nothing outside."
---

# Air-gapped targets

Only when the user says the target is offline or air-gapped. Packaging defaults are in
`docker-packaging`. Two jobs: **build it** so nothing comes from the public internet, then
**prove it**: the program works without a network and doesn't try to reach one.

## 1. Build it

**Where does the build happen?** Default to the first case unless the user says they build on the
offline side.

- **Built online, shipped offline (common):** build the image on a connected machine, then move it
  across: `docker save app:1.2 | gzip > app-1.2.tar.gz`, carry the file over, `docker load -i
  app-1.2.tar.gz`. Build-time downloads are fine here; the image must just be complete, so nothing
  is fetched at run time. Build for the target's CPU (`docker build --platform linux/amd64`, see
  `run-validation`), and ship every image the stack needs (database, proxy), not only the app.
- **Built on the offline side:** everything below applies to the build too, including the mirrors
  and `docker build --network=none`. Only when the user builds there.

- **Packages come from internal mirrors** when the build runs offline. Pin versions so builds can't drift to something the
  mirror doesn't have, but pin each package at the level the program actually needs: the major or
  minor version that has the features it uses (`fastapi>=0.110,<1`, `node:22`, `postgres:16`),
  not an exact patch for everything. Exact pins only where one specific build matters (a known
  regression, a release image digest); the lockfile (`uv.lock`, `package-lock.json`, `go.sum`)
  already records the exact resolved versions.
- **Mirrors from settings (optional, opt-in).** The user may list them under `[offline]` in
  `${XDG_CONFIG_HOME:-$HOME/.config}/agent-skills/settings.toml`. When a key is set, use it:

  | Key | Use it as |
  |---|---|
  | `apt_mirror` | the APT source in the Dockerfile (replace `deb.debian.org` / `archive.ubuntu.com`) |
  | `pypi_index` | `UV_INDEX_URL` / `PIP_INDEX_URL`, or `[[tool.uv.index]]` with `default = true` |
  | `npm_registry` | `registry=` in the project `.npmrc` |
  | `go_proxy` | `GOPROXY` (add `GOSUMDB=off` or `GONOSUMDB` only if the mirror can't serve checksums) |
  | `container_registry` | prefix for every base image: `<container_registry>/<image>:<tag>` |

  No file, or a key empty or missing → the settings don't apply: work as you normally would, from
  the project's own config and what the user tells you. Never ask the user to fill in the settings
  file, and never invent an internal hostname. Keep checksum verification on.
- **Nothing is fetched at run time,** and at build time too when the build runs offline: no
  `curl | sh`, runtime CDN, telemetry, update checks, crash uploads, remote config, or lazy
  downloads on first use (models, browsers, WASM, plugins). Bake those into the image.
- **Vendor web assets:** fonts, JS/CSS libraries, icons, maps, source maps, WASM. Drop analytics.
- **Images** are built ahead of time and moved as files, or mirrored into an internal registry and
  referenced by its path.

Package-manager offline modes, `docker build --network=none`, and web-asset details:
[references/packaging.md](references/packaging.md).

## 2. Prove it

"It started" or "the request failed" is not proof. Pick the claims the user needs, then gather
that evidence:

| Claim | Evidence |
|---|---|
| Local features work without a network | Run it isolated and exercise a real local operation that succeeds |
| External features degrade well | Bounded failure, a useful error, no crash, no endless retry |
| It doesn't try to reach out | A list of every request or connection made, with zero outside the app's own hosts |
| The shipped image is complete | `docker load` the exact file you ship on a clean machine (or after `docker rmi`), run it with `--network none`, exercise it |
| The build is self-contained (only if built offline) | Build with networking off after preparing mirrors and caches |
| A site renders offline | Page loads complete, with no failed or third-party requests; cold and warm (service worker) separately |

### Pick the isolation

| Target | Use | It proves | It doesn't prove |
|---|---|---|---|
| Python/Go/Node CLI or server | Docker `--network none` (any OS), or `scripts/run-airgap.sh` (Linux netns) | No connection succeeded; local behavior works | That nothing was attempted |
| Several services | Compose network with `internal: true` | East-west works, egress doesn't | That no service has a second network |
| Website, request audit | chrome-devtools: load, then `list_network_requests` | Every host the page contacted | OS-level egress (WebRTC, workers outside the page) |
| Website, offline behavior | Playwright `context.setOffline(true)`, or chrome-devtools `emulate` `Offline` | How the UI behaves with no network | Host isolation |
| Whole browser, hard no-egress | Playwright and Chromium in one `--network none` container with the app | The site fully loads with no network at all | Nothing beyond that container |
| Shipped image | `docker load` the file, then `docker run --network none` | The image runs with nothing to download | That the build is reproducible offline |
| Offline build (optional) | `docker build --network=none` | Dependencies resolve locally | That no fetch was attempted |

Browser emulation is a UI test, not proof the machine can't egress. Docker `internal` networks are a
test topology, not a security sandbox. Browser recipes (request audit, native error catalogue,
disconnect a loaded page, PWA): [references/browser.md](references/browser.md). Docker, Compose
and per-language recipes: [references/environments.md](references/environments.md).

### Workflow

1. **Write the matrix.** Cold start, one successful local operation, each external operation,
   restart, build, relevant UI states. Expected exit status, output, error, and timeout for each.
2. **Prepare while online.** Install dependencies, compile, download browsers, pull images. Never
   install inside the isolated run.
3. **Verify the isolation** before trusting it. Inside the isolated environment:
   `python3 scripts/probe_network.py`. It checks loopback works and a public IP and hostname are
   unreachable; interface names are informational, not part of the verdict. Linux shortcut:
   `bash scripts/run-airgap.sh --probe -- <cmd>`
   runs the probe, then the command, in a fresh network namespace, and refuses to run without one.
4. **Run the scenarios.** Capture stdout, stderr, exit status, duration, screenshots. Assert the
   local success as well as the expected external failure.
5. **Audit attempts** when the claim is "doesn't try to reach out": the browser request list, or a
   logging proxy / DNS sinkhole / firewall log for other programs. A blocked request is evidence of
   an attempt, not of its absence.
6. **Scan source and shipped assets:** `python3 scripts/scan_public_hosts.py <src> <dist>`. Explain
   every hit; mark a reviewed exception inline with `airgap-ok: <reason>`. Exit 1 = unexplained hits.
7. **Report** in the format below. Don't hide a failed probe or a skipped scenario.

Script paths are relative to this skill's directory.

## Report

```markdown
# Airgap test: <target>
Verdict: <pass | partial | fail> — <one-sentence basis>

Isolation: <mechanism> · probe: <result> · state: <fresh/warm profile, image and browser versions>

| Scenario | Expected | Observed | Evidence |
|---|---|---|---|

Requests / egress audit: <hosts contacted, or "not measured">
Public-host scan: <result, each accepted hit explained>
Limitations: <emulation-only parts, untested channels, skipped scenarios>
```

**Fail** if isolation wasn't verified, a local-only operation fails, or an unexplained public
dependency remains. **Partial** if behavior passes but attempts weren't audited and the user asked
for that.
