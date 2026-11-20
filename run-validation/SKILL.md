---
name: run-validation
description: Load before any test, build, Docker/compose run, VM, CPU-architecture, or browser check. Picks this machine vs local Docker vs a VM matching the deploy target, and gives the browser-check rules.
---

# Run validation

State the claim being tested, then pick the first environment that contains every property
relevant to it: 1. this machine → 2. local Docker → 3. a VM matching the target. Escalate only
when the lighter one would make the result incomplete or misleading. Never claim deployment or
architecture compatibility from an environment that doesn't have that property.

## Know the environments

Detect them; don't assume:

```sh
uname -sm                                                         # this machine, e.g. "Darwin arm64", "Linux x86_64"
docker info --format '{{.OSType}}/{{.Architecture}}' 2>/dev/null  # local Docker, e.g. "linux/aarch64"; empty = no Docker
```

Read `${XDG_CONFIG_HOME:-$HOME/.config}/agent-skills/settings.toml`, section `[validation]`:

| Key | Default | Meaning |
|---|---|---|
| `target` | `"linux/amd64"` | The platform you usually deploy to. A project's AGENTS.md overrides it. |
| `browser` | `"chrome-devtools"` | Browser-check tool: `chrome-devtools`, `playwright`, or `none`. |
| `local_tooling` | `"local-tooling"` | Private skill with the machine's VM commands (`~/.agents/skills/<name>/SKILL.md`). |

No file or no key → the default. A value outside the listed ones → the default, and tell the user.
`aarch64` and `arm64` are the same architecture; `x86_64` and `amd64` too.

## Does the claim depend on the CPU architecture?

Usually not. Only when it does, the environment must run the target's architecture natively.
Emulation (`--platform`, QEMU, Rosetta) is fine for a smoke test, never for an architecture claim.

**Architecture-independent** (a matching OS is enough; this machine or local Docker of any arch):
- Pure Python, JavaScript/TypeScript, Ruby, shell, and Go or Rust without native or `unsafe`/asm code.
- Business logic, parsing, config, templates, SQL, HTTP handlers, CLI behavior.
- Dependencies that ship as source or universal wheels / pure-JS packages.

**Architecture-dependent** (needs the target arch: local Docker if it matches, else a VM):
- Building or running a native binary or image for the target: compiled C/C++/Rust/Go with
  cgo, `GOARCH`/cross-compile output, Dockerfiles with arch-specific base images or downloads.
- Native extensions and prebuilt binaries: Python wheels with C code, npm native addons,
  vendored `.so`/`.dll`, tools fetched per arch (`*-amd64.tar.gz`).
- SIMD/intrinsics, inline asm, JIT, memory ordering and lock-free code, struct sizes and alignment.
- Performance or resource numbers you will quote for the target.
- "This image runs on the server", for a server of a different arch than local Docker.

When unsure, check what the build pulls or compiles (`file <binary>`, wheel tags, base image
manifest), then decide. Say which way you decided and why.

## This machine — default for portable, trusted work

Trusted work whose result doesn't depend on Linux, CPU architecture, kernel behavior, or
external infrastructure. Simple Docker containers too, when the behavior doesn't need Linux or a
specific architecture.

- Reading, searching, formatting, linting, type checking.
- Unit tests and interpreted-language application logic.
- Python deps inside `.venv`, uv, Poetry, or equivalent.
- Go tests without OS-specific behavior.
- Generating/inspecting files; parsing/validating config.
- Trusted project-native dev commands.

Never install deps globally or modify host config. A missing package alone is not a reason
for Docker; use the project's isolated environment. If this machine is already the target OS and
architecture, it can also prove architecture-dependent claims that don't need isolation.

## Local Docker — when the container or Linux userspace matters

The claim depends on the image, container filesystem, Linux userspace, service wiring, or
container networking.

- Building and starting the actual image; Docker Compose validation.
- Linux package dependencies.
- Databases and multi-service integration tests.
- Container paths, users, permissions, volumes, health checks, networking.
- Verifying a self-hosted service works as packaged.

Not a heavier venv for portable language-level tests. Local Docker proves architecture claims
only when its architecture matches `target`.

## VM matching the target

When local execution or Docker can't faithfully or safely validate:

- Architecture-dependent claims when local Docker's architecture differs from `target`.
- systemd, iptables, kernel, privileged networking, host package installation.
- Destructive experiments or untrusted code.
- Heavy storage, memory, CPU, or large downloads.
- Final deployment validation when the target differs materially from this machine.

Reuse a known VM dedicated to the same project when caches help and a clean environment
isn't required. When it is: fresh VM from a clean base image — no existing VM, prior test
data, or snapshot. Untrusted code or destructive experiments get a separate disposable VM so
they can't damage a cached project environment.

- Machine-specific VM CLIs and their commands: read the `local_tooling` skill if it exists;
  otherwise ask which VM tool to use.
- Keep a finite TTL. Delete one-off task VMs after the test; keep project VMs for reuse and
  delete them only when asked.
- Download needed results before a VM stops or expires.
- Cloud VMs are online; offline-target rules don't apply to them.

## Browser checks

Use the tool named by `browser`. Never Claude in Chrome (it prompts per site in VS Code even in
bypass, and its extension blocks localhost). Screenshots go to the scratchpad. Agents with no
browser job get no browser tools.

**`chrome-devtools`** (chrome-devtools MCP):
- Run the server with `--isolated`, so sessions don't share a browser profile.
- Each agent opens its own page (`new_page` + `isolatedContext: "<label>"`), passes that
  `pageId` on every call, never `select_page`, and closes it when done.

**`playwright`** (Playwright MCP):
- Run the server with `--isolated` (in-memory profile). For a logged-in session, add
  `--storage-state <file>` instead of reusing a real profile.
- Its tools act on the current tab, with no page id, so one agent drives one server at a time.
  Parallel browser agents each need their own server instance.
- Open your own tab (`browser_tabs` action `new` with `isolatedContext: "<label>"`), and close
  it (`browser_tabs` action `close`) when done.

**`none`**: say the check needs a browser tool, name the claim left unverified, and don't
substitute a guess (no "it should render fine").
