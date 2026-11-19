---
name: web-perimeter-audit
description: "Use when auditing a live or staging web domain's perimeter before launch, or hardening nginx/Caddy/CDN edge config. Passive, non-destructive curl probes mapped to OWASP Top 10:2025 leads: exposed .git/.env/compose/lockfiles, CORS reflection, cache poisoning (X-Forwarded-Host), HSTS/CSP, cookie flags, stack-trace leaks, security.txt."
---

# Web perimeter audit (OWASP Top 10:2025 surface leads)

Run non-destructive, deterministic perimeter checks against web apps, APIs and CDN edges. Map observable edge findings to OWASP Top 10:2025 categories as perimeter leads, and verify fixes with reproducible checks before shipping.

## What perimeter probing cannot prove

Response headers, CDN cache behavior and disclosure files only show the publicly observable edge. Passing this checklist does not establish OWASP Top 10:2025 compliance. Report these as unverified by perimeter probing unless backed by separate code review and authenticated testing:

- **Authorization and object-level access control (A01:2025):** BOLA/IDOR, tenant isolation and privilege escalation need authenticated multi-role integration tests ([OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)).
- **Authentication and session lifecycle (A07:2025):** MFA enforcement, credential stuffing defenses, token rotation and server-side session revocation cannot be proven from `Set-Cookie` flags alone ([OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)).
- **Injection and business logic (A05 / A06:2025):** SQL/NoSQL/command injection, SSRF and race conditions need source analysis (SAST) and targeted DAST ([OWASP Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Injection_Prevention_Cheat_Sheet.html)). Use `security-hunt` for the code side.
- **Internal security logging and alerting (A09:2025):** audit trail completeness, tamper resistance and alerting must be verified inside the telemetry pipeline ([OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)).

## Safety contract

- Never send destructive payloads, brute-force traffic, or unisolated cache-poisoning probes against shared production cache keys.
- Before sending any `X-Forwarded-Host` or `X-Forwarded-Scheme` probe against a live target, first prove query-key isolation using fresh, validated hex cache-busters (`set -euo pipefail`, `CB_A=$(openssl rand -hex 8)`, `CB_B=$(openssl rand -hex 8)`):
  1. Fail closed before sending any request if `CB_A` or `CB_B` is empty, equal, or does not match `^[0-9a-f]{16}$`.
  2. Send a clean request with `?__cb=${CB_A}` (`--connect-timeout 3 --max-time 5`), repeat the identical request at most twice (max 3 requests total, `--max-time 5` each) to confirm a cache `HIT`, then send one clean request with `?__cb=${CB_B}` (`--max-time 5`) and verify it is a cache `MISS`.
  3. If `HIT` followed by `MISS` is not confirmed within those bounded attempts, abort the live probe and run it only against an isolated staging environment.
- Use a private `mktemp -d` working directory with `trap` cleanup for all captured headers and bodies. Never write to predictable shared `/tmp` filenames.
- Verify real HTTP responses rather than trusting framework defaults. Reverse proxies and CDNs often strip or override upstream headers.
- Treat `403 Forbidden` on directory roots (such as `/.git/`) as insufficient unless direct object paths (`/.git/HEAD`, `/.git/config`) also return `404`/`403`.
- Keep all checks local (`curl` and standard system tools). Only call external CLIs or remote scorecard APIs when the user explicitly opts in and approves sharing the target hostname.

## Workflow

### 1. Exposed artifacts, CORS and cache isolation (A01 / A02:2025)

1. **Direct git object and config exposure (`git-dumper` vector).** Disabling directory indexing on `/.git/` does not prevent repository reconstruction if object paths stay readable. Probe each path with a bounded, file-specific signature (`--connect-timeout 3 --max-time 5`) without printing sensitive contents:
   - `/.git/HEAD`: status `200` and the first line matches `^ref: refs/` or a 40-char hex SHA (`^[0-9a-f]{40}$`).
   - `/.git/config`: status `200` and the body contains `[core]` or a `[remote "` section header.
   - `/docker-compose.yml` (also `/compose.yaml`): status `200` and the body has a top-level `services:` block.
   - Environment config paths (such as `/.env`): status `200` and lines match `^[A-Z][A-Z0-9_]+=` without `<!DOCTYPE` or `<html`. Report only a boolean detection signal; never echo secret values.
