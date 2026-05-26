#!/usr/bin/env bash
# github repository configuration
set -euo pipefail

REPO="kmontocam/amox"
ENVIRONMENT="release"
BRANCH="main"
TAG_PATTERN="v*"

if ! gh repo view "${REPO}" &>/dev/null; then
  gh repo create "${REPO}" \
    --public \
    --source=. \
    --remote=origin
fi

gh repo edit "${REPO}" \
  --default-branch="${BRANCH}" \
  --description="Schema on read based logging" \
  --enable-wiki=false \
  --enable-projects=false \
  --delete-branch-on-merge \
  --enable-squash-merge \
  --enable-merge-commit=false \
  --enable-rebase-merge=false

gh api "repos/${REPO}/environments/${ENVIRONMENT}" -X PUT --silent --input - <<EOF
{
  "deployment_branch_policy": {
    "protected_branches": false,
    "custom_branch_policies": true
  }
}
EOF

existing_branch=$(gh api "repos/${REPO}/environments/${ENVIRONMENT}/deployment-branch-policies" \
  --jq ".branch_policies[] | select(.name == \"${BRANCH}\") | .name")

if [ -z "${existing_branch}" ]; then
  gh api "repos/${REPO}/environments/${ENVIRONMENT}/deployment-branch-policies" -X POST --silent \
    -f name="${BRANCH}"
fi

existing_tag=$(gh api "repos/${REPO}/environments/${ENVIRONMENT}/deployment-branch-policies" \
  --jq ".branch_policies[] | select(.name == \"${TAG_PATTERN}\" and .type == \"tag\") | .name")

if [ -z "${existing_tag}" ]; then
  gh api "repos/${REPO}/environments/${ENVIRONMENT}/deployment-branch-policies" -X POST --silent \
    -f name="${TAG_PATTERN}" -f type="tag"
fi

existing_protection=$(gh api "repos/${REPO}/tags/protection" \
  --jq ".[] | select(.pattern == \"${TAG_PATTERN}\") | .pattern" 2>/dev/null || true)

if [ -z "${existing_protection}" ]; then
  gh api "repos/${REPO}/tags/protection" -X POST --silent -f pattern="${TAG_PATTERN}"
fi

# require PRs (no approval needed), block force pushes
gh api "repos/${REPO}/branches/${BRANCH}/protection" -X PUT --silent --input - <<EOF
{
  "required_status_checks": null,
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 0
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "block_creations": false
}
EOF
