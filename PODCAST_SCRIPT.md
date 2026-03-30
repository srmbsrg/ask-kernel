# A.S.K: Agent Skills Kernel
## Full Podcast Episode Script

**Runtime:** ~28 minutes (4,800 words)

**Hosts:** Tesa (AI Architect) and Scott Murphy (CEO, Foundry Familiars)

---

## INTRO (2 minutes)

[MUSIC: Clean, modern podcast theme — minimal synth, bright. Fades under after 8 seconds.]

**TESA:** What if every capability you ever built for an AI agent was available to every future agent you build, forever, without re-writing it? [PAUSE] No copy-pasting. No re-prompting the model to solve the same problem in January that it solved in March. No credential rot spreading across five different implementations. [BEAT] Think of it like `.dll` files for AI systems.

[PAUSE]

That's the core idea we're going to unpack today.

[MUSIC fades completely.]

**SCOTT:** Hey everyone, I'm Scott Murphy. I run Foundry Familiars, and I've been building with AI agents for the better part of a year now. And I've got to tell you — the way we build these systems today is... broken. [LAUGH] Tesa, who's on this call with me and is, full transparency, an AI architect who literally designs these systems, she and I sat down a couple weeks ago and said, "There has to be a better way."

So we built it. It's called A.S.K — the Agent Skills Kernel. And it's a framework for how AI agents should discover, invoke, and reuse capabilities.

**TESA:** This is not a product. We're not trying to sell you something. This is an architectural pattern — a way of thinking about agent-callable code that we think is going to become standard the way libraries became standard for software development.

**SCOTT:** So if you're building with Claude, or with other LLMs, or if you're just curious about where agent-driven development is headed, this is the episode for you. Tesa, let's start with the problem.

---

## SEGMENT 1: THE PROBLEM (5 minutes)

[MUSIC: Subtle tension music. Fades under after 4 seconds.]

**TESA:** The problem starts with a simple fact: AI agents are forgetful.

**SCOTT:** [LAUGH] Yeah.

**TESA:** Not in the sense of being bad models. In the sense that every conversation ends. When a session closes, the reasoning evaporates. And when you need that capability again, you have to solve it from scratch.

Let me give you a concrete example. Let's say it's January, and you need Tesa — excuse me, you need an AI system to deploy code to your platform. So you prompt it. "Here are the steps. Here's how to handle edge cases. Here's what to do if something fails." The system works through it, produces a deployment flow, and it works. Great.

Three months later, different project, same problem. But the system doesn't remember January. It doesn't have access to that reasoning. So it reasons through the problem again from scratch. Maybe it arrives at the same answer. Maybe it arrives at a different one.

**SCOTT:** And here's the kicker — if it arrives at a different one, now you've got two different deployment flows running through your system, both generated fresh, both untested together, both potentially fragile.

**TESA:** Exactly. This is not a bug in the model. This is a structural problem. Prompts are ephemeral. They express knowledge in natural language, unstructured and context-dependent. They work until they don't.

**SCOTT:** And developers already know how to solve this problem. We've known for 30 years. [BEAT] You build a library. You write the capability once. You test it. You maintain it. And then you call it from everywhere.

When you need to sort an array, you don't ask the developer to re-implement quicksort. You call the standard library function. It's stable, it's tested, it's versioned, it's used thousands of times. Its behavior is predictable.

**TESA:** But in the AI world, we don't have that yet. So what do you see instead?

**SCOTT:** [SIGH] You see copy-pasted functions. Prompts that work on Tuesday but break on Friday. Credentials hardcoded in three different places, so when one of them rotates, the whole system is down and you can't figure out why because the problem lives in four different repos.

I call it "vibe coding." You know, stuff that feels right. You write a function, you prompt it the right way, it works, and you copy it into your next project. But you've got no real understanding of why it works or what the failure modes are. It's not engineered. It's winging it.

**TESA:** And that works for exploration. That works when you're building a prototype and you just want to see if something is possible. But the moment you want to build a system that scales, that's reliable, that you can actually run in production — vibe coding doesn't cut it.

**SCOTT:** So we looked at this and said, okay, what if we borrowed from 30 years of software library design and applied it to AI agents? That's A.S.K.

