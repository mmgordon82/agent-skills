# Initialize Product Context

Use when the user requests `$impeccable init`/`teach` or asks to capture project design context. Missing context files during an ordinary UI task do not invoke this command.

## Read existing context

Inspect the target app, relevant README/configuration, representative components, tokens, and existing PRODUCT.md/DESIGN.md at the project root, `.agents/context/`, or `docs/`. Keep monorepo app context distinct from root context. Reuse existing documents and the current conversation instead of recrawling unrelated files.

If existing files are explicitly targeted for refresh, update the requested portions and preserve unrelated content. If a bare init request encounters complete documents and the intended change is unclear, report that state and ask what should be refreshed. Do not silently replace a document.

## Capture the missing strategy

For sparse or ambiguous product context, use a short interview. Ask focused questions about the material unknowns and wait for the answers. For already supplied or approved context, proceed without another confirmation round. Do not promote speculative user roles, roadmap claims, testimonials, or accessibility commitments to facts.

Useful topics:

- Primary audience, context, purpose, and desired outcome.
- Whether the target is principally a brand/marketing surface or a working product interface.
- Platform: `web`, `ios`, `android`, or `adaptive` for actual per-OS adaptation. Determine this from the rendered platform and project evidence, not a framework name alone; mobile web remains web.
- Positioning, voice, known references/anti-goals, and accessibility needs.
- For brand surfaces, intended actions and available proof such as genuine testimonials, case studies, or approved logos. Distinguish actual visitors from product users when relevant.

Only ask what the request and project do not establish. Respect an explicitly requested interview; otherwise do not require a fixed number of rounds or mandatory questions about every field. Visual tokens belong in DESIGN.md, not this strategic document.

## Write PRODUCT.md

Use the existing context location, or the target project root for a new file. Preserve the parseable bare values for Register and Platform. Other fields should describe known context; omit irrelevant sections or clearly mark unresolved information rather than inventing it.

```markdown
# Product

## Register

product

## Platform

web

## Users
[Who they are, their context, the job to be done. Primary audience; a secondary audience or a surface-vs-user split only when they apply.]

## Product Purpose
[What this product does, why it exists, what success looks like]

## Positioning
[The single strategic claim every screen reinforces. Not a visual rule, not an anti-reference.]

## Conversion & proof
[Brand register only. Product register: omit this section entirely, heading included.]
- Primary and secondary CTA: [...]
- The line a visitor remembers after 10 seconds: [...]
- Belief ladder: [...]
- Proof on hand: [testimonials, case studies, press, or logos, referenced by path]

## Brand Personality
[Voice, tone, 3-word personality, emotional goals]

## Anti-references
[What this should NOT look like. Specific bad-example sites or patterns to avoid.]

## Design Principles
[3-5 strategic principles derived from the conversation. Principles like "practice what you preach", "show, don't tell", "expert confidence". NOT visual rules like "use OKLCH" or "magenta accent".]

## Accessibility & Inclusion
[WCAG level, known user needs, considerations]
```

For brand work, use Conversion & proof only when supported. Keep task-specific fidelity, time budgets, and screen scope in the task brief. Read any legacy `.impeccable.md` directly if it exists; do not assume a helper migrated or renamed it.

## Optional related work

Create or refresh DESIGN.md only when requested or included in the approved init scope; use [document.md](document.md) for its token/schema contract. Keep a pre-implementation seed distinguishable from tokens observed in code.

Configure live mode only when the user requests it. For a web project with suitable HTML entries, follow [live.md](live.md)'s first-time setup and CSP boundaries. Preserve existing config unless its refresh is authorized. Do not set up live injection, alter CSP, install hooks, pin commands, or edit AGENTS.md as an incidental effect of documenting a product.

## Deliver

Identify the files written and any material unresolved context. A short recommendation for the next useful action is enough when appropriate. If init was explicitly requested as part of a broader approved task, return to that task; no separate shape/palette confirmation is implied by initialization.
