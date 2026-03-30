# A.S.K: Agent Skills Kernel

The A.S.K Framework is a versioned library of reusable skill definitions for AI agent systems. Instead of agents re-implementing capabilities every time they're needed, they invoke a skill by name. Think of it as `.dll` files for AI.

This document is for anyone new to A.S.K. If you're already familiar with the framework, start with the registry in `ASK.md`, or jump to `CONTRIBUTING.md` to write a new skill.

---

## What Is A.S.K?

A.S.K is a simple but powerful idea: separate the *definition* of a capability from its *invocation*. When your agent (Tesa, Dark Factory, or a future system) needs to do something—push code to GitHub, send a Telegram message, or save a memory to a vector database—it doesn't implement that logic inline. Instead, it references a skill by name.

Each skill is a Markdown file with a standard structure: what it does, when to use it, what inputs it expects, the reasoning behind its implementation, and what it returns. The skill is the contract. The implementation is just one possible realization of that contract—it could be Python, JavaScript, or a direct API call.

The most important insight: **Skills compound over time, but prompts evaporate.** Every time an agent solves a problem without recording the solution as a skill, that solution is lost. The next agent re-learns it from scratch. A.S.K breaks that cycle.

---

## Why This Matters

Without a skill library, every agent becomes a one-off. Tesa solves a problem in January, and if she doesn't document it as a reusable skill, she solves it again in March. The GFS platform needs to deploy code thousands of times—wouldn't it be absurd to re-prompt the deploy logic each time? A skill defines it once, correctly, and both Tesa and Dark Factory invoke the same proven procedure.

More subtly, a skill library becomes the *interface* between autonomous agents and the systems they control. Instead of letting an agent generate arbitrary API calls, you provide curated skills that represent authorized, tested patterns. This is how you build safeguards into autonomous systems—not by hoping the prompt is good enough, but by engineering the capabilities it can access.

---

## The Three Tiers

A.S.K skills are organized into three tiers, each with a clear boundary and purpose.

### Foundation Tier

Foundation skills are portable, system-agnostic capabilities that any agent in any context can use. They have no knowledge of GFS, Dark Factory, or other specific platforms. They're primitives.

Examples:
- `github-push`: Push files to a GitHub repository using a PAT and Python urllib
- `vercel-deploy`: Update environment variables and trigger a Vercel deployment
- `telegram-notify`: Send a message via Telegram to a registered contact

Foundation skills live in `/foundation/` and are versioned independently. If you need to push code to GitHub, you don't build that into your agent—you invoke the foundation skill.

### GFS Tier

GFS skills are specific to the Ghostfoundry Syndicate platform. They compose foundation skills and add GFS-specific business logic—knowledge about the codebase structure, the deployment pipeline, the database schema, and Scott's preferences.

Examples:
- `tes-deploy`: Full deployment cycle (code push → env update → redeploy → notify)
- `openbrain-write`: Save a thought to the persistent memory database
- `purchase`: Create a Privacy.com card within approved spend limits

GFS skills live in `/gfs/`. They assume the existence of `/context/gfs-env.md`, which contains all credentials and configuration for the platform.

### Dark Factory Tier

Dark Factory skills are patterns for self-building and architectural design. They invoke other skills but add meta-level reasoning—how to generate code autonomously, how to evaluate it, and how to improve it iteratively.

Examples:
- `df-evolve`: Generate new code, evaluate it against acceptance criteria, and commit if it passes
- `code-architect`: Design a system or produce an architecture decision record

Dark Factory skills live in `/dark-factory/` and assume the existence of `/context/df-env.md`.

---

## How to Invoke a Skill

Invoking a skill is simple. You reference it by its path and, optionally, provide inputs as JSON.

### Direct invocation (no inputs)

```
ASK: foundation/github-push
```

The agent reads the `foundation/github-push/SKILL.md` file, understands what it does, and follows the methodology section.

### With inputs

```
ASK: gfs/purchase {"merchant": "Namecheap", "amount": 1299, "category": "domains", "description": "Renew foundrytech.io"}
```

### Chained (composition)

Some skills orchestrate other skills. The `tes-deploy` skill composes `github-push`, `vercel-deploy`, and `telegram-notify` in sequence:

```
ASK: gfs/tes-deploy
  ├─► foundation/github-push [code push]
  ├─► foundation/vercel-deploy [env update]
  └─► foundation/telegram-notify [notification]
```

The orchestrator skill handles error propagation, retries, and notifications. You don't need to chain these manually—you invoke the orchestrator.

---

## Anatomy of a Skill

Every skill is a Markdown file with this structure:

```yaml
---
name: skill-name
description: One or two sentences explaining what this skill does and when to use it.
version: 1.0.0
tier: foundation | gfs | dark-factory
dependencies:
  - context/gfs-env.md
  - foundation/some-other-skill
---
```