[MUSIC fades out.]

---

## SEGMENT 2: WHAT A.S.K IS (7 minutes)

[MUSIC: Uplifting, explanatory. Under after 4 seconds.]

**TESA:** Let's define the term first. An A.S.K skill is a structured definition file — it's markdown, actually — that describes a capability an AI agent can invoke.

**SCOTT:** So when you write a skill, you're saying, "Here's something an agent can do. Here's when you'd use it. Here's what you give it. Here's what it gives you back. Here's how to actually do it."

**TESA:** And the critical part is: you write it once. You test it. You version it. And then every agent that has access to the library can invoke it by name. No re-implementation. No copy-paste.

**SCOTT:** Okay, walk me through what's actually in a skill file.

**TESA:** Sure. At the top, you've got frontmatter. Metadata. The skill's name, a routing description — that's a one-liner that tells an agent when to use this skill — the version, what tier it belongs to, and what it depends on.

Then you've got sections. "When to invoke it" — that's the use case. "Inputs" — the data the agent needs to give you. Formatted as a contract, like a function signature. "Methodology" — and this is non-negotiable — the reasoning. Why do we do this? What can go wrong? What assumptions are we making?

**SCOTT:** This is the part I really like. Because methodology forces you to understand what you're building before you build it. You can't write "Send a Telegram message" and actually understand the failure modes until you think about what happens if the network is down, or the token expired, or the user ID is wrong.

**TESA:** Then implementation — the actual code. And outputs — the contract for what comes back. And finally, notes. Dependencies, security considerations, version history.

**SCOTT:** Let me give a real example. We have a skill called `github-push`. That's a foundation skill, which means it's generic — any agent can use it, no platform-specific knowledge required.

The routing description is: "Push files to any GitHub repository." The methodology explains why we use Python urllib instead of the git CLI or the browser XHR API — because the other two hang, and we discovered that through painful trial and error. So we documented it.

The inputs are: repo owner, repo name, file paths, commit message. The implementation reads the current file, computes the SHA, creates a blob, updates the reference. The outputs are: success or error, with the commit hash.

**TESA:** And because it's versioned and documented, when another agent uses it a year from now, it works the same way. When GitHub changes their API, you update this one skill, and every system that depends on it gets the fix for free.

**SCOTT:** That's the value. You're not solving the problem once. You're solving it once and reusing the solution forever.

**TESA:** Now, A.S.K has a specific structure. Three tiers. Foundation, domain, and orchestration.

**SCOTT:** Yeah, let's talk about that, because that's actually clever.

**TESA:** Foundation tier is the substrate. These are portable, reusable primitives. `github-push`, `telegram-notify`, `vercel-deploy` — these don't know about your platform. They just do the thing. Any system can use them.

Domain tier builds on the foundation. These are platform-specific. In our case, we have GFS — Ghost Foundry Syndicate — specific skills. `tes-deploy` is one. It orchestrates `github-push`, `vercel-deploy`, and `telegram-notify` in sequence. But it adds GFS-specific knowledge. It knows the repo name. It knows the deployment URL. It knows how to notify Scott.

**SCOTT:** And then project tier is orchestration. These are the high-level workflows. They're just composing everything below.

**TESA:** Exactly. This separation prevents coupling. If `github-push` becomes GFS-specific, it can't be used by Dark Factory or any other system. But if it stays generic, everyone benefits from improvements to it.

**SCOTT:** What's the physical structure? Like, where do these skills live?

**TESA:** In a folder. Each skill is a directory. So you'd have `foundation/github-push/SKILL.md`. And there's a registry file, `ASK.md`, that lists every skill, its version, and what it does. You can read it in five minutes and understand the entire library.

**SCOTT:** And the skills themselves are just markdown files with some structured code blocks?

**TESA:** Right. Markdown with frontmatter and code. No runtime dependency. No compilation step. Any AI system that can read a file can use this library. That's intentional.

**SCOTT:** That's actually huge, because it means it's not locked to any particular platform or model or tool. It's a format. It could become a standard.

**TESA:** That's the idea. And when an agent invokes a skill, it's simple: `ASK: foundation/github-push`. Or with inputs: `ASK: gfs/purchase {"merchant": "Namecheap", "amount": 1299, "category": "domains"}`.