2. **CORS arbitrary origin reflection.** Send `Origin: https://evil-probe.invalid` with `--connect-timeout 3 --max-time 5`. If the response reflects `Access-Control-Allow-Origin: https://evil-probe.invalid` together with `Access-Control-Allow-Credentials: true`, record a HIGH-priority lead. Escalate to CRITICAL only after confirming the endpoint serves authenticated or non-public user data in a browser context. Public endpoints that return identical unauthenticated content regardless of cookies are a lower-severity misconfiguration.
3. **Unkeyed header web cache poisoning.** Only after proving query-key isolation (`?__cb=${CB_A}` reaches `HIT` within 3 bounded requests while `?__cb=${CB_B}` returns `MISS`), or on an isolated staging host, run the bounded probe in a private temp dir:
   ```bash
   set -euo pipefail
   CB_A="$(openssl rand -hex 8)"
   CB_B="$(openssl rand -hex 8)"
   if [[ ! "${CB_A}" =~ ^[0-9a-f]{16}$ ]] || [[ ! "${CB_B}" =~ ^[0-9a-f]{16}$ ]] || [[ "${CB_A}" == "${CB_B}" ]]; then
     echo "Fail closed: invalid cache-buster entropy" >&2
     exit 1
   fi

   WORK_DIR="$(mktemp -d)"
   trap 'rm -rf "${WORK_DIR}"' EXIT

   TARGET_BASE="https://example.com/"
   # Step 1: prove query-key isolation (max 3 attempts for HIT on CB_A, then MISS on CB_B)
   CACHE_HIT=0
   for attempt in 1 2 3; do
     curl -sS --connect-timeout 3 --max-time 5 -D "${WORK_DIR}/iso_a_headers.txt" -o /dev/null "${TARGET_BASE}?__cb=${CB_A}"
     if grep -Eiq '^(cf-cache-status:\s*HIT|x-cache:\s*Hit|age:\s*[1-9])' "${WORK_DIR}/iso_a_headers.txt"; then
       CACHE_HIT=1
       break
     fi
   done
   curl -sS --connect-timeout 3 --max-time 5 -D "${WORK_DIR}/iso_b_headers.txt" -o /dev/null "${TARGET_BASE}?__cb=${CB_B}"
   if [[ "${CACHE_HIT}" -ne 1 ]] || ! grep -Eiq '^(cf-cache-status:[[:space:]]*MISS([[:space:]]|$)|x-cache:[[:space:]]*Miss([[:space:]]|$))' "${WORK_DIR}/iso_b_headers.txt" || grep -Eiq '^(cf-cache-status:[[:space:]]*HIT|x-cache:[[:space:]]*Hit|age:[[:space:]]*[1-9])' "${WORK_DIR}/iso_b_headers.txt"; then
     echo "Aborting live probe: query-key cache isolation not proven; use isolated staging." >&2
     exit 1
   fi

   # Step 2: isolated GET probe on a fresh cache-buster key
   CB_PROBE="$(openssl rand -hex 8)"
   [[ "${CB_PROBE}" =~ ^[0-9a-f]{16}$ && "${CB_PROBE}" != "${CB_A}" && "${CB_PROBE}" != "${CB_B}" ]] || exit 1
   PROBE_URL="${TARGET_BASE}?__cb=${CB_PROBE}"

   curl -sS --connect-timeout 3 --max-time 5 \
     -D "${WORK_DIR}/probe_headers.txt" -o "${WORK_DIR}/probe_body.txt" "${PROBE_URL}" \
     -H "X-Forwarded-Host: cache-probe.invalid" \
     -H "X-Forwarded-Scheme: nothttps"

   # Step 3: clean follow-up GET to the identical URL without probe headers
   curl -sS --connect-timeout 3 --max-time 5 \
     -D "${WORK_DIR}/clean_headers.txt" -o "${WORK_DIR}/clean_body.txt" "${PROBE_URL}"
   ```
   - Flag MEDIUM (unkeyed input reflection) if `cache-probe.invalid` appears in `probe_headers.txt` (`Location`) or `probe_body.txt` on the first request alone.
   - Escalate to HIGH (confirmed web cache poisoning) only when the clean follow-up (`clean_headers.txt`, `clean_body.txt`) is served from cache (`CF-Cache-Status: HIT`, `X-Cache: Hit from cloudfront`, or `Age > 0`) and replays the injected `cache-probe.invalid` reflection or a poisoned `4xx`/`5xx` status.
   - **Self-checking loopback fixture (positive replay vs negative control).** Validate the detection logic locally without touching external networks:
     ```bash
     python3 - << 'EOF'
     import http.server, threading, urllib.request

     STORE = {}
     class EdgeFixture(http.server.BaseHTTPRequestHandler):
         def log_message(self, *args): pass
         def do_GET(self):
             mode, _, query = self.path.partition("?")
             xfh = self.headers.get("X-Forwarded-Host", "clean.example")
             # /vulnerable caches by query only (unkeyed X-Forwarded-Host)
             # /safe includes X-Forwarded-Host in the cache key (negative control)
             key = (mode, query) if mode == "/vulnerable" else (mode, query, xfh)
             if key in STORE:
                 body, hit = STORE[key], "HIT"
             else:
                 body = f"<link href='https://{xfh}/app.js'>".encode()
                 STORE[key], hit = body, "MISS"
             self.send_response(200)
             self.send_header("CF-Cache-Status", hit)
             self.end_headers()
             self.wfile.write(body)

     srv = http.server.HTTPServer(("127.0.0.1", 0), EdgeFixture)
     port = srv.server_port
     threading.Thread(target=srv.serve_forever, daemon=True).start()

     def check_path(path):
         url = f"http://127.0.0.1:{port}{path}?__cb=deadbeef01234567"
         req1 = urllib.request.Request(url, headers={"X-Forwarded-Host": "cache-probe.invalid"})
         urllib.request.urlopen(req1, timeout=3).read()
         resp2 = urllib.request.urlopen(url, timeout=3)
         body2 = resp2.read().decode()
         hit2 = resp2.headers.get("CF-Cache-Status")
         return hit2 == "HIT" and "cache-probe.invalid" in body2

     assert check_path("/vulnerable") is True, "Expected positive replay detection on /vulnerable"
     assert check_path("/safe") is False, "Expected negative control to stay clean on /safe"
     srv.shutdown()
     print("Staging fixture verified: positive replay detected and negative control clean.")
     EOF
     ```

