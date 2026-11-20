# Offline packaging and dependency preparation

Prepare everything while online (or against the internal mirrors). The isolated run never installs.

## Package managers

| Ecosystem | Prepare | Verify with no network |
|---|---|---|
| uv / Python | `uv sync --frozen` against the internal index | `uv sync --frozen --offline` with the prepared cache |
| pip / Python | `pip download -r requirements.txt -d wheels` | `pip install --no-index --find-links ./wheels -r requirements.txt` |
| npm | `npm ci` from the lockfile / internal registry | `npm ci --offline` in a fresh workspace; call local binaries, not `npx` |
| Go | fill the module cache through `GOPROXY` | `GOPROXY=off go build -mod=readonly ./...` |
| Rust | `cargo vendor`, configure the vendored source | `cargo build --locked --offline` |
| Maven / Gradle | fill the local repository / cache | `mvn -o test` / `gradle --offline test` |
| .NET | restore from approved sources | `dotnet test --no-restore` |

A package manager's `--offline` means "only use the local cache", not "self-contained". Check it
from a fresh cache: a developer's long-lived cache hides missing artifacts.

## Images and builds

**Built online, shipped offline** (the common case): build on a connected machine, move files.

```bash
docker build --platform linux/amd64 -t app:1.2 .           # target CPU, not the build machine's
docker save app:1.2 postgres:16 | gzip > stack-1.2.tar.gz  # every image the stack runs
# carry stack-1.2.tar.gz across, then on the offline machine:
docker load -i stack-1.2.tar.gz
```

Ship a compose file that references exactly these tags, with no `build:` sections the offline side
can't run. Before shipping, prove the file is complete: `docker load` it where the images aren't
already cached and run with `--network none`.

**Built on the offline side** (only when the user builds there):

```bash
docker build --network=none -t app:airgap .     # whole build without network
```

```dockerfile
RUN --network=none uv sync --frozen --offline    # one step without network (BuildKit)
```

- Pre-pull or mirror base images first; `--network=none` doesn't make a missing base image appear.
- Don't add a `# syntax=` line just for this: it fetches a frontend image.
- Mount prepared caches explicitly and check no `RUN` step fetches from the public internet.

## Web assets and runtime behavior

- Vendor fonts, stylesheets, browser libraries, icons, maps, needed source maps, WASM, models.
- Remove runtime CDN imports; don't rely on the airgap to block them.
- Disable update checks, crash uploads, analytics, telemetry, remote config, license checks, or
  point them at an approved local service.
- Service workers can make a site look offline-ready only after a warm-up. Test cold and warm.
- Scan the built, minified assets too: a build plugin can inject a public URL after source review.

## Auditing attempts (not just failures)

An isolated run shows that public connections fail, not that none were attempted. To show
"no attempts":

1. Route the program through a logging proxy, DNS sinkhole, or firewall that allows only approved
   internal destinations.
2. Log every allowed and denied destination, including direct IPs.
3. Fail on any unexplained destination; match each one to source or to the public-host scan.
