# Usability and design judgment

Use when deciding what a screen or flow should do, diagnosing why people miss, misclick, repeat, or abandon, specifying a control, form, error, mode, or destructive action, or reviewing a public page for clarity and trust. Covers app and tool UI and public sites.

Sources are credited in parentheses: Norman, *The Design of Everyday Things* (2013); Krug, *Don't Make Me Think, Revisited* (2014); Weinschenk, *100 Things Every Designer Needs to Know About People* (2011); Wathan and Schoger, *Refactoring UI*; Yablonski, *Laws of UX*, 2nd ed. (2024). Apply the rules; do not quote or lecture.

Other references go deeper on adjacent topics. Do not repeat them here:

| Topic | Reference |
|---|---|
| Nielsen heuristic scoring, cognitive-load checklist, personas, P0 to P3 severity | [critique.md](critique.md) |
| Interactive states, focus, forms, modals, undo toast, gestures, keyboard | [interaction-design.md](interaction-design.md) |
| Error, button, empty-state, and confirmation copy | [clarify.md](clarify.md) |
| Spacing scale, rhythm, grid, elevation scale, optical fixes, touch targets | [layout.md](layout.md) |
| Type scale, measure, line-height, tracking | [typeset.md](typeset.md) |
| Palette roles, OKLCH, tinted neutrals, dark mode | [colorize.md](colorize.md) |
| First run, empty states, tours | [onboard.md](onboard.md) |
| Responsive and touch adaptation | [adapt.md](adapt.md) |
| Surface register | [product.md](product.md), [brand.md](brand.md) |

## Decide before designing

A design decision is a bet under constraint. Name it before reaching for a fix.

### Name the decision

1. **Activity.** What is the person trying to do in the world, not which widget is ugly. The stated problem is usually a symptom; ask how you know it is the root problem and trace causes (Norman). If many people share a stable activity, design the activity rather than each stated preference.
2. **Cost of being wrong.** Annoyance, lost work, money, trust, or safety. Cost sets the strength of the constraint and how much evidence you need.
3. **Type.** Pick one. A tool from the wrong row does not answer the question.

| Type | Question | Wrong tool | Use |
|---|---|---|---|
| Problem | Are we solving the real activity? | A visual system | Norman: never solve the problem as first stated |
| Scope | What is in this release? | Another feature idea | Feature first, cut to the activity |
| Interaction | Can they do it and recover? | A style pass | Krug plus Norman |
| Visual | Does hierarchy match importance? | A new information architecture | Refactoring UI, after the action is settled |

Violation: "The checkout looks dated. Users miss the pay button and then cannot tell if payment succeeded." Fix: this is an interaction problem, not visual. Missing the button is a Gulf of Execution (signifier, placement, Fitts); not knowing it worked is a Gulf of Evaluation (feedback). Fix both before restyling.

### Evidence ladder

Use the lowest rung that can change the call.

