# Changes from upstream

Derived from pbakaus/impeccable (Apache-2.0), skill version 3.9.1 plus later reference files
(`ios.md`, `android.md`, `*.native.md`). Modified; kept as a fork, not a patch, because nearly
every file differs from any single upstream commit.

- `SKILL.md` trimmed (~22k → ~10k chars); trigger-first description; points to `ui-ux-pro-max`
  for research instead of stacking planning workflows.
- New `reference/usability.md`: usability heuristics merged from six design-book skills; the
  skill reads it before any UX critique, audit, or screen/flow decision.
- `reference/product.md`: never invent data in UI (no fake metrics, testimonials, logos).
- `reference/adapt.md`: `dvh` units and on-screen-keyboard handling.
- `reference/brand.md`, `SKILL.md`: remote fonts/CDNs are fine unless the target is offline.
- Scripts: Codex/`.agents` harness support (`lib/provider.mjs`, `pin.mjs`), shared font list.
