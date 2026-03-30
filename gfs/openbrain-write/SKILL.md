---
name: openbrain-write
description: Save a thought, memory, observation, or decision to the OpenBrain vector store. Use when capturing context that should persist across sessions — new facts about the business, project decisions, Scott's preferences, or anything that would be useful to recall in future conversations.
version: 1.0.0
tier: gfs
dependencies:
  - context/gfs-env.md
---

# OpenBrain Write

## When to invoke

When something is worth remembering across sessions. Ask: "Would a future version of Tesa benefit from knowing this?" If yes, write it. Examples:
- A decision was made (why we chose X over Y)
- Scott expressed a preference
- A new integration was added to the stack
- A project milestone was reached
- A vendor was evaluated and rejected

Do not write ephemeral task state — that belongs in todo lists, not OpenBrain. Write conclusions, not process.

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | string | yes | The thought to save. Write it as a complete, standalone statement — it must make sense when retrieved cold, without conversation context. |
| `metadata` | dict | no | Optional tags: `{"type": "decision", "topic": "infrastructure", "person": "scott"}` |

## Methodology

1. **Frame the content properly before embedding.** A thought retrieved in isolation must be self-contained. Bad: "We decided to go with that option." Good: "We chose Privacy.com over Stripe Issuing for autonomous purchasing because Privacy.com offers single-use cards with per-merchant locking, which reduces exposure on each transaction."

2. **Generate embedding** using OpenAI `text-embedding-3-small`. This is a 1536-dimension vector representing the semantic meaning of the content.

3. **Insert into Supabase** `thoughts` table with the content, embedding, and metadata.

4. **Graceful degradation:** If Supabase is unreachable (paused project, network issue), log the failure but do not crash the calling workflow. The thought is lost for this session — that is acceptable. Surface the failure so a retry can happen when the DB is restored.

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

def openbrain_write(content: str, metadata: dict = None) -> dict:
    try:
        embedding = get_embedding(content)
        row = {"content": content, "embedding": embedding, "metadata": metadata or {}}
        data = json.dumps(row).encode()
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/thoughts",
            data=data,
            method="POST",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            }
        )
        urllib.request.urlopen(req)
        return {"status": "saved", "content_preview": content[:80]}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
```

## Outputs

```json
{"status": "saved", "content_preview": "We chose Privacy.com over Stripe Issuing for autonomous..."}
```

or

```json
{"status": "error", "detail": "Connection refused — Supabase may be paused"}
```

## Notes

- The OpenBrain skill pair (`openbrain-write` + `openbrain-query`) is what gives Tesa persistent memory across sessions. Every significant decision or fact should flow through here.
- Supabase project ref: `yyjvctgyhubscuapkpqq`. If the project is paused, it must be restored at supabase.com before writes can succeed.
- Do not store secrets in OpenBrain. Content is queryable — treat it as a knowledge base, not a credential store.
