#!/usr/bin/env bash
set -euo pipefail

PYPROJECT="pyproject.toml"
MANIFEST="custom_components/crop/manifest.json"

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
pytest

# ── 5. Version bump type ─────────────────────────────────────────────────────
CURRENT_VERSION=$(sed -n 's/^version = "\(.*\)"/\1/p' "$PYPROJECT")
# Strip any pre-release suffix (e.g. 0.2.0-beta-1 → 0.2.0)
BASE_VERSION="${CURRENT_VERSION%%-*}"
IFS='.' read -r MAJOR MINOR PATCH <<< "$BASE_VERSION"

echo ""
echo "Current version: $CURRENT_VERSION"
echo "Select version bump type:"
select BUMP_TYPE in major minor patch snapshot; do
  [[ -n "$BUMP_TYPE" ]] && break
  echo "Invalid selection."
done

# ── 6. Calculate new version ──────────────────────────────────────────────────
case "$BUMP_TYPE" in
  major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
  minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
  patch) PATCH=$((PATCH + 1)) ;;
  snapshot) ;; # keep MAJOR.MINOR.PATCH as-is
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH"

echo ""
if $IS_MAIN; then
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
read -rp "Proceed with this release? [y/N] " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
  echo "Aborted."
  exit 0
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

echo ""
echo "Released $TAG successfully."
