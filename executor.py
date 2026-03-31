#!/usr/bin/env python3
"""
A.S.K Reference Executor
=========================
Demonstrates how an agent loads and invokes an A.S.K skill from the registry.

Usage:
    python executor.py foundation/github-push '{"repo_owner": "you", "repo_name": "myrepo", "files": [], "commit_message": "test"}'
    python executor.py --list

Signature verification:
    python executor.py --verify-signatures foundation/github-push '{}'
    ASK_VERIFY_SIGNATURES=1 python executor.py foundation/github-push '{}'

Design principle:
    Skills are definitions, not executables. The executor is the runtime that:
    1. Reads the SKILL.md definition
    2. Parses the contract (inputs, outputs)
    3. Optionally verifies the skill's cryptographic signature
    4. Executes the implementation block
    5. Returns structured output

This file is a minimal reference implementation. Production systems should
extend it with telemetry (ASK: foundation/ask-log), error handling, and
credential injection from secure secret stores (not context files).
"""

import sys
import os
import json
import re
import subprocess
import tempfile
from pathlib import Path

ASK_ROOT = Path(__file__).parent

# Signing module lives in signing/ alongside this executor.
SIGNING_DIR = ASK_ROOT / "signing"


def find_skill(skill_path: str) -> Path:
    """Resolve a skill path like 'foundation/github-push' to a SKILL.md file."""
    skill_dir = ASK_ROOT / skill_path
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        raise FileNotFoundError(f"Skill not found: {skill_file}")
    return skill_file


def parse_skill(skill_file: Path) -> dict:
    """
    Parse a SKILL.md file into a structured dict.

    Returns:
        {
            "name": str,
            "description": str,
            "version": str,
            "tier": str,
            "dependencies": list,
            "implementation_code": str,
            "sections": dict,
        }

    Why regex over a proper YAML parser:
        The SKILL.md format uses simple key: value frontmatter separated by ---.
        A full YAML parser adds a dependency for minimal gain on this format.
        If the frontmatter grows more complex (nested keys, multi-line values),
        migrate to PyYAML.
    """
    content = skill_file.read_text()

    # Parse YAML frontmatter between --- markers
    frontmatter_match = re.match(r"^---\n(.+?)\n---", content, re.DOTALL)
    if not frontmatter_match:
        raise ValueError(f"No frontmatter found in {skill_file}")

    fm_raw = frontmatter_match.group(1)
    frontmatter = {}
    for line in fm_raw.strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                # Simple list parsing: [item1, item2]
                items = [i.strip().strip("'\"") for i in val[1:-1].split(",") if i.strip()]
                frontmatter[key] = items
            else:
                frontmatter[key] = val.strip("'\"")

    # Extract implementation code block (first Python block)
    # Why: The implementation section contains the canonical executable logic.
    # We extract only Python blocks; other code blocks (TypeScript examples, etc.)
    # are illustrative and not executed by this runtime.
    code_match = re.search(r"## Implementation[\s\S]*?```python\n([\s\S]*?)```", content)
    implementation_code = code_match.group(1) if code_match else ""

    # Extract section bodies
    def extract_section(header: str) -> str:
        pattern = rf"## {re.escape(header)}\n([\s\S]*?)(?=\n## |\Z)"
        match = re.search(pattern, content)
        return match.group(1).strip() if match else ""

    return {
        "name": frontmatter.get("name", ""),
        "description": frontmatter.get("description", ""),
        "version": frontmatter.get("version", "1.0.0"),
        "tier": frontmatter.get("tier", ""),
        "dependencies": frontmatter.get("dependencies", []),
        "implementation_code": implementation_code,
        "sections": {
            "when_to_invoke": extract_section("When to invoke"),
            "inputs": extract_section("Inputs"),
            "methodology": extract_section("Methodology"),
            "outputs": extract_section("Outputs"),
            "notes": extract_section("Notes"),
        }
    }


