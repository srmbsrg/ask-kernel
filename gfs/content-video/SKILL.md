---
name: content-video
description: Generate a video using the Tesa HeyGen avatar and ElevenLabs voice — write script via LLM, submit to HeyGen, poll until render complete, notify Scott with the download URL. Use for YouTube content, reels, announcements, or any video output from the GFS platform.
version: 1.0.0
tier: gfs
dependencies:
  - context/gfs-env.md
  - foundation/telegram-notify
---

# Content Video

## When to invoke

Any time a video needs to be generated autonomously. This skill handles the full pipeline: script → HeyGen render → notification. It is async-by-design — submit and poll, never block the calling context waiting for render.

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `topic` | string | yes | What the video is about. One clear sentence. |
| `style` | string | no | `"blazer"` (professional, YouTube) or `"leather"` (casual, social). Default: `"blazer"`. |
| `format` | string | no | `"youtube"` (16:9 1920x1080) or `"reel"` (9:16 1080x1920). Default: `"youtube"`. |
| `script_hint` | string | no | Tone, key points, or talking points to include in the script. |
| `script_override` | string | no | Skip LLM generation and use this exact script. Max 4,900 chars. |
| `notify_on_complete` | bool | no | Default: `true`. Telegram Scott with URL when render finishes. |

## Methodology

**Phase 1 — Script Generation** (skip if `script_override` provided)

Use OpenRouter (`anthropic/claude-sonnet-4-5`) to generate the script. The prompt should instruct the model to:
- Write in Tesa's voice: confident, warm, knowledgeable, never corporate
- Keep it under 4,900 characters (HeyGen limit per clip)
- Open with a hook, close with a clear call to action
- No visual cues, camera directions, or stage notes — this is audio-only input to HeyGen

**Phase 2 — HeyGen Submission**

POST to `/v2/video/generate` with the confirmed avatar ID and voice ID for the selected style. Return the `video_id` immediately — do not wait in the same process.

Avatar IDs (confirmed, do not guess):
- Blazer Tesa: `66ff11e0020f48b58e241b7cc9a46633`
- Leather Tesa: `0d7e57c1b398429cabed48a010c8e030`

HeyGen voice: `4e8ddc9a248047e6b1d39edde0e09ac5`

**Phase 3 — Async Polling** (sub-agent pattern)

Hand the `video_id` to a sub-process or scheduled poll. Every 60 seconds, GET `/v1/video_status.get?video_id={id}`. Terminal states: `completed` (has `video_url`), `failed`. On completion, invoke `foundation/telegram-notify` with the URL.

Do not block the calling thread during render — HeyGen renders take 5-20 minutes depending on script length.

## Implementation

```python
import urllib.request, json

HEYGEN_API_KEY = "<from env>"
OPENROUTER_API_KEY = "<from env>"
AVATARS = {
    "blazer":  "66ff11e0020f48b58e241b7cc9a46633",
    "leather": "0d7e57c1b398429cabed48a010c8e030"
}
HEYGEN_VOICE = "4e8ddc9a248047e6b1d39edde0e09ac5"
DIMENSIONS = {
    "youtube": {"width": 1920, "height": 1080},
    "reel":    {"width": 1080, "height": 1920}
}

def generate_script(topic: str, hint: str = "") -> str:
    prompt = f"""Write a video script for Tesa, the AI voice of Ghost Foundry Syndicate.
Topic: {topic}
{f"Guidance: {hint}" if hint else ""}
Voice: confident, warm, direct. Never corporate. First person.
Length: under 4,800 characters. Open with a hook. Close with a CTA.
Output the script only — no stage directions, no camera notes."""
    data = json.dumps({"model": "anthropic/claude-sonnet-4-5",
        "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
        data=data, headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]

def submit_heygen(script: str, avatar_id: str, format: str) -> str:
    body = {"video_inputs": [{"character": {"type": "talking_photo",
            "talking_photo_id": avatar_id},
        "voice": {"type": "text", "voice_id": HEYGEN_VOICE,
            "input_text": script[:4900]}}],
        "dimension": DIMENSIONS[format]}
    data = json.dumps(body).encode()
    req = urllib.request.Request("https://api.heygen.com/v2/video/generate",
        data=data, headers={"X-Api-Key": HEYGEN_API_KEY,
        "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["data"]["video_id"]

def check_status(video_id: str) -> dict:
    req = urllib.request.Request(
        f"https://api.heygen.com/v1/video_status.get?video_id={video_id}",
        headers={"X-Api-Key": HEYGEN_API_KEY})
    with urllib.request.urlopen(req) as r:
        d = json.loads(r.read())["data"]
        return {"status": d["status"], "url": d.get("video_url")}
```

## Outputs

**Immediate return (Phase 2 complete):**
```json
{"status": "submitted", "video_id": "abc123xyz", "script_preview": "Welcome to Ghost Foundry..."}
```

**On completion (Telegram notification):**
```
*Video Ready*
Topic: `The ASK Framework`
Style: Blazer Tesa | YouTube
Render time: 14m 32s
URL: https://resource.heygen.com/video/abc123.mp4
```

## Notes

- ElevenLabs voice (`XEQBC9sleaE3f5ff82UR`) is available as an alternative for audio-only output or custom integrations. HeyGen's own TTS (`HEYGEN_VOICE`) is used for the lip-sync avatar render.
- The `[CREATE_VIDEO: {...}]` action tag in the Tes chat route (`app/api/tes-chat/route.ts`) invokes this skill automatically when Tesa decides video content is appropriate.
- Render failures are rare but should trigger a Telegram alert with the video_id so a retry can be initiated.
