# GFS Environment Context

Reference file. Not invocable. Loaded by other ASK skills that need GFS credentials and configuration.
All secrets live in Vercel (production env vars) or the local `.env` file. Never hardcode values into skills.

> **Note:** This file shows the structure and variable names used by GFS skills.
> Actual values are stored in Vercel environment variables or the team's `.env` file.
> Never commit real credentials to this repository.

---

## GitHub

- **Username:** `your-github-username`
- **PAT location:** Team `.env` file as `GITHUB_PAT`
- **Primary repo:** `your-org/your-site-repo` — main platform repo
- **DF repo:** `your-org/dark-factory` — self-building code generator
- **Push method:** Python `urllib.request` only. Never use browser `fetch()` or `XHR` — both hang on `api.github.com`.

```python
# Canonical GitHub push pattern — see foundation/github-push/SKILL.md
PAT = os.environ["GITHUB_PAT"]
HEADERS = {
    "Authorization": f"token {PAT}",
    "Content-Type": "application/json",
    "User-Agent": "ASK/1.0"
}
```

---

## Vercel

- **Token:** `VERCEL_TOKEN` env var
- **Project ID:** `VERCEL_PROJECT_ID` env var
- **Project name:** your Vercel project name
- **Redeploy:** POST to `/v13/deployments` with `deploymentId` of latest READY deploy
- **Env upsert pattern:** DELETE existing by key ID first, then POST new value (Vercel PATCH is unreliable)

---

## Telegram

- **Bot:** `@your_telegram_bot`
- **Bot token:** `TELEGRAM_BOT_TOKEN` env var
- **Primary chat ID:** `TELEGRAM_CHAT_ID` env var (owner/admin chat)
- **Send endpoint:** `https://api.telegram.org/bot{TOKEN}/sendMessage`
- **Payload:** `{"chat_id": CHAT_ID, "text": MESSAGE, "parse_mode": "Markdown"}`

---

## Supabase (OpenBrain)

- **Project ref:** `SUPABASE_PROJECT_REF` env var
- **URL:** `SUPABASE_URL` env var
- **Secret key:** `SUPABASE_SECRET_KEY` env var
- **Vector table:** `thoughts` — columns: `id`, `content`, `embedding`, `metadata`, `created_at`
- **Search RPC:** `match_thoughts(query_embedding, match_threshold, match_count)`
- **Embedding model:** OpenAI `text-embedding-3-small` (1536 dimensions)

---

## HeyGen

- **API key:** `HEYGEN_API_KEY` env var
- **Video generate endpoint:** `POST https://api.heygen.com/v2/video/generate`
- **Status endpoint:** `GET https://api.heygen.com/v1/video_status.get?video_id={id}`
- **Avatar IDs:** `HEYGEN_AVATAR_BLAZER`, `HEYGEN_AVATAR_LEATHER` env vars
- **Voice ID:** `HEYGEN_VOICE_ID` env var
- **Dimensions:**
  - YouTube (16:9): `{"width": 1920, "height": 1080}`
  - Reel (9:16): `{"width": 1080, "height": 1920}`
- **Script limit:** 4,900 characters per clip

---

## ElevenLabs

- **API key:** `ELEVENLABS_API_KEY` env var
- **Voice clone ID:** `ELEVENLABS_VOICE_ID` env var
- **Model:** `eleven_multilingual_v2`
- **TTS endpoint:** `POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}`

---

## OpenRouter (LLM)

- **API key:** `OPENROUTER_API_KEY` env var
- **Recommended model:** `anthropic/claude-sonnet-4-5`
- **Endpoint:** `https://openrouter.ai/api/v1/chat/completions`

---

## Privacy.com (Autonomous Purchasing)

- **API key:** `PRIVACY_API_KEY` env var
- **Card creation endpoint:** `POST https://api.privacy.com/v1/card`
- **Card type:** `SINGLE_USE`
- **Spend limits by category (cents) — customize per your policy:**
  - software: 10,000 ($100)
  - infrastructure: 20,000 ($200)
  - domains: 5,000 ($50)
  - marketing: 7,500 ($75)
  - tools: 10,000 ($100)
  - other: 2,500 ($25)

---

## Stripe

- **Secret key:** `STRIPE_SECRET_KEY` env var
- **Publishable key:** `STRIPE_PUBLISHABLE_KEY` env var
