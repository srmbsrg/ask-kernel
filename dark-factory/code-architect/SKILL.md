---
name: code-architect
description: Design a self-improving system from a problem statement — identify the right ASK skills to compose, design the data flow, define the generation target for Dark Factory, and produce an architectural decision record. Use before building anything non-trivial.
version: 1.0.0
tier: dark-factory
dependencies:
  - context/gfs-env.md
  - context/df-env.md
---

# Code Architect

## When to invoke

Before writing code. This is the planning skill — it produces the blueprint that `df-evolve` or direct implementation follows. Use it when:
- A new feature requires more than one file
- The right approach is unclear
- The feature touches multiple systems (DB + API + UI + Telegram, etc.)
- You want to identify which existing ASK skills can be composed vs. what needs to be built new

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `problem` | string | yes | What needs to be built or solved. Be specific about the desired outcome. |
| `constraints` | list | no | Known constraints: time, budget, existing dependencies, must-not-break paths. |
| `output_format` | string | no | `"adr"` (Architecture Decision Record) or `"plan"` (implementation plan). Default: `"plan"`. |

## Methodology

**Principle: design before typing.**

An architect's job is to make the easy path the right path. When this skill completes, the implementer (human or DF) should have no ambiguous decisions left to make.

**Step 1 — Understand the problem**
Restate the problem in one sentence. If you can't do this, the problem isn't defined well enough — surface that ambiguity before proceeding.

**Step 2 — Inventory existing capabilities**
Read `ASK.md` to identify which skills already cover parts of this problem. A good architecture uses the library rather than extending it unnecessarily. Ask: "What can be composed from what already exists?"

**Step 3 — Identify the gap**
What's left that ASK doesn't cover? This is the net-new code. Minimize it. The gap should be business logic, not infrastructure.

**Step 4 — Design the data flow**
Map: input → transformation → output. For each transformation, name which ASK skill handles it or what new code is needed. This becomes the sequence diagram for `df-evolve` or the implementation guide for direct coding.

**Step 5 — Define acceptance criteria**
Every new piece of code needs a measurable pass/fail test. "It works" is not acceptance criteria. "Returns 200 with a video_id within 5 seconds" is.

**Step 6 — Identify risks**
What's the most likely failure mode? What's the blast radius if it breaks? How do we detect and recover? This informs which failure paths need explicit handling.

**Step 7 — Produce the output**
Either an ADR (for significant architectural decisions) or an implementation plan (for feature work). Both formats are structured for an agent to consume — not just for human reading.

## Output Formats

**Implementation Plan:**
```markdown
## Problem
[One sentence restatement]

## ASK Skills Composed
- foundation/github-push — handles code persistence
- gfs/tes-deploy — handles deployment
- [new] gfs/webhooks — net-new, handles Stripe webhook events

## Data Flow
1. Stripe sends webhook → POST /api/gfs/webhooks
2. Verify signature → process event type
3. Update DB record → Prisma
4. Notify Scott → telegram-notify

## Files to Create/Modify
- CREATE: app/api/gfs/webhooks/route.ts
- MODIFY: prisma/schema.prisma (add WebhookEvent model)

## Acceptance Criteria
- [ ] Stripe test webhook returns 200
- [ ] DB record created for each event type
- [ ] Invalid signatures return 400 (not 500)

## Risk
- Webhook replay attacks if signature check is skipped
- DB write failure must not return 500 to Stripe (use 200 + internal alert)
```

**ADR (Architecture Decision Record):**
```markdown
## Decision
[What architectural choice was made]

## Context
[Why this decision was needed]

## Options Considered
1. Option A — [description, pros, cons]
2. Option B — [description, pros, cons]

## Decision
[Which option was chosen and why]

## Consequences
[What this enables, what it forecloses, what technical debt it creates]
```

## Outputs

Returns a structured plan or ADR as a string, ready to be passed to `df-evolve` as the `target` input, or used as a direct implementation guide.

## Notes

- This skill does not write code. It produces blueprints.
- The output of `code-architect` is the input to `df-evolve`. They are designed to chain.
- For architectural decisions that will persist (e.g., "we chose Supabase over PlanetScale"), save the ADR to OpenBrain via `gfs/openbrain-write` so future sessions have the reasoning.
