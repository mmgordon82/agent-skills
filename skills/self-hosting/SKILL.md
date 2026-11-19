---
name: self-hosting
description: Use when designing, packaging, or deploying a self-hosted or Docker service, or when the user says a target is offline/air-gapped. Docker packaging defaults, image choice, and the offline-target rules (mirrors, pinned versions, vendored web assets).
---

# Self-hosting

## Default (online target)
- Design for self-hosting: one small dockerizable app beats a sprawl of services.
- Online dependencies (CDNs, fonts, APIs, package registries) are fine unless the user says
  the target is offline.
- Package and run self-hosted services with Docker. Look for an existing official or
  well-maintained tagged image before writing a Dockerfile; pin the tag (digest for releases).
- Ordinary local development and tests don't need Docker when host-local commands validate
  them faithfully (see `run-validation`).

## Offline / air-gapped target (only when the user says so)
- Packages come from internal mirrors (e.g. Artifactory APT + PyPI). Pin every version.
- Nothing is fetched from the public internet at build or run time: no `curl | sh`, no
  runtime CDN, no telemetry, no update checks.
- Vendor web assets locally: fonts, JS/CSS libraries, icons, analytics (or drop analytics).
- Images are built or mirrored ahead of time; reference them by internal registry path.
- Before calling it done, grep the build and runtime config for public hostnames
  (`https?://`, `cdn`, `googleapis`, `unpkg`, `jsdelivr`) and explain each remaining hit.
