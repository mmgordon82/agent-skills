Generate a `DESIGN.md` file at the project root that captures the current visual design system, so AI agents generating new screens stay on-brand.

DESIGN.md follows the [official DESIGN.md format spec](https://raw.githubusercontent.com/google-labs-code/design.md/main/docs/spec.md): YAML frontmatter carrying machine-readable design tokens, followed by a markdown body with exactly six sections in a fixed order. **Tokens are normative; prose provides context for how to apply them.** Sections may be omitted when not relevant, but **do not reorder them and do not rename them**. Section headers must match the spec character-for-character so the file stays parseable by other DESIGN.md-aware tools (Stitch itself, awesome-design-md, skill-rest, etc.).

## The frontmatter: token schema

The YAML frontmatter is the machine-readable layer. It's what Stitch's linter validates and what the live panel renders tiles from. Keep it tight; every entry should correspond to a token the project actually uses.

```yaml
---
name: <project title>
description: <one-line tagline>
colors:
  primary: "#b8422e"
  neutral-bg: "#faf7f2"
  # ...one entry per extracted color; key = descriptive slug
typography:
  display:
    fontFamily: "Cormorant Garamond, Georgia, serif"
    fontSize: "clamp(2.5rem, 7vw, 4.5rem)"
    fontWeight: 300
    lineHeight: 1
    letterSpacing: "normal"
  body:
    # ...
rounded:
  sm: "4px"
  md: "8px"
spacing:
  sm: "8px"
  md: "16px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.neutral-bg}"
    rounded: "{rounded.sm}"
    padding: "16px 48px"
  button-primary-hover:
    backgroundColor: "{colors.primary-deep}"
---
```

Rules that matter:

- **Token refs** use `{path.to.token}` (e.g. `{colors.primary}`, `{rounded.md}`). Components may reference primitives; primitives may not reference each other.
- **Stitch validates colors as hex sRGB only** (`#RGB` / `#RGBA` / `#RRGGBB` / `#RRGGBBAA`); OKLCH/HSL/P3 trigger a linter warning, not a hard error. YAML accepts the string either way and our own parser is format-agnostic. Choose based on project posture: (a) if the project has an "OKLCH-only" doctrine or uses Display-P3 values that don't round-trip through sRGB, put OKLCH directly in the frontmatter and accept the Stitch linter warning; (b) if the project wants strict Stitch compliance or plans to use their Tailwind/DTCG export pipeline, put hex in the frontmatter and keep OKLCH in prose as the canonical reference. Never split the source of truth without explicit reason.
- **Component sub-tokens** are limited to 8 props: `backgroundColor`, `textColor`, `typography`, `rounded`, `padding`, `size`, `height`, `width`. Shadows, motion, focus rings, backdrop-filter: none of those fit. Carry them in the sidecar (Step 4b).
- **Scale keys are open-ended.** Use whatever names the project already uses (`oxblood-deep`, `surface-container-low`). Don't rename to Material defaults.
- **Variants are naming convention, not schema.** `button-primary` / `button-primary-hover` / `button-primary-active` as sibling keys.

## The markdown body: six sections (exact order)

1. `## Overview`
2. `## Colors`
3. `## Typography`
4. `## Elevation`
5. `## Components`
6. `## Do's and Don'ts`

Optional evocative subtitles are allowed in the form `## 2. Colors: The [Name] Palette` (Stitch's own outputs do this), but the literal word in each header (Overview, Colors, Typography, Elevation, Components, Do's and Don'ts) must be present. Do NOT add extra top-level sections (Layout Principles, Responsive Behavior, Motion, Agent Prompt Guide). Fold that content into the six spec sections where it naturally belongs.

## When to run

Run when the user asks to generate, seed, or refresh DESIGN.md, or when it is part of an approved documentation deliverable. Missing or stale documentation does not trigger this workflow during an unrelated UI edit.

Read an existing DESIGN.md before updating it. An explicit refresh request authorizes a focused update; preserve unrelated tokens and prose. Ask about replacement versus merge only if the intended action remains materially ambiguous. Reuse approved product/design answers rather than asking for them again.

## Two paths

- **Scan mode** (default): the project has design tokens, components, or rendered output. Extract facts, and clarify descriptive language only when it changes the intended meaning. Use when there's code to analyze.
- **Seed mode**: the project is pre-implementation (fresh init, nothing built yet). Use supplied direction and clarify only material gaps; write a minimal DESIGN.md marked `<!-- SEED -->`. Re-run in scan mode once there's code.

Decide by scanning first (Scan mode Step 1). If the scan finds no tokens, no component files, and no rendered site, use seed mode only when a starter design document was requested; otherwise report that there is no implemented system to extract. `$impeccable document --seed` forces seed mode regardless of code presence.

## Scan mode: extract and describe the existing system

### Step 1: Find the design assets

Search the codebase in priority order:

1. **CSS custom properties**: grep for `--color-`, `--font-`, `--spacing-`, `--radius-`, `--shadow-`, `--ease-`, `--duration-` declarations in CSS files (usually `src/styles/`, `public/css/`, `app/globals.css`, etc.). Record name, value, and the file it's defined in.
2. **Tailwind config**: if `tailwind.config.{js,ts,mjs}` exists, read the `theme.extend` block for colors, fontFamily, spacing, borderRadius, boxShadow.
3. **CSS-in-JS theme files**: styled-components, emotion, vanilla-extract, stitches; look for `theme.ts`, `tokens.ts`, or equivalent.
4. **Design token files**: `tokens.json`, `design-tokens.json`, Style Dictionary output, W3C token community group format.
5. **Component library**: scan the main button, card, input, navigation, dialog components. Note their variant APIs and default styles.
6. **Global stylesheet**: the root CSS file usually has the base typography and color assignments.
7. **Visible rendered output**: if browser automation tools are available, load the live site and sample computed styles from key elements (body, h1, a, button, .card). This catches values that tokens miss.

### Step 2: Auto-extract what can be auto-extracted

Build a structured draft from the discovered tokens. For each token class:

- **Colors**: Group into Primary / Secondary / Tertiary / Neutral (the Material-derived roles Stitch uses). If the project only has one accent, express it as Primary + Neutral; omit Secondary and Tertiary rather than inventing them.
- **Typography**: Map observed sizes and weights to the Material hierarchy (display / headline / title / body / label). Note font-family stacks and the scale ratio.
- **Elevation**: Catalogue the shadow vocabulary. If the project is flat and uses tonal layering instead, that's a valid answer; state it explicitly.
- **Components**: For each common component (button, card, input, chip, list item, tooltip, nav), extract shape (radius), color assignment, hover/focus treatment, internal padding.
- **Spacing + layout**: Fold into Overview or relevant Components. The spec does NOT have a Layout section.

### Step 2b: Stage the frontmatter

From the auto-extracted tokens, draft the YAML frontmatter now (you'll write it at the top of DESIGN.md in Step 4). This is the machine-readable layer: what the live panel and Stitch's linter consume.

- **Colors**: one entry per extracted color. Key = descriptive slug (`oxblood-deep`, `editorial-magenta`, not `blue-800`). Value = whichever format the project treats as canonical (OKLCH or hex; see the frontmatter rules above). Don't split the source of truth: one format in the frontmatter, don't redefine the same token in prose with a different value.
- **Typography**: one entry per role (`display`, `headline`, `title`, `body`, `label`). Typography is an object; include only the props that are real for the project (`fontFamily`, `fontSize`, `fontWeight`, `lineHeight`, `letterSpacing`, `fontFeature`, `fontVariation`).
- **Rounded / Spacing**: whatever scale steps the project actually uses, keyed by whatever scale name the project uses (`sm` / `md` / `lg`, or `surface-sm`, or numeric steps).
- **Components**: one entry per variant (`button-primary`, `button-primary-hover`, `button-ghost`). Reference primitives via `{colors.X}`, `{rounded.Y}`. If a variant needs a property Stitch's 8-prop set doesn't cover (shadow, focus ring, backdrop-filter), carry the full snippet in the sidecar instead.

Skip anything the project doesn't have. Empty scale keys or fabricated tokens pollute the spec.

### Step 3: Describe the observed visual language

Reuse qualitative language already supplied by the user or present in PRODUCT.md. Otherwise write a concise description grounded in the extracted system: its purpose, color roles, type character, elevation, and component treatment. A named metaphor is optional; a plain statement of the interface's purpose can fill the Creative North Star field.

Ask only when a material brand decision is missing and cannot be inferred from the requested documentation or source. Use the host's available question mechanism; do not require a particular tool or a questionnaire. Do not invent brand history or present suggested language as an accepted user decision.

### Step 4: Write DESIGN.md

The file opens with the YAML frontmatter staged in Step 2b (schema documented at the top of this reference), then the markdown body using the structure below. Headers must match character-for-character. Optional evocative subtitles (e.g. `## 2. Colors: The Coastal Palette`) are allowed.

```markdown
---
name: [Project Title]
description: [one-line tagline]
colors:
  # ... staged frontmatter from Step 2b
---

# Design System: [Project Title]

## 1. Overview

**Creative North Star: "[Named metaphor in quotes]"**

[2-3 paragraph holistic description: personality, density, aesthetic philosophy. Start from the North Star and work outward. State what this system explicitly rejects (pulled from PRODUCT.md's anti-references). End with a short **Key Characteristics:** bullet list.]

## 2. Colors

[Describe the palette character in one sentence.]

### Primary
- **[Descriptive Name]** (#HEX / oklch(...)): [Where and why this color is used. Be specific about context, not just role.]

### Secondary (optional; omit if the project has only one accent)
- **[Descriptive Name]** (#HEX): [Role.]

### Tertiary (optional)
- **[Descriptive Name]** (#HEX): [Role.]

### Neutral
- **[Descriptive Name]** (#HEX): [Text / background / border / divider role.]
- [...]

### Named Rules (optional, powerful)
**The [Rule Name] Rule.** [Short, forceful prohibition or doctrine, e.g. "The One Voice Rule. The primary accent is used on ≤10% of any given screen. Its rarity is the point."]

## 3. Typography

**Display Font:** [Family] (with [fallback])
**Body Font:** [Family] (with [fallback])
**Label/Mono Font:** [Family, if distinct]

**Character:** [1-2 sentence personality description of the pairing.]

### Hierarchy
- **Display** ([weight], [size/clamp], [line-height]): [Purpose; where it appears.]
- **Headline** ([weight], [size], [line-height]): [Purpose.]
- **Title** ([weight], [size], [line-height]): [Purpose.]
- **Body** ([weight], [size], [line-height]): [Purpose. Include max line length like 65–75ch if relevant.]
- **Label** ([weight], [size], [letter-spacing], [case if uppercase]): [Purpose.]

### Named Rules (optional)
**The [Rule Name] Rule.** [Short doctrine about type use.]

## 4. Elevation

[One paragraph: does this system use shadows, tonal layering, or a hybrid? If "no shadows", say so explicitly and describe how depth is conveyed instead.]

### Shadow Vocabulary (if applicable)
- **[Role name]** (`box-shadow: [exact value]`): [When to use it.]
- [...]

### Named Rules (optional)
**The [Rule Name] Rule.** [e.g. "The Flat-By-Default Rule. Surfaces are flat at rest. Shadows appear only as a response to state (hover, elevation, focus)."]

## 5. Components

For each component, lead with a short character line, then specify shape, color assignment, states, and any distinctive behavior.

### Buttons
- **Shape:** [radius described, exact value in parens]
- **Primary:** [color assignment + padding, in semantic + exact terms]
- **Hover / Focus:** [transitions, treatments]
- **Secondary / Ghost / Tertiary (if applicable):** [brief description]

### Chips (if used)
- **Style:** [background, text color, border treatment]
- **State:** [selected / unselected, filter / action variants]

### Cards / Containers
- **Corner Style:** [radius]
- **Background:** [colors used]
- **Shadow Strategy:** [reference Elevation section]
- **Border:** [if any]
- **Internal Padding:** [scale]

### Inputs / Fields
- **Style:** [stroke, background, radius]
- **Focus:** [treatment, e.g. glow, border shift, etc.]
- **Error / Disabled:** [if applicable]

### Navigation
- **Style, typography, default/hover/active states, mobile treatment.**

### [Signature Component] (optional; if the project has a distinctive custom component worth documenting)
[Description.]

## 6. Do's and Don'ts

Concrete, forceful guardrails. Lead each with "Do" or "Don't". Be specific: include exact colors, pixel values, and named anti-patterns the user mentioned in PRODUCT.md. **Every anti-reference in PRODUCT.md should show up here as a "Don't" with the same language**, so the visual spec carries the strategic line through. Quote PRODUCT.md directly where possible: if PRODUCT.md says *"avoid dark mode with purple gradients, neon accents, glassmorphism"*, the Don'ts here should repeat that by name.

### Do:
- **Do** [specific prescription with exact values / named rule].
- **Do** [...]

### Don't:
- **Don't** [specific prohibition, e.g. "use border-left greater than 1px as a colored stripe"].
- **Don't** [...]
- **Don't** [...]
```

### Step 4b: Write .impeccable/design.json sidecar (extensions only)

The frontmatter owns token primitives (colors, typography, rounded, spacing, components). The sidecar at `.impeccable/design.json` carries **what Stitch's schema can't hold**: tonal ramps per color, shadow/elevation tokens, motion tokens, breakpoints, full component HTML/CSS snippets (the panel renders these into a shadow DOM), and narrative (north star, rules, do's/don'ts). It extends the frontmatter, it doesn't duplicate it.

Regenerate the sidecar whenever you regenerate root `DESIGN.md`. If the user only asks to refresh the sidecar (e.g., from the live panel's stale-hint), preserve `DESIGN.md` and write only `.impeccable/design.json`.

#### Schema

```json
{
  "schemaVersion": 2,
  "generatedAt": "ISO-8601 string",
  "title": "Design System: [Project Title]",
  "extensions": {
    "colorMeta": {
      "primary":        { "role": "primary",  "displayName": "Editorial Magenta", "canonical": "oklch(60% 0.25 350)", "tonalRamp": ["...", "...", "..."] },
      "cool-paper": { "role": "neutral",  "displayName": "Cool Paper",    "canonical": "oklch(96% 0.005 230)", "tonalRamp": ["...", "...", "..."] }
    },
    "typographyMeta": {
      "display": { "displayName": "Display", "purpose": "Hero headlines only." }
    },
    "shadows": [
      { "name": "ambient-low", "value": "0 4px 24px rgba(0,0,0,0.12)", "purpose": "Diffuse hover glow under accent elements." }
    ],
    "motion": [
      { "name": "ease-standard", "value": "cubic-bezier(0.4, 0, 0.2, 1)", "purpose": "Default easing for state transitions." }
    ],
    "breakpoints": [
      { "name": "sm", "value": "640px" }
    ]
  },
  "components": [
    {
      "name": "Primary Button",
      "kind": "button | input | nav | chip | card | custom",
      "refersTo": "button-primary",
      "description": "One-line what and when.",
      "html": "<button class=\"ds-btn-primary\">GET STARTED</button>",
      "css": ".ds-btn-primary { background: #191c1d; color: #fff; padding: 16px 48px; letter-spacing: 0.05em; text-transform: uppercase; font-weight: 500; border: none; border-radius: 0; transition: background 0.2s, transform 0.2s; } .ds-btn-primary:hover { background: oklch(60% 0.25 350); transform: translateY(-2px); }"
    }
  ],
  "narrative": {
    "northStar": "The Editorial Sanctuary",
    "overview": "2-3 paragraphs of the philosophy, pulled from DESIGN.md Overview section.",
    "keyCharacteristics": ["...", "..."],
    "rules": [{ "name": "The One Voice Rule", "body": "...", "section": "colors|typography|elevation" }],
    "dos":   ["Do use ..."],
    "donts": ["Don't use ..."]
  }
}
```

**What changed from schemaVersion 1.** The old sidecar carried token primitive arrays (`tokens.colors[]`, `tokens.typography[]`, etc.). Those values now live in the frontmatter. The sidecar only carries metadata that can't live in the frontmatter (tonal ramps, canonical OKLCH when the hex is an approximation, display names, role hints), keyed by the frontmatter token name (`colorMeta.<token-name>`, `typographyMeta.<token-name>`). Components still carry full HTML/CSS because Stitch's 8-prop set can't hold them.

#### Component translation rules

The `html` and `css` fields must be **self-contained, drop-in snippets** that render correctly when injected into a shadow DOM. The panel applies them directly: no post-processing, no framework runtime.

1. **Tailwind expansion.** If the source uses Tailwind (className="bg-primary text-white rounded-lg px-6 py-3"), expand every utility to literal CSS properties in the `css` string. Do **not** reference Tailwind classes; do **not** assume a Tailwind CSS bundle is loaded. Each component is self-contained.
2. **Token resolution.** If the project exposes tokens as CSS custom properties on `:root` (e.g. `--color-primary`, `--radius-md`), reference them via `var(--color-primary)`; they inherit through the shadow DOM and stay live-bound. If tokens live only in JS theme objects (styled-components, CSS-in-JS), resolve to literal values at generation time.
3. **Icons.** Inline as SVG. Do not reference Lucide/Heroicons packages, icon fonts, or `<img src="...">`. A typical icon is 16-24px; copy the SVG path data directly.
4. **States.** Include `:hover`, `:focus-visible`, and (if meaningful) `:active` rules inline. A static default-only snapshot makes the panel feel dead. Hover + focus rules in the CSS make it feel alive.
5. **Reset bloat.** Extract only the component's *distinctive* CSS (background, color, padding, border-radius, typography, transition). Skip universal resets (`box-sizing: border-box`, `line-height: inherit`, `-webkit-font-smoothing`). The panel already has a neutral canvas; don't re-ship resets.
6. **Scoped class names.** Prefix every class with `ds-` (e.g. `ds-btn-primary`, `ds-input-search`) so component CSS doesn't collide with other components' CSS in the same shadow DOM.

#### What to include

Aim for a tight set of **5-10 components** that best represent the visual system:

- **Canonical primitives (always include if the project has them):** button (each variant as a separate component entry), input/text field, navigation, chip/tag, card.
- **Signature components (include if distinctive):** hero CTA, featured card, filter pill, any custom pattern the user mentioned as important in PRODUCT.md.
- **Skip the rest.** Utility components, form building blocks, wrapper layouts: not worth documenting unless visually distinctive.

If the project has **no component library yet** (bare landing page, new project), synthesize canonical primitives from the tokens using best-practice defaults consistent with the DESIGN.md's rules. Every `.impeccable/design.json` has *something* to render, even on day zero.

#### Tonal ramps

For each color token, generate an 8-step `tonalRamp` array: dark to light, same hue and chroma, stepped lightness from ~15% to ~95%. The panel renders this as a strip under the swatch. If the project already defines a tonal scale (Material `surface-container-low` family, Tailwind-style `blue-50..blue-900`), use those values. Otherwise synthesize in OKLCH.

#### Narrative mapping

Pull directly from the DESIGN.md you just wrote:

- `narrative.northStar` → the `**Creative North Star: "..."**` line from Overview
- `narrative.overview` → the philosophy paragraphs from Overview
- `narrative.keyCharacteristics` → the bulleted `**Key Characteristics:**` list
- `narrative.rules` → every `**The [Name] Rule.** [body]` across all sections, tagged with `section`
- `narrative.dos` / `narrative.donts` → the bullet lists from Do's and Don'ts verbatim

Do not reword. The panel shows these as secondary collapsible context; the same voice that's in the Markdown carries through.

### Step 5: Deliver the documents

Link DESIGN.md and any generated `.impeccable/design.json` sidecar. Briefly identify consequential inferred language and actual validation. Do not claim that the live panel rendered the result unless it was inspected. Requested revisions can continue without a mandatory follow-up questionnaire.

## Seed mode

Use when the user requests a starter design document and there is no visual system to extract. An explicit `--seed` request already selects this mode. Reuse supplied or approved choices without reconfirming the mode.

### Step 1: Establish available direction

Read the brief and any existing product/brand guidance. Identify the relevant palette roles, typography direction, motion needs, and provided references. Use a neutral, clearly labeled proposal for routine gaps; ask only about a missing choice that materially changes the requested direction. Do not require a fixed number of questions, named references, or an anti-reference.

### Step 2: Distinguish proposals from extracted values

A seed is a scaffold. Label proposed choices and unresolved values honestly; do not claim tokens or components were extracted from code that does not exist. Keep the starter proportionate to the requested scope.

### Step 3: Write seed DESIGN.md

Use the six-section spec from Scan mode. Populate the supplied or proposed seed choices; mark unresolved values explicitly. The seed is a scaffold, not a fabricated spec.

Lead the file with:

```markdown
<!-- SEED: re-run $impeccable document once there's code to capture the actual tokens and components. -->
```

Per-section guidance in seed mode:

- **Overview**: Describe the purpose and direction from the supplied brief. Include relevant references or anti-references when provided.
- **Colors**: Record supplied palette choices exactly and label new suggestions as proposals. Mark missing values as unresolved rather than inventing extracted tokens.
- **Typography**: Preserve the supplied type direction and any chosen fonts; distinguish proposed fonts from installed assets. Leave unresolved pairings explicit.
- **Elevation**: Describe the supplied or proposed depth treatment independently of motion. Leave it unresolved if it does not yet serve a design decision.
- **Components**: omit entirely; no components exist yet.
- **Do's and Don'ts**: carry PRODUCT.md's anti-references directly plus any relevant anti-reference supplied by the user.

Seed mode writes a minimal frontmatter with `name` and `description` only; no colors, typography, rounded, spacing, or components yet. Real tokens land on the next Scan-mode run. Skip the `.impeccable/design.json` sidecar in seed mode for the same reason: nothing to render.

### Step 4: Deliver

1. Show the seed DESIGN.md. Call out that it is a seed (the marker is the literal commitment).
2. Tell the user: "Re-run `$impeccable document` once you have some code. That pass will extract real tokens and generate the sidecar."

Your own write is the freshest source; no reload needed.

## Style guidelines

- **Frontmatter first, prose second.** Tokens go in the YAML frontmatter; prose contextualizes them. Don't redefine a token value in two places; the frontmatter is normative.
- **Cite PRODUCT.md anti-references by name** in the Do's and Don'ts section. If PRODUCT.md lists "SaaS landing-page clichés" or "generic AI tool marketing" as anti-references, the DESIGN.md Don'ts should repeat those phrases verbatim so the visual spec enforces the strategic line.
- **Match the spec, don't invent new sections.** The six section names are fixed. If you have Layout/Motion/Responsive content to document, fold it into Overview (philosophy-level rules) or Components (per-component behavior).
- **Descriptive > technical**: "Gently curved edges (8px radius)" > "rounded-lg". Include the technical value in parens, lead with the description.
- **Functional > decorative**: for each token, explain WHERE and WHY it's used, not just WHAT it is.
- **Exact values in parens**: hex codes, px/rem values, font weights; always the number in parens alongside the description.
- **Named rules are optional**: use `**The [Name] Rule.** [short principle]` only when a concise name clarifies a real design invariant. Do not invent slogans or a quota of rules to fill the schema.
- **Separate requirements from guidance.** Preserve real project constraints, but describe stylistic defaults as defaults. Do not turn a reviewer preference into a universal prohibition.
- **Concrete anti-pattern tests**. Stitch writes things like *"If it looks like a 2014 app, the shadow is too dark and the blur is too small."* A one-sentence audit test beats a paragraph of principle.
- **Reference PRODUCT.md**. The anti-references section of PRODUCT.md should directly inform the Do's and Don'ts section here. Quote or paraphrase.
- **Group colors by role**, not by hex-order or hue-order. Primary / Secondary / Tertiary / Neutral is the spec ordering.

## Pitfalls

- Don't paste raw CSS class names. Translate to descriptive language.
- Don't extract every token. Stop at what's actually reused; one-offs pollute the system.
- Don't invent components that don't exist. If the project only has buttons and cards, only document those.
- Preserve unrelated content in an existing DESIGN.md; explicit refresh authorization is sufficient for the requested update.
- Don't duplicate content from PRODUCT.md. DESIGN.md is strictly visual.
- Don't add a "Layout Principles" or "Motion" or "Responsive Behavior" top-level section. The spec has six, not nine. Fold that content where it belongs.
- Don't rename sections even slightly. "Colors" not "Color Palette & Roles". "Typography" not "Typography Rules". Tooling parsing depends on exact headers.
- Don't duplicate token values between frontmatter and prose. If a color is in `colors.primary` as hex, the prose can name it and describe its role but should not reassert a different hex. The frontmatter is normative.
- Don't invent frontmatter token groups outside Stitch's schema (no `motion:`, `breakpoints:`, `shadows:` at the top level). Stitch's Zod schema only accepts `colors`, `typography`, `rounded`, `spacing`, `components`. Anything else belongs in the sidecar's `extensions`.
