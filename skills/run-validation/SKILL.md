---
name: run-validation
description: Load before any test, build, Docker/compose run, amd64/VM, or browser check. Picks local Mac vs local Docker vs Linux amd64 VM and gives the rules; browser checks via chrome-devtools MCP.
---

# Run validation

State the claim being tested, then pick the first environment that contains every property
relevant to it: 1. Local Mac → 2. Local Docker → 3. Linux amd64 VM. Escalate only when the
lighter one would make the result incomplete or misleading. Never claim deployment or
architecture compatibility from a lower-fidelity test.

## Local Mac — default for portable, trusted work

Trusted, platform-agnostic program tests whose result doesn't depend on Linux, CPU
architecture, kernel behavior, or external infrastructure. Simple Docker containers too, when
the behavior doesn't need Linux or a specific CPU architecture.

- Reading, searching, formatting, linting, type checking.
- Unit tests and interpreted-language application logic.
- Python deps inside `.venv`, uv, Poetry, or equivalent.
- Go tests without Linux-specific behavior.
- Generating/inspecting files; parsing/validating config.
- Trusted project-native dev commands.

Never install deps globally or modify host config. A missing package alone is not a reason
for Docker; use the project's isolated environment.

## Local Docker — when the container or Linux userspace matters

The claim depends on the image, container filesystem, Linux userspace, service wiring, or
container networking.

- Building and starting the actual image; Docker Compose validation.
- Linux package dependencies.
- Databases and multi-service integration tests.
- Container paths, users, permissions, volumes, health checks, networking.
- Verifying a self-hosted service works as packaged.

Not a heavier venv for portable language-level tests. Local Docker is arm64; it cannot
truthfully validate amd64-specific behavior.

## Linux amd64 VM

When local execution or Docker can't faithfully or safely validate:

- Real Linux/amd64 builds and amd64-only images.
- systemd, iptables, kernel, privileged networking, host package installation.
- Destructive experiments or untrusted code.
- Heavy storage, memory, CPU, or large downloads.
- Final deployment validation when the target differs materially from the Mac.

Reuse a known VM dedicated to the same project when caches help and a clean environment
isn't required. When it is: fresh VM from a clean base image — no existing VM, prior test
data, or snapshot. Untrusted code or destructive experiments get a separate disposable VM so
they can't damage a cached project environment.

- Machine-specific VM CLIs and their commands: read the `local-tooling` skill
  (`~/.agents/skills/local-tooling/SKILL.md`) if it exists; otherwise ask which VM tool to use.
- Keep a finite TTL. Delete one-off task VMs after the test; keep project VMs for reuse and
  delete them only when asked.
- Download needed results before a VM stops or expires.
- Cloud VMs are online; offline-target rules don't apply to them.

## Browser checks

chrome-devtools MCP only, never Claude in Chrome (it prompts per site in VS Code even in
bypass, and its extension blocks localhost).

- Each agent opens its own page (`new_page` + `isolatedContext: "<label>"`), passes that
  `pageId` on every call, never `select_page`, and closes it when done.
- Screenshots go to the scratchpad.
- Agents with no browser job get "no browser tools".
- Run the MCP server with `--isolated` so sessions don't share a browser profile.