### 2. Supply chain and integrity (A03 / A08:2025)

1. **Public lockfiles and registry config.** Verify that dependency manifests return `404` or `403` in production so attackers cannot harvest the exact dependency tree: `/package.json`, `/package-lock.json`, `/pnpm-lock.yaml`, `/yarn.lock`, and on Python/Go stacks `/requirements.txt`, `/poetry.lock`, `/uv.lock`, `/go.mod`, `/go.sum`.
   - Probe `/.npmrc` and `/.yarnrc.yml` with bounded, non-exfiltrating signatures (`--connect-timeout 3 --max-time 5`): status `200` and lines match `^(registry|@[a-z0-9_-]+:registry|//[^:]+:_authToken|npmScopes:|npmRegistries:|npmAuthToken:|nodeLinker:)` without `<!DOCTYPE` or `<html`. Report only the status code and a boolean; never print contents or token values.
2. **Production source maps and SRI.**
   - Check whether production JS bundles expose `.js.map` files containing original source and business logic.
   - Require `integrity="sha384-..."` and `crossorigin="anonymous"` on third-party `<script>` tags loaded from external CDNs.

### 3. Transport and browser policy (A04 / A05:2025)

1. **HSTS and TLS posture.**
   - Plain `http://` must redirect immediately (`301`/`308`) to `https://`, and HTTPS responses must include `Strict-Transport-Security` with a sensible `max-age` (for example `max-age=31536000`).
   - Treat `includeSubDomains` and `preload` as deployment decisions, not defaults:
     - Add `includeSubDomains` only after confirming every subdomain under the registered domain serves valid HTTPS. Otherwise browsers refuse connections to HTTP-only internal or legacy subdomains.
     - Keep `preload` submission a separate, explicit decision after reviewing the [HSTS preload requirements](https://hstspreload.org/). Removal from browser preload lists takes months to propagate.
2. **Content-Security-Policy.**
   - Verify the CSP defines `default-src`, `script-src`, `object-src 'none'`, `base-uri 'self'` and `frame-ancestors`.
   - Flag `script-src 'unsafe-eval'` independently whenever present. Nonces (`'nonce-...'`) and hashes (`'sha256-...'`) only neutralize `'unsafe-inline'`; they do not disable `eval()` or string-to-code execution.
   - Flag `script-src 'unsafe-inline'` unless accompanied by `'strict-dynamic'` or per-response nonces/hashes (and no `unsafe-inline` fallback in modern browsers).

### 4. Session cookies (A07:2025)

- Every `Set-Cookie` carrying an auth or session identifier must include `HttpOnly` and `Secure`.
- Evaluate `SameSite` and lifetime against the app's architecture:
  - Default to `SameSite=Lax` (or `Strict`) for first-party flows. Only allow `SameSite=None; Secure` when cross-site embedding or federation is intended and explicit anti-CSRF tokens or Fetch Metadata (`Sec-Fetch-Site`) checks are enforced.
  - Ephemeral browser-session cookies may omit `Max-Age` and `Expires` so they clear on browser close. Persistent cookies must set a bounded `Max-Age` or `Expires` that fits the session risk.

### 5. Error surface and disclosure policy (A09 / A10:2025)

1. **Fail-closed errors (no stack trace leaks).** Request a non-existent route (`/api/__probe_404_<random>`) with `--connect-timeout 3 --max-time 5` and verify a clean, minimal JSON or HTML error with no stack traces (`java.sql.SQLException`, `PrismaClientKnownRequestError`, `Traceback`, `at Object.<anonymous>`, `/var/task/`, `node_modules/`).
2. **Vulnerability disclosure policy.** Verify RFC 9116 compliance at `/.well-known/security.txt`: `Contact:` and a non-expired `Expires:` field.

## Remediation (nginx and Caddy)

Fix the cause first: serve a build output directory, not the repo checkout, so `.git`, `.env`, compose files and lockfiles never sit under the web root. The path blocks below are a backstop. Start the CSP as `Content-Security-Policy-Report-Only` if you are unsure what it will break, then switch to enforcing.

nginx:

```nginx
server {
    listen 80;
    server_name example.com;
    return 301 https://example.com$request_uri;
}

server {
    listen 443 ssl;
    server_name example.com;
    # ssl_certificate / ssl_certificate_key ...

    # Add "; includeSubDomains" only after every subdomain serves HTTPS. "preload" is a separate decision.
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'" always;

    # Dotfiles and VCS metadata (.git, .env, .npmrc, ...), keeping /.well-known/ public.
    # Regex locations match in order, so keep these before other regex locations.
    location ~ /\.(?!well-known/) {
        return 404;
    }
    location ~ /(docker-compose\.ya?ml|compose\.ya?ml|package(-lock)?\.json|pnpm-lock\.yaml|yarn\.lock|requirements\.txt|poetry\.lock|uv\.lock|go\.(mod|sum))$ {
        return 404;
    }

    location / {
        proxy_pass http://app:8000;
    }
}
```

`add_header` is inherited from the enclosing level only when the current level defines no `add_header` of its own. A `location` that adds any header must repeat the security headers.

Caddy (HTTP to HTTPS redirect is automatic; HSTS is not):

```caddyfile
example.com {
    header {
        # Add "; includeSubDomains" only after every subdomain serves HTTPS.
        Strict-Transport-Security "max-age=31536000"
        X-Content-Type-Options "nosniff"
        Referrer-Policy "strict-origin-when-cross-origin"
        Content-Security-Policy "default-src 'self'; script-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    }

    # Any path segment starting with "." except /.well-known/
    @dotfiles {
        path */.*
        not path /.well-known/*
    }
    respond @dotfiles 404

    @manifests path */docker-compose.yml */docker-compose.yaml */compose.yaml */compose.yml */package.json */package-lock.json */pnpm-lock.yaml */yarn.lock */requirements.txt */poetry.lock */uv.lock */go.mod */go.sum
    respond @manifests 404

    reverse_proxy app:8000
}
```

Cookie flags: set `Secure`, `HttpOnly` and `SameSite` in the app's session/cookie settings, not at the proxy. As a backstop, nginx 1.19.3+ can force them on proxied cookies with `proxy_cookie_flags ~ secure httponly samesite=lax;`.

Re-run the probes above after deploying and confirm the real responses changed.

Adapted from affaan-m/everything-claude-code (MIT) @3f14a10: web-perimeter-owasp-2025-audit.
