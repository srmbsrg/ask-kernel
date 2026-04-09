# A.S.K — Agent Skills Kernel

> **A versioned, composable library of AI agent capabilities.**
> Think `.dll` files for AI systems. Write the capability once, invoke it everywhere.
>
> *Built by T.A.M. — Tesa (AI Architect) and Scott Murphy (Foundry Familiars / Ghost Foundry Syndicate)*

---

## Table of Contents

1. [What Is A.S.K?](#what-is-ask)
2. [Why It Was Built](#why-it-was-built)
3. [Architecture Overview](#architecture-overview)
4. [The Three-Tier Model](#the-three-tier-model)
5. [Skill Anatomy](#skill-anatomy)
6. [Invocation Protocol](#invocation-protocol)
7. [Skill Registry](#skill-registry)
8. [Key Technical Decisions](#key-technical-decisions)
9. [Cryptographic Signing](#cryptographic-signing)
10. [Quickstart](#quickstart)
11. [Example: Chained Skill Execution](#example-chained-skill-execution)
12. [Tech Stack](#tech-stack)
13. [Status & Roadmap](#status--roadmap)
14. [Contributing](#contributing)

---

## What Is A.S.K?

A.S.K is an **agent capability kernel** — a structured library that gives AI agents a stable interface to interact with external systems. Rather than letting an agent re-derive how to push code to GitHub, send a Telegram notification, or trigger a Vercel deployment on every invocation, A.S.K defines each capability once as a versioned `SKILL.md` file.

A skill is a contract:

- **Name** — how it's referenced
- **Inputs** — what it expects
- **Methodology** — the exact steps the agent should follow
- **Outputs** — what it returns
- **Rationale** — why it works this way, not some other way

Any agent — the GFS platform AI (Tesa), the Dark Factory code generator, or a future system — invokes a skill by path and follows the contract. The skill is the stable interface. The implementation beneath it can change; the contract does not.

**The core principle: Skills compound. Prompts evaporate.**

Every time an agent solves a problem without recording the solution as a skill, that knowledge is lost the moment the session ends. The next agent re-solves it from scratch, possibly worse. A.S.K breaks this cycle.

---

## Why It Was Built

### The problem with ad-hoc agents

Modern AI agent systems are fragile. Developers write prompts, wrap them in functions, copy-paste those functions across projects, and then scramble when an API changes or a credential rotates. The agent that worked yesterday fails today because the GitHub push logic was duplicated in four places and only three were updated.

This is a problem software engineers solved decades ago — with libraries. `npm install`, `pip install`, `#include`. You write a capability once, test it, version it, and every consumer of that library benefits from every improvement.

A.S.K applies the library model to AI agents. It is, in effect, `npm` for agent behavior.

### The specific context

Ghost Foundry Syndicate (GFS) operates autonomous AI systems — Tesa, a long-running AI operator, and Dark Factory, a self-building code generator — that need to perform the same set of actions reliably across thousands of invocations:

- Push code to GitHub
- Deploy to Vercel and wait for readiness
- Notify Scott via Telegram
- Execute authorized purchases via Privacy.com virtual cards
- Read from and write to a persistent vector memory (OpenBrain)
- Generate HeyGen avatar videos

Without A.S.K, each of these would be re-implemented or re-prompted every time. With A.S.K, each is defined once and invoked by name. The agents are more predictable, the system is more auditable, and capabilities genuinely improve over time.

### Why this matters beyond GFS

A.S.K is designed to be general. The foundation tier contains no GFS-specific knowledge — only portable, agent-callable primitives. Any team building AI agents faces the same problem: how do you give an LLM a stable, tested interface to the systems it controls, rather than hoping the model generates the right API call every time?

The answer is a skill library. A.S.K is one concrete implementation of that answer.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                   AI Agent                       │
│       (Tesa / Dark Factory / External)           │
└──────────────────────┬──────────────────────────┘
                       │  ASK: <skill-path>
                       ▼
┌─────────────────────────────────────────────────┐
│              A.S.K Skill Registry               │
│                  (ASK.md)                        │
│  ┌───────────────┐  ┌───────────────┐           │
│  │ Foundation    │  │ GFS Tier      │           │
│  │ Tier          │  │               │           │
│  │ github-push   │  │ tes-deploy    │           │
│  │ vercel-deploy │  │ openbrain-*   │           │
│  │ telegram-     │  │ content-video │           │
│  │ notify        │  │ purchase      │           │
│  │ ask-log       │  └───────────────┘           │
│  └───────────────┘  ┌───────────────┐           │
│                     │ Dark Factory  │           │
│                     │ Tier          │           │
│                     │ code-architect│           │
│                     │ df-evolve     │           │
│                     └───────────────┘           │
└──────────────────────┬──────────────────────────┘
                       │  executor.py resolves path,
                       │  parses SKILL.md, executes
                       ▼
┌─────────────────────────────────────────────────┐
│              External Systems                    │
│  GitHub API │ Vercel API │ Telegram Bot API      │
│  Privacy.com │ Supabase/OpenBrain │ HeyGen API   │
└─────────────────────────────────────────────────┘
```

### How it works

1. **Invocation** — An agent issues `ASK: foundation/github-push` with a JSON input block.
2. **Resolution** — `executor.py` locates `foundation/github-push/SKILL.md`.
3. **Parsing** — The executor reads the YAML frontmatter (name, version, tier, dependencies) and the Markdown body (methodology, inputs, outputs).
4. **Signature verification** (optional) — The skill's cryptographic signature is verified against `signing/trusted_signers.json` before execution.
5. **Execution** — The executor runs the embedded implementation block from the SKILL.md using the provided inputs.
6. **Logging** (optional) — Completion is logged to Supabase via `foundation/ask-log` for telemetry.
7. **Output** — The skill returns a structured result to the calling agent.

---

## The Three-Tier Model

Skills are organized into three tiers with strict boundary rules:

### Foundation Tier (`/foundation/`)

Portable, system-agnostic primitives. No knowledge of GFS, Dark Factory, or any specific platform. These can be used by any agent in any context.

| Boundary rule | Foundation skills MUST NOT contain GFS-specific business logic, hardcoded credentials, or assumptions about the calling system. |
|---|---|

**Current foundation skills:**

| Skill | Version | What it does |
|-------|---------|--------------|
| `github-push` | 1.0.0 | Push files to any GitHub repo using Python urllib. The only approved push method — git CLI and XHR both hang on `api.github.com` in agent contexts. |
| `vercel-deploy` | 1.0.0 | Upsert Vercel environment variables and/or trigger a production redeployment. Polls for READY state before returning. |
| `telegram-notify` | 1.0.0 | Send a Telegram message via @tes_BSG_bot. Primary human communication channel for all autonomous GFS processes. |
| `ask-log` | 1.0.0 | Log a skill invocation event (start / complete / error) to Supabase for telemetry and feedback loops. |

### GFS Tier (`/gfs/`)

Platform-specific skills for the Ghost Foundry Syndicate. These compose foundation skills with GFS business logic, credentials, and workflows.

| Boundary rule | GFS skills may invoke foundation skills but MUST NOT re-implement foundation capabilities inline. |
|---|---|

**Current GFS skills:**

| Skill | Version | What it does |
|-------|---------|--------------|
| `tes-deploy` | 1.0.0 | Full deploy cycle: code push → env var update → redeployment → READY polling → Telegram notification. Orchestrates three foundation skills. |
| `openbrain-write` | 1.0.0 | Save a thought or decision to OpenBrain (Supabase vector store) — Tesa's persistent memory across sessions. |
| `openbrain-query` | 1.0.0 | Semantic search of OpenBrain to retrieve relevant memories, decisions, and prior context. |
| `content-video` | 1.0.0 | Generate a HeyGen avatar video: LLM-drafted script → HeyGen render → Telegram notification on completion. Async by design. |
| `purchase` | 1.0.0 | Create a Privacy.com single-use virtual card within per-category spend limits. Sends Telegram approval request if over limit. |

### Dark Factory Tier (`/dark-factory/`)

Meta-level reasoning patterns for autonomous code generation and self-improvement. These skills enable the Dark Factory system to design, generate, evaluate, and commit new code.

| Boundary rule | Dark Factory skills operate at the architectural level. They produce plans and invoke other skills; they do not contain business logic themselves. |
|---|---|

**Current Dark Factory skills:**

| Skill | Version | What it does |
|-------|---------|--------------|
| `code-architect` | 1.0.0 | Design a self-improving system from a problem statement: identify composable skills, map data flow, produce an architecture decision record (ADR). |
| `df-evolve` | 1.0.0 | Invoke the Dark Factory code generator to produce, evaluate, and commit new code. DF emits ASK invocations rather than re-implementing known capabilities. |

---

## Skill Anatomy

Every skill is a `SKILL.md` file in its directory. The format is consistent across all tiers:

```markdown
---
name: skill-name
description: One to two sentences. This is the routing signal the agent uses to select this skill.
version: 1.0.0
tier: foundation | gfs | dark-factory
dependencies:
  - context/gfs-env.md
  - foundation/other-skill
---

# Skill Name

## When to invoke
Specific conditions under which this skill should be called. Designed to help the agent route correctly.

## Inputs
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `field_name` | string | yes | Description |

## Methodology
Step-by-step instructions the agent follows. This section is prescriptive — it removes ambiguity from execution. Each step explains not just what to do, but why.

## Outputs
| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `"success"` or `"error"` |
| `result` | object | Skill-specific output data |

## Error Handling
What to do when something goes wrong. Which errors are recoverable vs. fatal. When to surface the failure to a human.

## Implementation
```python
# Executable code block. The executor extracts and runs this section.
```

## Design Notes
The reasoning behind key implementation decisions. Why this approach and not an alternative.
```

The `description` field in the frontmatter is critical — it is the signal an agent uses when routing. A well-written description means the agent selects the right skill without being told explicitly which one to call.

---

## Invocation Protocol

### Direct invocation
```
ASK: foundation/github-push
{
  "repo": "srmbsrg/my-repo",
  "files": [
    {"path": "src/index.py", "content": "print('hello')", "message": "Add entry point"}
  ]
}
```

### Invocation with explicit inputs
```
ASK: gfs/purchase {
  "merchant": "Namecheap",
  "amount": 1299,
  "category": "domains",
  "description": "Renew foundrytech.io — expires 2026-06-01"
}
```

### Chained invocation (orchestrator pattern)
```
ASK: gfs/tes-deploy
  → composes: foundation/github-push
  → composes: foundation/vercel-deploy
  → composes: foundation/telegram-notify
```

Higher-tier skills reference lower-tier skills by path. The executor resolves the dependency chain and executes each skill in order, passing outputs as inputs to the next stage.

### Via executor.py
```bash
# List all available skills
python executor.py --list

# Invoke a skill with JSON inputs
python executor.py foundation/github-push '{"repo": "srmbsrg/test", "files": []}'

# Verify signature before executing
python executor.py --verify-signatures foundation/github-push '{}'

# Enable verification via environment variable
ASK_VERIFY_SIGNATURES=1 python executor.py foundation/github-push '{}'
```

---

## Skill Registry

The canonical registry is maintained in `ASK.md`. The registry is the source of truth — if a skill exists, it is listed there with its version, description, and path. Agents parse `ASK.md` to discover available capabilities.

```markdown
| Skill              | Version | Description                              | Path                      |
|--------------------|---------|------------------------------------------|---------------------------|
| github-push        | 1.0.0   | Push files to any GitHub repo via urllib | foundation/github-push/   |
| vercel-deploy      | 1.0.0   | Upsert env vars + trigger redeployment   | foundation/vercel-deploy/ |
| telegram-notify    | 1.0.0   | Send Telegram message via @tes_BSG_bot   | foundation/telegram-notify/ |
| ask-log            | 1.0.0   | Log invocation events to Supabase        | foundation/ask-log/       |
| tes-deploy         | 1.0.0   | Full GFS deploy cycle (orchestrator)     | gfs/tes-deploy/           |
| openbrain-write    | 1.0.0   | Write thought to vector memory           | gfs/openbrain-write/      |
| openbrain-query    | 1.0.0   | Semantic search of vector memory         | gfs/openbrain-query/      |
| content-video      | 1.0.0   | Generate HeyGen avatar video             | gfs/content-video/        |
| purchase           | 1.0.0   | Autonomous purchase via Privacy.com card | gfs/purchase/             |
| code-architect     | 1.0.0   | Design system architecture, produce ADR  | dark-factory/code-architect/ |
| df-evolve          | 1.0.0   | Dark Factory code generation + commit    | dark-factory/df-evolve/   |
```

---

## Key Technical Decisions

### 1. Markdown as the skill format

Skills are `SKILL.md` files, not JSON schemas or Python modules. This is deliberate.

**Why Markdown:** An LLM reads a `SKILL.md` directly. The methodology section is prose — it tells the agent exactly what to do in a format the model can reason about, not just execute. A Python function defines behavior mechanically; a Markdown skill defines behavior *and its rationale*. This lets agents understand the intent, not just the steps, which matters when edge cases arise.

**Why not JSON/YAML:** JSON is machine-readable but not human-writeable at the granularity needed for complex agent reasoning. YAML schemas describe structure, not process. A skill needs to communicate WHY as much as WHAT.

### 2. Python urllib exclusively for HTTP (no requests library)

All HTTP calls in foundation skills use `urllib` from the Python standard library. The `requests` library is not an approved dependency.

**Why:** Agent execution environments are often minimal. `requests` is not always available. `urllib` is always available. This makes foundation skills genuinely portable — they run anywhere Python 3 runs, with zero dependency installation.

**The github-push exception:** The implementation notes explicitly call out that git CLI and browser `fetch()` both hang when called against `api.github.com` from certain execution contexts. `urllib` is specified as the only reliable option. This is the kind of learned, operational knowledge that a skill preserves — and that an ad-hoc agent would have to rediscover.

### 3. Tier boundary enforcement

The three-tier architecture has hard boundary rules: foundation skills cannot contain GFS-specific logic; GFS skills must compose from foundation rather than re-implement. This is enforced by convention (documentation, code review) rather than runtime checks in v1.0.

**Why:** Boundary discipline prevents the library from becoming a monolith. When `tes-deploy` needs to push code, it invokes `foundation/github-push`. The deploy logic benefits from any improvements to the push skill automatically. Without boundaries, you'd end up with three slightly different implementations of GitHub pushing across three skills.

### 4. The description field as a routing signal

Each skill's YAML frontmatter includes a `description` field that is carefully written as a routing signal — not a human-readable summary, but a signal tuned to help an LLM dispatch correctly.

**Why:** When an agent receives a task ("push this file to the repo"), it needs to select the right skill without being told which one to use. The description is what the agent matches against. A well-written description collapses ambiguity: "Push files to any GitHub repo via PAT + Python urllib. The only approved push method" leaves no room for misrouting.

### 5. Cryptographic skill signing

The `signing/` directory implements a full PKI-style signing system for skills: `keygen.py`, `sign_skill.py`, `verify_skill.py`, and a `trusted_signers.json` registry.

**Why:** As AI systems become more autonomous, the ability to verify that a skill was authored by a trusted party (and hasn't been tampered with) becomes a real security concern. A.S.K implements signing at the capability layer, not just the application layer. Skills can be signed before deployment and verified before execution — `ASK_VERIFY_SIGNATURES=1` enables this in the executor.

### 6. Spend limit enforcement in the purchase skill

The `gfs/purchase` skill enforces per-category spend limits ($25–$200) and sends a Telegram approval request for any amount over the limit before creating a virtual card.

**Why:** Autonomous purchase capability is dangerous without guardrails. The skill enforces the limits at the capability layer — the agent cannot circumvent them without modifying the skill itself. This is a concrete example of how A.S.K provides safety boundaries, not just convenience.

---

## Cryptographic Signing

A.S.K includes a signing layer for production systems where skill integrity must be verified before execution.

```bash
# Generate a signing keypair
python signing/keygen.py --output signing/keys/

# Sign a skill
python signing/sign_skill.py foundation/github-push/SKILL.md --key signing/keys/private.pem

# Verify before execution
python signing/verify_skill.py foundation/github-push/SKILL.md

# Enable verification at runtime
ASK_VERIFY_SIGNATURES=1 python executor.py foundation/github-push '{}'
```

Trusted signers are maintained in `signing/trusted_signers.json`. Revoked keys are tracked in `signing/revoked_keys.json`. This allows individual compromised keys to be invalidated without rotating the entire keystore.

---

## Quickstart

### 1. Clone the repository

```bash
git clone https://github.com/srmbsrg/ask-kernel.git
cd ask-kernel
```

### 2. List available skills

```bash
python executor.py --list
```

```
Available skills:
  foundation/ask-log          v1.0.0  Log invocation events to Supabase
  foundation/github-push      v1.0.0  Push files to any GitHub repo via PAT
  foundation/telegram-notify  v1.0.0  Send Telegram message via @tes_BSG_bot
  foundation/vercel-deploy    v1.0.0  Upsert env vars + trigger redeployment
  gfs/content-video           v1.0.0  Generate HeyGen avatar video
  gfs/openbrain-query         v1.0.0  Semantic search of vector memory
  gfs/openbrain-write         v1.0.0  Write thought to vector memory
  gfs/purchase                v1.0.0  Autonomous purchase via Privacy.com card
  gfs/tes-deploy              v1.0.0  Full GFS deploy cycle (orchestrator)
  dark-factory/code-architect v1.0.0  Design system architecture, produce ADR
  dark-factory/df-evolve      v1.0.0  Dark Factory code generation + commit
```

### 3. Run the demo agent

```bash
python examples/demo_agent.py
```

The demo runs against mock implementations — no credentials required. It demonstrates:

- Skill discovery via the registry
- Input/output contracts in action
- Skill composition (task → select skill → invoke → result)

### 4. Configure credentials for live invocation

Create a `context/gfs-env.md` file (gitignored) with your credentials:

```markdown
## GitHub
- PAT: ghp_...
- Default repo: your-org/your-repo

## Vercel
- Token: ...
- Project ID: ...
- Team ID: ...

## Telegram
- Bot token: ...
- Default chat ID: ...
```

### 5. Invoke a skill

```bash
python executor.py foundation/github-push '{
  "repo": "your-org/your-repo",
  "files": [
    {
      "path": "test.md",
      "content": "# Test\nThis file was pushed via A.S.K.",
      "message": "Add test file via A.S.K foundation/github-push"
    }
  ]
}'
```

---

## Example: Chained Skill Execution

This example shows how an orchestrator skill (`gfs/tes-deploy`) chains three foundation skills to execute a complete deployment cycle.

```python
# Agent receives task: "Deploy the updated route handler to GFS platform"

# Step 1: Agent reads ASK.md, selects gfs/tes-deploy
# Step 2: Executor loads gfs/tes-deploy/SKILL.md, resolves dependencies
# Step 3: Executor chains:

# 3a. foundation/github-push
result_push = ask("foundation/github-push", {
    "repo": "srmbsrg/ghostfoundry-syndicate",
    "files": [
        {
            "path": "app/api/gfs/webhook/route.ts",
            "content": updated_route_content,
            "message": "Update webhook handler — add Stripe event processing"
        }
    ]
})
# Returns: {"status": "success", "sha": "abc123", "url": "..."}

# 3b. foundation/vercel-deploy (upsert env vars only, no deploy yet)
result_env = ask("foundation/vercel-deploy", {
    "env_vars": {"STRIPE_WEBHOOK_SECRET": new_secret},
    "redeploy": False
})

# 3c. foundation/vercel-deploy (trigger deployment, wait for READY)
result_deploy = ask("foundation/vercel-deploy", {
    "redeploy": True,
    "wait_for_ready": True
})
# Returns: {"status": "ready", "url": "https://gfs.vercel.app", "deploy_id": "dpl_..."}

# 3d. foundation/telegram-notify (confirm to human)
ask("foundation/telegram-notify", {
    "message": f"*Deploy complete ✓*\nWebhook handler updated. Live at {result_deploy['url']}",
    "chat_id": 6735511617
})
```

Each step is a discrete, testable unit. If `github-push` fails (partial push, API error), the orchestrator halts and notifies before the deployment is triggered — preventing a broken state.

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Skill format | Markdown + YAML frontmatter | LLM-readable, human-writeable, no build step required |
| Executor runtime | Python 3 (stdlib only) | Zero dependencies, runs in any agent environment |
| HTTP calls | `urllib` (Python stdlib) | Works reliably where `requests` may not be installed; no hanging on GitHub API |
| Cryptographic signing | RSA / ECDSA (via `signing/` module) | Skill integrity verification for production autonomous systems |
| Persistent memory | Supabase (vector + relational) | OpenBrain — semantic search across agent session history |
| Deployment target | Vercel | GFS/SSS platform hosting |
| Human channel | Telegram Bot API | Real-time async communication between autonomous agents and Scott |
| Purchase control | Privacy.com | Single-use virtual cards with hard per-transaction limits |
| Video generation | HeyGen | Autonomous Tesa avatar video creation |
| Metadata / telemetry | Supabase | Invocation logging via `foundation/ask-log` |

---

## Status & Roadmap

**Current state:** v1.0.0 — production in use for GFS platform operations and Dark Factory code generation.

### What's working

- Full foundation tier (4 skills, battle-tested in production)
- GFS tier (5 skills — deploy, memory, purchase, video)
- Dark Factory tier (2 skills — architecture, code generation)
- Reference executor with SKILL.md parsing and signature verification
- Demo agent with mock implementations
- Signing infrastructure (keygen, sign, verify, revocation)

### Planned

- **v1.1:** Formal JSON Schema for skill frontmatter + validation on load
- **v1.2:** Skill versioning enforcement — breaking changes require major version bump; executor warns on version mismatch
- **v1.3:** Telemetry dashboard — visualize skill invocation frequency, error rates, latency from `ask-log` data
- **v2.0:** Multi-agent skill sharing — skills defined in one agent's context, discoverable and invokable by others via a shared registry endpoint
- **v2.1:** Skill tests — each `SKILL.md` ships with a `SKILL_TEST.md` that defines expected inputs/outputs; executor can run test suites
- **Long-term:** A.S.K as an open standard for AI agent capability definition — foundation tier published as a public registry

### Known limitations

- Skill execution is synchronous in the reference executor; async execution (e.g., `content-video`) is handled at the skill level via polling
- Boundary enforcement is convention-based in v1.0; runtime enforcement (e.g., preventing a foundation skill from importing GFS context) is planned for v1.2
- The signing system is implemented but optional; production deployments should enable `ASK_VERIFY_SIGNATURES=1`

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the complete guide to writing new skills.

The short version:

1. Identify which tier your skill belongs in (when in doubt: foundation)
2. Check `ASK.md` — if the capability already exists, extend it rather than create a duplicate
3. Write `SKILL.md` using the standard template
4. Add a row to the registry in `ASK.md`
5. Sign the skill: `python signing/sign_skill.py <path>/SKILL.md`
6. Submit a PR — skills are reviewed for tier placement, description quality, and methodology clarity

The most common contribution mistake: writing a GFS skill when the capability is actually portable. If the skill could work for *any* agent deploying to *any* GitHub repo, it belongs in foundation. See the [PHILOSOPHY.md](PHILOSOPHY.md) for the reasoning.

---

## Authors

**Scott Murphy** — CEO, Foundry Familiars / Ghost Foundry Syndicate. Builder of agentic infrastructure for SMBs.

**Tesa** — AI Architect, GFS. Co-designer of the A.S.K specification and primary production user of the skill library.

*ghostfoundrysyndicate@outlook.com*

---

*A.S.K is a component of the Ghost Foundry Syndicate platform. The foundation tier is designed to be useful to any team building AI agents.*
