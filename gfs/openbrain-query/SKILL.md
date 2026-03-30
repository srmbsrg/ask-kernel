---
name: openbrain-query
description: Semantic search of the OpenBrain vector store to retrieve relevant memories, decisions, and context. Use at the start of any task where past knowledge might be relevant — project context, Scott's preferences, prior decisions, or integration details.
version: 1.0.0
tier: gfs
dependencies:
  - context/gfs-env.md
---

# OpenBrain Query

## When to invoke

At the beginning of tasks where prior context matters. This is how Tesa avoids repeating decisions that have already been made, and how she builds on prior work rather than starting from scratch each session. Examples:
- "What did we decide about X?" → query before answering
- Starting a deploy → query for recent deployment notes or known issues
- Generating a video → query for brand/voice guidance
- Evaluating a vendor → query for prior vendor decisions

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | yes | Natural language query. Write it the way you'd phrase a search: "Privacy.com purchasing setup" not "privacy". |
| `limit` | int | no | Default: 5. Max results to return. |
| `threshold` | float | no | Default: 0.5. Minimum similarity score (0-1). Lower = more results, less relevant. |

## Methodology

1. **Generate embedding** for the query using OpenAI `text-embedding-3-small`. Same model used at write time — consistency is critical for accurate similarity matching.

2. **Call `match_thoughts` RPC** on Supabase. This is a PostgreSQL function that computes cosine similarity between the query embedding and all stored thought embeddings, returning the top matches above the threshold.

3. **Fallback if RPC fails:** Call the REST API directly: `GET /rest/v1/thoughts?order=created_at.desc&limit={limit}`. This returns recent thoughts by time, not by relevance — still useful as a fallback.

4. **Return results with scores.** The caller decides what to do with them — don't filter further unless instructed.

5. **Empty results are valid.** Return an empty list, not an error. The system doesn't always have prior context on every topic, and that's fine.

## Implementation

```python
import urllib.request, json

OPENAI_API_KEY = "<from env>"
SUPABASE_URL = "https://yyjvctgyhubscuapkpqq.supabase.co"
SUPABASE_KEY = "<SUPABASE_SECRET_KEY from env>"

def get_embedding(text: str) -> list:
    data = json.dumps({"input": text, "model": "text-embedding-3-small"}).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/embeddings",
        data=data,
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["data"][0]["embedding"]

def openbrain_query(query: str, limit: int = 5, threshold: float = 0.5) -> list:
    try:
        embedding = get_embedding(query)
        # Try RPC first
        data = json.dumps({
            "query_embedding": embedding,
            "match_threshold": threshold,
            "match_count": limit
        }).encode()
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/rpc/match_thoughts",
            data=data,
            method="POST",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json"
            }
        )
        with urllib.request.urlopen(req) as r:
            results = json.loads(r.read())
            return [{"content": r["content"], "score": r["similarity"], "metadata": r.get("metadata", {})} for r in results]
    except Exception:
        # Fallback: recent thoughts by time
        try:
            req2 = urllib.request.Request(
                f"{SUPABASE_URL}/rest/v1/thoughts?order=created_at.desc&limit={limit}",
                headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
            )
            with urllib.request.urlopen(req2) as r:
                results = json.loads(r.read())
                return [{"content": r["content"], "score": None, "metadata": r.get("metadata", {})} for r in results]
        except Exception:
            return []
```

## Outputs

```json
[
  {
    "content": "We chose Privacy.com over Stripe Issuing for autonomous purchasing because Privacy.com offers single-use cards with per-merchant locking, reducing exposure on each transaction.",
    "score": 0.91,
    "metadata": {"type": "decision", "topic": "purchasing"}
  },
  {
    "content": "Privacy.com API key is pending — awaiting transaction confirmation before provisioning.",
    "score": 0.78,
    "metadata": {"type": "status", "topic": "purchasing"}
  }
]
```

Empty result: `[]` — not an error.

## Notes

- The `match_thoughts` RPC must exist in the Supabase database. It is created as part of the `prisma db push` + OpenBrain setup. If querying fails with "function not found", the RPC needs to be created manually.
- Score of `null` means the result came from the time-based fallback, not semantic search.
- Query specificity matters: "what avatar ID does HeyGen use for the blazer video" will score better than "heygen".
