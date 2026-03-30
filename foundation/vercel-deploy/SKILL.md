---
name: vercel-deploy
description: Push environment variables to Vercel and/or trigger a production redeployment of the GFS platform. Use after any code push that requires live env changes, or to redeploy after a GitHub push without env changes. Always verify READY state before returning.
version: 1.0.0
tier: foundation
dependencies:
  - context/gfs-env.md
---

# Vercel Deploy

## When to invoke

After `github-push` completes successfully, or any time environment variables need to be updated in the live GFS deployment. Never trigger a deploy if the preceding GitHub push had any errors — a broken deploy is worse than a stale one.

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `env_vars` | dict | no | `{"KEY": "value"}` pairs to upsert before redeploying. Omit if only triggering redeploy. |
| `redeploy` | bool | no | Default: `true`. Set to `false` if only updating env vars without redeploying. |
| `wait_for_ready` | bool | no | Default: `true`. Poll until READY or ERROR. |
| `timeout_seconds` | int | no | Default: 300. Max wait for READY state. |

## Methodology

1. **Load token and project ID** from `context/gfs-env.md`. Both are required. Never prompt the user.

2. **Upsert env vars** (if provided):
   - GET all current env vars for the project
   - For each key to upsert: if it exists, DELETE the old entry by its ID first
   - POST the new value with `type: "encrypted"` and `target: ["production", "preview"]`
   - Reason for delete-then-create: Vercel's PATCH on env vars is unreliable; the upsert pattern is the only safe approach we've confirmed.

3. **Trigger redeployment** (if `redeploy: true`):
   - POST to `/v13/deployments` with the `deploymentId` of the latest known READY deployment
   - This is a re-promotion, not a fresh build from source — it's fast (~2-3 minutes)
   - The latest known deployment ID is in `context/gfs-env.md`. If that deploy is no longer the latest, GET `/v6/deployments?projectId=...&limit=1` to find the current one.

4. **Poll for READY** (if `wait_for_ready: true`):
   - GET `/v13/deployments/{new_deploy_id}` every 15 seconds
   - Valid terminal states: `READY` (success), `ERROR` (fail), `CANCELED`
   - Return the deploy URL on READY; raise error with logs URL on ERROR

5. **Never** trigger a deploy while another deploy is in `BUILDING` state — Vercel will queue it but it wastes time. Check first.

## Implementation

```python
import urllib.request, json, time

TOKEN = "<from context/gfs-env.md>"
PROJECT_ID = "prj_VEEPqkog6qhB2sewuaHzR3QRgeWz"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

def upsert_env_var(key: str, value: str):
    # Get current envs
    req = urllib.request.Request(f"https://api.vercel.com/v10/projects/{PROJECT_ID}/env", headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        envs = json.loads(r.read()).get("envs", [])
    # Delete if exists
    for e in envs:
        if e["key"] == key:
            del_req = urllib.request.Request(
                f"https://api.vercel.com/v10/projects/{PROJECT_ID}/env/{e['id']}",
                method="DELETE", headers=HEADERS
            )
            urllib.request.urlopen(del_req)
    # Create new
    data = json.dumps({"key": key, "value": value, "type": "encrypted", "target": ["production", "preview"]}).encode()
    req2 = urllib.request.Request(f"https://api.vercel.com/v10/projects/{PROJECT_ID}/env", data=data, method="POST", headers=HEADERS)
    urllib.request.urlopen(req2)

def get_latest_deploy_id():
    req = urllib.request.Request(
        f"https://api.vercel.com/v6/deployments?projectId={PROJECT_ID}&limit=1",
        headers=HEADERS
    )
    with urllib.request.urlopen(req) as r:
        deps = json.loads(r.read()).get("deployments", [])
        return deps[0]["uid"] if deps else None

def trigger_redeploy(source_deploy_id: str):
    data = json.dumps({"deploymentId": source_deploy_id, "name": "gfs-deploy", "target": "production"}).encode()
    req = urllib.request.Request("https://api.vercel.com/v13/deployments", data=data, method="POST", headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["id"]

def poll_ready(deploy_id: str, timeout: int = 300):
    start = time.time()
    while time.time() - start < timeout:
        req = urllib.request.Request(f"https://api.vercel.com/v13/deployments/{deploy_id}", headers=HEADERS)
        with urllib.request.urlopen(req) as r:
            d = json.loads(r.read())
            state = d.get("status") or d.get("readyState")
            if state == "READY":
                return {"status": "ready", "url": d.get("url")}
            if state in ("ERROR", "CANCELED"):
                return {"status": state.lower(), "deploy_id": deploy_id}
        time.sleep(15)
    return {"status": "timeout", "deploy_id": deploy_id}
```

## Outputs

```json
{
  "env_updates": ["STRIPE_SECRET_KEY", "HEYGEN_API_KEY"],
  "deploy_id": "dpl_abc123",
  "status": "ready",
  "url": "gfs-deploy-xyz.vercel.app"
}
```

On error: `{"status": "error", "detail": "..."}` — caller must handle and notify Scott via `foundation/telegram-notify`.

## Notes

- Vercel's free tier has no deploy concurrency limit but does limit build minutes — the redeploy pattern (re-promote vs. rebuild) is preferred because it skips the build step.
- Environment variable changes take effect on the NEXT deploy. If you update env vars, you must also redeploy.
- `development` environment vars are not fetched by `vercel env pull` in this system — always use `production` target.
