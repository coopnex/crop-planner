#!/usr/bin/env bash
set -euo pipefail

PYPROJECT="pyproject.toml"
MANIFEST="custom_components/crop/manifest.json"

# ── Usage ─────────────────────────────────────────────────────────────────────
usage() {
  echo "Usage: script/release.sh [--bump major|minor|patch|snapshot] [--pre RC1] [--yes]"
  echo ""
  echo "  --bump   Version bump type (major, minor, patch, snapshot)"
  echo "  --pre    Pre-release suffix (e.g. RC1, beta-1); required on non-main branches"
  echo "  --yes    Skip confirmation prompt"
  exit 1
}

ARG_BUMP=""
ARG_PRE=""
ARG_YES=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bump) ARG_BUMP="$2"; shift 2 ;;
    --pre)  ARG_PRE="$2";  shift 2 ;;
    --yes)  ARG_YES=true;  shift   ;;
    -h|--help) usage ;;
    *) echo "Unknown flag: $1" >&2; usage ;;
  esac
done

# ── 1. Uncommitted changes check ─────────────────────────────────────────────
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Error: You have uncommitted changes. Please commit or stash them first." >&2
  exit 1
fi

# ── 2. Branch check ───────────────────────────────────────────────────────────
BRANCH=$(git rev-parse --abbrev-ref HEAD)
IS_MAIN=false
[[ "$BRANCH" == "main" ]] && IS_MAIN=true

if ! $IS_MAIN; then
  echo "You are on branch '$BRANCH' (not main)."
  echo "Only pre-release tags are allowed (e.g. RC1, beta-1)."
fi

# ── 3. Lint ───────────────────────────────────────────────────────────────────
echo "Running lint..."
script/lint

# ── 4. Tests ──────────────────────────────────────────────────────────────────
echo "Running tests..."
script/run-in-env.sh pytest

# ── 5. Version bump type ─────────────────────────────────────────────────────
CURRENT_VERSION=$(sed -n 's/^version = "\(.*\)"/\1/p' "$PYPROJECT")
# Strip any pre-release suffix (e.g. 0.2.0-beta-1 → 0.2.0)
BASE_VERSION="${CURRENT_VERSION%%-*}"
IS_PRERELEASE=false
[[ "$CURRENT_VERSION" == *-* ]] && IS_PRERELEASE=true
IFS='.' read -r MAJOR MINOR PATCH <<< "$BASE_VERSION"

echo ""
echo "Current version: $CURRENT_VERSION"
$IS_PRERELEASE && echo "(current version is a pre-release)"

if [[ -n "$ARG_BUMP" ]]; then
  BUMP_TYPE="$ARG_BUMP"
  echo "Bump type: $BUMP_TYPE"
else
  echo "Select version bump type:"
  select BUMP_TYPE in major minor patch snapshot; do
    [[ -n "$BUMP_TYPE" ]] && break
    echo "Invalid selection."
  done
fi

# ── 6. Calculate new version ──────────────────────────────────────────────────
# When the current version is a pre-release (e.g. 0.6.3-RC1), the base number
# (0.6.3) was already bumped for that pre-release cycle. Promoting it to stable
# or adding another pre-release tag should reuse that same base — not bump again.
case "$BUMP_TYPE" in
  major)
    if $IS_PRERELEASE && [[ $MINOR -eq 0 && $PATCH -eq 0 ]]; then
      : # base already reflects the major bump
    else
      MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0
    fi ;;
  minor)
    if $IS_PRERELEASE && [[ $PATCH -eq 0 ]]; then
      : # base already reflects the minor bump
    else
      MINOR=$((MINOR + 1)); PATCH=0
    fi ;;
  patch)
    if $IS_PRERELEASE; then
      : # base already reflects the patch bump
    else
      PATCH=$((PATCH + 1))
    fi ;;
  snapshot) ;; # keep MAJOR.MINOR.PATCH as-is
  *) echo "Invalid bump type: $BUMP_TYPE" >&2; usage ;;
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH"

echo ""
if [[ -n "$ARG_PRE" ]]; then
  PRE_SUFFIX="$ARG_PRE"
  NEW_VERSION="$NEW_VERSION-$PRE_SUFFIX"
elif $IS_MAIN; then
  read -rp "Enter pre-release suffix (e.g. RC1, beta-1) or leave empty for a stable release: " PRE_SUFFIX
  [[ -n "$PRE_SUFFIX" ]] && NEW_VERSION="$NEW_VERSION-$PRE_SUFFIX"
else
  while true; do
    read -rp "Enter pre-release suffix (e.g. RC1, beta-1): " PRE_SUFFIX
    [[ -n "$PRE_SUFFIX" ]] && break
    echo "Pre-release suffix is required on non-main branches."
  done
  NEW_VERSION="$NEW_VERSION-$PRE_SUFFIX"
fi

echo ""
echo "Version bump: $CURRENT_VERSION → $NEW_VERSION"

if ! $ARG_YES; then
  read -rp "Proceed with this release? [y/N] " CONFIRM
  if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
  fi
fi

# Update version in pyproject.toml and manifest.json
sed -i "s/^version = \".*\"/version = \"$NEW_VERSION\"/" "$PYPROJECT"
sed -i "s/\"version\": \".*\"/\"version\": \"$NEW_VERSION\"/" "$MANIFEST"

# ── 7. Commit the version bump ────────────────────────────────────────────────
TAG="v$NEW_VERSION"
git add "$PYPROJECT" "$MANIFEST"
git commit -m "Release version $NEW_VERSION"

# ── 8. Create tag ─────────────────────────────────────────────────────────────
git tag "$TAG"
echo "Created tag: $TAG"

# ── 9. Push commits + tags ────────────────────────────────────────────────────
git push origin "$BRANCH"
git push origin "$TAG"

# ── 10. Create GitHub release ─────────────────────────────────────────────────
GH_FLAGS="--title $TAG --generate-notes"
[[ "$NEW_VERSION" == *-* ]] && GH_FLAGS="$GH_FLAGS --prerelease"
# shellcheck disable=SC2086
#gh release create "$TAG" $GH_FLAGS

echo ""
echo "Released $TAG successfully."
