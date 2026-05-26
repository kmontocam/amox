#!/usr/bin/env bash
# create an annotated tag from __version__ on main.
set -euo pipefail

BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [ "${BRANCH}" != "main" ]; then
  echo "error: must be on main to tag"
  exit 1
fi

VERSION=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' src/amox/__init__.py)
TAG="v${VERSION}"

if git tag -l "${TAG}" | grep -q "${TAG}"; then
  echo "error: tag ${TAG} already exists"
  exit 1
fi

git tag -a "${TAG}" -m "Release ${VERSION}"

echo "tagged ${TAG}"
echo "run: git push --tags"
