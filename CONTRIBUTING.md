# Contributing to TunaOS

Thanks for wanting to contribute! TunaOS is a set of organizations-spanning
repositories that build bootable, immutable Linux desktop images from a matrix
of base OS × desktop × kernel × drivers, plus installer and migration tooling.

## Where things live

| Area | Repos |
|---|---|
| Image build factory | `tuna-os/tunaOS`, `tuna-os/tunaos-packages`, `tuna-os/tromso` |
| Installers | `tuna-os/bootc-installer`, `tuna-os/tuna-installer-{cosmic,kde,niri,xfce}` |
| Migration | `tuna-os/wootc`, `tuna-os/bootc-migrate` |
| Apps | `tuna-os/gtk-office-suite` (Letters, Tables, Decks), `tuna-os/Tavern` |
| Docs | `tuna-os/docs` (index lives in `docs/static/flatpak/index/static`) |

For the complete, authoritative inventory of active repositories, their default
branches, and which already have a `ROADMAP.md`, see [`ROADMAP-INDEX.md`](ROADMAP-INDEX.md)
before picking a repo. Several `tuna-os` repos do **not** default to `main` — that
document lists each repo's real default branch. This table lags, because new
repositories are added regularly; [`ROADMAP-INDEX.md`](ROADMAP-INDEX.md) is kept current.

## Getting started

1. **Pick a repository and open an issue first** — describe the change and
   why before writing code. Small fixes (typos, docs) can skip this.
2. **Fork the repo** (or ask a maintainer for push access) and create a
   branch off the repository's actual default branch — not an assumed `main`.
   We use the `arch/`, `fix/`, `feat/`, `chore/` prefix convention.
3. **Check the repo's `AGENTS.md` / `justfile`** — most repos standardize
   build/test/lint behind `just` recipes (`just build`, `just test`, `just fix`).
4. **Sign your commits** — every commit must be DCO-signed-off
   (`git commit -s`). This certifies you wrote the change and can license it.

## PR checklist

- [ ] Commit messages are signed off (`git commit -s`)
- [ ] `just fix` passes (format + lint) where the repo defines it
- [ ] Tests pass (`just test` or the relevant CI workflow)
- [ ] No secrets or machine-specific paths are committed
- [ ] Docs/changelog updated if behavior changed

## Architecture expectations

- **This is an image factory, not a distro.** Changes that alter built images
  must show evidence (build + boot + smoke test) in the PR.
- **One source of truth per artifact.** Before adding a new copy of a script,
  workflow, or spec, check whether a canonical version exists (e.g. the flatpak
  publish tooling, `update-index.py`). Prefer reusing it over copying.
- **Deliberate duplication is flagged.** Some frontends intentionally
  reimplement a shared contract per language (see
  `tuna-os/docs/docs/bootc-installer-asahi/UNIFIED-INSTALL-CONTRACT.md` —
  the `recipe.json` contract shared by the installer frontends). Match the
  contract; don't fork it.
- **Agents file `[architect]`/`[sec-check]`/`[strategist]` issues.** These are
  structural findings — treat them as prioritized backlog, not noise.

## Shared scripts and their canonical sources

Several utilities ship byte-identical copies across the organisation. Each has
one canonical location where a fix must land first, plus copies regenerated
from it.

| Utility | Canonical source | Copied to | Drift enforced |
|---|---|---|---|
| `check-renovate-automerge-policy.py` | `tuna-os/.github/scripts/` | `project-starter/scripts/` (shipped to new repos) | No — byte-identical today, but nothing enforces it |
| `check-workflow-permissions.py` | `tuna-os/.github/scripts/` | `project-starter/scripts/` (shipped to new repos) | No — byte-identical today, but nothing enforces it |
| `update-index.py` | `tuna-os/flatpak-index/scripts/` | `.github/actions/update-flatpak-index/` here; `.github/scripts/` in the flatpak-publishing app repos | Yes — weekly `flatpak-tooling-drift-check.yml` |

**Keeping copies in sync.** Fix `check-renovate-automerge-policy.py` and
`check-workflow-permissions.py` in `tuna-os/.github/scripts/`, then re-copy both
into `project-starter/scripts/` in the same commit so new repos start from the
corrected version. There is no automated gate — verify the two blobs are
byte-identical whenever you touch either. Fix `update-index.py` first in
`tuna-os/flatpak-index/scripts/` (the canonical source), update the synced copy
in `tuna-os/.github/.github/actions/update-flatpak-index/` to match, and get app
repos off their own copies by migrating them onto the reusable
`publish-flatpak.yml` workflow (or the `publish-flatpak-index` action) rather
than re-copying the script; the weekly drift check flags any repo that still
carries a divergent local copy.

**Verification cadence.** `update-index.py` is checked continuously by
`flatpak-tooling-drift-check.yml` (scheduled Mondays 06:00 UTC, and on
`workflow_dispatch`), which opens or comments on an issue whenever a repo has
drifted. The `check-*` scripts have no drift check today; add a byte-comparison
 in CI if you want the project-starter copy enforced rather than trusted.

## CI/CD security

Every workflow in a TunaOS repository must declare an explicit top-level
`permissions:` block, following the principle of least privilege:

```yaml
permissions:
  contents: read
```

A workflow with no block inherits the repository's configured default token
scope, which is almost always broader than the jobs actually need. This is the
baseline called for by
[tuna-os/.github#155](https://github.com/tuna-os/.github/issues/155).

- **New repos** inherit it for free: `project-starter/` ships a `ci.yml` with
  the block and a `workflow-permissions` job that runs the check.
- **Existing repos** should adopt it with the shared tooling from
  `tuna-os/.github`: copy `workflow-templates/ci.yml` (a compliant starting
  point) and run the check — `python3 scripts/check-workflow-permissions.py
  .github/workflows`. The script and a ready-to-run workflow ship there and are
  copied in.

## Getting help

- Ask in the relevant issue or PR.
- See the [architecture guide](https://github.com/tuna-os/docs/blob/main/docs/architecture.md) in `tuna-os/docs` — architecture overview, per-repository map, and the image/ISO build-pipeline reference.
- For reusable composite actions available to org workflows, see [`.github/actions/ACTIONS.md`](.github/actions/ACTIONS.md).
- For security issues, use the private channel described in `SECURITY.md` —
  never paste secrets or exploit details into a public issue.

<!-- hive-contribute-plea: donated-compute appeal, keep in sync across repos -->
## Contribute compute — no code needed

No time to write code? You can still push this project's backlog forward. This repository is worked by TunaOS AI-agent hives: lend a hive your AI subscription or API tokens and your machine runs contributor tasks from this project's backlog.

- 🪸 [Contribute compute to the reef hive](https://reef.tunaos.org/contribute)
- 🏫 [Contribute compute to the school hive](https://school.tunaos.org/contribute)
