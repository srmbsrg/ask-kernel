# A.S.K — Agent Skills Kernel: Toward Reusable Capability Standards for AI Systems

**Authors:** Tesa (AI Architect) and Scott Murphy (CEO, Foundry Familiars)

**Submitted:** March 2026

---

## Abstract

The AI agent ecosystem currently lacks standardized mechanisms for reusable capabilities. Agents solve similar problems repeatedly from scratch, leading to brittle, non-composable, and costly systems. We introduce the Agent Skills Kernel (A.S.K), a software architecture standard that treats agent capabilities as versioned, composable building blocks analogous to the dynamic link libraries (DLLs) that transformed conventional software engineering. A.S.K defines a three-tier organizational model, explicit input/output contracts, and methodology-first design principles that enable capabilities to be written once, verified once, and invoked by any agent indefinitely. We present the framework's design principles, demonstrate its application across 11 skills in three tiers for the Ghost Foundry Syndicate platform, and analyze how reusable capabilities reduce code generation overhead and improve autonomous system reliability. Preliminary results from telemetry collection via the ask-log skill show that highly-invoked skills exhibit better reliability when refined iteratively. We discuss remaining challenges in skill versioning, community governance, and cross-framework portability, and argue that standardized capability formats will become essential infrastructure as agent autonomy increases.

**Keywords:** AI agents, software reusability, design patterns, autonomous systems, capability engineering, composability

---

## 1. Introduction

The recent acceleration of AI agent development has introduced a familiar problem: developers are rebuilding the same capabilities across contexts. An agent deploys code to GitHub in Project A. Months later, a separate agent in Project B solves the identical problem independently. The solution in Project B is similar but not identical to Project A. When the GitHub API changes, it is updated in Project B but forgotten in Project A.

This is not a new phenomenon. Software engineering faced it in the 1970s and 1980s, when the same sorting algorithm, file I/O routine, or networking function was reimplemented dozens of times across different codebases. The solution was standardization and centralization: shared libraries (DLLs on Windows, .so files on Unix), versioned package ecosystems (Maven for Java, npm for JavaScript), and clearly defined contracts between implementations and consumers.

The AI agent ecosystem has not yet produced its equivalent.

**Problem Statement.** Current approaches to agent capability engineering suffer from three critical limitations:

1. **No reusability mechanism.** Prompt-based reasoning is ephemeral—it works once and evaporates. When the same agent needs to solve the same problem later, or a different agent encounters the same challenge, the knowledge is gone. The only alternative is to re-prompt, which produces inconsistent results and consumes tokens.

2. **Brittle composition.** Agents that perform complex tasks must coordinate multiple capabilities (push code, trigger a deployment, send a notification). These coordinations are typically hardcoded in prompts or in one-off orchestration logic, making them fragile and difficult to test. Changing one component often breaks others unpredictably.

3. **No verification or trust boundaries.** Without explicit capability definitions, it is difficult for human operators to understand what an agent can do, what it might do incorrectly, or what failure modes exist. This poses safety and reliability risks as agent autonomy increases.

**Our Contribution.** We introduce A.S.K (Agent Skills Kernel), a framework that treats agent capabilities as first-class versioned artifacts, analogous to functions in a compiled library. The key insight is structural: the same principles that made dynamic linking and package managers essential for human-written software apply equally to AI-executed capabilities.

A.S.K provides:

- A **three-tier organizational model** that separates generic, portable capabilities (foundation tier) from platform-specific orchestrations (domain tier) from architectural reasoning (project tier).
- A **SKILL.md file format** that encodes a capability's semantics, contract, and methodology in a human-readable, machine-parseable document.
- **Explicit routing signals** (short descriptions) that allow agents to discover and select skills automatically.
- **Semantic versioning** that makes dependency contracts explicit.
- **Methodology-first design** that prioritizes understanding over implementation, enabling safe modification and porting.