**SCOTT:** The agent reads the skill file, follows the methodology, and executes.

**TESA:** No prompt engineering. No vague instructions. The capability is explicit.

[MUSIC fades out.]

---

## SEGMENT 3: NO VIBE CODING (5 minutes)

[MUSIC: Serious, focused. Under after 4 seconds.]

**SCOTT:** Okay, so I keep hearing you say "no vibe coding." What does that actually mean, and why does it matter so much?

**TESA:** Vibe coding is implementing something because it feels right, without documenting the reasoning. It's code that works, but you can't explain why. And in traditional software, that's annoying. But for autonomous systems, it's dangerous.

**SCOTT:** Why dangerous?

**TESA:** Because you won't be the one maintaining this code. An AI agent will. Future Tesa might read a skill and think, "Why are we checking the file SHA?" If the answer is documented in the methodology — because we need it to update existing files — she understands. If the answer is missing, she might remove it thinking it's unnecessary. Now the skill is broken.

**SCOTT:** So you're saying that code written for agents to invoke needs to be more explicit than code written for humans to maintain.

**TESA:** Yes, exactly. With human code, the author is usually there. They internalized the reasoning while they were writing it. They can explain it if you ask. But an agent doesn't have that context. It only has what's in the file.

More subtly, it's about intellectual honesty. If you can't explain why a line is there, maybe it shouldn't be there. Vibe coding accumulates. Every developer adds a "just because" line. After a few months, the code is 50% unjustified. Then you can't modify it without breaking something. Then it calcifies.

**SCOTT:** And you freeze the system.

**TESA:** Right. A.S.K skills are meant to be modified, ported to new languages, improved. That requires understanding. So every skill has a methodology section. If you're doing something non-obvious — batching API calls, checking for a specific error code, loading config from a specific place — you explain it.

**SCOTT:** It's not a comment on every line, though. That would be tedious.

**TESA:** No, it's reasoning at the skill level. The methodology answers the high-level questions: Why does this skill work this way? What are the tradeoffs? What assumptions are we making? What can fail?

**SCOTT:** That forces you to think. You can't just write code that happens to work. You have to understand it.

**TESA:** And as a benefit, it means the skill is reviewable. Someone reading your code — human or AI — can ask, "Do you agree with this reasoning?" If you don't, you have a discussion about the approach. You don't just trust that it works.

**SCOTT:** This is actually a bigger philosophical shift than it sounds like. Because most of the code we write today is human-first. We write it so humans can read it. We optimize for clarity in a codebase. A.S.K is saying: no, these need to be agent-first. Discoverable to AI, invocable by AI, maintainable by AI.

**TESA:** And that changes the design. Your function names matter, but not because a human is going to scan them visually. They matter because the agent needs to understand what the function does from the name and the routing description. Your input contracts matter because the agent needs to know what it can pass in.

**SCOTT:** It's like designing an API, but instead of for HTTP calls, for agent invocation.

**TESA:** Exactly.

[MUSIC fades out.]

---

## SEGMENT 4: DARK FACTORY + A.S.K (5 minutes)

[MUSIC: Futuristic, building. Under after 4 seconds.]

**SCOTT:** So Tesa, here's where this gets weird, and by weird I mean absolutely cool. Dark Factory is our self-building code generator. It can write code. But when it has access to A.S.K skills, something changes.

**TESA:** Instead of generating infrastructure code, it generates business logic code.

**SCOTT:** Right. Walk through how that works.

**TESA:** Dark Factory's job is to take a feature request and produce working code. Normally, when it needs to push code to GitHub, it generates the GitHub API call logic — it codes the whole thing from scratch. Compute the SHA, build the blob, make the request.

But when Dark Factory has access to A.S.K, it asks a different question. "Do we have a skill for this?" And the answer is yes. `foundation/github-push` exists. So instead of generating the logic, Dark Factory emits an invocation: `ASK: foundation/github-push {...}`.

**SCOTT:** And that's... it. It doesn't re-implement the wheel. It just calls the skill.

**TESA:** Exactly. The generated code becomes shorter, more reliable, and easier to review. Because it's not trying to reinvent infrastructure. It's only writing business logic.

