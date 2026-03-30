---
name: tes-deploy
description: Full deployment cycle for the GFS platform — push code files to GitHub, optionally update Vercel env vars, trigger redeployment, wait for READY, and notify Scott via Telegram. Use any time a code change needs to go live on the GFS/SSS platform.
version: 1.0.0
tier: gfs
dependencies:
  - context/gfs-env.md
  - foundation/github-push
  - foundation/vercel-deploy
  - foundation/telegram-notify
---

# Tes Deploy

## When to invoke

When code changes need to go live. This is the complete deploy pipeline — it orchestrates three foundation skills in sequence and handles the happy path and error cases. Do not invoke the foundation skills individually for a GFS deploy; use this skill instead.

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `files` | list | yes | Files to push. Each: `{path, content, message}`. Same format as `foundation/github-push`. |
| `commit_summary` | string | yes | Human-readable summary of what changed. Used in Telegram notification. |
| `env_vars` | dict | no | Env vars to upsert before redeploying. Keys and values. |
| `branch` | string | no | Default: `main`. |
| `notify` | bool | no | Default: `true`. Send Telegram confirmation when READY. |

## Methodology

This skill is an orchestrator. Think of it as the conductor — it calls foundation skills in sequence and makes decisions based on their outputs.

**Step 1 — Push code**
Invoke `foundation/github-push` with the provided files and branch. If any file returns `status: error`, halt immediately. Do not proceed to deployment with partial code — a half-pushed feature is worse than no change. Notify Scott of the specific failure.

**Step 2 — Upsert env vars** (if provided)
Invoke `foundation/vercel-deploy` with `redeploy: false` and the env_vars dict. This updates the vars without triggering a deploy yet. If this fails, halt and notify.

**Step 3 — Trigger redeployment**
Invoke `foundation/vercel-deploy` with `redeploy: true` and `wait_for_ready: true`. Use the deploy ID returned from step 2 (or fetch the latest if step 2 was skipped).

**Step 4 — Notify**
If `notify: true`, invoke `foundation/telegram-notify` with a summary of what was deployed, the deploy URL, and elapsed time. If any step failed, the notification should describe the failure clearly.

**On any error:**
- Never silently swallow failures
- Always notify Scott via Telegram even when things go wrong
- Include enough detail for him to act: which step failed, what the error was, what state the system is in

## Sequence Diagram

```
tes-deploy
    │
    ├─► github-push [all files]
    │       └── any error? → telegram-notify(error) → HALT
    │
    ├─► vercel-deploy [env_vars only, no redeploy]  (if env_vars provided)
    │       └── error? → telegram-notify(error) → HALT
    │
    ├─► vercel-deploy [redeploy: true, wait: true]
    │       ├── READY → continue
    │       └── ERROR → telegram-notify(error) → HALT
    │
    └─► telegram-notify [success summary]
```

## Outputs

```json
{
  "status": "ready",
  "files_pushed": 3,
  "env_vars_updated": ["STRIPE_SECRET_KEY"],
  "deploy_id": "dpl_abc123",
  "deploy_url": "gfs-deploy-xyz.vercel.app",
  "elapsed_seconds": 142,
  "telegram_sent": true
}
```

## Notes

- The GFS repo is `srmbsrg/ghostfoundry-syndicate`. Do not push to other repos via this skill — use `foundation/github-push` directly for DF or archive repos.
- If you're only updating env vars without any code change, you can pass `files: []` and `env_vars: {...}`. The skill handles this gracefully (skips the github-push step).
- Typical deploy cycle: ~2-4 minutes from trigger to READY.