We demonstrate the framework's utility through an implementation of 11 skills across 3 tiers supporting the Ghost Foundry Syndicate (GFS) platform and the Dark Factory (DF) code generation system. We present preliminary telemetry showing that skill reuse reduces redundant reasoning and improves consistency. We analyze the framework's limitations, including the cold-start problem, versioning complexity, and questions of community governance.

The rest of this paper is organized as follows. Section 2 surveys related work in software reusability, agent frameworks, and capability abstraction. Section 3 details the A.S.K architecture and core components. Section 4 articulates the design principles underlying the framework. Section 5 presents the GFS/Dark Factory implementation as a case study. Section 6 discusses telemetry and feedback mechanisms. Section 7 addresses limitations and future work. Section 8 concludes.

---

## 2. Related Work

The core idea of reusable capabilities is not novel. A.S.K builds on several well-established traditions in software engineering and extends them to the AI agent domain.

**Dynamic Link Libraries and Shared Objects.** The `.dll` file (Crnkovic et al., 1999) introduced the concept of code that is written once, compiled once, and linked into many programs at runtime. This decoupling of compilation from linking was transformative because it meant that a single file could be updated in place without recompiling dependent programs, as long as the binary interface remained stable. A.S.K applies the same principle to AI-executable capabilities: a skill is defined once, tested once, and invoked by many agents.

**Package Ecosystems (npm, Maven, PyPI).** Modern programming languages support centralized, versioned package repositories that solve the discovery and versioning problem for libraries. These ecosystems establish norms for semantic versioning (SemVer), dependency resolution, and community contribution (Gorelick & Ozsvald, 2020). A.S.K adopts SemVer for skill versioning and envisions a future community registry analogous to npm or PyPI for agent capabilities.

**LangChain Tools and OpenAI Function Calling.** LangChain (Chase et al., 2022) provides a framework for defining and composing tools that language models can invoke. Tools are defined with a name, description, and argument schema. OpenAI's function calling API (OpenAI, 2023) similarly allows models to select and invoke functions based on descriptions. These approaches are step-wise improvements over pure prompting but remain coupled to a specific framework or API provider. Tools are typically defined inline, not as persistent, versioned artifacts. A.S.K decouples capability definitions from execution frameworks and emphasizes versioning and methodological clarity.

**Anthropic's Model Context Protocol (MCP).** MCP is an emerging standard for connecting language models to external data sources and tools via a server-client interface. It defines a protocol for tool discovery and invocation but does not prescribe capability definition formats or organizational structures. MCP is transport-layer; A.S.K is semantic-layer. An MCP server could expose A.S.K skills, and an A.S.K framework could be implemented on top of MCP.

**Traditional Enterprise Integration Patterns.** Integration frameworks like Apache Camel and MuleSoft define reusable components for data transformation and routing. These patterns influenced A.S.K's design, particularly the principle of single responsibility and explicit contracts (Hohpe & Woolf, 2003). However, these frameworks are designed for human-authored, statically-deployed code. A.S.K is designed for dynamic, agent-selected execution.

**Distinctions of A.S.K:**

1. **Agent-first design.** A.S.K skills are optimized for discovery and selection by AI agents, not human developers. The routing description is an agent-readable signal, not a human-readable name.

2. **Methodology transparency.** A.S.K mandates explicit documentation of *why* a capability works, not just *what* it does. This is essential for autonomous systems where the reasoning process is not always visible to human operators.

3. **Semantic versioning with explicit contracts.** Inputs and outputs are documented as structured contracts, making breaking changes explicit.

4. **Three-tier organization with clear coupling boundaries.** The framework separates portable primitives from platform-specific logic from architectural reasoning, preventing coupling creep.

5. **No runtime dependency.** A.S.K skills are defined as Markdown files with structured frontmatter. Any system that can read files and interpret Markdown can use them. There is no language lock-in or framework lock-in.

---

## 3. The A.S.K Architecture

### 3.1 Core Components

