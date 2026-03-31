# A.S.K Skill Signing

Every skill in the A.S.K framework can be cryptographically signed by its author or organization. The executor can verify these signatures before running a skill, giving you provenance guarantees and tamper detection.

This is code signing for AI agent skills.

---

## Why Signing Matters

A skill is executable code that runs inside your agent's process. Without provenance guarantees, you have no way to know:

- **Who wrote it.** A skill claiming to be `foundation/github-push` could have been added or modified by anyone with write access to the repo — or by anyone who placed a malicious file in your local skill path.
- **Whether it's been tampered with.** A dependency injection attack, a compromised supply chain, or a simple typo in the wrong place could change a skill's behavior silently.
- **Whether it's been reviewed.** A signed skill is an explicit claim by its author that the skill is intentional and represents their work.

Skill signing doesn't replace code review or sandboxing. It complements them by creating an auditable chain of custody from author to executor. When the executor verifies a signature, it's asking: *did the entity I trust actually produce this exact skill content?*

This matters most in three scenarios:

1. **Untrusted skill sources.** You're pulling skills from a public registry or a third-party repository. Signing lets you enforce that only approved organizations' skills can run.
2. **Automated pipelines.** Dark Factory or other agents generate and deploy skills autonomously. Signing ensures that even autonomously-generated skills must be approved by a trusted key before execution.
3. **Audit and compliance.** Regulated environments need a record of who approved what capability and when. The `.sig` sidecar provides exactly that.

---

## How Signing Works

The signing system uses **RSA-PSS with SHA-256**, implemented via Python's `cryptography` library. RSA-PSS is the modern, secure padding scheme for RSA signatures; it provides strong security properties and is widely standardized.

### What gets signed

The signature covers the **canonical content** of the `SKILL.md` file — the entire file with any existing `<!-- ASK-SIGNATURE: ... -->` comment stripped out. This means:

- Re-signing an already-signed skill produces a new valid signature over the same content.
- The signature covers frontmatter, methodology, and implementation — any change to any part invalidates the signature.

### Where the signature lives

Two places:

1. **Inline comment** at the bottom of `SKILL.md`:
   ```
   <!-- ASK-SIGNATURE: <base64-encoded RSA-PSS signature> -->
   ```
   This travels with the skill everywhere the file goes.

2. **Sidecar file** `SKILL.md.sig` in the same directory:
   ```json
   {
     "signer": "foundry-familiars",
     "algorithm": "RSA-PSS-SHA256",
     "pubkey_fingerprint": "a1b2c3d4e5f60718",
     "signature": "<base64>",
     "signed_at": "2026-03-31T00:00:00Z"
   }
   ```
   The sidecar contains full metadata: who signed it, when, and with which key fingerprint.

The executor checks that the inline comment and sidecar agree — a discrepancy indicates the file and its metadata have gotten out of sync.

### Key fingerprint format

The fingerprint is the first 16 hex characters of the SHA-256 hash of the DER-encoded SubjectPublicKeyInfo of the public key. It's a short, human-readable identifier used to match keys in the trusted registry and the revocation list.

---

## Setup: Generating a Keypair

First, install the `cryptography` library:

```bash
pip install cryptography
```

Then generate a keypair for your signer entity:

```bash
python signing/keygen.py --signer your-org-name --out ~/.ask/keys/your-org-name
```

This creates:
- `~/.ask/keys/your-org-name/private.pem` — **never commit this**
- `~/.ask/keys/your-org-name/public.pem` — share this; add to `trusted_signers.json`

The command also prints the entry to add to `signing/trusted_signers.json`.

**Important:** Store private keys outside the repository. Add `*.pem` and `keys/` to `.gitignore` for any directory where you might store keys.

---

## Registering a Trusted Signer

Edit `signing/trusted_signers.json` to add the new signer's public key:

```json
{
  "your-org-name": {
    "description": "Your Organization — brief description of who this is",
    "pubkey": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgk...\n-----END PUBLIC KEY-----",
    "fingerprint": "a1b2c3d4e5f60718"
  }
}
```

The `pubkey` field is the PEM-encoded public key as a single string with `\n` for line breaks (or a multiline string, depending on your JSON serializer). The `fingerprint` is printed by `keygen.py` and serves as a quick reference.

Commit this change. Updating `trusted_signers.json` is how you authorize a new entity to sign skills for your deployment.

---

## Signing a Skill

Once you have a private key and your signer is registered:

```bash
python signing/sign_skill.py \
    --skill foundation/github-push/SKILL.md \
    --key ~/.ask/keys/foundry-familiars/private.pem \
    --signer foundry-familiars
```

This modifies `SKILL.md` in place (adds the signature comment) and writes `SKILL.md.sig`. Both files should be committed to the repository.

**Re-signing:** If you update a skill, re-run `sign_skill.py`. It strips the old signature before computing the new one, so re-signing is idempotent and produces a clean git diff.

