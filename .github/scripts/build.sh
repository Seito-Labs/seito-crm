#!/usr/bin/env bash
# CI build script — builds and pushes the Seito CRM image to Artifact Registry.
#
# CACHE_BUST is still set to the exact commit SHA — that is the actual fix for the
# staleness bug this whole design exists because of. Dropping verification does not
# make this step optional; do not remove it.
#
# Required environment variables (set by the calling workflow):
#   FRAPPE_CRM_DIR  - path to the checked-out frappe_crm repo (owns the Containerfile)
#   APPS_JSON       - path to apps.json (this repo's .github/scripts/apps.json)
#   REF             - branch name apps.json points at (e.g. "main")
#   FULL_SHA        - exact commit SHA to build (github.sha of the triggering push)

set -euo pipefail

: "${FRAPPE_CRM_DIR:?FRAPPE_CRM_DIR is required}"
: "${APPS_JSON:?APPS_JSON is required}"
: "${REF:?REF is required}"
: "${FULL_SHA:?FULL_SHA is required}"

REGISTRY="asia-south1-docker.pkg.dev/org-dev-infra/seito-crm/crm"
FRAPPE_BRANCH="version-16"
SHORT_SHA="${FULL_SHA:0:8}"
TAG="${REF}-${SHORT_SHA}"

echo "==> frappe_crm : $FRAPPE_CRM_DIR"
echo "==> commit     : $FULL_SHA"
echo "==> image      : ${REGISTRY}:${TAG}"
echo

# apps.json must point at the same ref we're tagging, or the tag lies about contents.
# Cheap, and has real value on its own: it would catch apps.json accidentally pointing
# at a fork or the wrong branch before that mistake ever reaches a build.
python3 - "$APPS_JSON" "$REF" <<'PY'
import json, sys
path, ref = sys.argv[1], sys.argv[2]
apps = json.load(open(path))
for a in apps:
    if "seito-crm" in a.get("url", "") and a.get("branch") != ref:
        sys.exit(f"ERROR: apps.json branch is {a.get('branch')!r} but building ref {ref!r}")
print(f"apps.json branch matches ref ({ref})")
PY

docker buildx build \
  -f "${FRAPPE_CRM_DIR}/images/layered/Containerfile" \
  --build-arg FRAPPE_BRANCH="${FRAPPE_BRANCH}" \
  --build-arg CACHE_BUST="${FULL_SHA}" \
  --secret id=apps_json,src="${APPS_JSON}" \
  -t "${REGISTRY}:${TAG}" \
  --push \
  "${FRAPPE_CRM_DIR}"

echo
echo "==> pushed ${REGISTRY}:${TAG}"

if [ -n "${GITHUB_OUTPUT:-}" ]; then
  echo "tag=${TAG}" >> "${GITHUB_OUTPUT}"
fi