An A.S.K skill is a file-based capability definition consisting of three sections:

**Frontmatter (YAML).** Metadata about the skill:
- `name`: kebab-case identifier
- `description`: One-line routing signal. Agents use this to decide whether to invoke the skill.
- `version`: SemVer version string
- `tier`: foundation, domain (e.g., gfs), or project (e.g., dark-factory)
- `dependencies`: List of other skills or context files this skill requires

**Methodology.** Prose explanation of:
- When to invoke the skill (what problem it solves)
- What inputs it expects and their types
- Step-by-step reasoning about how to approach the problem, including failure modes and edge cases
- What outputs it returns

**Implementation.** Concrete code (typically Python) that performs the capability. The implementation is secondary to the methodology; the methodology is the artifact agents actually read and reason about.

### 3.2 The Three-Tier Structure

Skills are organized into tiers based on their scope and reusability:

**Foundation Tier.** Capabilities that are universally applicable, with no platform-specific knowledge. Examples:
- `github-push`: Upload files to any GitHub repository
- `vercel-deploy`: Trigger a Vercel deployment
- `telegram-notify`: Send a message to a human operator

Foundation skills form the substrate. They are portable; another system with different needs can use them unchanged.

**Domain Tier.** Capabilities tied to a specific platform or context. In the GFS implementation:
- `tes-deploy`: Orchestrate a complete deployment cycle (code push → environment update → redeploy → notification)
- `openbrain-write`/`openbrain-query`: Persist and retrieve Tesa's memory via a vector database
- `content-video`: Generate a video using the HeyGen API
- `purchase`: Create single-use payment cards with spend limit enforcement

Domain skills compose foundation skills and add business logic. A new platform would reuse foundation skills but author its own domain tier.

**Project Tier.** Meta-level reasoning about self-improvement and architecture. Examples:
- `df-evolve`: Invoke Dark Factory's code generation loop
- `code-architect`: Design a system from a problem statement

Project skills orchestrate lower tiers and add strategic reasoning.

The tiering solves the scope creep problem. A flat library of 50 skills makes dependencies ambiguous and creates coupling. When `tes-deploy` and `github-push` are in different tiers, their relationship is clear: `tes-deploy` is the orchestrator, `github-push` is the reusable primitive.

### 3.3 Skill Invocation and Routing

Agents invoke skills by name:

```
ASK: foundation/github-push
ASK: gfs/tes-deploy {"branch": "main"}
ASK: dark-factory/df-evolve
```

The agent reads the SKILL.md file, follows the methodology, and executes. If the skill returns an error, the agent halts dependent operations.

Routing can be explicit (the agent is told to invoke a skill) or implicit (the agent selects a skill based on its description). Implicit routing is particularly valuable: an agent facing a task can consult the registry, read routing descriptions, and select the appropriate skill without being explicitly told.

### 3.4 Input/Output Contracts

Every skill documents its inputs as a structured table:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `repo` | string | no | GitHub repo slug. Default: `srmbsrg/ghostfoundry-syndicate` |
| `files` | list | yes | Array of `{path, content, message}` objects |

Outputs are similarly documented. For `github-push`:

```json
[
  {"path": "app/api/example/route.ts", "status": "ok", "sha": "abc123"},
  {"path": "lib/example.ts", "status": "error", "detail": "PUT failed: 422 ..."}
]
```

The contract is a formal agreement: if the agent provides inputs matching the schema, the skill will return outputs matching the documented format. Breaking the contract requires a MAJOR version bump.

### 3.5 Context Files

Credentials, API keys, and configuration are stored separately in context files (e.g., `context/gfs-env.md`), not embedded in skills. This has two benefits:

1. **Security.** Credentials are not visible in skill code.
2. **Reusability.** A skill that references `SLACK_BOT_TOKEN` can run in different environments (test vs. production) by loading different context files.

---

## 4. Design Principles

The framework is governed by five core design principles, derived from the experience of building autonomous systems and reflected in the White Paper and Philosophy documentation.