The frontmatter is a routing signal. The agent reads the description to decide whether this skill is what it needs. The dependencies list tells you what context and other skills this one requires.

Below the frontmatter:

- **When to invoke:** When should you call this skill? What problems does it solve? Be specific.
- **Inputs:** A table of required and optional fields, with clear descriptions.
- **Methodology:** The reasoning behind how the skill works. Not just steps, but *why* each step matters.
- **Implementation:** The actual code (Python or pseudocode) that carries out the methodology.
- **Outputs:** What the skill returns, in JSON or structured format.
- **Notes:** Edge cases, version history, gotchas, or links to related skills.

---

## Adding a New Skill

If you're ready to contribute a skill, read `CONTRIBUTING.md`. But here's the skeleton:

1. **Create the folder:** `{tier}/{skill-name}/`
2. **Write SKILL.md** using the template above
3. **Add a row to ASK.md** under the appropriate tier
4. **Version it:** Start with `1.0.0`
5. **Bump the registry version** in ASK.md's header

Names are kebab-case, verb-noun preferred. Foundation skills are generic (`github-push`), while GFS and Dark Factory skills are scoped by their tier folder only.

For a worked example and detailed guidance, see `CONTRIBUTING.md`.

---

## Versioning

Skills use semantic versioning: `MAJOR.MINOR.PATCH`.

- **MAJOR:** Breaking change to inputs or outputs. Callers must update.
- **MINOR:** New optional inputs or additional output fields. Backwards compatible.
- **PATCH:** Documentation or implementation improvement. No contract change.

When you update a skill, update the version in `SKILL.md` and re-register it in `ASK.md`.

---

## The Design Rules

Every skill in A.S.K adheres to these rules. They're not suggestions—violating them degrades the library.

**One responsibility:** A skill does one thing well. Composition (chaining skills together) happens at the orchestrator level, not inside the skill. If you're tempted to add "and also do X," that's a sign you need a new skill.

**Inputs and outputs are contracts:** Never silently change what a skill accepts or returns. If you need to add a field, bump the MINOR version and note that the field is optional. If you need to remove one, that's MAJOR.

**Fail explicitly:** Errors are returned in a structured format with clear messages. Never swallow a failure or return a misleading success. If a push fails partway through, return the specific file that failed and its HTTP status.

**No vibe coding:** Every line in the implementation has a documented reason. If code exists just because "it felt right," it doesn't belong. This is especially important for autonomous systems—future maintainers (including future versions of Tesa) need to understand every decision.

**Load context, don't embed it:** Credentials, API keys, and configuration live in context files (`context/gfs-env.md`, `context/df-env.md`), not in skill bodies. A skill should be readable without revealing secrets.

**Async where it matters:** Long-running operations (video renders, code builds, deployments) submit and return immediately. Polling is a separate concern—it belongs in the orchestrator layer, not inside the skill. This keeps skills simple and composable.

**Document the why, not just the what:** The methodology section explains the reasoning behind each step. Why do we push the library file before the route that depends on it? Why do we check for errors at each step? Answering these questions makes skills adaptable to future contexts.

---

## When *Not* to Use A.S.K

A.S.K is for repeatable, reusable capabilities. Not everything should be a skill.

**One-off tasks:** If you're building something that will never be reused, you don't need a skill. Implement it inline, or write a script.

**Exploratory work:** If you're researching a new integration or testing an idea, don't commit it to the skill library yet. Live with it first. When it's proven and stable, that's the time to skill-ify it.

**Vague or variable logic:** Skills are contracts. If the logic is fuzzy and changes based on context, it's not ready to be a skill. A skill should be boring, predictable, and reliable.

---

## Architecture & Philosophy

For a deep dive into *why* A.S.K is structured the way it is—why skills instead of functions, why the three tiers, why no vibe coding, why context files—see `PHILOSOPHY.md`. That document is the "big ideas" explanation. This README is the practical guide.

---

## Quick Reference

| File | Purpose |
|------|---------|
| `ASK.md` | Master registry of all skills with versions and descriptions |
| `README.md` | This file. How to use and understand A.S.K |
| `CONTRIBUTING.md` | How to write a new skill |
| `PHILOSOPHY.md` | Why A.S.K is designed this way |
| `/foundation/*` | Portable, platform-agnostic skills |
| `/gfs/*` | GFS platform-specific skills |
| `/dark-factory/*` | Self-building and architectural skills |
| `/context/gfs-env.md` | GFS credentials and configuration |
| `/context/df-env.md` | Dark Factory configuration |

---

*A.S.K by T.A.M. — Agent Skills Kernel by Tesa and Murphy*
*Last updated: 2026-03-30*
