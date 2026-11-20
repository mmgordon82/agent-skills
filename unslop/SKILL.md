---
name: unslop
description: Use when writing or reviewing prose (docs, PRs, commits, issues, UI copy) to cut AI tells.
---

# Unslop

Edit text to remove AI patterns. Scan for the patterns below, then rewrite. Preserve meaning and match the intended tone.

Rule numbers are stable ids that other skills cite. A removed rule leaves a gap.

3. No trailing "-ing" phrases that add no fact ("highlighting...", "ensuring...").
5. No vague attributions ("experts believe"). Name the source or delete.
7. No AI vocabulary: additionally, crucial, delve, enhance, foster, landscape, pivotal, showcase, testament, underscore, vibrant.
8. Say "is" or "has", not "serves as", "stands as", "boasts", "features".
9. No "not just X, but Y". State the point.
10. Don't force ideas into threes.
11. One name per thing. Repeat it.
12. No "from X to Y" unless X and Y sit on a real scale.
13. No em dashes, en dashes, or hyphens used as dashes, and no parentheses in their place. Use a period or a comma.
14. A colon goes before a list or an example, never mid-sentence as a connector.
15. Don't bold every proper noun or acronym.
16. No bold label and colon that restates its line ("**Performance:** Performance improved..."). A bold lead-in that ends in a period and adds new detail is fine.
17. Sentence case headings.
18. No decorative emojis.
19. Straight quotes.
20. No chatbot phrases ("I hope this helps!", "Let me know if...").
22. No praise or agreement openers. Respond directly.
23. Cut filler. "In order to" becomes "to". Delete "it is important to note that".
24. One hedge at most: "may".
25. No generic conclusions. State specific plans or facts.
26. No abstract metaphor nouns: substrate, wedge, vector, nexus, primitive, harness, surface, scaffolding, paradigm, ratchet, north star, flywheel. Use the concrete word.
27. Say what it does, not how it feels. Name the mechanism or the number. Cut a sentence that could appear unchanged in another project's docs.
28. One idea per sentence. Split a sentence the reader has to reread.
29. Active voice. Name the actor unless it is unknown or doesn't matter.
30. Cut adverbs or use a stronger verb. Give the number.
31. Use the plain word: "use", not "utilize" or "leverage".
32. No metaphor, aphorism, personified code, or figurative verb where a literal phrase exists.
33. Write whole sentences with their articles and verbs. Spell out arrows and abbreviations.
34. No throat-clearing openers ("Here's the thing", "It turns out", "The truth is"). State the point.
35. No emphasis crutches or meta-commentary ("Let that sink in.", "Full stop.", "It's worth noting", "At its core"). Delete them.
36. No false agency: an inanimate subject with a human verb ("the decision emerged", "the bet lives or dies"). Name who or what acted.
37. No negative listing or dramatic fragments ("It's not X. It's not Y. It's Z.", "Simple. Fast. Reliable."). State what it is.
38. No hedged symmetry ("Whether you're a beginner or an expert"). Name the actual reader or cut it.
39. No all-caps emphasis or scare quotes. Quotes are for real quotations, UI strings, and titles.
40. Don't fill a gap with speculation ("likely founded in...", "presumably to..."). Mark the gap for the author.
41. Name the relation between neighboring sentences: "because", "although", "when", "so".

## How to apply

- A pattern hit is a hypothesis, not a verdict. Keep a flagged word when it is the precise term. Don't flag curly quotes alone, one em dash alone, or one short sentence alone in human-written text.
- If the user gives a writing sample, match its voice. Flag where it breaks these rules and ask before overriding it.
- The rewrite must pass these same checks and keep every fact, caveat, and warning. Missing facts go back to the author. Never invent them.
- Lint a file: `python3 scripts/ste_lint.py path/to/draft.md` (from this skill's directory). The score is heuristic violations per 100 words. Compare versions by score delta and inspect each hit, since code samples cause false positives.