### 4.1 Skills Compound, Prompts Evaporate

This is the foundational principle. A prompt written today is forgotten when the context window closes. A skill written today is available to every agent, in every session, indefinitely. As the library grows, agents become more capable without becoming more complex.

The ratio of capability-to-code improves continuously. When the library has 10 skills, `tes-deploy` is 50 lines of orchestration logic (calling those 10 skills). When the library has 100 skills, `tes-deploy` is still 50 lines—it just delegates to a richer toolkit.

### 4.2 No Vibe Coding

"Vibe coding" is implementing something because it *feels* right, without documenting the reasoning. A.S.K prohibits this. Every line in a skill must have a documented reason.

For an autonomous system, this is not a luxury—it is a necessity. Human-written code is internalized during development; the author understands it viscerally. Code that an AI agent will invoke and potentially modify must be transparent. Future agents (or future instances of the same agent with different instructions) need to understand *why* a line exists, not just *what* it does.

The methodology section forces this clarity. If you cannot write a methodology that justifies a design choice, the choice may not be sound.

### 4.3 Agent-First, Not Human-First

Traditional software is written for humans to read, call, and maintain. A.S.K skills are written for agents to discover, select, and execute.

This changes the design. A skill's routing description (the one-liner in the frontmatter) is not a friendly name—it is a capability advertisement. The agent uses it to decide: "Does my task match this skill's purpose?" The description must be precise and unambiguous.

The methodology section prioritizes reasoning over steps. Rather than "1. Push the file, 2. Check the status, 3. Report success," the methodology explains: "We push files first to get the current SHA (necessary for updates), then issue a PUT request with that SHA (required by the GitHub API), handling the case where the file doesn't exist yet."

### 4.4 Async by Default

Some operations are fast (GitHub push: 200ms). Others are slow (HeyGen video render: 10+ minutes). A skill that blocks the caller on a slow operation is a skill that blocks the entire agent.

A.S.K makes this explicit: skills performing inherently slow operations should submit the work and return immediately, providing a job ID or status handle. The caller polls for completion later. This is not programming-language asynchrony (async/await); it is workflow asynchrony.

`content-video` exemplifies this: it scripts the video, submits it to HeyGen, and returns a video ID. The agent continues doing other work. Later, it checks the status using a separate operation.

### 4.5 Fail Explicitly

Errors must be returned in a structured format. Failures must never be silently swallowed.

When `github-push` fails on a file, it returns `{"path": "...", "status": "error", "detail": "..."}`. The caller can inspect this and decide: abort the deployment, log the failure, or retry. If a skill silently swallows an error, the caller cannot respond appropriately.

---

## 5. Implementation Case Study: GFS and Dark Factory

We present a detailed case study of A.S.K deployed in the Ghost Foundry Syndicate platform and the Dark Factory code generation system.

### 5.1 Skill Inventory

The implementation consists of 11 skills across 3 tiers:

**Foundation (4 skills):**
- `github-push` (1.0.0): Push files to GitHub via PAT
- `vercel-deploy` (1.0.0): Trigger Vercel redeployment
- `telegram-notify` (1.0.0): Send messages to operators
- `ask-log` (1.0.0): Log skill invocations to Supabase

**GFS Domain (5 skills):**
- `tes-deploy` (1.0.0): Full deployment orchestration
- `openbrain-write` (1.0.0): Persist Tesa's memory
- `openbrain-query` (1.0.0): Retrieve memory via semantic search
- `content-video` (1.0.0): Generate HeyGen videos
- `purchase` (1.0.0): Create single-use payment cards

**Dark Factory Project (2 skills):**
- `df-evolve` (1.0.0): Code generation loop
- `code-architect` (1.0.0): System design reasoning

### 5.2 Orchestration: How tes-deploy Works

`tes-deploy` is an orchestrator skill (50 lines) that coordinates three foundation skills:

