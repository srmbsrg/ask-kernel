# Contributing to A.S.K

This guide walks you through writing a new skill for the A.S.K library. Whether you're adding a foundation skill, extending GFS, or building a Dark Factory pattern, the process is the same: think clearly about what the skill does, define its contract, and document the reasoning behind every decision.

This is pair-programming advice. I'm assuming you have a capability in mind, and we're going to build it together.

---

## Before You Write

Before you open a text editor, ask yourself three questions:

**1. Is this actually a skill?**

A skill is a reusable, stable capability that will be invoked by agents many times over months or years. If you're solving a one-off problem or exploring an untested idea, don't skill-ify it yet. Live with it first. When it's proven and boring, that's when it becomes a skill.

**2. What tier does it belong in?**

- **Foundation:** Generic, portable, no system-specific knowledge. Usable by any agent. Examples: "push files to GitHub," "send a notification," "authenticate to a service."
- **GFS:** Specific to the Ghostfoundry platform. Composes foundation skills and assumes knowledge of the codebase, deployment pipeline, and business logic.
- **Dark Factory:** Meta-level reasoning about code generation, architecture, and self-improvement.

If you're unsure, it's probably a foundation skill.

**3. What other skills does it depend on?**

Could this skill invoke a foundation skill instead of re-implementing that logic? The `tes-deploy` skill doesn't re-implement GitHub pushing—it invokes `foundation/github-push`. This is the design rule in action: compose skills rather than build monoliths.

---

## The SKILL.md Template

Every skill is a Markdown file named `SKILL.md` in its folder. Here's the structure, field by field.

### Frontmatter

```yaml
---
name: skill-name
description: One or two sentences. This is a routing signal.
version: 1.0.0
tier: foundation | gfs | dark-factory
dependencies:
  - context/gfs-env.md
  - foundation/github-push
---
```

**`name`:** Kebab-case only. Verb-noun preferred: `github-push`, `openbrain-write`, `slack-notify`. Avoid generic prefixes in GFS/DF skills—the tier folder already scopes it. Don't write `gfs/gfs-purchase`; write `gfs/purchase`.

**`description`:** This is what an agent reads when deciding whether to invoke this skill. Be specific. Bad: "A skill for purchases." Good: "Autonomously purchase a product or service using a Privacy.com single-use virtual card within pre-approved per-category spend limits."

The description is a routing signal. It should answer: What does this skill do? When would I use it?

**`version`:** Start with `1.0.0`. When you make breaking changes to inputs or outputs, bump MAJOR. New optional inputs? Bump MINOR. Documentation fix? PATCH.

**`tier`:** One of `foundation`, `gfs`, or `dark-factory`.

**`dependencies`:** List any skills or context files this skill requires. The agent will need to load these before invoking your skill. If you call `foundation/github-push` inside your skill, list it here. If you read from `context/gfs-env.md`, list it here.

### When to Invoke

Write 2-3 sentences about when an agent should use this skill. Be specific about the problem it solves and any preconditions.

Example (from `openbrain-write`):
> When something is worth remembering across sessions. Ask: "Would a future version of Tesa benefit from knowing this?" If yes, write it. Examples: A decision was made, Scott expressed a preference, a new integration was added, or a project milestone was reached. Do not write ephemeral task state—write conclusions, not process.

This tells the agent: use this when you want to save knowledge, but NOT for temporary state. That distinction matters.

### Inputs

Create a table with four columns: Field, Type, Required, Description.

```markdown
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `merchant` | string | yes | Name of the merchant or service. |
| `amount` | int | yes | Amount in cents (e.g., 4999 = $49.99). |
| `category` | string | yes | One of: `software`, `infrastructure`, `domains`, `marketing`, `tools`, `other`. |
| `description` | string | yes | Why this purchase is being made. |
| `merchant_url` | string | no | Merchant website (optional). |
```

Be exact. If a number is in cents, say so. If a field is one of an enumerated set, list them. If it's optional, explain what happens when it's absent.

For complex inputs (nested objects), provide an example JSON structure:

```markdown
| `config` | object | no | Configuration. Example: `{"timeout": 30, "retries": 3}` |
```

### Methodology

This is where you explain *how* the skill works and *why* each step matters. This is not a step-by-step procedure list. It's reasoning.

Start with the design principle if there is one. From `df-evolve`:
> Design principle: DF is minimal code + maximum ASK. Any capability already in the ASK library must be referenced, not re-implemented.

Then walk through the phases or logic. Use prose, not bullet points, unless the steps are genuinely procedural (like "5 distinct operations in sequence"). For each step, explain the reasoning.

From `github-push`:
> **Order matters for dependent files.** If pushing a new route and its associated lib, push the lib first.

Why? Because if the route is pushed first, the deployment might try to use the lib before it exists. This is a subtle but critical detail. Document it.

