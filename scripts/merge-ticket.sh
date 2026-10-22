#!/usr/bin/env bash
# Merge an implementer branch into the current (integration) branch, then check it.
#
# Usage (from anywhere inside the repo, on the integration branch, clean working tree):
#   bash scripts/merge-ticket.sh <branch> [--feature <slug> --ticket <NN>]
#
# Steps:
#   1. git merge --no-ff --no-edit <branch>
#      Conflict -> git merge --abort, exit 3: dispatch a merger subagent.
#   2. With --feature/--ticket: scripts/check_hot_files.py --feature <slug> --ticket <NN> <before>..<branch>
#   3. The check command (default `npm run check --prefix frontend`).
#      Step 2 or 3 fails -> git reset --hard <before>, exit 1.
#
# Exit codes: 0 merged and checked (merge commit kept); 1 hot-file or check failure (rolled back);
# 2 usage error, dirty working tree, or the merge failed for another reason; 3 merge conflict (aborted).
#
# Env: AIGORA_MERGE_CHECK_CMD overrides the check command, e.g.
#   AIGORA_MERGE_CHECK_CMD='npm run check:fast --prefix frontend' bash scripts/merge-ticket.sh <branch>
set -u

usage() {
  sed -n '4,5p' "$0" | sed 's/^# \{0,1\}//' >&2
  exit 2
}

branch=""
feature=""
ticket=""
while [ $# -gt 0 ]; do
  case "$1" in
    --feature) [ $# -ge 2 ] || usage; feature="$2"; shift 2 ;;
    --ticket) [ $# -ge 2 ] || usage; ticket="$2"; shift 2 ;;
    -h|--help) usage ;;
    -*) echo "merge-ticket: unknown option $1" >&2; usage ;;
    *) [ -z "$branch" ] || usage; branch="$1"; shift ;;
  esac
done
[ -n "$branch" ] || usage
if { [ -n "$feature" ] && [ -z "$ticket" ]; } || { [ -z "$feature" ] && [ -n "$ticket" ]; }; then
  echo "merge-ticket: --feature and --ticket go together" >&2
  exit 2
fi

root=$(git rev-parse --show-toplevel) || exit 2
cd "$root" || exit 2

git rev-parse --verify --quiet "$branch^{commit}" >/dev/null || {
  echo "merge-ticket: no such branch or commit: $branch" >&2
  exit 2
}
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "merge-ticket: working tree has uncommitted changes; commit or set them aside first" >&2
  exit 2
fi

before=$(git rev-parse HEAD)
current=$(git rev-parse --abbrev-ref HEAD)
echo "merge-ticket: merging $branch into $current ($before)"

if ! git merge --no-ff --no-edit "$branch"; then
  if git rev-parse --verify --quiet MERGE_HEAD >/dev/null; then
    git merge --abort
    echo "merge-ticket: conflict merging $branch; merge aborted. Dispatch a merger subagent." >&2
    exit 3
  fi
  echo "merge-ticket: git merge failed; nothing merged" >&2
  exit 2
fi

rollback() {
  git reset --hard "$before" >/dev/null
  echo "merge-ticket: $1; reset $current to $before" >&2
  exit 1
}

if [ -n "$feature" ]; then
  echo "merge-ticket: hot-file check (feature $feature, ticket $ticket)"
  uv run --directory backend python ../scripts/check_hot_files.py \
    --feature "$feature" --ticket "$ticket" "$before..$branch" \
    || rollback "hot-file check failed"
fi

check_cmd="${AIGORA_MERGE_CHECK_CMD:-npm run check --prefix frontend}"
echo "merge-ticket: running $check_cmd"
bash -c "$check_cmd" || rollback "check failed ($check_cmd)"

echo "merge-ticket: merged $branch into $current; checks passed"