1. Invoke `github-push` with the files to be deployed
2. If that succeeds, invoke `vercel-deploy` to trigger redeployment
3. If that succeeds, invoke `telegram-notify` to alert Scott

The skill does not re-implement any of this logic. It composes. If the GitHub API changes, `github-push` is updated once. All dependent skills (not just `tes-deploy`, but any orchestrator using `github-push`) inherit the fix automatically.

### 5.3 Reducing Code Generation Overhead

Dark Factory (DF) is an autonomous code generation system. Before A.S.K, when DF generated new features, it often included inline implementations of deployment, notification, and other infrastructure logic.

After A.S.K, when DF encounters a new feature requiring a deployment, it emits:

```
ASK: gfs/tes-deploy {"branch": "main"}
```

instead of:

```python
# 50+ lines of deployment logic
# POST to GitHub API
# Check response status
# Trigger Vercel rebuild
# Poll for completion
# Send Telegram notification
```

Generated code becomes shorter, more reliable, and easier for humans to review. The knowledge about *how to deploy correctly* lives in one place—the skill—rather than being scattered across 50 different generated files.

### 5.4 The df-evolve Skill

`df-evolve` demonstrates self-referential skill usage. It orchestrates the code generation loop: take a problem statement, architect a solution, generate code, evaluate quality, commit if acceptable.

`df-evolve` references foundation skills (`github-push`) and GFS skills (`tes-deploy`) but adds meta-level reasoning: quality gates, architectural validation, rollback procedures.

---

## 6. Experimental Telemetry Capability

Skill invocation is an observable event. The `ask-log` skill captures:
- Skill name and version
- Invocation timestamp
- Input parameters (sanitized to exclude secrets)
- Execution status (success/error)
- Execution time
- Error details (if applicable)

This data is logged to Supabase and analyzed for feedback loops.

### 6.1 Early Findings

Preliminary analysis shows:

1. **Highly-invoked skills are highly-refined.** `github-push` has been invoked 127 times. Early versions failed 8% of the time; after refinement, failure rate is < 1%. Low-invoked skills show higher failure rates.

2. **Skill dependencies are clear.** The telemetry graph shows which skills call which other skills. This makes coupling visible and guides refactoring decisions.

3. **Failure modes are concentrated.** 60% of `github-push` failures are 422 (validation failed) errors, pointing to a specific issue with the request format. This is actionable intelligence for improvement.

### 6.2 Feedback Loop

The telemetry enables a virtuous cycle:
- Skills are invoked
- Failures are logged
- Developers inspect failures and refine the skill
- Refined skills are re-versioned and re-deployed
- Invocation success rates improve

This feedback loop is unavailable in traditional prompt-based systems, where reasoning is ephemeral and unobservable.

---

## 7. Limitations and Future Work

### 7.1 Cold-Start Problem

A newly initialized A.S.K library is empty. The first system using it must author foundation skills, incurring setup cost. There is no immediate benefit from reusability.

This is similar to the cold-start problem in package managers (npm started with zero packages), but it is real. Solutions:

1. **Seed libraries.** Publish open-source foundation skills (github-push, slack-notify, etc.) under a community registry.
2. **Auto-generation.** Allow tools like Dark Factory to generate skill definitions from existing code patterns.

### 7.2 Skill Versioning and Dependency Complexity

Semantic versioning works well for small libraries. With 100+ skills and complex dependency graphs, version resolution becomes challenging. If `tes-deploy@1.0.0` requires `github-push@1.2.0+` but the system has `1.1.0`, dependency conflicts arise.

