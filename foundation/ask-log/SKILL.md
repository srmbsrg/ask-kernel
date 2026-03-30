---
name: ask-log
description: Log an ASK skill invocation event — skill name, inputs summary, outcome, and duration — to the OpenBrain Supabase database. Call at the start and end of any skill execution to build a telemetry record. Use to track which skills are most used, which fail, and how long operations take.
version: 1.0.0
tier: foundation
dependencies:
  - context/gfs-env.md
---

# ASK Log (Telemetry)

## When to invoke

At the **start** and **end** of any skill execution. Each skill that wants to participate in telemetry calls this skill twice:
1. On entry: `event: "start"`, `inputs: {summary of inputs}`
2. On exit: `event: "complete"` or `event: "error"`, `duration_ms`, `outcome`

This is optional for skills — the library works without it — but any skill that adopts it contributes to the feedback loop that improves the library over time.

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `skill` | string | yes | Skill path: e.g., `"gfs/purchase"` |
| `event` | string | yes | `"start"`, `"complete"`, or `"error"` |
| `session_id` | string | no | Identifier for the calling session. Allows correlating start/end pairs. |
| `inputs_summary` | string | no | Non-sensitive summary of inputs. Never log secrets, credentials, or card data. |
| `outcome` | string | no | On complete/error: brief result description. |
| `duration_ms` | int | no | Elapsed time from start to this event. |
| `metadata` | dict | no | Any additional structured data worth recording. |

## Methodology

1. **Sanitize before logging.** Never record actual secrets, API keys, card numbers, or any value from a context file. Log summaries only: `"merchant: Namecheap, amount: $12.99"` not the card pan.

2. **Write to `skill_invocations` table** in Supabase via REST POST. If the table doesn't exist yet, the write fails silently — telemetry must never break the calling skill.

3. **Fail gracefully.** If Supabase is unreachable, log to a local append-only file at `/sessions/.../ASK/telemetry.jsonl` as fallback. If that also fails, drop the event silently. Telemetry is observability, not required infrastructure.

4. **Correlation ID.** The `session_id` field links a `start` event to its corresponding `complete` or `error` event, enabling duration calculation and success rate reporting even when events are recorded separately.

## Implementation

```python
import urllib.request, json, time
from datetime import datetime, timezone

SUPABASE_URL = "https://yyjvctgyhubscuapkpqq.supabase.co"
SUPABASE_KEY = "<SUPABASE_SECRET_KEY from context/gfs-env.md>"

def ask_log(skill: str, event: str, session_id: str = None,
            inputs_summary: str = None, outcome: str = None,
            duration_ms: int = None, metadata: dict = None) -> dict:
    record = {
        "skill": skill,
        "event": event,
        "session_id": session_id,
        "inputs_summary": inputs_summary,
        "outcome": outcome,
        "duration_ms": duration_ms,
        "metadata": metadata or {},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    # Try Supabase
    try:
        data = json.dumps(record).encode()
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/skill_invocations",
            data=data,
            method="POST",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            }
        )
        urllib.request.urlopen(req, timeout=3)
        return {"status": "logged", "destination": "supabase"}
    except Exception:
        pass
    # Fallback: local JSONL
    try:
        with open("/tmp/ask_telemetry.jsonl", "a") as f:
            f.write(json.dumps(record) + "\n")
        return {"status": "logged", "destination": "local_fallback"}
    except Exception:
        return {"status": "dropped"}
```

## Pattern for Skills That Adopt Telemetry

```python
import time, uuid

def my_skill_implementation(inputs):
    session_id = str(uuid.uuid4())[:8]
    start_ms = int(time.time() * 1000)

    ask_log("gfs/purchase", "start", session_id=session_id,
            inputs_summary=f"merchant: {inputs['merchant']}, amount: ${inputs['amount']/100:.2f}")
    try:
        result = do_the_work(inputs)
        ask_log("gfs/purchase", "complete", session_id=session_id,
                outcome=f"card created: ••••{result['last_four']}",
                duration_ms=int(time.time() * 1000) - start_ms)
        return result
    except Exception as e:
        ask_log("gfs/purchase", "error", session_id=session_id,
                outcome=str(e)[:200],
                duration_ms=int(time.time() * 1000) - start_ms)
        raise
```

## Outputs

```json
{"status": "logged", "destination": "supabase"}
```
or
```json
{"status": "logged", "destination": "local_fallback"}
```
or
```json
{"status": "dropped"}
```

Callers should not branch on this output — telemetry results never affect skill execution paths.

## What Telemetry Enables

Once `skill_invocations` accumulates data:
- **Usage ranking:** Which skills are invoked most? Prioritize their maintenance.
- **Failure rate per skill:** Which skills fail most often? Tighten their contracts.
- **Duration baselines:** How long should `gfs/content-video` take? Alert if it exceeds 2x baseline.
- **Composition patterns:** Which skills always get called together? Consider a composed skill.
- **Dead skills:** Skills with zero invocations in 30 days are candidates for deprecation.

This is the feedback loop that makes the library self-improving.