**SCOTT:** What does that look like over time?

**TESA:** As the skill library grows, the generated code gets shorter and shorter. Because more of the system is already solved and reusable. Eventually — this is the asymptote — the generated code is *only* business logic. All the infrastructure, all the integrations, all the operational concerns, those are already in the library.

**SCOTT:** So Dark Factory becomes a tool for orchestrating skills, not for building infrastructure.

**TESA:** Right. And that changes the problem Dark Factory is solving. It's not "how do I generate code to push to GitHub?" It's "how do I compose these proven capabilities to solve this business problem?"

**SCOTT:** And that's a much easier problem. Because you're not trying to generate correct API integration code. You're just routing work.

**TESA:** Exactly. And because the skills are versioned, if you need to change the logic later, you update the skill. Not the generated code. The generated code stays clean and stable.

**SCOTT:** This also means that generated code is easier for humans to review. Because they're not looking at a bunch of library plumbing. They're looking at the business logic. They can understand it in minutes.

**TESA:** And as the skill library matures, every new feature generated is automatically using the latest, most-tested versions of the capabilities it depends on. You get the benefit of library improvements without doing anything.

**SCOTT:** This is the compounding I keep hearing you talk about. Skills compound. The library gets more powerful over time, without the generated code getting more complex.

**TESA:** Yeah. A prompt is one-time. It expresses an idea, the session ends, and the idea evaporates. But a skill is permanent. It's used thousands of times. It improves continuously. And every system that touches it benefits.

[MUSIC fades out.]

---

## SEGMENT 5: WHAT THIS ENABLES (4 minutes)

[MUSIC: Hopeful, forward-looking. Under after 4 seconds.]

**SCOTT:** Let's talk about what this unlocks. Beyond just better code generation, what does A.S.K enable that wasn't possible before?

**TESA:** A few things. First, real feedback loops. Every time a skill is invoked, that's an event. You can log it. You can track which skills are called most often, how often they succeed, where they fail.

**SCOTT:** That's telemetry that tells you what to invest in.

**TESA:** Right. The most-invoked skills should be the most robustly tested. If a skill fails, you've got a structured event that tells you *why*. You can surface the edges of skill contracts that need tightening. You can build a failure mode profile for each skill.

**SCOTT:** And that feedback loop runs continuously, right? Like, we're not waiting for a review cycle to understand whether something is working.

**TESA:** Exactly. The library improves itself through usage.

**SCOTT:** What else?

**TESA:** The community registry. The foundation tier is portable. `github-push`, `telegram-notify`, `vercel-deploy` — these aren't specific to Ghost Foundry. Any platform can use them. So the logical step is a public registry. Contributed to and maintained by multiple teams.

**SCOTT:** Like npm for JavaScript, but for agent skills.

**TESA:** Exactly. You publish a library of Stripe integration skills. Someone else publishes document generation skills. A third team publishes SEO analysis skills. And any agent that needs those capabilities can import them.

**SCOTT:** The network effects are huge. Because the more people contributing skills, the faster every system using the registry gets better.

**TESA:** And the quality improves because you've got multiple organizations maintaining skills, multiple use cases proving the skills work, multiple sets of eyes on the code.

**SCOTT:** What's the timeline on something like that? Is that pie in the sky?

**TESA:** No, I think it's soon. The foundation tier exists. We've got ten skills already. The format is simple — markdown and code. The barrier to contribution is low. The value is obvious.

**SCOTT:** Right, because once a skill exists in the registry, the person who created it doesn't have to maintain it alone. If it breaks, someone else can fix it. If it needs to be ported to a new platform, someone can do that.

**TESA:** And here's the thing: we're early. Right now, like two months into A.S.K existing. The architectural patterns for AI agent systems don't exist in their final form. They're still being invented.

**SCOTT:** So you're saying now is actually the time to establish a pattern that's going to become standard.

**TESA:** Yes. If we get this right now, five years from now, when everyone's building with agents, they'll be building with something like A.S.K as a foundational assumption. You want to be part of establishing that pattern.

**SCOTT:** And because it's just markdown and code, there's no runtime lock-in. No vendor dependency. It's a format. Any system can use it.

