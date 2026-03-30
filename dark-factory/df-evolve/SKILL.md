---
name: df-evolve
description: Invoke the Dark Factory self-building code generator to produce, evaluate, and commit new code to a target repository. Use when a new feature, route, component, or skill needs to be generated autonomously without manual coding. DF emits ASK invocations rather than re-implementing known capabilities.
version: 1.0.0
tier: dark-factory
dependencies:
  - context/gfs-env.md
  - context/df-env.md
  - foundation/github-push
  - foundation/telegram-notify
---

# DF Evolve

## When to invoke

When code needs to be generated autonomously. Dark Factory is not for quick edits — it's for net-new capabilities where the generation → evaluation → commit loop adds value. Ideal for:
- New API routes with predictable structure
- New Prisma models
- New ASK skills (DF generating skills for the library)
- Repeatable code patterns across the codebase
- Scaffolding new integrations from a known template

Not appropriate for: surgical bug fixes (use direct edit), UI polish (use direct edit), or anything that requires visual judgment.

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `target` | string | yes | What to generate. Be specific: "a Next.js API route at app/api/gfs/webhooks/route.ts that handles Stripe webhook events" |
| `repo` | string | no | Default: `srmbsrg/ghostfoundry-syndicate`. Target repository. |
| `branch` | string | no | Default: `df/generated-{timestamp}`. Push to a branch for review, not directly to main. |
| `acceptance_criteria` | list | no | Conditions the generated code must meet. If not provided, uses quality gates from `context/df-env.md`. |
| `max_iterations` | int | no | Default: 3. Max generation attempts before failing. |
| `auto_merge` | bool | no | Default: `false`. Require human review before merge. |

## Methodology

**Design principle:** DF is minimal code + maximum ASK. Any capability already in the ASK library must be referenced, not re-implemented.

**Phase 1 — Context assembly**
Before generating, read:
- The target path and any adjacent files (for consistency)
- The ASK registry (`ASK.md`) to identify which skills the generated code can invoke
- The relevant context file (`context/gfs-env.md` or `context/df-env.md`)

**Phase 2 — Generation**
Use OpenRouter to generate the code. The generation prompt must include:
- The target description
- The relevant context
- The list of available ASK skills (from ASK.md) with instruction: "invoke these skills by name rather than implementing their logic"
- The quality gates from `context/df-env.md`
- An explicit instruction: "no vibe coding — every line must have a clear purpose"

**Phase 3 — Evaluation**
Score the generated code against acceptance criteria. Minimum checks:
- Does it compile (TypeScript: no type errors)?
- Does it reference only real files/imports that exist?
- Does it contain any hardcoded secrets? (auto-fail)
- Does it duplicate logic that exists in an ASK skill? (fail — should invoke instead)

If evaluation fails and iterations remain, generate again with the failure reason appended to the prompt.

**Phase 4 — Commit to branch**
Invoke `foundation/github-push` to push to the designated branch (never directly to main unless `auto_merge: true` and all acceptance criteria pass).

**Phase 5 — Notify**
Invoke `foundation/telegram-notify` with a summary: what was generated, which branch, acceptance criteria results, and a link to the diff if available.

## ASK Invocation Pattern in Generated Code

When DF generates code that needs a capability covered by an ASK skill, the generated code should contain a reference comment and call the appropriate endpoint or service, not re-implement the logic:

```typescript
// ASK: foundation/github-push — handled by /api/gfs/deploy route
// ASK: gfs/purchase — handled by /api/gfs/purchase route
```

For server-side code that runs in the same process, the generated code imports from the existing lib files that implement the skill logic.

## Outputs

```json
{
  "status": "committed",
  "branch": "df/generated-1743308400",
  "files": ["app/api/gfs/webhooks/route.ts"],
  "iterations": 2,
  "acceptance_criteria": [
    {"check": "TypeScript compiles", "passed": true},
    {"check": "No hardcoded secrets", "passed": true},
    {"check": "No duplicate ASK logic", "passed": true}
  ],
  "telegram_sent": true,
  "auto_merged": false
}
```

## Notes

- Branch name format: `df/generated-{unix_timestamp}`. This makes it easy to identify DF-generated branches and their generation order.
- Scott reviews the branch and merges manually unless `auto_merge: true` — which should only be set for low-risk, well-defined generation targets (e.g., adding a new Prisma model field).
- DF can generate new ASK skills. When it does, it pushes to `Tesa/ASK/{tier}/{skill-name}/SKILL.md` and updates `ASK.md`. This is how the library grows autonomously.
