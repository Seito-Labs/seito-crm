#!/usr/bin/env bash
# CI build script — builds and pushes the Seito CRM image to Artifact Registry.
#
# Adapted from deploy/image-build/build.sh (the local/manual script, in the
# infra-planning workspace, NOT this repo — kept as-is with its content-verification
# step). Two real differences here, not cosmetic:
#
#   1. Post-push content verification is REMOVED — an explicit, discussed decision.
#      See CI_CD_PLAN.md's pushback table and FUTURE_IMPROVEMENTS.md item 18 for the
#      residual risk this accepts: nothing now catches a build that silently contains
#      the wrong commit, the way this exact class of bug was caught once before.
#
#   2. Repo paths and the commit to build come from the calling workflow, not resolved
#      here via `git fetch`. The workflow already knows exactly which commit triggered
#      it (github.sha) — re-resolving "origin/main" inside this script would risk
#      building a DIFFERENT, newer commit than the one this run is actually for, if
#      main moved again while this run was queued waiting for manual approval.
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
