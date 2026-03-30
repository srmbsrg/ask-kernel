---
name: purchase
description: Autonomously purchase a product or service using a Privacy.com single-use virtual card within pre-approved per-category spend limits. Sends Scott a Telegram approval request if the amount exceeds the limit. Use when Tesa determines a purchase serves a business need and falls within authorized spend parameters.
version: 1.0.0
tier: gfs
dependencies:
  - context/gfs-env.md
  - foundation/telegram-notify
---

# Purchase

## When to invoke

When an autonomous purchase is appropriate — software subscriptions, domain renewals, API credits, infrastructure, or tools. This skill enforces spend limits and always notifies Scott. It does not make purchasing decisions; it executes decisions already made by the calling context.

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `merchant` | string | yes | Name of the merchant or service. |
| `amount` | int | yes | Amount in cents (e.g., 4999 = $49.99). |
| `category` | string | yes | One of: `software`, `infrastructure`, `domains`, `marketing`, `tools`, `other`. |
| `description` | string | yes | Why this purchase is being made. Stored in audit log and included in Telegram notification. |
| `merchant_url` | string | no | Merchant website. Used to lock the card to that merchant in Privacy.com. |

## Spend Limits (per transaction, in cents)

| Category | Limit |
|----------|-------|
| software | $100.00 |
| infrastructure | $200.00 |
| domains | $50.00 |
| marketing | $75.00 |
| tools | $100.00 |
| other | $25.00 |

## Methodology

**Step 1 — Limit check**

Compare `amount` against the category limit. If over limit: invoke `foundation/telegram-notify` with an approval request (see template below) and return `status: pending_approval`. Do not create a card. The calling context must stop and wait.

**Step 2 — Card creation** (if within limit)

POST to Privacy.com `/v1/card` with `type: SINGLE_USE`, spend limit set to `amount + 1` (1 cent buffer), and merchant URL if provided. A single-use card is destroyed after one transaction — zero residual exposure.

**Step 3 — Notify Scott**

Always send a Telegram notification after card creation, regardless of whether the purchase is complete yet. Include: merchant, amount, category, card last four, and description. This is an audit trail, not a request for approval.

**Step 4 — Return card details**

Return the card number, expiry, and CVV to the calling context for use in the actual transaction. These are single-use — they expire after one charge or 24 hours.

**Never:**
- Store card details in any log, file, or database
- Re-use a card after the transaction
- Create a card for a purchase that exceeds limits without Scott's explicit approval via Telegram

## Implementation

```python
import urllib.request, json

PRIVACY_API_KEY = "<from env PRIVACY_API_KEY>"

SPEND_LIMITS = {
    "software": 10000, "infrastructure": 20000, "domains": 5000,
    "marketing": 7500, "tools": 10000, "other": 2500
}

def create_virtual_card(merchant: str, amount: int, category: str, merchant_url: str = None) -> dict:
    limit = SPEND_LIMITS.get(category, 2500)
    if amount > limit:
        return {"status": "over_limit", "limit": limit, "requested": amount}

    body = {
        "type": "SINGLE_USE",
        "spend_limit": amount + 1,
        "spend_limit_duration": "TRANSACTION",
        "memo": f"{category}: {merchant}"
    }
    if merchant_url:
        body["merchant_merchant_url"] = merchant_url

    data = json.dumps(body).encode()
    req = urllib.request.Request(
        "https://api.privacy.com/v1/card",
        data=data,
        method="POST",
        headers={
            "Authorization": f"api-key {PRIVACY_API_KEY}",
            "Content-Type": "application/json"
        }
    )
    with urllib.request.urlopen(req) as r:
        card = json.loads(r.read())
        return {
            "status": "created",
            "card_token": card["token"],
            "last_four": card["last_four"],
            "pan": card["pan"],
            "cvv": card["cvv"],
            "exp_month": card["exp_month"],
            "exp_year": card["exp_year"]
        }
```

## Message Templates

**Approval request (over limit):**
```
*Purchase Approval Required*
Merchant: `Adobe Creative Cloud`
Amount: `$54.99` (limit: `$100.00 software`)
Category: `software`
Reason: Annual Creative Cloud subscription renewal

Reply YES to approve or NO to decline.
```

**Confirmation (within limit):**
```
*Purchase Card Created*
Merchant: `Namecheap`
Amount: `$12.99`
Category: `domains`
Card: `••••4821`
Reason: Renew foundrytech.io for 1 year
```

## Outputs

**Within limit:**
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

**Over limit:**
```json
{"status": "pending_approval", "limit": 10000, "requested": 15000}
```

## Notes

- Privacy.com API key is pending provisioning (`PRIVACY_API_KEY` not yet set in Vercel). Skill will fail gracefully until the key is provided.
- Monthly spend summary is available via GET to the GFS purchase API: `GET /api/gfs/purchase`.
- All card creation events are logged to the `PurchaseCard` Prisma model if DB is online.