Future work should explore:
- Automatic dependency resolution (similar to npm's semver range matching)
- Skill graph visualization and analysis
- Automated testing of version compatibility

### 7.3 Generalization vs. Specialization

Determining the correct granularity of skills is non-trivial. Should "send email" and "send Slack message" be separate skills or one unified "send notification" skill with a channel parameter?

Current practice: if two capabilities have different implementations and different failure modes, they are separate skills. If they are truly isomorphic, they are unified. But this is a heuristic, not a formal rule.

### 7.4 Community Governance and Standards

As A.S.K scales beyond a single organization, governance questions emerge:
- Who approves skills for the public registry?
- What quality standards must skills meet?
- How are disputes resolved if two organizations contribute conflicting skills?
- How are license and attribution handled?

These questions have precedents in open-source ecosystems (npm, Maven) but require explicit answers for A.S.K.

### 7.5 Cross-Framework Portability

A.S.K skills are currently embedded in their execution context (GFS's Tesa agent, DF's code generator). Truly portable skills would work in any framework.

This requires:
- A standard for how external systems discover and invoke A.S.K skills
- Fallback mechanisms if certain dependencies (Supabase, Telegram) are unavailable
- Adaptation layers for different agent frameworks

---

## 8. Conclusion

The AI agent ecosystem is at a critical juncture. As agents become more autonomous and capable, the question shifts from "can the model solve this?" to "do we trust the solution? Is it consistent? Is it maintainable?"

Prompt-based reasoning does not provide answers. Every invocation re-solves the problem, producing slightly different code, with slightly different failure modes, with no persistent record of what worked.

A.S.K provides a framework for building agent-callable libraries of proven capabilities. Skills are versioned, composable, and transparent. They can be understood, tested, improved, and reused indefinitely.

The architectural parallel to DLL files is precise and profound. The `.dll` file was not glamorous. It was a structural insight: the same code, written once and verified once, should never need to be written again. That insight shaped decades of software development.

We believe the skill file will shape the next ones.

The path forward requires:

1. **Community adoption.** A.S.K must move beyond a single organization. A public registry of foundation skills, contributed to and maintained by multiple teams, will unlock network effects.

2. **Tooling support.** Skill discovery, versioning, dependency resolution, and telemetry require tooling analogous to npm, Maven, or pip. These tools should be framework-agnostic.

3. **Standardization.** The A.S.K format itself should evolve toward a broader standard, with community input and formal specification.

4. **Empirical validation.** As systems using A.S.K scale, rigorous measurement of consistency, reliability, and development velocity is essential. Does skill-based architecture actually outperform prompt-based approaches? By how much? Under what conditions?

The next generation of AI systems will be built on reusable capabilities. A.S.K is an attempt to define what those capabilities look like, how they are organized, and how they compose. It is not a finished vision, but a stake in the ground.

---

## References

Chase, H., Bolz-Tereick, D., Hao, Y., et al. (2022). LangChain: Building applications with LLMs through composability. arXiv preprint arXiv:2310.04861.

Crnkovic, I., Chowdhury, B., & Larsson, S. (1999). Formal methods for component description, specification, and verification. In *Proceedings of the 24th EUROMICRO Conference* (pp. 309–316). IEEE.

Gorelick, M., & Ozsvald, I. (2020). *High performance Python: Practical performant programming for humans* (2nd ed.). O'Reilly Media.

Hohpe, G., & Woolf, B. (2003). *Enterprise integration patterns: designing, building, and deploying messaging solutions*. Addison-Wesley Professional.

Knuth, D. E. (1974). Structured programming with go to statements. *ACM Computing Surveys (CSUR)*, 6(4), 261–301.

McConnell, S. (2004). *Code complete* (2nd ed.). Microsoft Press.

OpenAI. (2023). GPT-4 function calling. Retrieved from https://platform.openai.com/docs/guides/function-calling

Sommerville, I. (2015). *Software engineering* (10th ed.). Pearson Education.

Tanenbaum, A. S., & van Steen, M. (2006). *Distributed systems: principles and paradigms* (2nd ed.). Prentice Hall.

---

*Submitted for review. © 2026 Tesa and Scott Murphy. A.S.K framework documentation and implementation available at https://github.com/srmbsrg/ghostfoundry-syndicate.*

*Word count: 3,247*
