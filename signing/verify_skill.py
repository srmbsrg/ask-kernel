#!/usr/bin/env python3
"""
verify_skill.py — A.S.K Skill Signature Verifier
==================================================
Verifies that a SKILL.md file has a valid cryptographic signature from a
trusted signer listed in trusted_signers.json.

Verification steps:
    1. Load the .sig sidecar file next to SKILL.md
    2. Check the signer is in trusted_signers.json
    3. Check the key fingerprint is NOT in revoked_keys.json
    4. Strip the ASK-SIGNATURE comment from SKILL.md to get canonical content
    5. Verify the RSA-PSS signature using the signer's registered public key
    6. Confirm the inline comment signature matches the sidecar signature

Exit codes:
    0 — Signature valid
    1 — Signature invalid or missing (with reason printed to stderr)

Usage:
    python signing/verify_skill.py --skill foundation/github-push/SKILL.md
    python signing/verify_skill.py --skill foundation/github-push/SKILL.md --registry signing/trusted_signers.json

Requires: pip install cryptography
"""

import argparse
import base64
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.exceptions import InvalidSignature
except ImportError:
    print("Error: 'cryptography' library not installed. Run: pip install cryptography", file=sys.stderr)
    sys.exit(1)

SIGNATURE_COMMENT_PATTERN = re.compile(
    r"\n?<!-- ASK-SIGNATURE: ([A-Za-z0-9+/=]+) -->\n?", re.MULTILINE
)

# Default paths relative to the repo root (where this script lives).
SIGNING_DIR = Path(__file__).parent
DEFAULT_REGISTRY = SIGNING_DIR / "trusted_signers.json"
DEFAULT_REVOKED = SIGNING_DIR / "revoked_keys.json"


def load_registry(registry_path: Path) -> dict:
    if not registry_path.exists():
        print(f"Error: Trusted signers registry not found: {registry_path}", file=sys.stderr)
        sys.exit(1)
    with registry_path.open(encoding="utf-8") as f:
        return json.load(f)


def load_revoked(revoked_path: Path) -> list:
    if not revoked_path.exists():
        return []
    with revoked_path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data.get("revoked_fingerprints", [])


def compute_fingerprint(public_key) -> str:
    """SHA-256 of DER-encoded public key, hex, first 16 chars."""
    der_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(der_bytes).hexdigest()[:16]


def verify_skill(
    skill_path: Path,
    registry_path: Path = DEFAULT_REGISTRY,
    revoked_path: Path = DEFAULT_REVOKED,
    quiet: bool = False,
) -> bool:
    """
    Verify a skill's signature. Returns True if valid, False otherwise.
    Prints status to stdout (or stderr on failure) unless quiet=True.
    """

    def fail(msg: str) -> bool:
        if not quiet:
            print(f"INVALID: {msg}", file=sys.stderr)
        return False

    def ok(msg: str) -> bool:
        if not quiet:
            print(f"OK: {msg}")
        return True

    if not skill_path.exists():
        return fail(f"SKILL.md not found: {skill_path}")

    # Step 1: Load sidecar .sig file.
    sidecar_path = skill_path.parent / "SKILL.md.sig"
    if not sidecar_path.exists():
        return fail(f"No .sig sidecar found at {sidecar_path}. Skill is unsigned.")

    try:
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return fail(f"Malformed .sig file: {e}")

    required_fields = {"signer", "algorithm", "pubkey_fingerprint", "signature", "signed_at"}
    missing = required_fields - sidecar.keys()
    if missing:
        return fail(f"Sidecar missing fields: {missing}")

    signer_name = sidecar["signer"]
    fingerprint = sidecar["pubkey_fingerprint"]
    signature_b64 = sidecar["signature"]
    algorithm = sidecar["algorithm"]

    # We only support RSA-PSS-SHA256 for now.
    if algorithm != "RSA-PSS-SHA256":
        return fail(f"Unsupported signing algorithm: {algorithm}. Expected RSA-PSS-SHA256.")

    # Step 2: Check signer is in the trusted registry.
    registry = load_registry(registry_path)
    if signer_name not in registry:
        return fail(f"Signer '{signer_name}' is not in trusted_signers.json.")

    signer_entry = registry[signer_name]
    pubkey_pem = signer_entry.get("pubkey", "")
    if not pubkey_pem:
        return fail(f"No public key found for signer '{signer_name}' in registry.")

    # Step 3: Check the fingerprint is not revoked.
    revoked = load_revoked(revoked_path)
    if fingerprint in revoked:
        return fail(
            f"Key fingerprint '{fingerprint}' for signer '{signer_name}' has been revoked. "
            "This skill was signed with a compromised key and must be re-signed."
        )

    # Load the registered public key.
    try:
        public_key = serialization.load_pem_public_key(pubkey_pem.encode("utf-8"))
    except Exception as e:
        return fail(f"Could not load public key for '{signer_name}': {e}")

    # Verify the registered key's fingerprint matches what the sidecar claims.
    actual_fingerprint = compute_fingerprint(public_key)
    if actual_fingerprint != fingerprint:
        return fail(
            f"Fingerprint mismatch: sidecar claims '{fingerprint}', "
            f"but registered key for '{signer_name}' has fingerprint '{actual_fingerprint}'."
        )

    # Step 4: Reconstruct the canonical content (strip signature comment).
    raw_content = skill_path.read_text(encoding="utf-8")
    canonical_content = SIGNATURE_COMMENT_PATTERN.sub("", raw_content)

    # Step 5: Verify the RSA-PSS signature.
    try:
        signature_bytes = base64.b64decode(signature_b64)
    except Exception as e:
        return fail(f"Could not decode signature from sidecar: {e}")

    try:
        public_key.verify(
            signature_bytes,
            canonical_content.encode("utf-8"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
    except InvalidSignature:
        return fail(
            "Signature verification failed. The skill content has been tampered with, "
            "or the signature was produced by a different key."
        )
    except Exception as e:
        return fail(f"Unexpected error during signature verification: {e}")

    # Step 6: Confirm the inline comment matches the sidecar signature.
    # This catches cases where someone updated the sidecar but not the file, or vice versa.
    inline_match = SIGNATURE_COMMENT_PATTERN.search(raw_content)
    if not inline_match:
        return fail(
            "No ASK-SIGNATURE comment found in SKILL.md. "
            "The sidecar exists but the inline signature is missing — file may be corrupted."
        )
    if inline_match.group(1) != signature_b64:
        return fail(
            "Inline signature comment does not match sidecar signature. "
            "The .sig file and SKILL.md are out of sync."
        )

    return ok(
        f"{skill_path} — signed by '{signer_name}' "
        f"(fingerprint: {fingerprint}, signed: {sidecar['signed_at']})"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Verify the cryptographic signature of an A.S.K SKILL.md file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--skill",
        required=True,
        help="Path to the SKILL.md file to verify.",
    )
    parser.add_argument(
        "--registry",
        default=str(DEFAULT_REGISTRY),
        help=f"Path to trusted_signers.json. Default: {DEFAULT_REGISTRY}",
    )
    parser.add_argument(
        "--revoked",
        default=str(DEFAULT_REVOKED),
        help=f"Path to revoked_keys.json. Default: {DEFAULT_REVOKED}",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output. Use exit code to determine result.",
    )
    args = parser.parse_args()

    valid = verify_skill(
        Path(args.skill),
        Path(args.registry),
        Path(args.revoked),
        quiet=args.quiet,
    )
    sys.exit(0 if valid else 1)


if __name__ == "__main__":
    main()
