---
name: ship-audit
description: Use when asked "is this ready to ship?", "what breaks in prod?", or for a pre-launch or post-merge readiness review of an app or self-hosted service. Local-evidence audit with score caps and a short ship/block answer; no external scanners or repo uploads.
---

# Ship audit

Use when the user asks whether an app or service is ready to ship, what could break in production, or what must be fixed before a launch.

## When to use

- "Is this production-ready", "what would break in prod", "what did we miss", "audit this repo", "ready to ship?"
- A feature was merged and needs a pre-deploy or post-merge risk pass.
- A public launch, demo or customer rollout is close.
- CI is green but the user wants production risk, not only test status.
- A deployed URL, release branch, PR or current checkout is available as evidence.

## When not to use

- During active implementation, when the right lens is line-level secure coding; use `security-hunt` first.
- For pure libraries, templates, docs-only repos or scaffolds, unless the user wants packaging/release readiness.
- For a formal compliance audit. This is engineering triage, not legal, financial, medical or regulatory certification.
- When the only evidence is a product idea with no repo, deployment, CI or runtime surface.

## How it works

Build the audit from local and user-authorized evidence. Do not run unpinned remote code, upload repository contents to third-party services, or call external scanners unless the user explicitly approves that specific tool and data flow.

Order:

1. Establish the release surface.
2. Read recent changes and current branch state.
3. Inspect the runtime, auth, data, background-job, deployment and (if present) payment and AI boundaries that actually exist in the repo.
4. Check CI, tests, migrations, environment docs and rollback path.
5. Produce a short ship/block recommendation with specific fixes.

## Evidence checklist

Start with cheap, local signals:

```text
git status --short --branch
git log --oneline --decorate -20
git diff --stat origin/main...HEAD
```

Then inspect the project-specific surface:

- Build scripts, CI workflows, release scripts, Dockerfiles, compose files and deployment manifests.
- API routes, webhooks, auth middleware, background workers, cron jobs and database migrations.
- Environment variable docs and startup checks.
- Observability: error reporting, logs, health checks, dashboards.
- Rollback, seed, migration and backfill instructions.
- E2E coverage for the user paths that matter most.

If a deployed URL is in scope, run HTTP checks only against that URL and avoid credentialed actions unless the user supplies a safe test account. For edge and header checks, use `web-perimeter-audit`.

## Risk lenses

### Security and auth

- Are public, API and admin routes clearly separated?
- Are auth and authorization enforced server-side?
- Are secrets kept out of client bundles, logs, example output and checked-in files?
- Are rate limits, CSRF protection, CORS policy and upload validation present where the app needs them?
- If the app has an AI or agent surface: does it defend against prompt injection, tool abuse and untrusted content crossing into privileged actions?

### Data integrity

- Do migrations run forward cleanly, with a rollback or recovery plan? (See `db-migrations`.)
- Are destructive migrations, backfills and data imports staged safely?
- Do database grants and service-role boundaries match the app's tenancy model?
- Are retries idempotent for writes, jobs and webhook handlers?

### Payments and webhooks (only if the product takes payments or receives webhooks)

- Are webhook signatures verified before trusting payload fields?
- Is each payment, subscription or fulfillment webhook idempotent?
- Are replay, duplicate delivery and out-of-order delivery handled?
- Are test-mode and live-mode credentials separated?

### Operations

- Can the app start from a clean checkout using documented commands?
- Are required environment variables named, validated and fail-fast?
- Is there a health check that proves dependencies are reachable?
- Are deploy, rollback and incident-owner paths documented?
- Are logs useful without leaking secrets or personal data?

### Self-hosted release (Docker services)

- **Images use version tags.** Every `image:` in compose and every `FROM` names a version tag at the level the service needs (`postgres:16`), not a bare name or `latest`. A digest only where one exact build matters.
- **Backup and restore both tested.** A backup job exists, and a restore into a scratch database or container has been run and checked with a query that proves the data is there. An untested restore counts as no backup.
- **Rollback path.** The previous image digest is recorded, and the pending migrations are backward-compatible with it (expand-contract), so redeploying the old image works.
- **Healthchecks.** Services define `healthcheck:` (compose) or `HEALTHCHECK` (Dockerfile), and dependents use `depends_on: condition: service_healthy` where start order matters.
- **No secrets baked into images.** No secrets in `ENV`/`ARG` or copied files: check `docker history --no-trunc <image>`, and confirm `.dockerignore` excludes `.env` and similar files. Secrets arrive at runtime (env file, mounted secret).
- **Offline targets only (when the user says the target is offline):** no runtime calls to the public internet. Grep built assets and config for external URLs (fonts, CDNs, analytics, update checks), then run the stack on a network with no egress (for example a compose network with `internal: true`) and confirm it still works.

### User experience

- Are the launch-critical paths covered on desktop and mobile?
- Are forms usable on mobile without input zoom, layout overlap or blocked submit states?
- Do loading, empty, error and permission-denied states tell the user what happened?
- Is there a support or recovery path when a critical operation fails?

## Scoring

Scores force prioritization; they do not imply mathematical certainty.

| Band | Score | Meaning |
| --- | --- | --- |
| Blocked | 0-49 | Do not ship until the top risks are fixed |
| Risky | 50-69 | Ship only behind a small rollout or internal beta |
| Launchable with caveats | 70-84 | Ship if owners accept the listed risks |
| Strong | 85-100 | No obvious launch blockers from available evidence |

Cap the score at `69` if any of these are true:

- Authentication or authorization is missing on sensitive data.
- The product takes payments or webhooks and the payment or fulfillment webhooks are not idempotent.
- Required migrations cannot be run safely.
- Secrets are exposed in client bundles, logs, images or committed files.
- There is no rollback path for a high-impact release.
- A stateful service has no tested restore.

Cap the score at `84` if CI is not green or the launch-critical path was not tested end to end.

## Output format

Lead with one sentence:

```text
Ship audit: 76/100, launchable with caveats; untested restore and missing rollback note are the two risks to fix before launch.
```

Then list:

- `Blockers`: must-fix items before deploy.
- `High-value fixes`: next fixes if the user wants a higher score.
- `Evidence checked`: files, commands, CI runs, deployed URL or PRs inspected.
- `Evidence missing`: what would change confidence if provided.
- `Next action`: one concrete fix or verification step.

Keep strengths short. The user asked about readiness, so the useful answer is the remaining risk and the next action.

## Example

User:

```text
is this ready to ship?
```

Response:

```text
Ship audit: 68/100, risky, because Stripe webhooks are verified but not idempotent and there is no rollback note for the pending migration.

Blockers:
- Add idempotency for `checkout.session.completed` before fulfilling orders.
- Write and test the rollback path for `20260511_add_billing_state.sql`.

High-value fixes:
- Add a health check that verifies database and payment-provider reachability.
- Replace `postgres:latest` in compose.yaml with `postgres:16`.

Evidence checked:
- `app/payments/webhooks.py`
- `db/migrations/20260511_add_billing_state.sql`
- `compose.yaml`
- CI run for the release branch

Evidence missing:
- Last successful restore test date.

Next action: Want me to patch webhook idempotency first?
```

## Anti-patterns

- Running `npx <package>@latest` or any unpinned remote scanner as the default audit path.
- Uploading source, secrets, customer data or private topology to an external audit service without explicit approval.
- Producing a score without naming the evidence checked.
- Treating green CI as production readiness.
- Ending with a generic "let me know what you want to do."

Adapted from affaan-m/everything-claude-code (MIT) @3f14a10: production-audit.
