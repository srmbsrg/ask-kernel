#!/usr/bin/env python3
"""
keygen.py — A.S.K Skill Signing Key Generator
===============================================
Generates an RSA-2048 keypair for a new signer entity.

Usage:
    python keygen.py --signer foundry-familiars --out ./keys/

Outputs:
    {out}/private.pem  — Keep secret. Used by sign_skill.py to sign skills.
    {out}/public.pem   — Share publicly. Added to trusted_signers.json.

The public key fingerprint (first 16 hex chars of SHA-256 of DER-encoded key)
is printed to stdout so you can register it in trusted_signers.json.

Key storage advice:
    - Private keys should live outside the repo (e.g., ~/.ask/keys/{signer}/private.pem)
    - Never commit private.pem to version control
    - Add *.pem to .gitignore if storing keys near the repo

Requires: pip install cryptography
"""

import argparse
import hashlib
import sys
from pathlib import Path

try:
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
except ImportError:
    print("Error: 'cryptography' library not installed. Run: pip install cryptography")
    sys.exit(1)


def compute_fingerprint(public_key) -> str:
    """
    Compute a short fingerprint for a public key.

    Method: SHA-256 of the DER-encoded SubjectPublicKeyInfo, hex-encoded,
    first 16 characters. This is enough to uniquely identify a key in a
    small registry while remaining human-readable.
    """
    der_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    full_hash = hashlib.sha256(der_bytes).hexdigest()
    return full_hash[:16]


def generate_keypair(signer: str, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    private_key_path = output_dir / "private.pem"
    public_key_path = output_dir / "public.pem"

    # Warn if private key already exists — never silently overwrite.
    if private_key_path.exists():
        print(f"Warning: {private_key_path} already exists. Aborting to prevent overwrite.")
        print("Delete it manually if you intend to rotate keys.")
        sys.exit(1)

    # RSA-2048 is the minimum recommended key size for new keys.
    # We use 65537 as the public exponent — the standard choice.
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_key = private_key.public_key()

    # Write private key (PEM, unencrypted).
    # For production use, consider encrypting with a passphrase via
    # serialization.BestAvailableEncryption(b"passphrase").
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    private_key_path.write_bytes(private_pem)
    private_key_path.chmod(0o600)  # Owner read-only

    # Write public key (PEM).
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    public_key_path.write_bytes(public_pem)

    fingerprint = compute_fingerprint(public_key)

    print(f"\nKeypair generated for signer: {signer}")
    print(f"  Private key: {private_key_path}  (keep secret!)")
    print(f"  Public key:  {public_key_path}")
    print(f"  Fingerprint: {fingerprint}")
    print()
    print("Next step — add this entry to signing/trusted_signers.json:")
    print(f"""
  "{signer}": {{
    "pubkey": "{public_pem.decode().strip()}",
    "description": "Describe this signer entity here",
    "fingerprint": "{fingerprint}"
  }}
""")
    print("Then sign a skill with:")
    print(f"  python signing/sign_skill.py --skill <tier>/<skill-name>/SKILL.md --key {private_key_path} --signer {signer}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate an RSA keypair for A.S.K skill signing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--signer",
        required=True,
        help="Name of the signer entity (e.g., 'foundry-familiars', 'my-org'). Used in metadata only.",
    )
    parser.add_argument(
        "--out",
        default="./keys",
        help="Output directory for private.pem and public.pem. Default: ./keys",
    )
    args = parser.parse_args()
    generate_keypair(args.signer, Path(args.out))


if __name__ == "__main__":
    main()
