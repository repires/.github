# .github/actions/ACTIONS.md — Reusable composite actions index

Index of reusable composite actions hosted in `.github/actions/` in `tuna-os/.github`.

Downstream workflows or composite actions reference these actions using:

```yaml
- uses: tuna-os/.github/.github/actions/<action-name>@main
  with:
    ...
```

> **Note on caller context:** In a reusable (`workflow_call`) workflow, steps run against the caller's repository checkout. Composite actions in this repository allow scripts and tool configurations hosted here to travel with the action via `$GITHUB_ACTION_PATH`, avoiding code duplication or drift across repositories.

---

## Actions Overview

| Action | Path | Description | README |
|---|---|---|---|
| **Arch Plan** | [`.github/actions/arch-plan`](arch-plan/) | Validates and normalizes target architectures (`x86_64`, `aarch64`) for Flatpak builds, emitting execution plans, runner maps, and primary tags. | — |
| **CI Contract Check** | [`.github/actions/ci-contract-check`](ci-contract-check/) | Verifies that all criteria declared in `green-criteria.yml` are asserted by reachable workflow jobs or steps. | — |
| **Fork Safety Check** | [`.github/actions/fork-safety-check`](fork-safety-check/) | Verifies that `pull_request` workflows declare permissions, avoid unsafe triggers (`pull_request_target`), and protect write steps. | — |
| **Publish Flatpak OCI Index** | [`.github/actions/publish-flatpak-index`](publish-flatpak-index/) | Wraps `update-flatpak-index` with clone, commit, and push-with-retry against `tuna-os/docs` to avoid concurrency races among publishers. | [README](publish-flatpak-index/README.md) |
| **Simplified Technical English Lint** | [`.github/actions/ste-lint`](ste-lint/) | Lints Markdown prose against ASD-STE100 rules using a configurable per-repository budget and advisory PR annotations. | [README](ste-lint/README.md) |
| **Update Flatpak OCI Index** | [`.github/actions/update-flatpak-index`](update-flatpak-index/) | Updates a Flatpak `index/static` file from an OCI layout directory with digest, architecture, and AppStream metadata. | [README](update-flatpak-index/README.md) |

---

## Detailed Directory

### 1. `arch-plan`
- **Location:** [`.github/actions/arch-plan/action.yml`](arch-plan/action.yml)
- **Description:** Validates the `archs` input (JSON array) against supported architecture targets (`x86_64`, `aarch64`) and produces matrix output, primary target mapping, and architecture-to-runner mappings for matrix jobs.
- **Inputs:**
  - `archs` *(required)*: JSON array of architectures (e.g. `'["x86_64","aarch64"]'`).
- **Outputs:**
  - `matrix`: Validated, deduplicated JSON array of architectures.
  - `primary`: Architecture tracked by the unsuffixed `latest` tag.
  - `runners`: JSON object mapping each architecture to its runner label.
- **Usage:**
  ```yaml
  - name: Plan build architectures
    id: arch-plan
    uses: tuna-os/.github/.github/actions/arch-plan@main
    with:
      archs: '["x86_64", "aarch64"]'
  ```

---

### 2. `ci-contract-check`
- **Location:** [`.github/actions/ci-contract-check/action.yml`](ci-contract-check/action.yml)
- **Description:** Ensures CI gate criteria in `green-criteria.yml` are wired up to active workflows. Runs validation logic located in `.github/scripts/ci_contract.py`.
- **Inputs:**
  - `criteria-path` *(optional, default: `.github/green-criteria.yml`)*: Path to the criteria definition file.
  - `workflows-dir` *(optional, default: `.github/workflows`)*: Path to workflow YAML files.
  - `python-version` *(optional, default: `"3.11"`)*: Python runtime version.
- **Usage:**
  ```yaml
  - name: Check CI contracts
    uses: tuna-os/.github/.github/actions/ci-contract-check@main
    with:
      criteria-path: .github/green-criteria.yml
      workflows-dir: .github/workflows
  ```

---

### 3. `fork-safety-check`
- **Location:** [`.github/actions/fork-safety-check/action.yml`](fork-safety-check/action.yml)
- **Description:** Scans pull request workflows to prevent credential leakage and untrusted code execution from fork PRs. Runs validation logic in `.github/scripts/fork_safety.py`.
- **Inputs:**
  - `workflows-dir` *(optional, default: `.github/workflows`)*: Path to workflow YAML files.
  - `python-version` *(optional, default: `"3.11"`)*: Python runtime version.
