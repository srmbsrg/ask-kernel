---
name: github-push
description: Push one or more files to a GitHub repository using the GFS PAT. Use when any file needs to be created or updated in a GitHub repo — new routes, components, lib files, skill files, config changes, or schema updates. Always use this instead of git CLI or browser fetch, which hang on api.github.com.
version: 1.0.0
tier: foundation
dependencies:
  - context/gfs-env.md
---

# GitHub Push

## When to invoke

Any time a file needs to land in a GitHub repository. This is the only approved push mechanism for GFS and DF systems. The git CLI and browser XHR both fail silently or hang — this skill uses Python urllib which is reliable from any execution context.

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `files` | list | yes | Each entry: `{path, content, message}`. Path is relative to repo root. |
| `repo` | string | no | Default: `srmbsrg/ghostfoundry-syndicate`. Override for DF or other repos. |
| `branch` | string | no | Default: `main`. |

## Methodology

Think through this before executing:

1. **Load PAT** from `context/gfs-env.md`. Never prompt the user for it — it lives in the Tesa `.env` file at the path specified there.

2. **For each file**, execute a two-step operation:
   - GET the current SHA of that path. If the file doesn't exist, SHA is `None` — that's fine, it becomes a create.
   - PUT with base64-encoded content, the commit message, branch, and SHA if present.

3. **Order matters for dependent files.** If pushing a new route and its associated lib, push the lib first.

4. **Batch when possible** — multiple files in one invocation reduces round trips, but each file is still its own API call (GitHub's Contents API is file-level, not commit-level for this pattern).

5. **On failure:** Log which file failed and its HTTP status. Do not silently continue — a failed push means the deployment will use stale code.

6. **Never use `git` CLI** in this system. Never use `fetch()` or `XMLHttpRequest` from a browser context. Both hang indefinitely on `api.github.com`.

## Implementation

```python
import urllib.request, json, base64

def github_push(files: list, repo: str = "srmbsrg/ghostfoundry-syndicate", branch: str = "main", pat: str = None):
    """
    files: [{"path": "app/api/example/route.ts", "content": "...", "message": "feat: add example route"}]
    """
    headers = {
        "Authorization": f"token {pat}",
        "Content-Type": "application/json",
        "User-Agent": "GFS-ASK/1.0"
    }
    results = []
    for f in files:
        url = f"https://api.github.com/repos/{repo}/contents/{f['path']}"
        # Step 1: get SHA
        sha = None
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as r:
                sha = json.loads(r.read()).get("sha")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                results.append({"path": f["path"], "status": "error", "detail": f"GET failed: {e.code}"})
                continue
        # Step 2: push
        body = {
            "message": f["message"],
            "content": base64.b64encode(f["content"].encode()).decode(),
            "branch": branch
        }
        if sha:
            body["sha"] = sha
        req2 = urllib.request.Request(url, data=json.dumps(body).encode(), method="PUT", headers=headers)
        try:
            with urllib.request.urlopen(req2) as r:
                resp = json.loads(r.read())
                results.append({"path": f["path"], "status": "ok", "sha": resp["content"]["sha"]})
        except urllib.error.HTTPError as e:
            results.append({"path": f["path"], "status": "error", "detail": f"PUT failed: {e.code} {e.read().decode()}"})
    return results
```

## Outputs

Returns a list of results, one per file:

```json
[
  {"path": "app/api/example/route.ts", "status": "ok", "sha": "abc123"},
  {"path": "lib/example.ts", "status": "error", "detail": "PUT failed: 422 ..."}
]
```

Any `status: error` should be surfaced to the caller and halt dependent steps (e.g., don't trigger Vercel deploy if a push failed).

## Notes

- Max file size via Contents API: 1MB. Larger files require the Git Data API (separate skill if needed).
- Binary files: base64-encode the raw bytes, same pattern.
- Rate limit: 5,000 requests/hour with a PAT. Rarely a concern for our volumes.
