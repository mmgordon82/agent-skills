---
name: docker-packaging
description: Use when designing or packaging a self-hosted service or Docker image. One small dockerizable app, existing tagged images over new Dockerfiles, Docker only where it validates something.
---

# Docker packaging

- Design for self-hosting: one small dockerizable app beats a sprawl of small services.
- Online dependencies (CDNs, fonts, APIs, package registries) are fine unless the user says the
  target is offline. Then also follow the `airgap` skill.
- Package and run self-hosted services with Docker. Look for an existing official or
  well-maintained tagged image before writing a Dockerfile. Use a version tag at the level the app
  needs (`postgres:16`, `node:22`), never `latest`. Add a digest (`name:tag@sha256:…`) only where
  one exact build matters, such as a release image you must be able to roll back to.
- Ordinary local development and tests don't need Docker when host-local commands validate them
  faithfully (see `run-validation`).

## Package the service

Inspect existing Dockerfiles, Compose files, CI, and deployment docs first. Reuse working project
conventions; don't rewrite working packaging for style. Add only what the service needs:

- A `Dockerfile` when no suitable maintained image can run the app.
- A `.dockerignore` for every build context.
- A `compose.yaml` when it captures runtime configuration or service dependencies more clearly than
  a `docker run` command.
- An `.env.example` with safe placeholders and concise build, run, and configuration docs.

For a new Dockerfile:

- Start from a small, maintained base and apply the tag rule above to every `FROM` and
  Compose `image:`.
- Install from the project's lockfile. Use multi-stage builds when build tools or development
  dependencies should not ship in the runtime image.
- Run non-root unless the service needs a specific privilege. Use an exec-form `ENTRYPOINT`/`CMD`
  and make sure the application receives stop signals.
- Exclude VCS metadata, `.env`, secrets, caches, local dependency directories, and build output;
  copy only the files the build or runtime needs.
- Supply runtime secrets through the app's environment, file, or mounted-secret mechanism. For
  build-time credentials, use `RUN --mount=type=secret`; never use `ARG`, `ENV`, or `COPY` for them.

## Make the runtime explicit

- Document required environment variables, listening address, and port. Validate required
  configuration at startup and fail with a useful error.
- Put persistent data on named volumes and ensure the container user can write to them.
- Add a healthcheck that tests actual readiness. Use `depends_on` with `condition:
  service_healthy` when one service needs another to be ready.
- Publish only the intended entrypoint; keep databases and other internal service ports off the
  host unless requested.
- Set a restart policy for long-running services unless the project already has another policy.

## Prove the package

Choose the environment with `run-validation`, then:

1. Validate Compose configuration with `docker compose config -q`, when present.
2. Build the actual image and start a clean stack. Use a fresh Compose project or disposable test
   resources for isolation; never delete existing data to make a test clean.
3. Wait for health, hit the real endpoint, and perform one meaningful operation. A running
   container or successful config parse alone is not proof.
4. For stateful services, recreate the app container and verify that the data survives.
5. Stop the service and inspect logs for startup, permission, and shutdown errors.
6. Report the image reference and platform actually tested, plus anything left unverified. Remove
   only test resources you created.

## Handoff

Document build/run commands, configuration and secret inputs, persistent-data paths, the update
procedure, and how to return to the previous image tag or digest. Use `ship-audit` for release
readiness and `db-migrations` for schema changes; a packaging smoke test is not a production audit.