- **Usage:**
  ```yaml
  - name: Check fork safety
    uses: tuna-os/.github/.github/actions/fork-safety-check@main
    with:
      workflows-dir: .github/workflows
  ```

---

### 4. `publish-flatpak-index`
- **Location:** [`.github/actions/publish-flatpak-index/action.yml`](publish-flatpak-index/action.yml)
- **Documentation:** [`.github/actions/publish-flatpak-index/README.md`](publish-flatpak-index/README.md)
- **Description:** Clones `tuna-os/docs`, invokes `update-flatpak-index`, commits, and pushes back to GitHub with jittered exponential backoff and retry logic to gracefully resolve concurrent publisher collisions.
- **Inputs:**
  - `oci-dir` *(required)*: Path to local OCI layout directory containing `index.json`.
  - `repo-name` *(required)*: Target registry repository name (e.g. `tuna-os/tavern`).
  - `token` *(required)*: GitHub token with write permissions to `docs-repo` (`FLATPAK_INDEX_TOKEN`).
  - `index-file` *(optional, default: `static/flatpak/index/static`)*: Relative path to index in docs repo.
  - `registry` *(optional, default: `ghcr.io`)*: Container registry host.
  - `tags` *(optional, default: `latest`)*: Space-separated list of image tags.
  - `docs-repo` *(optional, default: `tuna-os/docs`)*: Target documentation repository.
  - `max-attempts` *(optional, default: `"8"`)*: Maximum push attempts before failure.
- **Usage:**
  ```yaml
  - name: Publish Flatpak index
    uses: tuna-os/.github/.github/actions/publish-flatpak-index@main
    with:
      oci-dir: oci/mandelbrot-oci-x86_64
      repo-name: tuna-os/mandelbrot
      tags: latest
      token: ${{ secrets.FLATPAK_INDEX_TOKEN }}
  ```

---

### 5. `ste-lint`
- **Location:** [`.github/actions/ste-lint/action.yml`](ste-lint/action.yml)
- **Documentation:** [`.github/actions/ste-lint/README.md`](ste-lint/README.md)
- **Description:** Enforces ASD-STE100 Simplified Technical English guidelines on Markdown documentation, comparing against a repository's `.ste-budget` file and reporting line annotations on pull requests.
- **Inputs:**
  - `budget-file` *(optional, default: `.ste-budget`)*: File containing maximum tolerated findings.
  - `budget` *(optional, default: `""`)*: Explicit numeric budget fallback if budget file is missing.
  - `node-version` *(optional, default: `"24"`)*: Node.js runtime version.
  - `run-tests` *(optional, default: `"true"`)*: Whether to run internal STE lint unit tests first.
  - `base-ref` *(optional, default: `""`)*: Git base ref for advisory diff comparison.
  - `annotations` *(optional, default: `"true"`)*: Emit GitHub Actions warning annotations.
- **Usage:**
  ```yaml
  - name: Lint English prose
    uses: tuna-os/.github/.github/actions/ste-lint@main
    with:
      budget-file: .ste-budget
  ```

---

### 6. `update-flatpak-index`
- **Location:** [`.github/actions/update-flatpak-index/action.yml`](update-flatpak-index/action.yml)
- **Documentation:** [`.github/actions/update-flatpak-index/README.md`](update-flatpak-index/README.md)
- **Description:** Low-level index updater script (`update-index.py`) that reads local OCI image digests and metadata to update an entry in a Flatpak OCI index file.
- **Inputs:**
  - `oci-dir` *(required)*: Local path to OCI layout directory containing `index.json`.
  - `repo-name` *(required)*: Repository name on registry (e.g. `tuna-os/tavern`).
  - `index-file` *(optional, default: `index/static`)*: Destination index file path.
  - `registry` *(optional, default: `ghcr.io`)*: Registry hostname.
  - `tags` *(optional, default: `latest`)*: Space-separated list of image tags.
  - `require-appstream` *(optional, default: `"false"`)*: Fail if AppStream metadata labels are missing.
- **Usage:**
  ```yaml
  - name: Update index
    uses: tuna-os/.github/.github/actions/update-flatpak-index@main
    with:
      oci-dir: oci/mandelbrot-oci-x86_64
      repo-name: tuna-os/mandelbrot
      index-file: index-repo/static/flatpak/index/static
      tags: latest
  ```