---

## Verifying a Skill

To verify a skill manually:

```bash
python signing/verify_skill.py --skill foundation/github-push/SKILL.md
```

Exit code 0 = valid. Exit code 1 = invalid (reason printed to stderr).

To verify all skills in the repo:

```bash
find . -name "SKILL.md" | while read f; do
    python signing/verify_skill.py --skill "$f" || echo "FAILED: $f"
done
```

---

## Enforcing Signatures in the Executor

By default, the executor warns about unsigned skills but proceeds. This preserves backward compatibility for local development.

**To enforce verification**, use either:

```bash
# CLI flag (per-invocation):
python executor.py --verify-signatures foundation/github-push '{}'

# Environment variable (process-wide):
ASK_VERIFY_SIGNATURES=1 python executor.py foundation/github-push '{}'
```

When enforcement is on:
- Skills without a `.sig` sidecar are **rejected**.
- Skills with an invalid signature are **rejected**.
- Skills signed by a key not in `trusted_signers.json` are **rejected**.
- Skills signed by a revoked key fingerprint are **rejected**.
- Only valid, trusted, non-revoked signatures allow execution.

Set `ASK_VERIFY_SIGNATURES=1` in your production environment to make enforcement the default.

---

## Key Rotation

When you need to rotate a key (scheduled rotation, team member departure, key material loss):

1. **Generate a new keypair** with `keygen.py` under the same or a new signer name.
2. **Add the new public key** to `trusted_signers.json`.
3. **Re-sign all skills** that were signed by the old key using `sign_skill.py` with the new key.
4. **Revoke the old key** by adding its fingerprint to `revoked_keys.json`:
   ```json
   {
     "revoked_fingerprints": [
       {
         "fingerprint": "a1b2c3d4e5f60718",
         "signer": "foundry-familiars",
         "reason": "Scheduled annual rotation",
         "revoked_at": "2027-01-01T00:00:00Z"
       }
     ]
   }
   ```
5. Optionally, remove the old public key from `trusted_signers.json` (but keep the revocation entry — it's what stops any remaining old-signed skills from running).

**Why revoke if you've already re-signed everything?** Defense in depth. If a copy of the old-signed skill ends up in someone's local clone, the revocation list prevents it from running even if the signature is technically valid.

---

## Key Revocation (Emergency)

If a private key is compromised:

1. **Immediately add the key's fingerprint to `revoked_keys.json`** and push. This is the fastest path to protection — the executor checks the revocation list before verifying signatures.
2. Generate a new keypair and re-sign all affected skills.
3. Update `trusted_signers.json` with the new key (or remove the compromised entry after all skills are re-signed).

The revocation list is checked before the cryptographic verification step, so a revoked key cannot be used to pass verification even if the signature bytes are valid.

---

## Skill Inheritance and Fork Policy

When you fork an existing skill from another organization's registry:

**You must re-sign the forked skill under your own key.** The original signature only covers the original author's version. If you change even one character, the old signature is invalid.

To trace the lineage of a forked skill, add a `parent_skill` field to the SKILL.md frontmatter:

```yaml
---
name: my-github-push
description: "Customized GitHub push skill for MyOrg, forked from foundry-familiars/foundation/github-push v1.2.0"
version: 1.0.0
tier: foundation
parent_skill: "foundry-familiars/foundation/github-push@1.2.0"
dependencies: []
---
```

This is informational — the executor doesn't enforce parent lineage. But it lets auditors trace where a skill originated, and it creates a paper trail if a bug in the upstream skill needs to be hunted down across forks.

---

## Future: Signed Skill Manifests

The current system signs individual skill files. A natural extension is a **signed registry manifest** — a single file that lists all skills, their versions, and their individual signature fingerprints. This is analogous to how npm's `package-lock.json` or apt's `Release` file works.

With a signed manifest, you can:
- Verify the entire skill registry in one check.
- Detect if a skill was added or removed without authorization.
- Support offline verification without fetching individual `.sig` files.

This is tracked as a future enhancement. For now, per-skill `.sig` sidecars provide the core provenance guarantee.

---

## Quick Reference

| Task | Command |
|------|---------|
| Generate keypair | `python signing/keygen.py --signer <name> --out ~/.ask/keys/<name>` |
| Sign a skill | `python signing/sign_skill.py --skill <path>/SKILL.md --key <private.pem> --signer <name>` |
| Verify a skill | `python signing/verify_skill.py --skill <path>/SKILL.md` |
| Run with enforcement | `python executor.py --verify-signatures <skill-path> '{}'` |
| Run with env enforcement | `ASK_VERIFY_SIGNATURES=1 python executor.py <skill-path> '{}'` |
| Revoke a key | Add fingerprint to `signing/revoked_keys.json` and push |

---

*A.S.K Signing System — designed for the Foundry Familiars*
*Last updated: 2026-03-31*
