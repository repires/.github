# tuna-os/.github

Organization-wide defaults, templates, and shared CI/CD tooling for the [`tuna-os`](https://github.com/tuna-os) GitHub organization. Nothing in this repository builds a standalone product; files here apply across other TunaOS repositories.

## Directory Structure

| Path | Contents |
|---|---|
| `.github/ISSUE_TEMPLATE/`, `.github/PULL_REQUEST_TEMPLATE.md` | Default issue forms (`bug.yml`, `feature.yml`, `adoption.yml`) and pull request template |
| `DISCUSSION_TEMPLATE/` | Default GitHub Discussion category forms |
| `.github/workflows/` | Reusable (`workflow_call`) workflows and repository policy checks — see [`docs/WORKFLOWS.md`](docs/WORKFLOWS.md) |
| `.github/actions/` | Reusable composite actions — see [`.github/actions/ACTIONS.md`](.github/actions/ACTIONS.md) |
| `.github/scripts/`, `scripts/` | Policy verifiers, CI contract and fork-safety validators, roadmap index generator, Auto-QA tuner, and unit tests — see [`docs/SCRIPTS.md`](docs/SCRIPTS.md) |
| `workflow-templates/` | Starter CI workflow template (`ci.yml`) for existing repositories |
| `project-starter/` | Copyable scaffold for new TunaOS repositories — see [`project-starter/README.md`](project-starter/README.md) |
| `profile/README.md` | Public organization profile rendered on [`github.com/tuna-os`](https://github.com/tuna-os) |
| `docs/` | Reference documentation for [reusable workflows](docs/WORKFLOWS.md), [validation scripts](docs/SCRIPTS.md), and [observability guidelines](docs/OBSERVABILITY.md) |
| `default.json`, `renovate.json` | Shared Renovate preset (`local>tuna-os/.github`) and this repository's Renovate configuration |
| `.claude/skills/` | Shared agent skills (`flatpak-oci-remote`, `hive-contribute`) |

## How Changes Propagate

Changes in this repository reach other `tuna-os` repositories through four mechanisms:

| Mechanism | Paths | Propagation |
|---|---|---|
| **Immediate inheritance** | `.github/ISSUE_TEMPLATE/`, `.github/PULL_REQUEST_TEMPLATE.md`, `DISCUSSION_TEMPLATE/`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md` | Applied automatically by GitHub to every organization repository that does not define its own copy |
| **Organization profile** | `profile/README.md` | Rendered directly on [`github.com/tuna-os`](https://github.com/tuna-os) |
| **Opt-in live references (`@main`)** | `.github/workflows/*.yml` (`workflow_call`), `.github/actions/*`, `default.json` | Active on the next run for every repository that references them via `uses: tuna-os/.github/...@main` or `"extends": ["local>tuna-os/.github"]` |
| **Copied templates** | `project-starter/`, `workflow-templates/`, `scripts/check-*.py` | Copied when scaffolding a new repository or adopting shared policy checks |

Inputs for reusable workflows and composite actions are a public contract because callers pin `@main`. Read [`AGENTS.md`](AGENTS.md) before you change workflow inputs, action interfaces, or shared scripts.

## When to Edit Here

- **Add or update a default template:** Edit `.github/ISSUE_TEMPLATE/`, `.github/PULL_REQUEST_TEMPLATE.md`, or `DISCUSSION_TEMPLATE/` for changes that apply to all repositories.
- **Update the organization profile page:** Edit [`profile/README.md`](profile/README.md) to update [`github.com/tuna-os`](https://github.com/tuna-os).
- **Add or change a shared workflow or composite action:** Edit `.github/workflows/` or `.github/actions/` and update [`docs/WORKFLOWS.md`](docs/WORKFLOWS.md) or [`.github/actions/ACTIONS.md`](.github/actions/ACTIONS.md).
- **Update the new-repository baseline:** Edit [`project-starter/`](project-starter/README.md) (keep synced scripts in `scripts/` and `project-starter/scripts/` byte-identical).

## Key Documents

- [`AGENTS.md`](AGENTS.md) — Maintainer and agent guide for blast radius, security rules, and policy checks
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — Contribution workflow, DCO sign-off requirements, and sync rules for shared scripts
- [`docs/WORKFLOWS.md`](docs/WORKFLOWS.md) — Reference and adoption guide for reusable workflows
- [`docs/SCRIPTS.md`](docs/SCRIPTS.md) — Reference guide for CI validation scripts and project-starter sync
- [`.github/actions/ACTIONS.md`](.github/actions/ACTIONS.md) — Index of reusable composite actions
- [`ROADMAP.md`](ROADMAP.md) & [`ROADMAP-INDEX.md`](ROADMAP-INDEX.md) — Organization enablement roadmap and active repository inventory (including non-`main` default branches)
- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) & [`SECURITY.md`](SECURITY.md) — Community standards and vulnerability disclosure policy
