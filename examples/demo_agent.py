#!/usr/bin/env python3
"""
A.S.K Demo Agent
================
A minimal autonomous agent that uses the A.S.K skill library to complete tasks.

This demo shows the core A.S.K pattern:
  - The agent receives a task description
  - It consults the ASK registry to find the right skill
  - It invokes the skill with structured inputs
  - It chains skills to complete multi-step workflows

Run this demo:
    python examples/demo_agent.py

What this demonstrates:
    1. Skill discovery via the registry
    2. Input/output contracts in practice
    3. Skill composition (task -> select skill -> invoke -> result)
    4. Why ASK beats ad-hoc prompting for agent systems

Note: This demo uses mock implementations so it runs without real credentials.
To run against live skills, configure credentials in a .env file and update
the credential injection in executor.py.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# ---
# Simulated skill registry
# In production, the agent parses ASK.md and builds this map dynamically.
# The "description" field is the routing signal - how the agent decides
# which skill to call without being explicitly told.
# ---
SKILL_REGISTRY = {
    "foundation/github-push": {
        "description": "Push files to any GitHub repo via PAT + Python urllib. The only approved push method.",
        "inputs": ["repo_owner", "repo_name", "files", "commit_message"],
    },
    "foundation/telegram-notify": {
        "description": "Send a Telegram message to Scott or any registered contact via the bot.",
        "inputs": ["message", "chat_id"],
    },
    "foundation/vercel-deploy": {
        "description": "Upsert Vercel env vars and trigger production redeployment. Waits for READY state.",
        "inputs": ["env_vars", "redeploy", "wait_for_ready"],
    },
    "gfs/tes-deploy": {
        "description": "Full GFS deploy cycle: code push -> env update -> redeploy -> verify READY -> notify.",
        "inputs": ["files", "commit_message", "env_vars"],
    },
    "gfs/purchase": {
        "description": "Create a Privacy.com single-use card within per-category spend limits.",
        "inputs": ["merchant", "amount", "category", "description"],
    },
}


def route_to_skill(task: str) -> tuple:
    """
    Select the best skill for a given task by comparing the task description
    to each skill routing signal.

    In production, this uses semantic similarity (embeddings) or an LLM call.
    This demo uses simple keyword matching to illustrate the concept.

    Why routing descriptions matter:
        The description field in SKILL.md frontmatter is not documentation.
        Its a capability advertisement. The agent reads it to decide
        which skill to invoke - without being explicitly told.
        This is what makes the library agent-first, not human-first.
    """
    task_lower = task.lower()
    keyword_map = {
        "foundation/github-push": ["push", "github", "commit", "file", "repo", "code"],
        "foundation/telegram-notify": ["notify", "message", "telegram", "send", "alert", "ping"],
        "foundation/vercel-deploy": ["deploy", "vercel", "environment", "env", "production"],
        "gfs/tes-deploy": ["deploy", "push", "redeploy", "full", "complete", "release"],
        "gfs/purchase": ["buy", "purchase", "payment", "card", "spend", "merchant"],
    }
    scores = {}
    for skill_path, keywords in keyword_map.items():
        scores[skill_path] = sum(1 for kw in keywords if kw in task_lower)
    best = max(scores, key=scores.get)
    confidence = scores[best] / max(len(keyword_map[best]), 1)
    return best, confidence


def mock_execute(skill_path: str, inputs: dict) -> dict:
    """Mock execution for demo purposes. Replace with executor.execute_skill() for real runs."""
    if skill_path == "foundation/github-push":
        files = inputs.get("files", [])
        return {"status": "success", "results": [{"path": f["path"], "status": "created", "sha": "abc123de"} for f in files]}
    elif skill_path == "foundation/telegram-notify":
        return {"ok": True, "message_id": 42}
    elif skill_path == "foundation/vercel-deploy":
        return {"status": "ready", "url": "https://your-project.vercel.app", "deployment_id": "dpl_demo123"}
    elif skill_path == "gfs/tes-deploy":
        return {"status": "ready", "url": "https://your-project.vercel.app", "files_deployed": len(inputs.get("files", []))}
    elif skill_path == "gfs/purchase":
        return {"status": "created", "card_last_four": "1111", "expiry": "12/27"}
    return {"status": "unknown_skill"}


class ASKAgent:
    """
    Minimal autonomous agent demonstrating A.S.K invocation pattern.

    Architecture: Task -> Route -> Invoke -> Result -> (optionally) Chain

    The agent does NOT re-implement capabilities. It routes to skills.
    This is the core value of A.S.K: agents stay thin; the library stays fat.
    """

    def __init__(self, name="demo-agent"):
        self.name = name
        self.history = []

    def run(self, task: str, inputs: dict = None) -> dict:
        print(f"\n{'='*60}")
        print(f"Agent: {self.name}")
        print(f"Task:  {task}")
        print(f"{'='*60}")

        skill_path, confidence = route_to_skill(task)
        skill_info = SKILL_REGISTRY[skill_path]

        print(f"\n-> Routing to: {skill_path}")
        print(f"   Confidence: {confidence:.0%}")
        print(f"   Skill: {skill_info['description'][:80]}")

        if inputs is None:
            inputs = {}

        missing = [k for k in skill_info["inputs"] if k not in inputs]
        if missing:
            print(f"\n   Missing inputs: {missing}")

        print(f"\n-> Invoking: ASK: {skill_path}")
        print(f"   Inputs: {json.dumps(inputs, indent=4)}")

        result = mock_execute(skill_path, inputs)

        print(f"\n-> Result:")
        print(f"   {json.dumps(result, indent=4)}")

        self.history.append({"task": task, "skill": skill_path, "inputs": inputs, "result": result})
        return result

    def chain(self, steps: list) -> list:
        """Execute a sequence of skills. One skill output feeds the next step context."""
        results = []
        for task, inputs in steps:
            result = self.run(task, inputs)
            results.append(result)
        return results


def main():
    agent = ASKAgent("ask-demo")

    print("A.S.K Demo Agent")
    print("Demonstrating skill routing and invocation")

    print("\n--- Demo 1: Push a file to GitHub ---")
    agent.run(
        task="push this file to github",
        inputs={
            "repo_owner": "srmbsrg",
            "repo_name": "ask-kernel",
            "files": [{"path": "examples/output.txt", "content": "Hello from A.S.K!"}],
            "commit_message": "demo: agent-generated file via ASK",
        }
    )

    print("\n--- Demo 2: Send a notification ---")
    agent.run(
        task="send a telegram message to notify the team",
        inputs={"message": "Deploy complete. All systems nominal.", "chat_id": "1234567890"}
    )

    print("\n--- Demo 3: Full deploy chain ---")
    agent.chain([
        ("push code to github", {
            "repo_owner": "srmbsrg",
            "repo_name": "ask-kernel",
            "files": [{"path": "src/feature.ts", "content": "export const newFeature = () => {};"}],
            "commit_message": "feat: add new feature",
        }),
        ("deploy to vercel", {
            "env_vars": {"FEATURE_FLAG": "true"},
            "redeploy": True,
            "wait_for_ready": True,
        }),
        ("notify on telegram that deploy is done", {
            "message": "Deploy complete! New feature is live.",
            "chat_id": "1234567890",
        }),
    ])

    print("\n--- Session Summary ---")
    print(f"Skills invoked: {len(agent.history)}")
    for entry in agent.history:
        status = entry["result"].get("status", "unknown")
        print(f"  ASK: {entry['skill']} -> {status}")

    print("\nDemo complete. See github.com/srmbsrg/ask-kernel for the full library.")
    print("\nTo run with real skills:")
    print("  1. Clone: git clone https://github.com/srmbsrg/ask-kernel")
    print("  2. Set credentials in .env (see context/gfs-env.md for schema)")
    print("  3. Import executor.py and call execute_skill(skill_path, inputs)")


if __name__ == "__main__":
    main()
