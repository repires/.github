#!/usr/bin/env python3
"""Verify that pull_request workflows survive execution from forks.

On a pull_request event raised from a fork, GitHub issues a read-only GITHUB_TOKEN
and all repository secrets are empty. This script verifies that:
  1. All pull_request workflows declare explicit permissions
  2. pull_request_target is not used without an explicit exception
  3. Steps performing write operations or referencing secrets are properly guarded

Usage:
    check-fork-safety.py [--workflows-dir DIR] [--json] [--quiet]

Exit code is 0 when all workflows are fork-safe, 1 if violations are found.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("error: PyYAML is required. Install with: python3 -m pip install pyyaml", file=sys.stderr)
    sys.exit(1)

WRITE_ACTIONS = re.compile(
    r"git push|gh pr (comment|create|edit|review|merge)|gh issue (comment|create|edit)"
    r"|gh api [^\n]*(--method|-X) ?(POST|PATCH|PUT|DELETE)"
    r"|gh api [^\n]*-F |gh release |actions/github-script"
)
SECRET_REF = re.compile(r"\$\{\{\s*secrets\.(?!GITHUB_TOKEN\b)([A-Za-z0-9_]+)")
FORK_GUARDS = (
    "github.event_name != 'pull_request'",
    'github.event_name != "pull_request"',
    "github.event_name == 'workflow_dispatch'",
    "head.repo.fork",
    "head.repo.full_name",
    "IS_FORK",
    "no_r2_credentials",
)


def load_yaml(path: Path) -> dict:
    """Load a YAML file."""
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        print(f"warning: failed to parse {path.name}: {e}", file=sys.stderr)
        return {}


def get_triggers(doc: dict) -> dict:
    """Extract trigger configuration from a workflow document."""
    on = doc.get("on", doc.get(True, {}))
    if isinstance(on, str):
        return {on: None}
    if isinstance(on, list):
        return {k: None for k in on}
    return on or {}


def is_fork_aware(text: str) -> bool:
    """Check if text contains a fork guard expression."""
    return any(g in text for g in FORK_GUARDS)


def check_fork_safety(workflows_dir: Path = Path(".github/workflows")) -> tuple[bool, list[str]]:
    """Verify fork safety of workflows. Returns (is_safe, violations)."""
    if not workflows_dir.is_dir():
        return True, []

    files = sorted(list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml")))
    pr_workflows = [
        f
        for f in files
        if "pull_request" in get_triggers(load_yaml(f))
        or "pull_request_target" in get_triggers(load_yaml(f))
    ]

    violations = []

    for wf in pr_workflows:
        doc = load_yaml(wf)
        # 1. Check permissions declared
        has_top_permissions = "permissions" in doc
        jobs = doc.get("jobs") or {}
        if not has_top_permissions:
            missing = [
                j
                for j, body in jobs.items()
                if "permissions" not in (body or {}) and "uses" not in (body or {})
            ]
            if missing:
                violations.append(f"{wf.name}: jobs {missing} lack explicit `permissions:` declaration.")

        # 2. Check pull_request_target
        if "pull_request_target" in get_triggers(doc):
            violations.append(f"{wf.name}: uses `pull_request_target` which exposes secrets to untrusted code.")

        # 3. Check write actions and secrets in steps
        for job_id, job in jobs.items():
            job = job or {}
            job_guard = is_fork_aware(str(job.get("if", "")))
            steps = job.get("steps") or []
            aware_ids = {
                s.get("id")
                for s in steps
                if s.get("id")
                and is_fork_aware(
                    str(s.get("if", "")) + yaml.dump(s.get("env") or {}) + str(s.get("run", ""))
                )
            }
            for step in steps:
                blob = yaml.dump(step)
                needs_write = bool(WRITE_ACTIONS.search(blob))
                secrets = [m.group(1) for m in SECRET_REF.finditer(blob)]
                if not needs_write and not secrets:
                    continue
                cond = str(step.get("if", ""))
                step_text = cond + "\n" + yaml.dump(step.get("env") or {}) + "\n" + str(step.get("run", ""))
                guarded_by_preflight = any(f"steps.{sid}.outputs" in cond for sid in aware_ids)
                if job_guard or guarded_by_preflight or is_fork_aware(step_text) or step.get("continue-on-error"):
                    continue
                what = "secrets " + ",".join(sorted(set(secrets))) if secrets else "a write action"
                violations.append(
                    f"{wf.name}: job {job_id!r} step {step.get('name', '?')!r} uses {what} without fork guard"
                )

    return len(violations) == 0, violations


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workflows-dir",
        type=Path,
        default=Path(".github/workflows"),
        help="Directory containing workflow YAML files (default: .github/workflows)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output; exit code only",
    )

    args = parser.parse_args()

    is_safe, violations = check_fork_safety(args.workflows_dir)

    if args.quiet:
        return 0 if is_safe else 1

    if args.json:
        result = {
            "safe": is_safe,
            "violations": violations,
            "count": len(violations),
        }
        print(json.dumps(result, indent=2))
    else:
        if is_safe:
            print("✅ All pull_request workflows are fork-safe.")
        else:
            print(f"❌ Fork safety violations found ({len(violations)}):")
            for v in violations:
                print(f"  • {v}")

    return 0 if is_safe else 1


if __name__ == "__main__":
    sys.exit(main())
