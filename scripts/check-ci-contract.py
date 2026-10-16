#!/usr/bin/env python3
"""Verify that every green criterion in green-criteria.yml is asserted by reachable workflows.

Validates that:
  - Every criterion defines a freshness_sla_days
  - Every gate workflow exists and is reachable from an active trigger
  - Every gate workflow is mentioned in the asserted_by prose
  - Every referenced job and step exists in its workflow
  - Blocking gates do not have continue-on-error set

Usage:
    check-ci-contract.py [--criteria-path PATH] [--workflows-dir DIR] [--json]

Exit code is 0 when all criteria are satisfied, 1 if violations are found.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("error: PyYAML is required. Install with: python3 -m pip install pyyaml", file=sys.stderr)
    sys.exit(1)

ACTIVE_TRIGGERS = {"schedule", "push", "pull_request", "merge_group", "workflow_run", "release"}


def load_workflows(directory: Path) -> dict[str, dict]:
    """Load all workflow YAML files from a directory."""
    docs = {}
    for f in sorted(list(directory.glob("*.yml")) + list(directory.glob("*.yaml"))):
        try:
            doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            docs[f"{directory}/{f.name}"] = doc
            docs[f.name] = doc
        except yaml.YAMLError as e:
            print(f"warning: failed to parse {f.name}: {e}", file=sys.stderr)
    return docs


def triggers(doc: dict) -> dict:
    """Extract trigger configuration from a workflow document."""
    on = doc.get("on", doc.get(True, {}))
    if isinstance(on, str):
        return {on: None}
    if isinstance(on, list):
        return {k: None for k in on}
    return on or {}


def callers(workflows: dict[str, dict]) -> dict[str, set[str]]:
    """Map reusable workflows to the workflows that call them."""
    out: dict[str, set[str]] = {}
    for name, doc in workflows.items():
        for job in (doc.get("jobs") or {}).values():
            uses = (job or {}).get("uses", "")
            if isinstance(uses, str) and uses.startswith("./"):
                out.setdefault(uses[2:], set()).add(name)
    return out


def is_reachable(name: str, workflows: dict[str, dict], _seen: set[str] | None = None) -> bool:
    """Check if a workflow is reachable from an active trigger (direct or via caller chain)."""
    _seen = _seen or set()
    if name in _seen:
        return False
    _seen.add(name)
    doc = workflows.get(name)
    if doc is None:
        return False
    if ACTIVE_TRIGGERS & set(triggers(doc)):
        return True
    return any(is_reachable(c, workflows, _seen) for c in callers(workflows).get(name, ()))


def check_ci_contract(
    criteria_path: Path = Path(".github/green-criteria.yml"),
    workflows_dir: Path = Path(".github/workflows"),
) -> tuple[bool, list[str]]:
    """Verify the CI contract. Returns (is_valid, violations)."""
    if not criteria_path.is_file():
        return True, []

    if not workflows_dir.is_dir():
        return False, [f"Workflows directory not found at {workflows_dir}"]

    try:
        raw = yaml.safe_load(criteria_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        return False, [f"Failed to parse {criteria_path}: {e}"]

    criteria = raw.get("criteria", [])
    workflows = load_workflows(workflows_dir)

    violations = []
    for criterion in criteria:
        cid = criterion.get("id", "unknown")
        gates = criterion.get("gates")
        if not gates:
            if criterion.get("asserted_by"):
                violations.append(f"{cid}: asserted_by names something but there is no `gates` block")
            continue
        if "freshness_sla_days" not in criterion:
            violations.append(f"{cid}: missing freshness_sla_days")
        blocking = criterion.get("enforcement") == "blocking"
        prose = criterion.get("asserted_by") or ""

        for gate in gates:
            wf = gate.get("workflow", "")
            wf_basename = wf.split("/")[-1]
            doc = workflows.get(wf) or workflows.get(wf_basename)
            if doc is None:
                violations.append(f"{cid}: gate workflow {wf} does not exist")
                continue
            if wf_basename not in prose:
                violations.append(f"{cid}: gate workflow {wf} is not mentioned in asserted_by")
            if not is_reachable(wf, workflows) and not is_reachable(wf_basename, workflows):
                violations.append(f"{cid}: {wf} is not reachable from any active trigger")

            jobs = doc.get("jobs") or {}
            for job_id, verdict_step in (gate.get("jobs") or {}).items():
                job = jobs.get(job_id)
                if job is None:
                    violations.append(f"{cid}: {wf} has no job {job_id!r}")
                    continue
                cond = str(job.get("if") or "")
                if cond.strip() in {"false", "${{ false }}"}:
                    violations.append(f"{cid}: {wf}:{job_id} is hard-disabled")
                if blocking and job.get("continue-on-error"):
                    violations.append(f"{cid}: blocking gate {wf}:{job_id} has continue-on-error")
                if verdict_step:
                    step_names = [s.get("name") for s in (job.get("steps") or []) if s.get("name")]
                    if verdict_step not in step_names:
                        violations.append(f"{cid}: {wf}:{job_id} has no step named {verdict_step!r}")

    return len(violations) == 0, violations


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--criteria-path",
        type=Path,
        default=Path(".github/green-criteria.yml"),
        help="Path to green-criteria.yml (default: .github/green-criteria.yml)",
    )
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

    args = parser.parse_args()

    is_valid, violations = check_ci_contract(args.criteria_path, args.workflows_dir)

    if args.json:
        result = {
            "valid": is_valid,
            "violations": violations,
            "count": len(violations),
        }
        print(json.dumps(result, indent=2))
    else:
        if is_valid:
            print(f"✅ CI contract valid: {len(violations)} violations.")
        else:
            print(f"❌ CI contract violations found ({len(violations)}):")
            for v in violations:
                print(f"  • {v}")

    return 0 if is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
