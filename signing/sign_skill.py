#!/usr/bin/env python3
"""
sign_skill.py — A.S.K Skill Signer
=====================================
Signs a SKILL.md file using an RSA private key (RSA-PSS / SHA-256).

The signature is embedded in the SKILL.md file as a comment at the bottom:

    <!-- ASK-SIGNATURE: <base64-encoded signature> -->

A sidecar JSON file is also written alongside the SKILL.md:

    <skill-dir>/SKILL.md.sig

The sidecar contains:
    {
        "signer":            "foundry-familiars",
        "algorithm":         "RSA-PSS-SHA256",
        "pubkey_fingerprint": "a1b2c3d4e5f60718",
        "signature":         "<base64>",
        "signed_at":         "2026-03-31T00:00:00Z"
    }

What is signed:
    The entire SKILL.md content, with any existing ASK-SIGNATURE comment
    stripped first. This makes re-signing idempotent — signing an already-
    signed file produces a new valid signature over the same canonical content.

Usage:
    python signing/sign_skill.py \\
        --skill foundation/github-push/SKILL.md \\
        --key ~/.ask/keys/foundry-familiars/private.pem \\
        --signer foundry-familiars

Requires: pip install cryptography
"""

import argparse
import base64
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
except ImportError:
    print("Error: 'cryptography' library not installed. Run: pip install cryptography")
    sys.exit(1)

# The regex pattern that matches an existing ASK-SIGNATURE comment.
# We strip this before computing the signature so re-signing is idempotent.
SIGNATURE_COMMENT_PATTERN = re.compile(
    r"\n?<!-- ASK-SIGNATURE: [A-Za-z0-9+/=]+ -->\n?", re.MULTILINE
)


def strip_signature_comment(content: str) -> str:
    """Remove any existing ASK-SIGNATURE comment from skill content."""
    return SIGNATURE_COMMENT_PATTERN.sub("", content)


def compute_fingerprint(public_key) -> str:
    """SHA-256 of DER-encoded public key, hex, first 16 chars."""
    der_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(der_bytes).hexdigest()[:16]


def sign_skill(skill_path: Path, key_path: Path, signer: str) -> None:
    if not skill_path.exists():
        print(f"Error: SKILL.md not found: {skill_path}")
        sys.exit(1)

    if not key_path.exists():
        print(f"Error: Private key not found: {key_path}")
        sys.exit(1)

    # Load and validate the private key.
    key_bytes = key_path.read_bytes()
    try:
        private_key = serialization.load_pem_private_key(key_bytes, password=None)
    except Exception as e:
        print(f"Error: Could not load private key: {e}")
        sys.exit(1)

    public_key = private_key.public_key()
    fingerprint = compute_fingerprint(public_key)

    # Read skill content and strip any previous signature comment.
    raw_content = skill_path.read_text(encoding="utf-8")
    canonical_content = strip_signature_comment(raw_content)

    # Sign the canonical content bytes.
    # RSA-PSS is the modern, secure padding scheme. MGF1 with SHA-256 and
    # salt_length=PSS.MAX_LENGTH gives maximum security margin.
    signature_bytes = private_key.sign(
        canonical_content.encode("utf-8"),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )
    signature_b64 = base64.b64encode(signature_bytes).decode("ascii")

    # Embed the signature as a comment at the end of the SKILL.md.
    # Trailing newline is intentional — keeps git diffs clean.
    signed_content = canonical_content.rstrip("\n") + f"\n\n<!-- ASK-SIGNATURE: {signature_b64} -->\n"
    skill_path.write_text(signed_content, encoding="utf-8")

    # Write the sidecar .sig file with full metadata.
    signed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sidecar = {
        "signer": signer,
        "algorithm": "RSA-PSS-SHA256",
        "pubkey_fingerprint": fingerprint,
        "signature": signature_b64,
        "signed_at": signed_at,
    }
    sidecar_path = skill_path.parent / "SKILL.md.sig"
    sidecar_path.write_text(json.dumps(sidecar, indent=2) + "\n", encoding="utf-8")

    print(f"Signed: {skill_path}")
    print(f"  Signer:      {signer}")
    print(f"  Fingerprint: {fingerprint}")
    print(f"  Algorithm:   RSA-PSS-SHA256")
    print(f"  Signed at:   {signed_at}")
    print(f"  Sidecar:     {sidecar_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Sign an A.S.K SKILL.md file with an RSA private key.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--skill",
        required=True,
        help="Path to the SKILL.md file to sign (e.g., foundation/github-push/SKILL.md).",
    )
    parser.add_argument(
        "--key",
        required=True,
        help="Path to the PEM-encoded RSA private key.",
    )
    parser.add_argument(
        "--signer",
        required=True,
        help="Signer entity name (must match an entry in trusted_signers.json).",
    )
    args = parser.parse_args()
    sign_skill(Path(args.skill), Path(args.key), args.signer)


if __name__ == "__main__":
    main()
