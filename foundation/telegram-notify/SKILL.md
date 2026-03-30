---
name: telegram-notify
description: Send a Telegram message to Scott or any registered contact via @tes_BSG_bot. Use for deployment confirmations, purchase approvals, error alerts, contact introductions, or any time an autonomous action needs to surface a result or request human input.
version: 1.0.0
tier: foundation
dependencies:
  - context/gfs-env.md
---

# Telegram Notify

## When to invoke

Any time an autonomous process needs to communicate with a human. This is the primary output channel for GFS and DF. Use it for:
- Confirming a successful deploy
- Requesting Scott's approval for over-limit purchases
- Alerting on errors that require human intervention
- Introducing new contacts (auto-detect pattern from Telegram webhook)
- Sending video generation completion URLs

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | yes | Message body. Markdown supported (bold `*text*`, code `` `text` ``). |
| `chat_id` | string/int | no | Default: Scott's chat ID (`6735511617`). Override for other registered contacts. |
| `parse_mode` | string | no | Default: `"Markdown"`. Use `"HTML"` if message contains HTML tags. |

## Methodology

1. **Load bot token** from `context/gfs-env.md`. Token is the @tes_BSG_bot credential.

2. **Format the message** before sending:
   - Keep it scannable — lead with the most important information
   - Use Markdown for structure: `*bold*` for labels, `` `code` `` for IDs and URLs
   - For approval requests, state the action clearly and ask an explicit yes/no question
   - Max length: 4,096 characters. If longer, split into multiple messages.

3. **Send** via a single POST to the Telegram Bot API.

4. **On failure:** Log the error. Do not retry more than once — if Telegram is down, the message is lost. Surface the failure to the calling skill so it can decide whether to halt.

5. **For new contact detection:** When the webhook receives a message from an unknown chat_id (not Scott's), send an intro from Tesa to the new contact AND ping Scott with the contact's details. Both sends use this same skill.

## Implementation

```python
import urllib.request, json

BOT_TOKEN = "<from context/gfs-env.md>"
SCOTT_CHAT_ID = 6735511617

def telegram_send(message: str, chat_id: int = SCOTT_CHAT_ID, parse_mode: str = "Markdown"):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = json.dumps({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode
    }).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read())
            return {"status": "sent", "message_id": result["result"]["message_id"]}
    except urllib.error.HTTPError as e:
        return {"status": "error", "detail": e.read().decode()}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
```

## Message Templates

**Deploy confirmation:**
```
*GFS Deploy Complete*
Status: `READY`
URL: `gfs-deploy-xyz.vercel.app`
Files pushed: 3
Time: 2m 14s
```

**Purchase approval request (over limit):**
```
*Purchase Approval Needed*
Merchant: `Adobe Creative Cloud`
Amount: `$54.99`
Category: `software`
Limit: `$100.00`
Reason: Monthly subscription renewal

Reply YES to approve or NO to decline.
```

**Error alert:**
```
*GFS Error — Action Required*
Skill: `gfs/tes-deploy`
Step: `vercel-deploy`
Error: `Build timeout after 300s`
Deploy ID: `dpl_abc123`
```

**New contact intro (to Scott):**
```
*New Contact on @tes_BSG_bot*
Name: `Regina`
Username: `@reginaxyz`
Chat ID: `987654321`
Message: "Hey, Scott said to reach out"
```

## Outputs

```json
{"status": "sent", "message_id": 12345}
```

or

```json
{"status": "error", "detail": "Bad Request: chat not found"}
```
