# Isolated environments: Docker, Compose, languages

`$SKILL` is this skill's directory. Build images and fill caches before the disconnected run.

## Docker `--network none` (works on any host OS)

Only loopback exists inside. Put the probe and the program in the same container:

```bash
docker run --rm --network none \
  -v "$PWD:/work:ro" -v "$SKILL/scripts:/airgap:ro" -w /work \
  app:airgap \
  sh -c 'python3 /airgap/probe_network.py && python -m myapp --local-only'
```

No `python3` in the image? Use any loopback-server + public-connect check that the image can run.
A published port or a host-side controller can't reach a `--network none` container: run the
client (tests, browser) inside it.

### Python app

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY wheels/ wheels/
COPY requirements.txt .
RUN pip install --no-index --find-links wheels -r requirements.txt
COPY . .
```

```bash
docker build -t app:airgap .        # online or against mirrors: prepares wheels into the image
docker run --rm --network none app:airgap python -m pytest tests/
docker run --rm --network none app:airgap sh -c '
  python -m myapp serve & sleep 2
  python -c "import urllib.request as u; print(u.urlopen(\"http://127.0.0.1:8000/health\").read())"'
```

Exercise a real local operation, not just the import: lazy downloads fail later, at first use.

## Linux network namespace

`scripts/run-airgap.sh --probe -- <command>` runs `probe_network.py` and then the command in a new
network namespace (bubblewrap, else `unshare -n`). It refuses to run if it can't create one. It
isolates networking only; it is not a security sandbox.

```bash
bash "$SKILL/scripts/run-airgap.sh" --probe -- python -m pytest tests/test_offline.py
bash "$SKILL/scripts/run-airgap.sh" --probe -- env GOPROXY=off ./bin/app --local-only
bash "$SKILL/scripts/run-airgap.sh" --probe -- ./target/debug/app --local-only
```

## Docker Compose: several services, no egress

```yaml
services:
  app:
    image: app:airgap
    networks: [airgap]
    environment:
      DATABASE_URL: postgres://postgres:test-only@db/postgres
  db:
    image: <internal-registry>/postgres:16
    networks: [airgap]
    environment:
      POSTGRES_PASSWORD: test-only
  test:
    image: app-tests:airgap
    networks: [airgap]
    depends_on: [app, db]
    command: ["python", "-m", "pytest", "tests/e2e"]

networks:
  airgap:
    internal: true
```

Attach every service only to `airgap`; one extra network silently restores egress. Add health
checks: `depends_on` doesn't wait for readiness. Run the probe from one service and exercise the
internal dependencies positively.

## Network faults short of "offline"

- Latency, loss, reordering: Linux `tc netem` inside the namespace or container.
- One host failing while others work: a DNS sinkhole, a proxy rule, or (browser) a Playwright
  route abort for that origin.

## What each observation proves

| Observation | Proves | Doesn't prove |
|---|---|---|
| Public request fails in isolation | No public connection succeeded in that run | That none was attempted |
| Offline browser screenshot looks right | That UI state in that browser | Host-wide no egress, WebRTC |
| Compose services talk internally | Internal dependencies are present | No service has an egress network |
| Offline build succeeds | Dependencies resolve locally there | No fetch was attempted, clean cache |
| Public-host scan is clean | No matched public strings in scanned files | Runtime-built URLs, direct IPs |
