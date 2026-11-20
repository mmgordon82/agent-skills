---
name: security-hunt
description: Use when reviewing your own code or product for exploitable, remotely reachable vulnerabilities (SSRF, auth bypass, injection, RCE, path traversal, XSS). Keeps only findings where user input provably reaches a meaningful sink; drops noisy local-only patterns.
---

# Security hunt

Use this to find exploitable issues in your own code and products, not for a broad best-practices review. Bias toward remotely reachable, user-controlled attack paths and throw away patterns that are local-only or theoretical.

## When to use

- Scanning a repository for exploitable vulnerabilities before release
- Triage where the question is "can someone actually exploit this?" rather than "is this theoretically unsafe?"

For edge and header checks on a deployed site, use `web-perimeter-audit`.

## Patterns that matter

| Pattern | CWE | Typical impact |
| --- | --- | --- |
| SSRF through user-controlled URLs | CWE-918 | internal network access, cloud metadata theft |
| Auth bypass in middleware or API guards | CWE-287 | unauthorized account or data access |
| Remote deserialization or upload-to-RCE paths | CWE-502 | code execution |
| SQL injection in reachable endpoints | CWE-89 | data exfiltration, auth bypass, data destruction |
| Command injection in request handlers | CWE-78 | code execution |
| Path traversal in file-serving paths | CWE-22 | arbitrary file read or write |
| Auto-triggered XSS | CWE-79 | session theft, admin compromise |

## Skip these

Usually low-signal unless there is a concrete remote path or impact:

- Local-only `pickle.loads`, `torch.load` or equivalent with no remote path
- `eval()` or `exec()` in CLI-only tooling
- `shell=True` on fully hardcoded commands
- Missing security headers by themselves
- Generic rate-limiting complaints without exploit impact
- Self-XSS requiring the victim to paste code manually
- CI/CD injection, unless the pipeline is part of this review
- Demo, example or test-only code

## Workflow

1. Set scope: which repo, services and deployments are under review.
2. Find real entrypoints: HTTP handlers, uploads, background jobs, webhooks, parsers and integration endpoints.
3. Run static tooling where it helps, but treat it as triage input only.
4. Read the real code path end to end.
5. Prove user input reaches a meaningful sink.
6. Confirm exploitability and impact with the smallest safe PoC, against a local or staging instance.
7. Check whether the issue is already tracked before writing it up.

## Triage loop

```bash
semgrep --config=auto --severity=ERROR --severity=WARNING --json
```

`--config=auto` pulls rules from the Semgrep registry over the network. For offline targets, point `--config` at a local ruleset (a vendored rules file or directory) instead.

Then filter by hand:

- drop tests, demos, fixtures, vendored code
- drop local-only or non-reachable paths
- keep only findings with a clear network or user-controlled route

## Finding format

```markdown
## Description
[What the vulnerability is and why it matters]

## Vulnerable code
[File path, line range, and a small snippet]

## Proof of concept
[Minimal working request or script]

## Impact
[What an attacker can achieve]

## Affected version
[Version, commit, or deployment tested]

## Fix
[Smallest change that closes the path]
```

## Quality gate

Before reporting a finding:

- The code path is reachable from a real user or network boundary
- The input is genuinely user-controlled
- The sink is meaningful and exploitable
- The PoC works
- The issue is not already tracked, or already covered by a known advisory for a dependency

Adapted from affaan-m/everything-claude-code (MIT) @3f14a10: security-bounty-hunter.
