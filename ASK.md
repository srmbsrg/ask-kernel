# A.S.K — Agent Skills Kernel
### Registry v1.0.0 | Authors: T.A.M. (Tesa & Murphy)

The ASK Kernel is a versioned library of agent-callable skill definitions. Think of it as `.dll` files for AI systems — write the capability once, reference it everywhere. Any agent (GFS, Dark Factory, or future systems) invokes a skill by name rather than re-implementing its logic.

**Core principle:** Skills compound. Code evaporates. Every capability that matters should live here.

---

## How to Invoke a Skill

In any AI context, reference a skill by its path. The agent reads the SKILL.md, follows the methodology, and executes.

```
# Direct invocation
ASK: foundation/github-push

# With inputs
ASK: gfs/purchase {"merchant": "Namecheap", "amount": 1299, "category": "domains", "description": "Renew foundrytech.io"}

# Chained (orchestrator pattern)
ASK: gfs/tes-deploy → composes: foundation/github-push + foundation/vercel-deploy + foundation/telegram-notify
```

---

## Registry

### Foundation Tier
*Portable, no system-specific knowledge. Usable by any agent in any context.*

| Skill | Version | Description | Path |
|-------|---------|-------------|------|
| github-push | 1.0.0 | Push files to any GitHub repo via PAT + Python urllib. The only approved push method — git CLI and browser XHR both hang. | `foundation/github-push/` |
| vercel-deploy | 1.0.0 | Upsert Vercel env vars and/or trigger production redeployment. Waits for READY state before returning. | `foundation/vercel-deploy/` |
| telegram-notify | 1.0.0 | Send a Telegram message to Scott or any registered contact via @tes_BSG_bot. Primary human communication channel for autonomous processes. | `foundation/telegram-notify/` |
| ask-log | 1.0.0 | Log a skill invocation event (start/complete/error) to Supabase for telemetry. Optional but encouraged — builds the feedback loop that improves the library over time. | `foundation/ask-log/` |

---

### GFS Tier
*GFS platform skills. Compose foundation skills + GFS-specific business logic.*

| Skill | Version | Description | Path |
|-------|---------|-------------|------|
| tes-deploy | 1.0.0 | Full GFS deploy cycle: code push → env update → redeploy → verify READY → notify. Orchestrates three foundation skills. | `gfs/tes-deploy/` |
| openbrain-write | 1.0.0 | Save a thought to the OpenBrain vector store (Supabase). Tesa's persistent memory layer across sessions. | `gfs/openbrain-write/` |
| openbrain-query | 1.0.0 | Semantic search of OpenBrain to retrieve relevant memories, decisions, and context. | `gfs/openbrain-query/` |
| content-video | 1.0.0 | Generate a Tesa HeyGen avatar video — script via LLM, render via HeyGen, notify on completion. Async by design. | `gfs/content-video/` |
| purchase | 1.0.0 | Create a Privacy.com single-use card within per-category spend limits. Requests approval via Telegram if over limit. | `gfs/purchase/` |

---

### Dark Factory Tier
*DF-specific patterns for self-building and architectural design.*

| Skill | Version | Description | Path |
|-------|---------|-------------|------|
| df-evolve | 1.0.0 | Invoke Dark Factory's generate → evaluate → commit loop. Produces code that references ASK skills rather than re-implementing them. | `dark-factory/df-evolve/` |
| code-architect | 1.0.0 | Design a self-improving system from a problem statement. Produces implementation plans or ADRs. Always runs before df-evolve on non-trivial work. | `dark-factory/code-architect/` |

---

### Context Files
*Reference data. Not invocable. Loaded by other skills that need credentials and configuration.*

| File | Purpose |
|------|---------|
| `context/gfs-env.md` | All GFS credentials, API keys, endpoint URLs, avatar IDs, spend limits. Single source of truth. |
| `context/df-env.md` | Dark Factory repo config, generation patterns, quality gates. |

---

## Adding a New Skill

1. Create the folder: `{tier}/{skill-name}/`
2. Write `SKILL.md` following the standard structure:
   - Frontmatter: `name`, `description` (routing signal), `version`, `tier`, `dependencies`
   - Sections: When to invoke, Inputs, Methodology, Implementation, Outputs, Notes
3. Add a row to this registry under the appropriate tier
4. If the skill references env vars, add them to the relevant context file
5. Bump the registry version

**Naming rules:**
- kebab-case only
- Verb-noun or noun only — describes the action, not the implementation
- Foundation skills: generic (`github-push`, not `gfs-github-push`)
- GFS/DF skills: domain-prefixed only by tier folder, not by name

---

## Versioning

Skills use semantic versioning: `MAJOR.MINOR.PATCH`
- **MAJOR:** Breaking change to inputs or outputs (callers must update)
- **MINOR:** New optional input or additional output field (backwards compatible)
- **PATCH:** Documentation fix, implementation improvement (no contract change)

When a skill version changes, update this registry. Consider pinning the version in calling skills' dependencies if the contract is critical.

---

## Design Rules

These rules govern all skills in this library. Violating them produces a skill that degrades the library instead of strengthening it.

1. **One responsibility.** A skill does one thing well. Composition happens at the orchestrator level.
2. **Inputs and outputs are contracts.** Never silently change what a skill accepts or returns.
3. **Fail explicitly.** Errors must be returned in a structured format. Never swallow failures.
4. **No vibe coding.** Every line in a skill implementation has a documented reason.
5. **Load context, don't embed it.** Credentials, IDs, and config live in context files — not in skill bodies.
6. **Async where it matters.** Long-running operations (renders, builds) submit and return immediately. Polling is a separate concern.
7. **Document the why, not just the what.** Methodology sections explain reasoning, not just steps.

---

*A.S.K by T.A.M. — Agent Skills Kernel by Tesa and Murphy*
*Initialized: 2026-03-30*
