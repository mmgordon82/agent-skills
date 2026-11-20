# Product surfaces

Use for app interfaces, dashboards, settings, tables, and tools where people are completing tasks. Familiar conventions often reduce effort; visual identity should support the workflow.

## Hierarchy and typography

Expose the primary action and relevant result promptly. Use the existing type system; one legible family may cover headings, labels, and data. A compact rem scale often suits dense controls, while fluid sizing can help particular layouts. Choose from the actual content and viewing conditions rather than imposing a fixed scale. Keep sustained prose readable and tables appropriately dense.

## Color and components

Use semantic roles for selection, focus, errors, warnings, success, and disabled states. Keep the same meaning consistent across the product and verify text/control contrast in supported themes. Accent colors can support hierarchy and identity as well as actions.

Reuse familiar accessible components. Cover states that apply to each interaction: a static label does not need loading/error states, while a submitting form does. Choose skeletons, progress indicators, spinners, or immediate updates according to delay and task. Empty and error states should explain the situation and a supported next action.

## Layout and interaction

Build each screen around the decision its user makes there: a chart's title states the question it answers, and table columns come from that decision, not a generic schema. Never invent data: no made-up stats, deltas, activity feeds, testimonials, or "John Doe" filler. Show real data, a labeled sample, or an empty state that names the cause and the next action. No nav links or controls that lead nowhere.

Group related controls, preserve navigation and context, and adapt density to the user's task. Responsive changes can reorganize sidebars, columns, or data views. Use modals for bounded decisions or focused tasks where they fit; consider inline or progressive alternatives when they preserve context better.

Keep actions available to keyboard, touch, and assistive technology. Test focus, labels, content extremes, and overlay clipping where affected. Native work follows the target platform's control and navigation conventions.

## Motion

Provide clear state feedback without delaying the task. Short transitions are often sufficient; instant changes are appropriate when animation adds no meaning or reduced motion is requested. Preserve interaction during motion and keep essential content visible when animation does not run.

## Review

Check task completion, predictable behavior, coherent component vocabulary, and readability before cosmetic novelty. Preserve the existing brand and deliberate exceptions. Validate the changed flow and relevant responsive/states; do not expand a small UI fix into a redesign or exhaustive product audit.