From `purchase`:
> **Never:**
> - Store card details in any log, file, or database
> - Re-use a card after the transaction
> - Create a card for a purchase that exceeds limits without Scott's explicit approval via Telegram

These are not arbitrary rules—they're security principles. Document them as such.

Good methodology sections answer the question: "I'm implementing this skill in a new language or environment. What do I need to know?" They're implementation-agnostic but contain the hard-won wisdom.

### Implementation

This is the actual code—Python pseudocode, JavaScript, or a detailed algorithm. Include enough that someone could implement it in another language without re-inventing the logic.

```python
def openbrain_write(content: str, metadata: dict = None) -> dict:
    try:
        embedding = get_embedding(content)
        row = {"content": content, "embedding": embedding, "metadata": metadata or {}}
        # ... push to Supabase
        return {"status": "saved", "content_preview": content[:80]}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
```

Include error handling. Real code has bugs and failures. Show how to handle them gracefully.

If the skill is complex, break it into logical sections with comments. If it calls external services, show the request structure (headers, auth, payload shape).

Do not include secrets in the code. Reference them as `<from env PRIVACY_API_KEY>` or similar.

### Outputs

Document what the skill returns. Use JSON if it's structured data.

From `purchase`:
```json
{
  "status": "created",
  "last_four": "4821",
  "pan": "4111111111114821",
  "cvv": "123",
  "exp_month": "03",
  "exp_year": "2027"
}
```

Or, for error cases:
```json
{"status": "pending_approval", "limit": 10000, "requested": 15000}
```

Always include a `status` field. Use this to signal to the caller what happened. Values like `created`, `error`, `pending_approval`, `over_limit`, etc. are clear and composable.

### Notes

Anything else: version history, gotchas, edge cases, links to related skills, or configuration quirks.

From `github-push`:
> Max file size via Contents API: 1MB. Larger files require the Git Data API (separate skill if needed).

This tells the next person: if you hit a 1MB file, you'll need a different approach.

---

## A Worked Example: The `slack-notify` Skill

Let's build a hypothetical foundation skill together: sending a Slack message.

```yaml
---
name: slack-notify
description: Send a message to a Slack channel or user via the Slack Web API. Use when Tesa or Dark Factory needs to communicate asynchronously with a team channel or individual.
version: 1.0.0
tier: foundation
dependencies:
  - context/gfs-env.md
---

# Slack Notify

## When to invoke

When you need to send a message to Slack—error notifications, deployment updates, or status reports. This is more flexible than Telegram (which is for alerting Scott specifically) and useful for team visibility.

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `channel` | string | yes | Slack channel name (e.g., `#deployments`) or user ID for DMs. |
| `message` | string | yes | The message text. Markdown and emoji supported. |
| `thread_ts` | string | no | If replying to a thread, the timestamp of the parent message. |
| `blocks` | array | no | Rich formatting via Slack Block Kit. Overrides `message` if provided. |

## Methodology

The Slack Web API is our communication layer to the team. We use the `chat.postMessage` endpoint, which is stable and widely used.

**Workspace assumption:** All invocations target a single Slack workspace (Foundry Familiars). The bot token is stored in `context/gfs-env.md` as `SLACK_BOT_TOKEN`. This token has `chat:write` permission.

**Channel resolution:** If the channel name starts with `#`, we look it up via the Conversations API to get its ID. If it's already an ID (starts with `C`), we use it directly. If it's a username, we look it up as a user ID (starts with `U`). This flexibility is important—the caller shouldn't need to know the internal ID format.

**Error handling:** If the channel doesn't exist, return `status: channel_not_found`. If the user lacks permissions, return `status: permission_denied`. Never silently drop a message.

**Thread replies:** If `thread_ts` is provided, the message is posted as a reply in a thread, keeping related messages grouped. This reduces noise in busy channels.

**Rich blocks:** If `blocks` is provided, we use it for richer formatting (buttons, images, lists). Fall back to plain text if blocks parsing fails—degraded but still functional.

## Implementation

```python
import urllib.request, json

SLACK_BOT_TOKEN = "<from env SLACK_BOT_TOKEN>"

def resolve_channel(name: str) -> str:
    """Convert #channel, username, or ID to a Slack channel/user ID."""
    if name.startswith("C") or name.startswith("U"):
        return name  # Already an ID
    if name.startswith("#"):
        name = name[1:]  # Strip #
    # Look up via Slack API (simplified)
    return name

def slack_notify(channel: str, message: str, thread_ts: str = None, blocks: list = None) -> dict:
    channel_id = resolve_channel(channel)
    payload = {
        "channel": channel_id,
        "text": message,
    }
    if thread_ts:
        payload["thread_ts"] = thread_ts
    if blocks:
        payload["blocks"] = blocks

    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=data,
        headers={
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json"
        }
    )

    try:
        with urllib.request.urlopen(req) as r:
            resp = json.loads(r.read())
            if resp.get("ok"):
                return {
                    "status": "sent",
                    "channel": channel_id,
                    "ts": resp.get("ts")
                }
            else:
                error = resp.get("error", "unknown_error")
                return {"status": "error", "detail": error}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
```

