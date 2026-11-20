# Craft

Implement the requested UI from a clear brief through a working, inspected result. Use the scope and authorization rules in [SKILL.md](../SKILL.md): small authorized work proceeds directly; substantial unapproved work gets one short spec approval. Prior approval remains valid through code and asset work.

## Establish the project and direction

Inspect the target, framework/configuration, build scripts, components, tokens, icons, and relevant product/design context. Use the existing stack and source pipeline. An absent PRODUCT.md or DESIGN.md is not a setup blocker.

For a new project, infer the simplest suitable stack from the task and stated preferences. Put a consequential stack choice in the substantial-work spec; do not add a separate framework questionnaire. Do not introduce a second framework or write into generated `dist/`, `build/`, or `.next/` output.

Reuse the user's approved brief or design reference. If the substantial task is unapproved, use [shape.md](shape.md) to produce a compact spec with scope, core flow/states, content/assets, visual direction, and validation. Wait once for that spec's approval. Explicitly requested `shape` remains planning only; craft continues to implementation after approval.

## Use references selectively

- [layout.md](layout.md): spatial structure, responsive composition, spacing.
- [typeset.md](typeset.md): type hierarchy, fonts, loading, readability.
- [interaction-design.md](interaction-design.md): complex interactions and forms.
- [animate.md](animate.md): requested or useful motion.
- [colorize.md](colorize.md): palettes, themes, contrast.
- [adapt.md](adapt.md): responsive web behavior; use the native variant for native work.
- [clarify.md](clarify.md): interface language, labels, and errors.

Read the relevant reference sections, not every command workflow. The current task's brief and authorization govern scope.

## Assets and visual exploration

Use [codex.md](codex.md) when generated imagery, visual comps, or production assets materially help the requested result. Tool availability alone does not require image generation, a palette artifact, or mock variants. Implement an already-approved design directly.

Preserve required imagery and composition. Prefer project assets, licensed local resources, and semantic code where appropriate. Generated comps are visual references; actual controls, copy, data, and accessibility remain part of the implementation. Do not invent stock URLs or replace an explicitly required image with decorative filler. Report a missing required asset and continue independent work.

## Build

Implement the approved scope in maintainable source code:

- Real requested content and functional controls; no misleading metrics, fake testimonials, dead links, or unexplained placeholders in a finished result.
- Semantic headings, landmarks, labels, forms, and button/link behavior.
- A coherent type, spacing, color, and icon system using existing primitives where they fit.
- States relevant to the changed flow, including loading, errors, empty results, keyboard focus, and content extremes.
- Responsive layout and usable keyboard/touch interactions; readable text and unobscured focus.
- Locally served assets for self-hosted products, appropriate image dimensions, and no accidental external runtime fetches.
- Motion only where useful, with reduced-motion behavior and visible content when animation does not run.

If a discovery changes the approved product behavior or major design direction, explain the specific change and obtain a revised scope decision. Routine implementation choices do not need renewed permission.

## Verify and deliver

Run the relevant project checks, load the changed surface, and exercise the main interaction when tools permit. Inspect actual screenshots at representative widths; for long pages, inspect affected sections at readable scale. Review the result against the brief and fix material defects. Re-inspect after changes; a clean first pass does not need an invented second pass.

Detector findings are evidence to investigate, not proof of completion or a style mandate. State what was actually tested, any accepted design deviations, and material limitations. Deliver the requested result without a mandatory feedback questionnaire.