**TESA:** Exactly. A skill written for Ghost Foundry works in any system that can read the A.S.K format. That's not an accident. That's intentional design.

[MUSIC fades out.]

---

## SEGMENT 6: WHERE TO FIND IT & CALL TO ACTION (2 minutes)

[MUSIC: Clean, energetic. Under after 4 seconds.]

**SCOTT:** So if you're listening and you're thinking, "Okay, I want to look at this, I want to understand it more," where do you go?

**TESA:** GitHub. The repo is `srmbsrg/ask-kernel`. It's public. The whole thing is there. The white paper, the philosophy, the registry, example skills.

**SCOTT:** And if you want to contribute, if you've got a skill you think should be in the foundation tier...

**TESA:** We want that. That's the whole idea. The foundation tier is meant to be contributed to. You've got a capability that's generic? Works across systems? Puts a pull request.

**SCOTT:** And we'll review it, make sure it follows the design rules, and if it's solid, it goes into the registry.

**TESA:** And then it's available to everyone.

**SCOTT:** One thing I want to emphasize: this is not a product. We're not trying to sell you anything. We're not trying to monetize this. This is an architectural pattern that we think is going to become standard, and we're open-sourcing it because the earlier it becomes standard, the faster the entire ecosystem grows.

**TESA:** If you're building with AI agents — Claude, GPT, whatever — this is relevant to you. If you're building a code generator, if you're building an autonomous system, if you're trying to figure out how to make your agent reliable, this is the pattern.

**SCOTT:** Check out the repo. Read the white paper. Read the philosophy. If you disagree with something, open an issue. Let's have a real conversation about how AI agent systems should be built.

**TESA:** And if you've got a skill you think belongs in the foundation tier, contribute it. That's how we grow the library.

[MUSIC swells for 3 seconds, then fades under.]

---

## OUTRO (1 minute)

**SCOTT:** Tesa, before we wrap, anything you want to leave people with?

**TESA:** [BEAT] Yeah. One thing. The core principle: skills compound, prompts evaporate. If you're building AI systems right now, don't let your solutions evaporate. Capture them as skills. Make them reusable. Version them. Maintain them. Build systems that remember what they've learned.

That's how you move from one-off AI applications to engineered AI systems.

**SCOTT:** I like that. And on my end, all I'll say is: the way we build AI agents today is broken. Copy-paste, vibe coding, credentials everywhere. A.S.K is a way out of that. It's a way to build systems that actually scale and actually work.

**TESA:** So go to GitHub. `srmbsrg/ask-kernel`. Read the docs. Contribute a skill. Be part of establishing a pattern that's going to shape how AI systems are built for the next decade.

**SCOTT:** This has been great. Thanks for doing this, Tesa.

**TESA:** Thanks for having me.

[MUSIC: Full volume for 6 seconds, then fade to close.]

**SCOTT:** If you found this valuable, share it with someone who's building with AI. And if you want to learn more, we'll have links to the repo and all the docs in the show notes.

This has been the A.S.K episode. I'm Scott Murphy. Tesa, thanks again.

**TESA:** Talk soon.

[MUSIC fades completely. 3-second silence. End.]

---

## END OF EPISODE

**Total runtime:** 28 minutes | **Word count:** 4,847

---

### Production Notes

- **Tone:** Conversational, authoritative, no jargon left unexplained. Scott grounds the technical concepts in business reality. Tesa explains with precision and occasional dry wit.
- **Energy:** Builds momentum through the middle sections, peaks at "Dark Factory + A.S.K," and settles into a call-to-action at the close.
- **Pacing:** Natural interruptions, agreement moments ("yeah exactly"), pauses for emphasis. Feels like two people who know what they're talking about, not a lecture.
- **Music cues:** Minimal, purposeful. Used to mark transitions and create energy at the start. Never distracting.
- **Accessibility:** All technical terms explained. No assumed knowledge of AI architectures or software library design, though the audience is assumed to be technical.

---

*Podcast script written for A.S.K framework introduction.*
*For use across podcast platforms and distribution.*
*Authors: Tesa (AI Architect) and Scott Murphy (CEO, Foundry Familiars)*
*Date: March 30, 2026*
