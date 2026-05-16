# Development Workflow

## Branch Protection

The `main` branch is protected. All changes must be made on a dedicated branch and merged via a GitHub Pull Request reviewed and approved by the project owner.

## Branching Model

Branches are always created from an up-to-date `main`:

```bash
git checkout main
git pull origin main
git checkout -b <type>/<short-description>
```

Branch prefix by task type:

| Prefix  | When to use                                  |
|---------|----------------------------------------------|
| `feat/` | New feature or behaviour                     |
| `fix/`  | Bug fix                                      |
| `chore/`| Tooling, CI, dependency updates, refactoring |

## Pre-Commit Checklist

Before committing, verify both of these pass:

```bash
# Linting (Ruff + Pylint on changed files)
script/lint

# Formatting check
script/check_format
```

Fix any issues before creating the commit.

## Manual / UI Testing

Test the integration using Playwright MCP against `http://localhost:8123`.

If the HA dev server is not running, start it with:

```bash
script/develop.sh
```

The Lovelace card resource also needs to be available. Start the sibling project from its directory:

```bash
cd ../crop-planner-card
yarn start
```

Both services must be running before running Playwright tests.

## Pushing and Pull Requests

After pushing the branch, verify that the PR description accurately reflects the actual changes. Update it if the description is stale or incomplete before requesting review.

## Releases

Releases are always created with the release script:

```bash
script/release.sh [--bump major|minor|patch|snapshot] [--pre <suffix>] [--yes]
```

### Flags

| Flag | Values | Description |
|------|--------|-------------|
| `--bump` | `major`, `minor`, `patch`, `snapshot` | Version component to increment. `snapshot` keeps the base version as-is. |
| `--pre` | any string, e.g. `RC1`, `beta-1` | Appends a pre-release suffix (`0.9.0-RC1`). Required on non-`main` branches. |
| `--yes` | — | Skips the confirmation prompt. |

The script runs lint and tests before bumping, updates `pyproject.toml` and `manifest.json`, commits, tags, and pushes.

### Version bump behaviour

When the current version is already a pre-release (e.g. `0.9.0-beta-1`), the base number was already bumped for that cycle. Promoting it to stable or cutting another pre-release reuses the same base — it does not bump again.

### Examples

```bash
# Stable patch release from main (interactive suffix prompt)
script/release.sh --bump patch

# Stable minor release from main, no prompt
script/release.sh --bump minor --yes

# First beta from a feature branch
script/release.sh --bump minor --pre beta-1

# Subsequent beta on the same branch
script/release.sh --bump snapshot --pre beta-2

# Release candidate from main
script/release.sh --bump patch --pre RC1
```

When releasing from a feature or fix branch, use incremental **beta** suffixes (`beta-1`, `beta-2`, …) and use `--bump snapshot` for each subsequent cut so the base version is not bumped again.
