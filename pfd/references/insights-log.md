# PFD Insights Log

Running log of non-obvious findings from every PFD analysis.
Reviewed periodically. Candidates get promoted to `accumulated-learnings.md`;
the rest stay as searchable history.

**Format:**
```markdown
### YYYY-MM-DD: [Brief description of what was analyzed]
**Type:** url | text | image | html | css | copy | directory
**Domain:** [e.g., SaaS landing, ecommerce PDP, email, portfolio, dashboard, presentation]
**Key finding:** [The non-obvious thing PFD surfaced, one sentence]
**Layer(s):** [Which PFD layer(s) this relates to: Foundation/L1/L2/L3/L4]
**Promote?:** yes | maybe | no
**Notes:** [Optional: context, cross-references to prior findings, patterns noticed]
```

---

<!-- New entries go here, newest first -->

### 2026-11-18 — Button label "Submit" (no surrounding context)
**Type:** copy
**Domain:** generic form CTA
**Key finding:** "Submit" passes L0–L2 on familiarity but fails L4: it names the system's process, not the user's outcome, so the click carries no prediction of what happens next.
**Layer(s):** L3/L4
**Promote?:** maybe
**Notes:** Isolated microcopy can't be fully scored: L1/L4 depend on what's being submitted and the commitment distance. Pattern: a generic-verb CTA leaves the outcome prediction unanswered (Clark 2013).