## Outputs

On success:
```json
{
  "status": "sent",
  "channel": "C1234567890",
  "ts": "1234567890.123456"
}
```

On failure:
```json
{
  "status": "error",
  "detail": "channel_not_found"
}
```

or

```json
{
  "status": "permission_denied",
  "detail": "Bot lacks chat:write permission in this workspace"
}
```

## Notes

- Slack bot token should have `chat:write` and `conversations:read` scopes.
- Message length limit: 4,000 characters for plain text, no strict limit for blocks (but keep it reasonable).
- The skill targets a single workspace. If we need multi-workspace support in the future, add a `workspace` input parameter and update the token resolution logic.
- Thread replies preserve message hierarchy and reduce channel noise, especially useful for deployment chains or error sequences.
```

That's a complete skill. Notice:

- The methodology explains *why* each step is there, not just *what* it does.
- The inputs are exact: channel name format, character limits, optional fields.
- The implementation shows error handling and graceful degradation.
- The notes section catches edge cases and future considerations.

---

## Writing Good Descriptions (Routing Signals)

The description field is the most important for agent routing. A bad description means the agent won't invoke your skill when it should, or will invoke it for the wrong reasons.

**Bad:** "A skill for sending Slack messages."
- This is too generic. What agent wants to send a Slack message? Many. When should this one be chosen over a different notification skill?

**Good:** "Send a message to a Slack channel or user via the Slack Web API. Use when Tesa or Dark Factory needs to communicate asynchronously with a team channel or individual."
- This says what it does, what tool it uses, and when you'd pick it over alternatives.

**Better:** "Send a message to a Slack channel or user via the Slack Web API. Use for team-visible status updates, deployment notifications, or async communication. Use `foundation/telegram-notify` for urgent alerts to Scott; use this for team channels."
- Now the agent understands the distinction. Telegram is urgent, Slack is team-visible.

Routing signals answer: Why would I use this instead of something else?

---

## The Methodology Philosophy

Methodology sections are where you capture the hard-won wisdom. They're the "why" not just the "how."

Bad methodology:
> 1. Load the PAT from env.
> 2. Call GitHub API to get the file SHA.
> 3. Push the new content.

Good methodology:
> Load the PAT from env. Never prompt the user—it lives in the Tesa env file at the path specified in dependencies. For each file, execute a two-step operation: (1) GET the current SHA. If the file doesn't exist, SHA is None—that's fine, it becomes a create. (2) PUT with base64-encoded content. Order matters for dependent files—if pushing a new route and its lib, push the lib first, because deployment might try to use the lib before it exists.

The second version explains the reasoning. It's something a future implementation can learn from, not just copy mechanistically.

---

## Testing Your Skill

Before you contribute a skill:

1. **Write the methodology first**, separate from implementation. Does it make sense? Is every step justified?
2. **Implement it** in the language your system uses (Python for Tesa, TypeScript for GFS, etc.).
3. **Test it** with real inputs. Does it handle errors gracefully? Does it return the documented output format?
4. **Review the contract:** Do the inputs and outputs actually match the methodology? Inconsistencies are bugs.
5. **Get feedback** from someone who's written a skill before. They'll catch vague descriptions and missing edge cases.

---

## Updating and Versioning

If you need to change a skill:

- **Adding an optional field to inputs?** MINOR version bump. Backwards compatible.
- **Removing a required field or changing output structure?** MAJOR bump. Callers must update.
- **Fixing documentation or improving implementation without changing contract?** PATCH bump.

When you update, update both `SKILL.md` and the row in `ASK.md`.

---

## Checklist

Before submitting your skill:

- [ ] Name is kebab-case, verb-noun format
- [ ] Description is specific and answers "when would I use this?"
- [ ] Frontmatter includes all dependencies
- [ ] "When to invoke" section is clear and has examples
- [ ] Inputs table is exact (types, defaults, why each field matters)
- [ ] Methodology explains reasoning, not just steps
- [ ] Implementation includes error handling
- [ ] Outputs document all possible return states
- [ ] Notes section catches edge cases and future considerations
- [ ] No vibe coding—every line has a clear purpose
- [ ] No hardcoded secrets or environment-specific paths
- [ ] Version is `1.0.0` for new skills
- [ ] Skill is registered in `ASK.md` under the appropriate tier

---

## Questions?

If you get stuck, look at existing skills in the library. `openbrain-write` and `df-evolve` are good references. And remember: a skill is a contract between an agent and a system. Make the contract clear, and everything else follows.

---

*A.S.K by T.A.M. — Agent Skills Kernel by Tesa and Murphy*
*Last updated: 2026-03-30*
