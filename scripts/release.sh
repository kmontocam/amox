#!/usr/bin/env bash
# bump version, commit on a release branch. Optionally push and create PR.
set -euo pipefail

VERSION_FILE="src/lumberjack/__init__.py"
PYPROJECT_FILE="pyproject.toml"
LOCKFILE="uv.lock"
SEMVER_RE='^[0-9]+\.[0-9]+\.[0-9]+$'

PUSH=false
PR=false
VERSION=""

for arg in "$@"; do
  case "${arg}" in
  --push) PUSH=true ;;
  --pr) PR=true ;;
  *) VERSION="${arg}" ;;
  esac
done

if [ -z "${VERSION}" ]; then
  echo "usage: $0 [--push] [--pr] <version>"
  echo "example: $0 --push --pr 1.0.0"
  exit 1
fi

if ! [[ "${VERSION}" =~ ${SEMVER_RE} ]]; then
  echo "error: invalid semver: ${VERSION}"
  exit 1
fi

BRANCH="release/${VERSION}"

git checkout -b "${BRANCH}"

sed -i '' "s/__version__ = \"[^\"]*\"/__version__ = \"${VERSION}\"/" "${VERSION_FILE}"
echo "updated: ${VERSION_FILE}"

sed -i '' "s/^version = \"[^\"]*\"/version = \"${VERSION}\"/" "${PYPROJECT_FILE}"
echo "updated: ${PYPROJECT_FILE}"

uv lock
uv run taplo format "${PYPROJECT_FILE}"

git add "${VERSION_FILE}" "${PYPROJECT_FILE}" "${LOCKFILE}"
git commit -m "build: ${VERSION}"

echo ""
echo "version bumped to ${VERSION} on ${BRANCH}"

if [ "${PUSH}" = true ] || [ "${PR}" = true ]; then
  git push origin "${BRANCH}"
fi

if [ "${PR}" = true ]; then
  gh pr create --fill --base main
fi

if [ "${PUSH}" = false ]; then
  echo "  git push origin ${BRANCH}"
fi

if [ "${PR}" = false ]; then
  echo "  gh pr create --fill --base main"
fi
