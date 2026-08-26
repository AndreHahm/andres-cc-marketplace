#!/bin/bash
# Validates that all Git conflicts have been resolved
# Returns 0 if no conflicts remain, 1 otherwise

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}Error: Not a git repository${NC}" >&2
    exit 1
fi

# Function to check for conflict markers in files
check_conflict_markers() {
    local files_with_markers=()
    local unmerged
    unmerged=$(git diff -z --name-only --diff-filter=U 2>/dev/null || true)

    # If no unmerged paths remain, still scan every tracked file -- a resolved file can
    # be staged/committed with markers left inside it, and diff --diff-filter=U exits 0
    # with empty output in that case, not a failure that would trigger a fallback.
    # NUL-delimited throughout (`-z`, `-d ''`) rather than line-based: a path can legally
    # contain a newline, and a plain (non `-z`) listing C-quotes special characters -- either
    # way a line-based split can silently skip a file, which is exactly the failure mode this
    # check exists to catch. Same rationale as handle-deleted-modified.sh's own NUL-delimited
    # porcelain parsing.
    local files_to_check
    if [[ -n "$unmerged" ]]; then
        files_to_check="$unmerged"
    else
        files_to_check=$(git ls-files -z)
    fi

    while IFS= read -r -d '' file; do
        if [[ -f "$file" ]] && grep -l '^<<<<<<<\|^=======\|^>>>>>>>' "$file" > /dev/null 2>&1; then
            files_with_markers+=("$file")
        fi
    done <<< "$files_to_check"

    if [[ ${#files_with_markers[@]} -gt 0 ]]; then
        echo -e "${RED}✗ Found conflict markers in the following files:${NC}"
        printf '  %s\n' "${files_with_markers[@]}"
        return 1
    fi

    return 0
}

# Function to check for unmerged paths
check_unmerged_paths() {
    local unmerged_files
    unmerged_files=$(git diff --name-only --diff-filter=U 2>/dev/null || true)

    if [[ -n "$unmerged_files" ]]; then
        echo -e "${RED}✗ Found unmerged paths:${NC}"
        echo "$unmerged_files" | sed 's/^/  /'
        return 1
    fi

    return 0
}

# Function to check for delete-related conflicts (DU/UD/DD only -- AA/AU/UA are add/add
# conflicts, not deletions; those are still caught by check_unmerged_paths above, just not
# under this function's "delete/modify" label). Matches handle-deleted-modified.sh's own
# scope exactly, and SKILL.md Step 5's "Deleted-modified conflicts" description.
check_deleted_modified() {
    local status
    status=$(git status --porcelain 2>/dev/null || true)

    local deleted_modified=$(echo "$status" | grep -E '^(DU|UD|DD)[[:space:]]' || true)

    if [[ -n "$deleted_modified" ]]; then
        echo -e "${YELLOW}⚠ Found files with delete/modify conflicts:${NC}"
        echo "$deleted_modified" | sed 's/^/  /'
        return 1
    fi

    return 0
}

# Function to check merge state
check_merge_state() {
    if git rev-parse MERGE_HEAD > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠ Repository is still in merge state${NC}"
        echo "  Ask the resolving-merge-conflicts skill to hand off to its commit step once"
        echo "  resolved -- there is no 'git merge --continue'; a plain commit finalizes a merge"
        return 1
    fi

    if [[ -f .git/MERGE_HEAD ]]; then
        echo -e "${YELLOW}⚠ MERGE_HEAD file exists${NC}"
        return 1
    fi

    return 0
}

# Main validation
echo "🔍 Validating conflict resolution..."
echo ""

all_clear=true

if ! check_conflict_markers; then
    all_clear=false
fi

if ! check_unmerged_paths; then
    all_clear=false
fi

if ! check_deleted_modified; then
    all_clear=false
fi

if ! check_merge_state; then
    all_clear=false
fi

echo ""
if [[ "$all_clear" == true ]]; then
    echo -e "${GREEN}✓ All conflicts resolved successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Review changes: git diff --cached"
    echo "  2. Run tests to validate"
    echo "  3. Ask the resolving-merge-conflicts skill to hand off to its commit step"
    exit 0
else
    echo -e "${RED}✗ Conflicts still exist. Please resolve them before continuing.${NC}"
    exit 1
fi