1. Convention and prior research (Jakob's law, known patterns).
2. Expert review against this reference.
3. A task test with a few participants. Three people on a real task surface the serious problems (Krug).
4. A reversible ship with a measure tied to the activity, not a vanity metric.

Arguments about nav placement, the fold, or click counts are not evidence. Separate fact (needs a source or test), convention (breaking it needs a reason), and taste (does not block a ship if the page passes the trunk test). A dominant voice in the room is not a user signal; groups follow a dominant personality and uncertain people let others decide (Weinschenk).

Violation: the team has argued for two weeks about whether search goes in the header or a menu. Fix: stop arguing; give three participants a task that needs search and watch where they look. Because people scan and satisfice, the placement has to be obvious on first glance, which the test shows directly (Krug).

### Reversibility

- Reversible and cheap: decide, ship, watch the stage that failed.
- Expensive or one-way (data loss, payments, a public convention change): constrain, preview, and test before commit.

### When principles conflict

Name the conflict. Do not average the two sides.

| Tension | Resolution |
|---|---|
| Familiar vs better | Start with the convention. Break it only for a gain the person can feel, with feedforward for the new action (Krug; Norman; Jakob). |
| More choice vs faster choice | People want more options than they can process and equate choice with control. Keep control without dumping the set: strong default, categories, progressive disclosure that does not hide state (Weinschenk; Hick). |
| Pretty vs usable | Polish makes a broken flow feel fine. Test the task anyway; polish after the trunk test passes (aesthetic-usability). |
| Engagement vs autonomy | Variable rewards raise repeat use. For ongoing work, prefer progress, mastery, and control (Weinschenk). |
| Simple screen vs real complexity | Complexity is conserved. Move it into the system, a default, or a constraint (Tesler; Norman). |
| Instructions vs redesign | A label, tour, or tooltip added to make a control usable is a failed signifier. Fix the control first (Norman; Krug). |
| Wrong action has a real cost | Norman wins: constraints and undo beat extra copy. |
| Action right, screen looks unfinished | Refactoring UI wins on hierarchy, spacing, type, and color. Do not restyle a failed mapping. |

Violation: engineering wants a novel gesture navigation to replace the tab bar because it will feel innovative. Fix: keep the tab bar unless the gesture gives a gain users feel, has a visible signifier and a visible fallback, and wins a task test. Usability iteration improves known activities; it does not deliver radical innovation, and convention changes take a long time to land (Norman).

### Product calls

Sequence for "what do we build":

1. State the activity, not the feature name.
2. Check it is the root problem. If the only evidence is a stakeholder request, say so and name the observation that would confirm it.
3. Design the feature, not the shell. Navigation, sidebar, logo, and layout grid wait until a few real features exist (Refactoring UI).
4. Cut to what answers the activity in this release. Norman's law: the day the team is named it is already behind schedule and over budget. Cut scope, not signifiers; a smaller flow that answers every stage question beats a complete flow with weak feedforward.
5. Leave a fast path for experts and knowledge in the world for the rare path.
6. Design the peak and the end. A clumsy confirmation can ruin a good flow (peak-end).
7. Pick the next test before visual polish.

Prioritize by failure cost and frequency:

| | Frequent | Rare |
|---|---|---|
| High cost | Design the path and the recovery now | Constrain so it cannot happen by accident |
| Low cost | Make it obvious and fast | Do not design the shell around it |

Refuse or shrink: a shell, design system, or homepage redesign before the core task is designable; choice added because "users want control" when the set is large; points, streaks, or variable rewards on a task that fails because the control is unclear; a promise of radical innovation from a usability cycle.

Violation: "Build the app shell, design system, and homepage before we design search" for a flight booking product. Fix: design the search flow first with real fields and results; the shell is shaped by the features it must hold. Next test: can three people find and book a specific flight.

### Record the call

For a substantive call, write this. For a small fix, just apply the rule.

```
Decision:
Type: problem | scope | interaction | visual
Activity:
Cost of being wrong:
Why a reasonable person fails or stalls:
Call:
Tradeoff accepted:
Convention kept / broken and why:
Not doing:
Next test: who, what task, what result would reverse this
```

"Looks better" is not a test. Name the page question they must answer, the task they must finish, or the metric that would reverse the call.

## Make actions discoverable and understandable

Good design gives **discoverability** (what actions are possible, where, and how) and **understanding** (what it means and what the controls do). Complexity is acceptable; confusion is not. Do not "simplify" by hiding state (Norman).

### The action cycle

People act in a cycle. Every question must be answerable from the product itself. A question answered only by memory, a manual, or a teammate is an open gulf.

| Stage | Side | Question the person asks |
|---|---|---|
| Goal | | What do I want to accomplish? |
| Plan | Execution | What are the alternative action sequences? |
| Specify | Execution | What action can I do now? |
| Perform | Execution | How do I do it? |
| Perceive | Evaluation | What happened? |
| Interpret | Evaluation | What does it mean? |
| Compare | Evaluation | Is this okay? Did I reach the goal? |

- **Gulf of Execution**: gap between intent and the actions the thing appears to allow. Close it with feedforward: signifiers, constraints, mappings, conceptual model.
- **Gulf of Evaluation**: gap between what happened and what the person can perceive, interpret, and compare to the goal. Close it with immediate, informative feedback and a model that matches the goal.

A findable control that is silent after activation closed execution and left evaluation open. A visible result that cannot be interpreted ("Error 47") has not closed evaluation.

Review move: for each critical step, answer the seven questions as the user would, from the screen alone.

### The seven principles

All seven should hold for ordinary tasks. A missing principle is a finding, not a style note.

| Principle | Holds when |
|---|---|
| Discoverability | Possible actions and current state can be determined without trial and error or a manual. |
| Feedback | After an action, the new state is fully and continuously available. |
| Conceptual model | The product projects enough structure to predict results and feel in control. |
| Affordances | The desired action is actually possible for this person (reach, permission, device, input method). |
| Signifiers | Perceivable signals show where to act and how to read the result. |
| Mappings | Controls relate to outcomes by spatial analogy, proximity, or timing. Related controls are grouped. |
| Constraints | Physical, semantic, cultural, and logical limits make the wrong move hard. |

### Affordances and signifiers

- An **affordance** is a relationship between an object and an agent: what actions are possible for this person. You do not "add" one. On a touch screen the whole screen affords touching; a drawn circle only signifies where. A control someone cannot reach, see, or activate has no affordance for them, which is why accessibility failures are affordance failures.
- A **signifier** is any perceivable signal of where and how to act: a label, icon, handle, arrow, drop shadow under a button, or an accidental one like a worn path. Signifiers are what design controls.
- **Perceived affordances can lie.** A flat bar that looks pushable on a door that must be pulled is a misleading signifier.

Rules:

- Make the form suggest the action. Buttons look pressable, sliders draggable, and text that is not an action does not look like a button (Norman; Krug: ambiguous clickability is a tax paid on every visit).
- If a simple control needs a sign, the control failed. A bolted-on label, tooltip, or tour on a simple control is evidence of failed discoverability, not a fix. Fix shape, placement, or mapping first; keep a short label if the convention is weak.
- Unknown icons are unlabeled doors. Icon-only controls need a conventional shape and an accessible name; unfamiliar ones need a visible text label.
- Accidental signifiers get read whether you meant them or not: empty regions, disabled rows, badge counts, a stray item on an empty shelf. Design them.
- Screens lack incidental physical cues (how much is left, where the edge is). Add them on purpose: progress, counts, scroll affordance, position in a list.
- Do not use deliberately misleading signifiers in tools. People learn the lie and ignore later signals.
- Invisible anti-affordances need a signifier, the way glass needs a mark. A hidden limit, a field that silently truncates, or a gesture-only action is a secret rule.

Violation: a dashboard team says users are "too stupid" and asks for a longer onboarding tour and more tooltips. Fix: treat tickets as design findings; walk the action cycle on the failing tasks and fix the signifiers and mappings. Tooltips go on what remains genuinely unconventional, not on every control. "Human error" on an ordinary task is a design finding until proven otherwise.

### Mapping

- Put the control on or beside the object it changes. A global toolbar action for a local item is a mapping defect; delete belongs on the item unless it deletes the page (Norman, semantic constraint).
- Arrange controls in the same pattern as the things they control. A row of identical controls with no layout match forces memorization, which fails under interruption.
- Group related actions; separate description-similar dangerous neighbors (Archive and Delete side by side).
- Place the primary action where the mapping predicts it: at the end of a left-to-right form, on the item it affects.
- "Up, right, forward means more or next" is a convention, not nature. Check the audience; mirror for right-to-left; do not invent a second mapping for the same gesture.
- A mapping feels natural when the conceptual model is easy to imagine, even if the mechanism differs. Support a simple model; do not expose the mechanism.

Violation: a settings screen has two identical toggle rows both labeled "Enable" and a single Save hidden in a menu; people flip the wrong one and are unsure it saved. Fix: label each toggle with what it enables, place it next to the thing it affects, and either save on toggle with visible "Saved" feedback or show a visible Save whose result is confirmed in place. A confirmation dialog fixes neither problem.

### Feedback

- **Immediate.** Direct manipulation needs a response within about a tenth of a second; silence beyond that is already disconcerting (Norman). Interaction feels productive when neither side waits; above about 400 ms, acknowledge at once and say what was received and what is in progress (Doherty). Silent submit buttons get pressed again.
- **Informative.** A flash or beep that does not say what happened is worse than nothing if it causes anxiety. Name the outcome in the user's goal language: "Saved to drafts" is not "Published".
- **Attributable.** The person must know which control or part of the system responded. Show the result near where they acted; people miss changes outside their attention (Weinschenk).
- **Prioritized.** Unimportant information stays quiet; important signals capture attention. Too much feedback is a backseat driver: people disable it and miss the one that mattered.
- **Not one channel for many states.** Do not encode several states in one beep, one badge, or one color. Pair color with text or shape.
- Empty, loading, partial, error, and success are designed states. An empty region with no signifier is a Norman door. See [interaction-design.md](interaction-design.md) for the state set.

### Conceptual model and system image

Three models exist: the designer's model, the user's mental model, and the system image (everything the product presents: layout, labels, behavior, errors, timing). Users never see the designer's model; they infer theirs from the system image. If the two diverge, the design failed.

- A simplified model is fine until an assumption breaks: a cloud file shown as local that cannot be saved offline, automation that changed mode, a setting that only applies inside one activity. When an assumption breaks, the interface must say which one.
- Metaphors (files, folders, trash) are models, not storage.
- Settings that affect a later screen must be predictable from the model. Hidden cross-effects produce confident wrong plans.
- Activity presets are fine. Overriding one parameter must not reset the rest, and a manual override must not destroy the current activity.
- Show current state before asking for a decision: selected, saved, sent, offline, automated, permission.

### Three levels of processing

| Level | What it judges | Design job |
|---|---|---|
| Visceral | Immediate look and feel | Signal what this is before reading. A threatening or toy-like look is believed over the copy. |
| Behavioral | Can I specify the action and read the result? | Make the action and the immediate result match expectations. |
| Reflective | The story afterward: control, blame, pride, trust | Support a good story; a humiliating error message fails here even if the task succeeded. |

"I can't do it" is usually behavioral; "it feels wrong" is visceral or reflective. Fix the level that failed. Visceral polish does not repair a behavioral failure (Norman; aesthetic-usability).

### Knowledge in the world vs in the head

| | In the world | In the head |
|---|---|---|
| Learning | Easy at the moment of use | Must be learned |
| Speed once learned | Slower: look and interpret | Fast |
| Reminding | Cues itself if present at the right time and place | No cue; fails when interrupted or rare |
| Failure | Clue missing, ambiguous, or late | Forgotten, especially under stress |

- First-run, rare, interrupted, and return-after-absence paths need knowledge in the world: examples, defaults, inline structure, visible state, persisted drafts.
- Expert paths may live in the head: shortcuts and accelerators, without removing the signifiers.
- Multi-step infrequent flows show progress and a review before commit. Do not require the plan to stay in memory.
- Capture head knowledge into the world as it arrives (pilots write down clearances as they hear them). Let people paste, pin, or carry values forward instead of retyping them.
- A reminder needs a **signal** (something needs attention) and a **message** (what). A red dot alone fails the message test; a note no one opens fails the signal test. Too early is as useless as absent.
- Constraints let precise behavior come from imprecise knowledge. Do not demand memorized precision the interface could have constrained.

### Discoverability smells

- Trial and error on a task done daily.
- One memorized setting; the rest of the panel ignored.
- Instructions taped to the object (a label explaining a simple control).
- Identical controls that need opposite actions.
- State that becomes visible only after the wrong action.

### Spec lines for a new control or step

```
Affordance:  who can actually do this (permission, device, reach, input method)
Signifier:   what they see or hear that shows where and how
Mapping:     why it is here and what it moves
Feedforward: what they are told will happen
Feedback:    what changes, in what words, by when
Constraint:  what wrong action is impossible
Recovery:    undo, draft, or lock-in, and the cost if they are wrong
```

If any line is "the user will know", the spec is incomplete.

## Pages people grasp at a glance

### Do not make them think

Every page should be self-evident, or at least self-explanatory. If the person must pause to work out what something is or whether it is clickable, that moment failed. Thought is acceptable on genuinely hard domain decisions; it is not acceptable on "where do I click" or "what does this label mean" (Krug).

### How people actually use screens

- **They scan.** They look for words that match their task and skip the rest.
- **They satisfice.** They take the first reasonable option, not the best one.
- **They muddle through.** They do not read instructions or form a correct model; once something works, they keep doing it.

Design for that reader, not a careful one. Consequences: the right choice must look right at a glance; labels must match the words people already have in mind; instructions will not be read, so the interface must not depend on them.

### Billboard rules

- **Hierarchy matches importance.** Important things look important, related things are grouped and visually nested. Weinschenk: people group nearby items, and past experience sets where they look.
- **Conventions are a feature.** Use them. Break one only when the gain is obvious, and then make the new thing clearly signified (Krug; Jakob).
- **Clickable things look clickable.** No hover-only affordances.
- **Cut noise.** Decoration, needless instructions, and "happy talk" (welcome blurbs that say nothing) compete with the task.
- **Omit needless words, then cut again.** Shorter pages make the useful content more prominent and reduce scrolling.
- **Mindless choices.** Categories should be obvious buckets (animal, vegetable, mineral), not clever names. A choice that needs thought is a labeling defect.
- **Support reading as scanning.** Real headings, short paragraphs, lists, examples instead of definitions. Reading is not comprehending, and screen text is harder than paper (Weinschenk). Copy rules live in [clarify.md](clarify.md).

### Trunk test for navigation

Pick any page at random. At a glance, answer:

| Question | Passes when |
|---|---|
| What site or product is this? | Identity (name or logo) is visible in a consistent place |
| What page is this? | A page name is prominent and matches what was clicked to get here |
| What are the major sections? | Primary navigation is visible and labeled |
| What can I do at this level? | Local options and the primary action are visible |
| Where am I? | Current section and page are marked (active state, breadcrumb) |
| How do I search? | Search is where people expect it, if the product has search |

Any miss is a navigation or identity defect, not a content problem.

Violation: an app page with no product name, a title of "Dashboard", and navigation made of unlabeled icons. Fix: show identity, a specific page title, and text labels on the navigation (or conventional icons with labels on hover and accessible names, only if the icons are truly standard). Do this before any new visual system.

### Home page and first screen

Answer, without a paragraph: what is this, what can I do here, why should I care, where do I start. If it takes a paragraph, the screen failed (Krug). Look and feel is the first trust signal (Weinschenk), and the visceral read is believed over the copy (Norman).

### Goodwill

People arrive with a limited reservoir of goodwill. You drain it by hiding what they came for, asking for information you do not need, demanding input in your format, or scolding them for mistakes. Spend it only on something they value. Courtesy is a usability requirement (Krug). People apply social rules to software, so a rude interface feels rude (Weinschenk).

Violation: a signup form asks for phone number, company size, and referral source before showing the tool. Fix: ask only for what is required to start; collect the rest later, when it has a visible purpose, or never.

### Mobile and touch

No hover, less room, more satisficing. Prioritize the task; do not ship a shrunk desktop. Affordances must be visible without a cursor change. Gestures are invisible signifiers; always give a visible alternative (Krug; Norman). See [adapt.md](adapt.md) and [interaction-design.md](interaction-design.md).

### Accessibility is part of the first law

If someone cannot perceive the control or the heading structure, the page has already made them think. Unnamed controls and tiny hit areas are failed affordances for the people who cannot use them. Meet the project standard from the start; it is not a later coat (Krug; Norman).

### Test small and often

Three participants on a real task, observed, reveal the serious problems. Fix those, test again. A short recurring session beats a lab study that never happens. When the team is arguing, specify the test instead of picking a winner (Krug).

## How people perceive, remember, and decide

Apply the group that matches the failure; do not recite all of them. Each finding is from Weinschenk unless credited otherwise. When citing one in a call, state what a test would show if it does not apply here.

### See and read

| Finding | Design move |
|---|---|
| Vision dominates; people see patterns and group nearby or similar items. | Use proximity and similarity to show what belongs together. Do not rely on borders to fix ambiguous spacing. |
| People miss changes they are not attending to. | Show results where the eye already is, next to the control that caused them. Announce status changes; do not change a distant region silently. |
| Past experience decides where people look. | Put things where comparable products put them (Jakob). An unexpected location is effectively hidden. |
| Peripheral vision carries cues; the layout is taken in before content is read. | Make the structure itself say what the page is. |
| Color-vision deficiency affects about 9% of men and 0.5% of women; red/blue combinations are hard to read. | Never rely on color alone. Pair with text, icon, or shape. Avoid red and blue text adjacent. |
| Reading is not comprehending; screen reading is harder than paper. | Headings, short chunks, examples. Cut words before adding explanation. |

### Remember

| Finding | Design move |
|---|---|
| Working memory is small. | Chunk information. Keep context visible across steps instead of making people carry it. |
| Recognition beats recall. | Show options, recent items, and suggestions instead of requiring typed or remembered values. |
| People remember meaning better than detail, and remember beginnings, endings, and distinct items better than middles. | Lead with the point. Make the one thing to remember distinct (von Restorff). Design the ending (peak-end). |
| Rare facts are forgotten. | Put them in the world at the moment of use. |

### Think

| Finding | Design move |
|---|---|
| People build mental models and meet the conceptual model the product presents. | Match the model they bring; when it breaks, explain the break (Norman). |
| Stories beat abstract facts; examples teach. | Teach with a worked example or sample data, not a definition. |
| People invent categories to make sense of things. | Organize by the categories users already use, not the org chart or database schema. |
| Uncertain people defend their ideas harder. | Expect confident wrong plans when the model is weak; fix the model, not the person. |
| Culture changes what seems logical. | Check reading order, color meaning, date and time direction before calling a mapping natural. |
| Flow needs challenge matched to skill and few interruptions. | Do not interrupt focused work with modals, mode changes, or required confirmations. |

### Attention

| Finding | Design move |
|---|---|
| Attention is selective; only salient cues get in, and something must be perceived before it can be attended to. | Give the one thing that matters a salient, perceivable cue. |
| Practiced skills run without conscious attention. | People will click through a dialog they have seen many times without reading it. Do not rely on routine confirmations for safety (Norman). |
| Sustained attention is on the order of ten minutes. | Break long tasks into steps with save points and visible progress. |
| People do not multitask; they switch, and miss things. | Do not require reading, deciding, and navigating at once. Co-locate what one decision needs. |
| Motion, faces, danger, and stories win attention automatically. | Do not animate what does not matter; motion steals attention from the task. |

Violation: users do not notice an account warning in the footer. Fix: the footer is outside attention, so move the warning to a salient position near the task it affects, with an icon and text, not color alone. This is selective attention, not carelessness.

### Motivation

| Finding | Design move |
|---|---|
| People push harder as they get closer to a goal. | Show progress toward completion. |
| Progress, mastery, autonomy, and control beat extrinsic rewards for lasting work. | For tools people use for real work, prefer visible progress and control over points or badges. |
| Variable rewards and information-seeking are powerful and habit-forming; unpredictability keeps people searching. | Use deliberately and only where repeat checking serves the person. They do not fix an unclear control. |
| People take the lazy path and use shortcuts only if the shortcut is easy. | Make the default path the right one. Shortcuts must be discoverable and cheaper than the long way. |
| Habits form from many small steps over time. | Support repeated small actions; do not expect one onboarding session to create a habit. |
| People blame the person, not the situation. | Applies to teams too: "user error" on an ordinary task is a design finding (Norman). |

Violation: a request to add a variable-reward pull-to-refresh so people open the app more. Fix: state the trade honestly. Variable rewards do increase repeat seeking. For an ongoing work product, progress and control are the durable motivators; use the reward loop only if the repeat visit serves the person.

### Social and trust

| Finding | Design move |
|---|---|
| Online interaction is judged by social rules. | Polite, specific errors. No scolding. |
| People imitate and follow others when uncertain. | Real usage and real customer evidence help an uncertain visitor decide. Never invent it (see [brand.md](brand.md), [product.md](product.md)). |
| Look and feel is the first trust signal. | A broken or careless visual read loses trust before content is read. |
| Anecdotes persuade more than data tables. | A specific real story or case beats a stat grid for persuasion. Keep data for people who are evaluating. |
| People prefer the familiar when anxious. | Use conventional patterns in stressful flows: payment, errors, security, account recovery. |
| Achieved difficulty can increase liking. | Not a reason to make a tool hard. |

### Mistakes and decisions

| Finding | Design move |
|---|---|
| There is no fail-safe product; error types are predictable; stress increases error. | Design for error (next section). Simplify and constrain the paths used under pressure. |
| Not every mistake is bad. | Cheap, reversible mistakes are how people explore. Make exploration safe instead of blocking it. |
| Most decisions are unconscious, and mood changes them. | Defaults and presentation decide more than explanations do. Choose defaults responsibly. |
| People want more choice and information than they can process, and treat choice as control. | Strong default, grouped options, and an obvious way to reach the rest. |
| Uncertain people let others decide. | Mark a recommended option when there is a sensible one. |
| A product in front of people is valued more. | Show the real product (screenshot, preview, sample) instead of describing it. |
| People may value time over money. | When it fits, frame a benefit in time saved. |

Violation: a settings page exposes 40 toggles because "users want control". Fix: people will scan, satisfice, and leave most at defaults. Pick good defaults, group by task, show the common few, and keep the rest reachable behind an obvious "Advanced" entry that shows which values differ from default.

## Laws of UX: when each applies

Each law is a lens for a specific constraint (time, reach, memory, choice, trust). State the move and the misuse you are avoiding, and what test would show the law did not apply.

| Law | What it says | Applies when | Move | Misuse |
|---|---|---|---|---|
| Jakob | People spend most of their time in other products and expect yours to work the same way. | Navigation, forms, checkout, standard controls, any first-use path. | Start from common patterns. Test any break; signify the new action. | Sameness for its own sake, or novelty with no signifier. |
| Fitts | Time to hit a target depends on its distance and size. | Primary actions, touch layouts, toolbars, dense tables. | Make primary targets larger and closer to where the hand or pointer already is. Keep destructive targets a step away. | Making every target large so nothing is primary. |
| Miller | Working memory holds about 7±2 chunks. | Forms, codes, comparisons, multi-step flows. | Chunk and group; prefer recognition over recall. | Capping navigation at seven items. Real navigation exceeds this; the limit is on what must be held in mind, not what is shown. |
| Hick | Decision time grows with the number and complexity of choices. | Menus, filters, settings, plan selection, onboarding choices. | Categorize, default, disclose progressively. | Removing options people need for control. |
| Postel | Be liberal in what you accept, conservative in what you send. | Input fields (dates, phones, names, pasted data), imports. | Accept messy input; store and display predictable formats. | Silent correction with no way to see what was saved. |
| Peak-end | People judge an experience by its most intense moment and its end, not the average. | Checkout, signup, onboarding completion, error recovery, cancellation. | Design the peak step and the completion state. | A dead end, vague error, or clumsy confirmation after a good middle. |
| Aesthetic-usability | Attractive design is perceived as more usable. | Trust and first impressions; also when reviewing tests and stakeholder claims. | Polish supports trust and tolerance. | Treating a polished mock as proof the task works. |
| Von Restorff | The item that differs is the one remembered. | One primary action, one critical warning, one key number. | Isolate the one thing that matters. | Highlighting everything, so nothing stands out. |
| Tesler | Every system has irreducible complexity; someone has to carry it. | Simplification requests, settings, automation, "make it one click". | Move the complexity into the product (defaults, inference, constraints) rather than onto the person. | Calling the product simple while users hold the rules in their heads. |
| Doherty | Interaction feels productive below about 400 ms, when neither side waits. | Submits, searches, saves, anything with latency. | Respond within that window or acknowledge immediately and show what was received and what is happening. | A spinner with no statement of state. |

Notes:

- Miller vs critique.md: the chunk counts in [critique.md](critique.md) are review heuristics for a single decision point. Neither they nor Miller's law cap total navigation length; group instead of counting links.
- Fitts and Norman agree: the primary action is easy to reach, and the dangerous action is distinct and slightly harder, not merely a different color.
- Doherty and Norman agree: direct manipulation answers in about a tenth of a second; slower work acknowledges at once.

Violation: a filter panel shows 25 ungrouped options. Fix (Hick, not Miller): group into labeled categories, surface the most used, and collapse the rest; keep every option reachable. Do not cut it to seven.

Violation: the Pay button is small and in a far corner; Cancel is large and centered. Fix (Fitts): make Pay the large, primary target at the end of the reading path where the eye and pointer arrive; make Cancel a secondary, smaller target separated from it.

Violation: stakeholders say a redesign is more usable because it looks premium. Fix: that is the aesthetic-usability effect. It shows perceived usability, not task success. Run the task test.

## Constraints, errors, and recovery

Assume every mishap will happen. Minimize its chance and its cost (Norman).

### Four kinds of constraint

Use all four; they are knowledge in the world.

| Kind | Uses | Interface example |
|---|---|---|
| Physical | Shape, size, reach, orientation | A drag handle only on the header. A field that accepts only digits. |
| Semantic | Meaning of the situation | Delete belongs to the item, not the page chrome. |
| Cultural | Learned conventions | Reading order, what a switch position means, color meaning in this audience. |
| Logical | Reasoning from what remains | Mutually exclusive options shown as a single choice. The one unassigned value maps to the one remaining slot. |

Conventions are cultural constraints: they make new things usable and make change painful. A better design that breaks a convention will be disliked until the new convention is signified and learned (destination-control elevators). Standardize where choices are arbitrary but must be remembered; a standard can be arbitrary and still right because it moves knowledge into the world.

### Forcing functions

| Type | What it does | Interface use |
|---|---|---|
| Interlock | Forces operations in order | Must select a target environment before Deploy enables; must review before Submit. |
| Lock-in | Prevents ending an operation early | Unsaved-work prompt that offers Save in the prompt itself, not only Leave. Never as a business trap. |
| Lockout | Blocks entry to a dangerous state | Typed confirmation of the resource name, a covered or separated destructive control. |

People disable forcing functions that block normal work. Use enough restraint to catch the rare disaster and not enough to get taped down. If operators will bypass it, the design failed.

Deliberate difficulty is right only for actions that should be hard: irreversible destruction, identity confirmation. Difficulty must block the unwanted action, not the wanted one. A hard-to-read label is not a safety feature; a lockout is.

### Slips and mistakes

| | Intention | What went wrong | Design lever |
|---|---|---|---|
| Slip | Correct | The action, or memory of it, went wrong | Signifiers, mapping, spacing, avoiding modes, undo |
| Mistake | Wrong | The goal or plan was wrong | Conceptual model, constraints, visible system state |

Slip patterns to design against:

| Slip | Cause | Fix |
|---|---|---|
| Capture | A frequent sequence takes over a rare one that starts the same way. | Make the rare path start differently. |
| Description-similarity | Right action on the wrong object that looks alike. | Make the dangerous one distinct in shape, position, and label (Archive vs Delete). |
| Mode error | Same action means different things; the current mode is not salient. | Avoid modes. If needed, make the mode as visible as the control it changes. |
| Memory lapse | Interrupted before the last step. | Persist incomplete work in the world: drafts, resume state, visible pending items. |

Rule-based mistakes come from a good rule applied in the wrong situation; knowledge-based mistakes come from reasoning with a weak model. Fix with a better system image, not a longer policy document. A skipped safety step is often a procedure that makes the job impossible; treat it as a design defect.

### Modes

- Prefer modeless actions.
- If a mode exists (edit vs view, live vs test, production vs staging), its indicator must be as salient as the controls whose meaning changed.
- Changing mode must not silently cancel the current activity.
- The same shortcut must not do opposite things in two modes without a signifier.

Violation: a deploy tool auto-selects production when the branch is main, and operators sometimes ship to the wrong environment without noticing. Fix: this is a mode error from a weak system image, not careless operators. Show the target environment as prominently as the Deploy button, name it in the button ("Deploy to production"), make production a deliberate interlock step, and make the auto-selection visible and explained. A color change alone is not enough.

### Error and recovery rules

- **Reversible actions:** do it, show feedback, offer undo. Do not ask "Are you sure?" first. Implementation in [interaction-design.md](interaction-design.md).
- **Irreversible or costly actions:** lockout or interlock, the consequence stated in the step, and the safe alternative available in the same step.
- **Make errors cheap:** drafts, soft delete, preview, sandboxes.
- **Unsaved work:** lock-in that offers Save, not only Leave.
- **Disabled controls** either explain why or are not shown. A dead control with no reason is a wall with no sign.
- **Validation** fires at the moment of the mistake, next to the field, and never wipes entered work.
- **Error messages** answer interpret and compare: what happened, what it means, what to do now. Assist; do not scold. If an error message teaches what the interface should have signified, fix the interface. Copy patterns in [clarify.md](clarify.md).
- **Collaborate:** do not give the machine the easy part and the person the vigilance. People are bad at long monitoring and at machine-precise repetition.
- **Reporting must be safe.** Hidden errors repeat.

Violation: an admin tool needs a "delete project" action that removes production data and cannot be undone. Fix: not a generic "Are you sure?" modal. Separate the action from routine controls, state exactly what will be destroyed (data, environments, counts), require typing the project name as a lockout, offer export or archive in the same step, and name it "Delete project permanently".

### Automation

Automation takes the easy cases and fails on the hard ones, exactly when it is needed, leaving the person out of the loop and slow to recover.

- Show the automated mode and the hand-back condition before failure.
- Keep enough state visible for the person to rebuild the model quickly, without nagging.
- Failure must be a salient signal, not a footnote or a consequence they discover later.
- Alarms that cry wolf shift risk onto the operator.

## Visual craft for usability

Use after the feature and its primary action are settled; visual work does not answer a problem or interaction question. Concrete scales and values live in [layout.md](layout.md), [typeset.md](typeset.md), and [colorize.md](colorize.md). This section covers the reasoning they do not (Refactoring UI unless credited).

### Order of work

- Start with a feature, not the shell. Design what you are building now, not every screen it might grow.
- Work in grayscale first so hierarchy is carried by spacing, size, weight, and contrast. Add color after the structure works; hunt typefaces and shadows last.
- Choose a personality and a limited set of options (type sizes, spacing steps, colors, shadows) up front, so each screen is not a new system.

### Hierarchy by de-emphasis

- Not all elements are equal. Decide the one primary element per view, then a few secondary, and mute the rest.
- Emphasize by de-emphasizing the neighbors. When the primary element does not stand out, make competitors quieter (lighter weight, softer color) before making it bigger.
- Size is one lever; weight and contrast often do more. Keep them in balance; too much of any collapses the scale.
- Labels are a last resort. When the value is self-explanatory (an email, a price with currency, a date), drop the label or fold it into the value ("12 left in stock" instead of "Stock: 12").
- Visual hierarchy is not document hierarchy. A section heading can be visually small if the content under it is what people came for; semantic heading level stays correct for assistive technology.
- Actions follow the same rule: one primary button style per view, secondary actions quieter, destructive actions not in the primary style unless they are the point of the view (Norman: one style, one meaning).

Violation: a card has a border, a gray label above every value, and the price is the same size as the helper text. Fix: drop labels where the value speaks for itself, make the price dominant through weight and contrast, mute helper text, and separate with spacing rather than adding more boxes.

### Space

- Start with too much space, then remove it. Cramped layouts are the default failure; dense layouts are fine when many values must be seen at once, as a deliberate choice.
- Use a constrained scale where adjacent steps differ enough to make the choice obvious (Refactoring UI suggests roughly 25% between steps from a 16px base). A one-pixel or linear crawl makes 120 vs 125 a non-decision. Use the project's scale; see [layout.md](layout.md).
- Avoid ambiguous spacing. Space between groups must be clearly larger than space within them, or people cannot tell what belongs together. A form label equidistant from the field above and below is ambiguous.
- You do not have to fill the screen. Give content the width it needs.
- Grids are a tool, not a goal; fixed widths are often right for sidebars and forms.

Violation: paddings of 13, 15, 18, and 21 px across components. Fix: replace with values from one scale with clearly distinct steps, applied consistently.

### Type and links

- Use a small type scale, not a new size per element.
- Constrain line length; line-height decreases as size increases; align text for reading (avoid centered paragraphs); baseline-align mixed sizes on one line. Values in [typeset.md](typeset.md).
- Not every link needs its own color. In link-dense interfaces, use weight or a darker tone and reveal underline on hover, while keeping links in body text clearly identifiable.

### Color

- Define shade scales before painting screens: grays, a primary, and semantic colors (success, warning, danger), each with several steps. A palette of one primary and one gray is not enough.
- Keep saturation as lightness moves to the extremes, so the lightest and darkest steps do not go dull. Gray can be tinted toward the brand hue. [colorize.md](colorize.md) prefers OKLCH over the HSL Refactoring UI uses; the principle carries over.
- Accessible contrast does not require an ugly palette: when white text on a color fails, try dark text on a light tint of the same hue.
- Never put gray text on a colored background; use a shade of the background hue.
- Never rely on color alone for meaning (Refactoring UI; Weinschenk; Norman).

### Depth

- Pick one light source (usually above) and stay consistent: raised elements are lighter on top and cast shadows below; inset elements the reverse.
- Shadows communicate elevation: small for buttons, larger for dropdowns and dialogs. A shadow can combine a tight, dark contact shadow and a larger, soft cast shadow.
- Overlapping elements creates layers without another box. Flat interfaces still need a depth cue (a lighter or darker surface) to show what is raised or pressed.

### Images

- Use good photos or none. Text over images needs a consistent contrast treatment (overlay, lowered image contrast, or a text shadow).
- Every image slot has an intended size, and user uploads will violate it. Constrain crop, aspect ratio, and fallback; do not let a user avatar or logo break the layout.
- Icons drawn for small sizes look clumsy when scaled up; place them in a shape or use a larger-size icon instead.

### Finish

- Improve default controls (buttons, inputs, selects, checkboxes) before adding decoration.
- Use fewer borders. Separate with spacing, a background shift, or a box shadow; use an accent border to mark state or emphasis instead of boxing every region.
- Empty states are part of the feature, often the first screen a new user sees. Design them with the action that fills them ([onboard.md](onboard.md)).

## Applying by surface

### Public sites: home, landing, product, marketing

- **First screen:** what is this, what can I do, why care, where to start, answered without a paragraph (Krug).
- **Identity and navigation:** passes the trunk test on every page, including deep pages reached from search.
- **One primary call to action** per view, visually isolated (von Restorff) and easy to reach (Fitts). Secondary actions quieter.
- **Conventions:** logo returns home, navigation where comparable sites have it, links that look like links (Jakob; Krug).
- **Copy:** no happy talk, no instructions; cut words, use real headings for scanning.
- **Trust:** look and feel is read first (Weinschenk; aesthetic-usability), but it does not prove the product works. Show the real product. Real anecdotes beat stat grids; never fabricate proof.
- **Forms and signup:** ask only what is needed to start; accept messy input (Postel); keep entered data on error (Krug goodwill; Norman).
- **Choice:** pricing and plan pages group options and mark a recommended one when there is a sensible default (Hick; Weinschenk).
- **End of the funnel:** the confirmation and next step after signup or purchase shape the memory (peak-end).
- **Mobile:** prioritize the task, no hover-only affordances, no shrunk desktop.

### App and tool UI: dashboards, settings, forms, internal tools

- **Each screen answers the seven stage questions** for its primary task, from the screen alone.
- **State before decisions:** selected, saved, offline, automated, environment, permission.
- **Feedback** within the Norman and Doherty limits, in goal language, attributable to the control.
- **Mapping:** actions on the object they affect; dangerous neighbors separated.
- **Modes** avoided or made as salient as the control.
- **Defaults and progressive disclosure** for large option sets, without hiding current state (Hick; Weinschenk).
- **Knowledge in the world** for rare and first-run paths; keyboard shortcuts and bulk actions for experts, without removing signifiers.
- **Errors:** undo for reversible actions, lockout or interlock for costly ones, drafts for interrupted work, validation inline without data loss.
- **Long tasks:** steps, progress, save points, review before commit (attention span; memory lapse).
- **Automation:** visible mode, explicit hand-back, failure as a salient signal.
- **Density** deliberate when people compare many values; hierarchy still by de-emphasis.

## Review checklist

Answer from the artifact alone. "They will remember" or "the docs explain it" counts as a failure.

Decision

- [ ] Activity named, and it is the root problem rather than a stated symptom.
- [ ] Decision type identified; the fix matches the type.
- [ ] Cost of being wrong named; constraint strength matches it.
- [ ] Next test named.

Discoverability and feedback

- [ ] All seven stage questions answerable for the primary task.
- [ ] Every interactive element looks interactive; nothing non-interactive looks clickable.
- [ ] No simple control depends on a tooltip, tour, or helper text to be operable.
- [ ] Controls sit on or beside what they affect; dangerous neighbors are distinct.
- [ ] Every action gets immediate, attributable feedback in goal language; slow work acknowledges at once.
- [ ] Empty, loading, partial, error, and success states are designed.
- [ ] Current state and mode are visible before decisions.

At a glance

- [ ] Trunk test passes on a random page.
- [ ] First screen answers what, what can I do, why, where to start.
- [ ] The primary element and action are obvious; the rest is de-emphasized.
- [ ] Labels and categories are obvious, not clever.
- [ ] Words cut; no happy talk or unread instructions.
- [ ] No goodwill drains: hidden goal, needless data, rigid input format, scolding.

People

- [ ] Nothing important relies on color alone.
- [ ] Nothing relies on recall that recognition could provide.
- [ ] Critical signals are salient and placed where attention is.
- [ ] Large choice sets have defaults and grouping, with full control reachable.
- [ ] Look and feel signals what this is and supports trust.

Errors

- [ ] Reversible actions have undo, not confirmation.
- [ ] Irreversible actions have a lockout or interlock with the consequence and a safe alternative in the same step.
- [ ] Interrupted work persists.
- [ ] Validation is inline, timely, and never wipes input.
- [ ] Disabled controls explain why.
- [ ] No protection so annoying people will bypass it.

Visual craft

- [ ] Hierarchy reads in grayscale.
- [ ] Spacing from one scale; group spacing clearly larger than within-group spacing.
- [ ] No gray text on color; contrast meets the standard in [SKILL.md](../SKILL.md).
- [ ] Shadows consistent with one light source and meaningful elevation.
- [ ] User content (long names, odd images) constrained.

Severity for findings, which maps onto the P0 to P2 scale in [critique.md](critique.md):

| Severity | Meaning |
|---|---|
| Blocks task | Cannot discover or complete the action. |
| Causes error | Possible, but easy to do wrong, with a real cost. |
| Friction | Possible and recoverable, but the model or feedback is weak. |

Findings table for a full review: step or control, failed stage, principle or law, severity, why a reasonable person fails, change.

## Common failure patterns

| Symptom | Likely cause | Fix |
|---|---|---|
| People need a sign or tooltip on a simple control | Failed signifier | Change the control's form, placement, or mapping |
| People repeat an action | Missing or late feedback | Acknowledge immediately; show what was received |
| Right intention, wrong control | Mapping, mode error, or description-similarity slip | Move controls to their objects; make modes salient; differentiate look-alikes |
| Wrong plan, confident user | Weak conceptual model | Fix the system image; show state and consequences |
| Experts fast, novices lost | Knowledge only in the head | Put it in the world for rare paths; keep expert shortcuts |
| Feature works, people hate the change | Convention broken without felt gain | Restore the convention or signify the new one heavily |
| Nobody notices a warning | Outside attention or not salient | Move it to where attention is, with text and icon |
| People leave a form early | Goodwill spent on needless fields or strict formats | Cut fields; accept messy input |
| Users stall on a big menu or settings page | Choice overload | Default, group, disclose progressively |
| Team wants every edge case in v1 | Norman's law | Scope to the activity; keep signifiers |
| Polished redesign "tests" well with stakeholders | Aesthetic-usability | Run a task test |
| Everything highlighted, nothing stands out | Von Restorff misuse | One primary element; mute the rest |

Fixes that are usually wrong:

- Another confirmation dialog where undo or a constraint would work.
- A tour, tooltip, or longer instructions as the first fix for a non-obvious control.
- Disabling a control without saying why.
- One badge, color, or sound encoding several states.
- A mode that changes what a control does without a signifier as salient as the control.
- Automation that fails silently and hands back with no time to re-enter the loop.
- A forcing function so annoying people bypass it.
- An error message that teaches what the interface should have signified.
- Capping navigation at seven items.
- Removing options people need to make a screen look simpler.
- Restyling a screen whose real problem is a failed mapping or missing feedback.
- Starting from the app shell, navigation, or a moodboard before the feature exists.
- Settling a usability argument by taste when three participants could settle it.