def verify_skill_signature(skill_file: Path) -> bool:
    """
    Verify the cryptographic signature of a skill before execution.

    Delegates to signing/verify_skill.py, which handles:
      - Sidecar .sig file presence check
      - Trusted signer registry lookup
      - Revoked key check
      - RSA-PSS signature verification
      - Inline comment / sidecar consistency check

    Returns True if the skill is validly signed, False otherwise.
    Prints the verification result to stdout/stderr.

    Why a subprocess call instead of a direct import:
        verify_skill.py imports `cryptography`, which may not be installed
        in all environments. Calling it as a subprocess means the executor
        stays importable even without the cryptography library — only
        signature verification requires it. If the library is not installed,
        the subprocess fails with a clear error message.
    """
    verify_script = SIGNING_DIR / "verify_skill.py"
    if not verify_script.exists():
        print(
            f"Warning: signing/verify_skill.py not found at {verify_script}. "
            "Cannot verify signature.",
            file=sys.stderr,
        )
        return False

    try:
        result = subprocess.run(
            [sys.executable, str(verify_script), "--skill", str(skill_file)],
            capture_output=False,  # Let verify_skill.py print directly to terminal
            text=True,
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Error running signature verification: {e}", file=sys.stderr)
        return False


def should_verify_signatures() -> bool:
    """
    Returns True if signature verification is required.

    Verification is enabled when:
      - The --verify-signatures CLI flag is present (handled in main())
      - The ASK_VERIFY_SIGNATURES environment variable is set to "1" or "true"
    """
    env_val = os.environ.get("ASK_VERIFY_SIGNATURES", "").strip().lower()
    return env_val in ("1", "true", "yes")


def execute_skill(skill_path: str, inputs: dict, verify_signatures: bool = False) -> dict:
    """
    Execute an A.S.K skill by path with the given inputs.

    If verify_signatures is True (or ASK_VERIFY_SIGNATURES=1), the skill's
    cryptographic signature is checked before execution. An unsigned or
    tampered skill will cause execution to abort with a clear error.

    This is a minimal executor for demonstration purposes.
    In production, skills would inject credentials from a secure store,
    not from context files committed to the repo.

    Why exec() instead of importlib:
        Skill code blocks are embedded in Markdown, not importable modules.
        exec() lets us run the extracted block without a build step.
        Tradeoff: less isolation than subprocess, but simpler for a reference impl.
    """
    skill_file = find_skill(skill_path)

    # Signature verification gate.
    # If the flag is set (CLI or env var), we must have a valid signature.
    # If not set, we warn but proceed — this preserves backward compatibility
    # for local dev workflows where skills haven't been signed yet.
    effective_verify = verify_signatures or should_verify_signatures()

    if effective_verify:
        print(f"Verifying signature for: {skill_path}")
        is_valid = verify_skill_signature(skill_file)
        if not is_valid:
            return {
                "status": "signature_error",
                "skill": skill_path,
                "message": (
                    "Skill signature verification failed. Refusing to execute. "
                    "This skill may be unsigned, tampered with, or signed by an untrusted key. "
                    "See signing/SIGNING.md for how to sign skills."
                ),
            }
        print(f"Signature verified. Proceeding with execution.")
    else:
        # Check if a .sig file exists at all; if not, emit a warning so
        # operators know this skill is running without provenance guarantees.
        sidecar = skill_file.parent / "SKILL.md.sig"
        if not sidecar.exists():
            print(
                f"Warning: {skill_path} has no signature (.sig file missing). "
                "Set ASK_VERIFY_SIGNATURES=1 or use --verify-signatures to enforce signing. "
                "Proceeding anyway (dev mode).",
                file=sys.stderr,
            )

    skill = parse_skill(skill_file)

    if not skill["implementation_code"]:
        return {
            "status": "no_implementation",
            "skill": skill_path,
            "message": (
                "This skill has no Python implementation block. "
                "It may be a definition-only skill (e.g., context files) "
                "or require a language-specific executor."
            )
        }

    # Inject inputs into the execution namespace.
    # Why not environment variables: inputs are structured data, not strings.
    # Passing them as namespace vars lets the skill code reference them directly.
    namespace = {
        "inputs": inputs,
        "__skill_path__": skill_path,
        "__skill_version__": skill["version"],
    }

    # Warning: exec() is powerful. In a multi-tenant or untrusted skill environment,
    # use subprocess with sandboxing instead.
    exec(skill["implementation_code"], namespace)  # noqa: S102

    # Skills that define a run(inputs) function get called with inputs.
    # Skills that run top-level code produce a result variable.
    if "run" in namespace and callable(namespace["run"]):
        result = namespace["run"](inputs)
    elif "result" in namespace:
        result = namespace["result"]
    else:
        result = {"status": "executed", "note": "No run() function or result variable defined."}

    return result


def list_skills() -> None:
    """Print all skills in the registry."""
    registry_file = ASK_ROOT / "ASK.md"
    if not registry_file.exists():
        print("ASK.md registry not found.")
        return

    content = registry_file.read_text()
    # Find table rows: | skill | version | description | path |
    rows = re.findall(r"\| `([^`]+)` \| ([\d.]+) \| (.+?) \| `([^`]+)` \|", content)

    print(f"\nA.S.K Registry — {len(rows)} skills\n")
    print(f"  {'PATH':<35} {'VERSION':<10} DESCRIPTION")
    print(f"  {'-'*35} {'-'*10} {'-'*40}")
    for name, version, desc, path in rows:
        print(f"  {path:<35} {version:<10} {desc[:60]}")
    print()


def main():
    args = sys.argv[1:]

    if not args or args[0] == "--help":
        print(__doc__)
        sys.exit(0)

    if args[0] == "--list":
        list_skills()
        sys.exit(0)

    # Parse --verify-signatures flag (can appear anywhere before the skill path).
    verify_signatures = False
    if "--verify-signatures" in args:
        verify_signatures = True
        args = [a for a in args if a != "--verify-signatures"]

    skill_path = args[0]
    inputs = {}
    if len(args) > 1:
        try:
            inputs = json.loads(args[1])
        except json.JSONDecodeError as e:
            print(f"Error: inputs must be valid JSON. {e}")
            sys.exit(1)

    print(f"\nASK: {skill_path}")
    print(f"Inputs: {json.dumps(inputs, indent=2)}")
    print("-" * 50)

    try:
        skill_file = find_skill(skill_path)
        skill = parse_skill(skill_file)
        print(f"Skill: {skill['name']} v{skill['version']} ({skill['tier']} tier)")
        print(f"Description: {skill['description'][:80]}...")
        print(f"Dependencies: {skill['dependencies'] or 'none'}")
        print("-" * 50)
        result = execute_skill(skill_path, inputs, verify_signatures=verify_signatures)
        print("Result:")
        print(json.dumps(result, indent=2))
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nAvailable skills:")
        list_skills()
        sys.exit(1)
    except Exception as e:
        print(f"Execution error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
