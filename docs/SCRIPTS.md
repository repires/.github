# Validation Scripts Guide

Reference guide for the CI validation scripts in `scripts/` (and their synchronized copies in `project-starter/scripts/`).

These scripts run in CI workflows across `tuna-os/.github` and downstream organization repositories to enforce security boundaries, dependency update safety, least-privilege workflow permissions, and supply chain integrity.

All validation scripts are intentionally dependency-free (written using Python standard library modules or Node standard library) so that they run on standard GitHub Actions runners (`ubuntu-latest` / `ubuntu-24.04`) without requiring `pip install`, `npm install`, or external dependencies.

---

## Table of Contents

- [Overview & Quick Reference](#overview--quick-reference)
- [Scripts](#scripts)
  - [1. `check-renovate-automerge-policy.py`](#1-check-renovate-automerge-policypy)
  - [2. `check-workflow-permissions.py`](#2-check-workflow-permissionspy)
  - [3. `check-workflow-action-pins.py`](#3-check-workflow-action-pinspy)
  - [4. `arch-plan.py`](#4-arch-planpy)
  - [5. `auto-qa-tuner.mjs`](#5-auto-qa-tunermjs)
  - [6. `roadmap-index.py`](#6-roadmap-indexpy)
- [Synchronization with `project-starter`](#synchronization-with-project-starter)
- [Authoring & Updating Policy Scripts](#authoring--updating-policy-scripts)

---

## Overview & Quick Reference

| Script | Purpose | Canonical Location | CI Workflow |
|---|---|---|---|
| [`check-renovate-automerge-policy.py`](#1-check-renovate-automerge-policypy) | Enforces that `renovate.json` configs never automerge major updates | `scripts/` (synced to `project-starter/scripts/`) | `renovate-policy-check.yml` |
| [`check-workflow-permissions.py`](#2-check-workflow-permissionspy) | Enforces top-level `permissions:` blocks in all workflow files | `scripts/` (synced to `project-starter/scripts/`) | `workflow-permissions-check.yml` |
| [`check-workflow-action-pins.py`](#3-check-workflow-action-pinspy) | Enforces that external `uses:` action references are pinned to full 40-character commit SHAs | `scripts/` | `workflow-action-pin-check.yml` |
| [`arch-plan.py`](#4-arch-planpy) | Validates architecture input matrix (`x86_64`, `aarch64`) for Flatpak packaging | `scripts/` | `arch-plan-check.yml` |
| [`auto-qa-tuner.mjs`](#5-auto-qa-tunermjs) | Self-tunes QA gate threshold parameters based on workflow outcome observations | `scripts/` | `auto-qa-tuner.yml` |
| [`roadmap-index.py`](#6-roadmap-indexpy) | Verifies and regenerates `ROADMAP-INDEX.md` inventory against live GitHub API data | `scripts/` | `roadmap-index-automation.yml` |

---

## Scripts

### 1. `check-renovate-automerge-policy.py`

#### Purpose & Policy Background
Enforces organization policy ([tuna-os/.github#12](https://github.com/tuna-os/.github/issues/12)): minor, patch, pin, pinDigest, and digest updates may automerge once CI passes, but **major updates must always require human review**.

A syntactically valid `renovate.json` can inadvertently automerge major updates when package rules are layered across presets and overrides (see incidents [tuna-os/tunaOS#1612](https://github.com/tuna-os/tunaOS/issues/1612) and [tuna-os/tunaOS#1636](https://github.com/tuna-os/tunaOS/issues/1636)). Standard JSON schema validators cannot detect this semantic configuration interaction.

This script acts as a conservative semantic analyzer:
- It tracks the running automerge state across top-level configurations and unscoped `packageRules`.
- Any unscoped rule that omits `matchUpdateTypes` or includes `"major"` and sets `"automerge": true` triggers a violation.
- Package-scoped rules (using scoping keys like `matchPackageNames`, `matchDatasources`, `matchDepNames`, etc.) setting `"automerge": true` for major updates are flagged independently. Narrow package rules setting `"automerge": false` are never allowed to clear broader unscoped violations.

#### CLI Usage & Examples
```bash
# Validate default Renovate configuration (defaults to renovate.json if no argument provided)
python3 scripts/check-renovate-automerge-policy.py renovate.json

# Validate shared organization preset
python3 scripts/check-renovate-automerge-policy.py default.json

# Validate project-starter configuration
python3 scripts/check-renovate-automerge-policy.py project-starter/renovate.json

# Run unit tests and project-starter sync check
python3 scripts/test-renovate-automerge-policy.py
```

#### Exit Codes
- `0`: Compliant — no rule permits automerging major updates.
- `1`: Violation detected (or input file could not be read / parsed as JSON).

#### Common Failure Scenarios & Troubleshooting
- **Error:** `FAIL: renovate.json violates the org automerge policy: 'major' updates would automerge...`
  - *Cause:* A top-level `"automerge": true` was set without disabling automerge for major updates, or a `packageRules` entry enabled automerge without restricting `matchUpdateTypes` to non-major updates.
  - *Fix:* Ensure major updates are explicitly excluded or have automerge disabled:
    ```json
    {
      "packageRules": [
        {
          "matchUpdateTypes": ["minor", "patch", "pin", "digest"],
          "automerge": true
        }
      ]
    }
    ```
- **Error:** `ERROR: could not read/parse <file>: ...`
  - *Cause:* File path does not exist or JSON syntax is invalid.
  - *Fix:* Check file path and validate JSON syntax (e.g. `jq . renovate.json`).

---

### 2. `check-workflow-permissions.py`

#### Purpose & Policy Background
Enforces organization security baseline ([tuna-os/.github#155](https://github.com/tuna-os/.github/issues/155)): **every GitHub Actions workflow must declare an explicit top-level `permissions:` block**.

Workflows without an explicit top-level `permissions:` block inherit the repository's default token scope (`GITHUB_TOKEN`), which is typically configured as read-and-write across multiple scopes. Under the principle of least privilege, workflows should declare minimum required scopes (such as `contents: read`).

The script is dependency-free: it implements a lightweight YAML structural scanner that parses top-level mapping keys and indentation without requiring PyYAML. It checks every document in a YAML stream (handling multi-document files separated by `---`).

#### CLI Usage & Examples
```bash
# Scan a directory of workflow files (.yml and .yaml)
python3 scripts/check-workflow-permissions.py .github/workflows

# Output results in machine-readable JSON format
python3 scripts/check-workflow-permissions.py .github/workflows --json

# Quiet mode (suppress output, return exit code only)
python3 scripts/check-workflow-permissions.py .github/workflows --quiet

# Run unit tests
python3 scripts/test_check_workflow_permissions.py
```

#### Exit Codes
- `0`: Compliant — every workflow file declares an explicit, non-empty top-level `permissions:` block.
- `1`: Violation detected — one or more workflow files lack a top-level `permissions:` block (or the specified directory does not exist).

#### Common Failure Scenarios & Troubleshooting
- **Error:** `❌ 1 workflow(s) missing an explicit top-level permissions block: .github/workflows/foo.yml: missing top-level permissions: block`
  - *Cause:* The workflow file either omits `permissions:`, declares an empty map (`permissions: {}`), or only declares permissions inside individual jobs rather than at the top level.
  - *Fix:* Add a top-level `permissions:` block near the top of the workflow file:
    ```yaml
    name: CI
    on: [push, pull_request]

    permissions:
      contents: read
    ```
- **Error:** `Commented-out permissions block flagged`
  - *Cause:* Lines beginning with `#` are comments and do not satisfy the required permission block.

---

### 3. `check-workflow-action-pins.py`

#### Purpose & Policy Background
Enforces supply-chain security standards ([tuna-os/.github#285](https://github.com/tuna-os/.github/issues/285)): **external GitHub Actions references (`uses:`) must be pinned to full 40-character commit SHAs**.

A `uses:` reference targeting mutable tags (such as `@v4`, `@v7.0.1`) or branches (such as `@main`) executes whatever code exists at that ref when the workflow triggers. If an upstream repository is compromised or a tag is moved, malicious code can execute in CI. Pinning to an immutable 40-character commit SHA prevents this attack vector.

Special rules:
- **Local actions:** Relative path references (e.g. `uses: ./.github/actions/foo`) are exempt because they are already bound to the repository commit being checked out.
- **Self-repository references:** References into the repository being checked (passed via `--self-repo owner/repo`) are exempt from SHA pinning because they resolve to the same repository tree.

#### CLI Usage & Examples
```bash
# Scan workflows directory for unpinned action references
python3 scripts/check-workflow-action-pins.py .github/workflows

# Scan with self-repository exemption (exempts references to tuna-os/.github)
python3 scripts/check-workflow-action-pins.py .github/workflows --self-repo "tuna-os/.github"

# Output in JSON format
python3 scripts/check-workflow-action-pins.py .github/workflows --json

# Run unit tests
python3 scripts/test_check_workflow_action_pins.py
```

#### Exit Codes
- `0`: Compliant — all external `uses:` action references are pinned to full 40-character hex commit SHAs.
- `1`: Violation detected — one or more `uses:` lines reference mutable branches or version tags.
- `2`: Usage error (e.g. target directory does not exist).

#### Common Failure Scenarios & Troubleshooting
- **Error:** `❌ 1 GitHub Actions reference(s) not pinned to a commit SHA: uses reference actions/checkout@v4 is pinned to mutable ref @v4 -- use a 40-character commit SHA`
  - *Cause:* An action is pinned to a release tag (`@v4`) or branch (`@main`).
  - *Fix:* Resolve the full 40-character commit SHA of the tag or release and include an inline comment indicating the version:
    ```yaml
    - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
    ```

---

### 4. `arch-plan.py`

#### Purpose & Policy Background
Serves as the single source of truth for architecture planning in the reusable `publish-flatpak.yml` workflow ([tuna-os/.github#90](https://github.com/tuna-os/.github/issues/90), [tuna-os/tunaOS#90](https://github.com/tuna-os/tunaOS/issues/90)).

Before this script existed, architecture inputs were parsed independently in multiple workflow steps, causing issues when unsupported or misspelled architectures entered the matrix without corresponding download or index steps.

`arch-plan.py`:
- Validates the input array against supported architectures (`x86_64`, `aarch64`).
- Rejects empty lists, duplicates, and unknown architectures.
- Assigns runner targets (`ubuntu-24.04` for `x86_64`, `ubuntu-24.04-arm` for `aarch64`).
- Designates a deterministic primary architecture (preferring `x86_64`) for the unsuffixed `:latest` tag.
- Emits `$GITHUB_OUTPUT` parameters (`matrix`, `primary`, `runners`) when executed in GitHub Actions.

#### CLI Usage & Examples
```bash
# Run with CLI argument (JSON array)
python3 scripts/arch-plan.py '["x86_64","aarch64"]'

# Run with environment variable ARCHS_INPUT
ARCHS_INPUT='["x86_64"]' python3 scripts/arch-plan.py

# Run unit tests
python3 scripts/test-arch-plan.py
```

#### Exit Codes
- `0`: Success — plan JSON generated and printed to stdout (and written to `$GITHUB_OUTPUT` if defined).
- `1`: Invalid input — invalid JSON, unsupported architecture, duplicate entry, or empty list.

#### Common Failure Scenarios & Troubleshooting
- **Error:** `ERROR: unsupported architecture 'arm64': supported values are x86_64, aarch64`
  - *Cause:* An invalid or shorthand architecture name was passed (e.g. `arm64` instead of `aarch64`).
  - *Fix:* Use the canonical names `x86_64` or `aarch64`.

---

### 5. `auto-qa-tuner.mjs`

#### Purpose & Policy Background
Implements self-tuning quality-gate thresholds ([tuna-os/.github#56](https://github.com/tuna-os/.github/issues/56)). It monitors QA gate failure rates across recent runs and dynamically adjusts `alert_threshold` within configured `[min_threshold, max_threshold]` bounds in `.github/auto-qa-tuning.json`:
- When failure rates are consistently low, it tightens thresholds by a configured step.
- When failure rates exceed thresholds, it holds thresholds and signals a breach (preventing premature loosening during active incidents).
- When samples are below `min_sample_runs`, it preserves current thresholds.

#### CLI Usage & Examples
```bash
# Analyze observations and report recommendations
node scripts/auto-qa-tuner.mjs \
  --config .github/auto-qa-tuning.json \
  --observations /tmp/observations.json \
  --report /tmp/tuning-report.md

# Apply recommendations in place to the configuration file
node scripts/auto-qa-tuner.mjs \
  --config .github/auto-qa-tuning.json \
  --observations /tmp/observations.json \
  --apply

# Run unit tests
node scripts/test-auto-qa-tuner.mjs
```

#### Exit Codes
- `0` (`EXIT_STEADY`): Steady state — all gates operating normally within bounds, no changes needed.
- `1` (`EXIT_ATTENTION`): Attention needed — a threshold breach was detected, or a threshold adjustment is proposed.
- `2` (`EXIT_ERROR`): Usage or input error (missing files, malformed JSON, invalid arguments).

---

### 6. `roadmap-index.py`

#### Purpose & Policy Background
Regenerates and verifies the organization-wide `ROADMAP-INDEX.md` repository table against the live GitHub API ([tuna-os/.github#110](https://github.com/tuna-os/.github/issues/110)). It checks each active repository in the `tuna-os` organization to determine its real default branch and whether a `ROADMAP.md` exists on that branch.

#### CLI Usage & Examples
```bash
# Verify whether ROADMAP-INDEX.md matches current GitHub state (read-only)
python3 scripts/roadmap-index.py --check

# Regenerate ROADMAP-INDEX.md in place
python3 scripts/roadmap-index.py --write

# Run unit tests
python3 scripts/test-roadmap-index.py
```

#### Exit Codes
- `0`: Up to date (under `--check`), or successfully written (under `--write`).
- `1`: Drift detected (table in `ROADMAP-INDEX.md` does not match live GitHub data).
- `2`: Network or GitHub API error.

---

## Synchronization with `project-starter`

Two validation scripts ship as byte-identical copies in `project-starter/scripts/` so that newly scaffolded repositories receive current policy enforcement gates:

1. `scripts/check-renovate-automerge-policy.py` ↔ `project-starter/scripts/check-renovate-automerge-policy.py`
2. `scripts/check-workflow-permissions.py` ↔ `project-starter/scripts/check-workflow-permissions.py`

### Why Synchronization Matters
`project-starter/` is copied verbatim into new repositories when they are created. If a bug fix or security policy update is made to `scripts/` without updating `project-starter/scripts/`, new repositories will inherit outdated or drifting checks.

### Verifying Synchronization
- The unit test `scripts/test-renovate-automerge-policy.py` includes an automated assertion verifying that `scripts/check-renovate-automerge-policy.py` and `project-starter/scripts/check-renovate-automerge-policy.py` are byte-identical.
- You can manually verify file synchronization at any time using `cmp` or `diff`:
  ```bash
  diff -u scripts/check-renovate-automerge-policy.py project-starter/scripts/check-renovate-automerge-policy.py
  diff -u scripts/check-workflow-permissions.py project-starter/scripts/check-workflow-permissions.py
  ```

---

## Authoring & Updating Policy Scripts

When modifying existing validation scripts or authoring new checks, adhere to the following principles:

1. **Zero External Dependencies:**
   - Keep scripts dependency-free using the standard library (`sys`, `os`, `json`, `re`, `argparse`, `pathlib`).
   - Scripts must execute directly on standard GitHub Actions runners (`ubuntu-latest`) without requiring `pip install` or package manager steps.

2. **Conservative Security Boundaries (Fail Closed):**
   - For security checks (like Renovate policies and workflow action pins), err on the side of reporting a violation rather than silently skipping unknown syntax or narrow rules.
   - Flag potential bypasses and let human reviewers confirm or adjust.

3. **Multi-Document & Quoting Safety:**
   - Parse YAML streams taking into account multi-document markers (`---`).
   - Avoid shell string interpolation (`${{ ... }}`) in workflow caller definitions; pass values via environment variables to avoid code injection vulnerabilities (see [`AGENTS.md`](../AGENTS.md)).

4. **Update Both Copies Simultaneously:**
   - Whenever editing `scripts/check-renovate-automerge-policy.py` or `scripts/check-workflow-permissions.py`, copy the updated script into `project-starter/scripts/` in the same commit.
   - Run `python3 scripts/test-renovate-automerge-policy.py` before committing to ensure the byte-sync assertion passes.

5. **Provide Automated Unit Tests:**
   - Pair every new or modified validation script with a corresponding unit test in `scripts/` (e.g. `scripts/test_*.py`).
