# Visual Direction and Asset Production

Read when the task benefits from generated visual comps or bitmap assets. This guidance uses actual available image tools and their current instructions; it does not assume a model name or a specific host capability.

## Decide what is needed

Reuse the approved brief, palette, references, and existing assets. Generate only what helps answer an unresolved design question or fulfills a requested asset. A palette image and a set of mocks are optional; a known visual direction can go straight to code.

For substantial unapproved design work, include direction, asset roles, and intended implementation in the lead workflow's short spec. That is the approval gate. Approval already given for the brief or implementation also covers its routine asset production; do not ask again for palette, atmosphere, or mock confirmation. If the user explicitly asks for a staged visual-selection workflow, honor those requested stages.

## Comps

When a visual comparison is useful, create a small number of genuinely different compositions around the brief's content, hierarchy, density, and visual voice. Reuse agreed colors and type unless those are the decision being explored. Show enough of a page or flow to assess the actual question.

Use the current image-generation tool/skill if available and appropriate. Do not install a tool to satisfy this reference. If generation is unavailable, use an appropriate code-native sketch, existing reference, or clear brief; identify a blocker only when the requested output actually requires generation.

Treat selected comps as direction, not as production UI: preserve the major composition, imagery, and hierarchy while implementing real text, semantic controls, states, and responsive behavior. Do not claim factual fidelity for a generated depiction of a real product or place without verification.

## Asset inventory

For a selected comp or image-led brief, identify only the ingredients needed for implementation:

- Image subjects and major visual motifs, with their purpose and placement.
- Existing licensed assets versus generated or sourced raster assets.
- Content that should stay HTML/CSS/SVG, icons, data visualization, or canvas.
- Dimensions, format, crop, transparency, and meaningful alternate text.

Do not rasterize UI text, controls, tables, or data. Preserve required imagery; do not replace it with generic cards, fake metrics, or decorative panels. A material departure from the approved direction needs a scope decision; routine faithful implementation does not.

## Production

Delegate a bounded asset job when it can run independently alongside useful implementation. Use the available subagent tool with a self-contained brief: the reference image/path, asset role, dimensions/format, output directory, constraints, and which elements remain semantic code. Use the bundled asset-producer configuration only if the host supports it; otherwise pass equivalent instructions to an available agent. Reuse existing delegation authorization and follow current tool capabilities instead of inventing a permission gate.

Produce assets locally when delegation is unavailable or adds no value. Inspect generated results before using them and keep required outputs until the parent has integrated them. Do not fetch or publish assets outside the task's authorization. Self-hosted products serve approved assets locally, subject to their licenses and the host's media-handling rules.

Return the selected direction/assets and any meaningful limitation to [craft.md](craft.md). Continue the authorized build; do not end at a mood board when the user asked for an implementation.
