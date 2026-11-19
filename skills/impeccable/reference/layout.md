Space is the most underused design tool. Find the layout's actual problem (monotone spacing, weak hierarchy, identical card grids) and fix the structure, not the surface.

---

## Register

Brand: asymmetric compositions, fluid spacing with `clamp()`, intentional grid-breaking for emphasis. Rhythm through contrast: tight groupings paired with generous separations.

Product: predictable grids, consistent densities, familiar navigation patterns. Responsive behavior is structural (collapse sidebar, responsive table), not fluid typography. Consistency IS an affordance.

Native (`ios` / `android` / `adaptive`): structure follows the Layout section of [ios.md](ios.md) / [android.md](android.md) (read it first if Setup hasn't already): platform navigation, insets, and touch targets, never the CSS tooling below.

---

## Assessment and optional detector evidence

Inspect the target's layout before reading detector findings, so the scan does not anchor the visual assessment. For a substantial review, use a bounded independent subagent for the manual assessment while another agent or the parent runs the mechanical scan. Reuse the session's delegation authorization. For a small fix or unavailable delegation, perform the two checks sequentially.

The relevant detector command is:

```bash
node "$IMPECCABLE_DIR/scripts/detect.mjs" --json --scope layout [target files or dirs]
```

Use the loaded skill directory and offline environment defined in SKILL.md. If Node or the helper is unavailable, continue with source/rendered inspection and report that the automated scan was not run; do not install tooling merely to complete this command. Exit code 2 means findings, not a crashed scan.

The detector has limited coverage. For layout, inspect arbitrary spacing and stacking values against the project's tokens; for type, inspect relative/fluid sizing and line-height in the actual layout. Confirm real issues before fixing them, preserve justified design choices, and do not treat aesthetic detector matches as automatic defects.

Apply only changes within the requested scope. A clean scan does not replace visual verification. Report relevant gaps without a mandatory methodology banner or another approval loop.

---

## Assess Current Layout

Use the relevant checklist items for the independent or local assessment. Analyze what's weak about the current spatial design:

1. **Spacing**:
   - Is spacing consistent or arbitrary? (Random padding/margin values)
   - Is all spacing the same? (Equal padding everywhere = no rhythm)
   - Are related elements grouped tightly, with generous space between groups?

2. **Visual hierarchy**:
   - Apply the squint test: blur your (metaphorical) eyes. Can you still identify the most important element, second most important, and clear groupings?
   - Is hierarchy achieved effectively? (Space and weight alone can be enough; is the current approach working?)
   - Does whitespace guide the eye to what matters?

3. **Grid & structure**:
   - Is there a clear underlying structure, or does the layout feel random?
   - Are identical card grids used everywhere? (Icon + heading + text, repeated endlessly)

4. **Rhythm & variety**:
   - Does the layout have visual rhythm? (Alternating tight/generous spacing)
   - Is every section structured the same way? (Monotonous repetition)
   - Are there intentional moments of surprise or emphasis?

5. **Density**:
   - Is the layout too cramped? (Not enough breathing room)
   - Is the layout too sparse? (Excessive whitespace without purpose)
   - Does density match the content type? (Data-dense UIs need tighter spacing; marketing pages need more air)

**CRITICAL**: Layout problems are often the root cause of interfaces feeling "off" even when colors and fonts are fine. Space is a design material; use it with intention.

## Plan Layout Improvements

Create a systematic plan:

- **Spacing system**: Use a consistent scale (a framework's built-in scale like Tailwind's, rem-based tokens, or a custom system). The specific values matter less than consistency.
- **Hierarchy strategy**: How will space communicate importance?
- **Layout approach**: What structure fits the content? Flex for 1D, Grid for 2D, named areas for complex page layouts.
- **Rhythm**: Where should spacing be tight vs generous?

## Improve Layout Systematically

### Establish a Spacing System

- Use a consistent spacing scale (framework scales like Tailwind, rem-based tokens, or a custom scale all work). What matters is that values come from a defined set, not arbitrary numbers.
- Prefer a 4pt base scale (4, 8, 12, 16, 24, 32, 48, 64, 96px) over 8pt; 8pt is too coarse and you'll frequently need 12px between 8 and 16.
- Name tokens semantically if using custom properties: `--space-xs` through `--space-xl`, not `--spacing-8`
- Use `gap` for sibling spacing instead of margins; eliminates margin collapse hacks
- Apply `clamp()` for fluid spacing that breathes on larger screens

### Create Visual Rhythm

- **Tight grouping** for related elements (8-12px between siblings)
- **Generous separation** between distinct sections (48-96px)
- **Varied spacing** within sections (not every row needs the same gap)
- **Asymmetric compositions**: a deliberate choice when the content invites it (not a default to chase).

### Choose the Right Layout Tool

- **Use Flexbox for 1D layouts**: Rows of items, nav bars, button groups, card contents, most component internals.
- **Use Grid for 2D layouts**: Page-level structure, dashboards, data-dense interfaces, anything where rows AND columns need coordinated control.
- Use named grid areas (`grid-template-areas`) for complex page layouts; redefine at breakpoints.
- Use **container queries** for components, viewport queries for page layouts. A card in a narrow sidebar can stay compact while the same card in a main content area expands automatically:

```css
.card-container { container-type: inline-size; }
.card { display: grid; gap: var(--space-md); }
@container (min-width: 400px) {
  .card { grid-template-columns: 120px 1fr; }
}
```

### Break Card Grid Monotony

- Don't default to card grids for everything; spacing and alignment create visual grouping naturally
- Use cards when grouping helps; avoid redundant nested surfaces that obscure hierarchy
- Vary card sizes, span columns, or mix cards with non-card content to break repetition

### Strengthen Visual Hierarchy

- Use the fewest dimensions needed for clear hierarchy. Space alone can be enough; generous whitespace around an element draws the eye. Some of the most polished designs achieve rhythm with just space and weight. Add color or size contrast only when simpler means aren't sufficient.
- The best hierarchy combines 2–3 dimensions at once. A heading that's larger, bolder, AND has more space above it reads as primary without trying:

| Tool | Strong Hierarchy | Weak Hierarchy |
|------|------------------|----------------|
| **Size** | 3:1 ratio or more | <2:1 ratio |
| **Weight** | Bold vs Regular | Medium vs Regular |
| **Color** | High contrast | Similar tones |
| **Position** | Top/left (primary) | Bottom/right |
| **Space** | Surrounded by white space | Crowded |

- Be aware of reading flow: in LTR languages, the eye naturally scans top-left to bottom-right, but primary action placement depends on context (e.g., bottom-right in dialogs, top in navigation).
- Create clear content groupings through proximity and separation.

### Manage Depth & Elevation

- Build a consistent shadow scale (sm → md → lg → xl); shadows should be subtle
- Use elevation to reinforce hierarchy, not as decoration

### Optical Adjustments

- If an icon looks visually off-center despite being geometrically centered, nudge it. But only if you're confident it actually looks wrong. Don't adjust speculatively.
- Text at `margin-left: 0` looks slightly indented because of letterform whitespace; a negative margin (`-0.05em`) optically aligns it. Geometrically centered glyphs often look off-center (play icons need to shift right, arrows shift toward their direction).
- Touch targets must be 44×44px minimum even when the visual element is smaller. Expand the hit area with padding or a pseudo-element:

```css
.icon-button { width: 24px; height: 24px; position: relative; }
.icon-button::before {
  content: ''; position: absolute; inset: -10px;
}
```

## Layout criteria

Use the spacing system consistently and introduce exceptions when content requires them. Choose cards, nesting, repeated grids, dividers, and emphasized metrics for their information role. Repetition can aid scanning; variation can clarify hierarchy. Prominent numbers must represent real data or clearly marked sample content.

## Verify Layout Improvements

- **Squint test**: Can you identify primary, secondary, and groupings with blurred vision?
- **Rhythm**: Does the page have a satisfying beat of tight and generous spacing?
- **Hierarchy**: Is the most important content obvious within 2 seconds?
- **Breathing room**: Does the layout feel comfortable, not cramped or wasteful?
- **Consistency**: Is the spacing system applied uniformly?
- **Responsiveness**: Does the layout adapt gracefully across screen sizes?

Answer each item above by citing the file, selector, or value that satisfies it; never a bare yes. Then re-run the pre-scan and fix until the count of unresolved items and unaccepted findings is zero.

Complete the requested change and its relevant checks. Use `$impeccable polish` only when broader polish is requested or remaining evidence justifies that work.

## Live-mode signature params

Each variant MUST declare a `density` param. Drive all spacing tokens in the variant's scoped CSS through `calc(var(--p-density, 1) * <base>)`: paddings, gaps, column widths. Users slide from airy to packed and see layout re-breathe with no regeneration.

```json
{"id":"density","kind":"range","min":0.6,"max":1.4,"step":0.05,"default":1,"label":"Density"}
```

For variants whose topology genuinely changes (stacked vs. side-by-side, grid vs. bento), use a `steps` param whose scoped CSS branches via `:scope[data-p-structure="X"]`. One structure param + one density param is a powerful combo; resist adding a third.

```json
{"id":"structure","kind":"steps","default":"grid","label":"Structure","options":[
  {"value":"stacked","label":"Stacked"},
  {"value":"grid","label":"Grid"},
  {"value":"bento","label":"Bento"}
]}
```

See `reference/live.md` for the full params contract.
