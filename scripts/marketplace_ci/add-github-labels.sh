#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# 🏷️  GitHub Labels Sync Script
# ──────────────────────────────────────────────────────────────────────────────
# Usage: ./scripts/marketplace_ci/add-github-labels.sh
#
# This script:
# 1. Reads labels from local .github/labels.yml
# 2. Fetches labels from GitHub remote (origin/main)
# 3. Warns and exits if remote has labels not defined locally
# 4. Creates labels that exist locally but not on remote
# 5. Updates labels where color or description differs
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# 🎨 Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LABELS_FILE="$REPO_ROOT/.github/labels.yml"

# Temp workspace (auto-cleaned on exit)
WORK_DIR=$(mktemp -d)
trap 'rm -rf "$WORK_DIR"' EXIT

LOCAL_JSON="$WORK_DIR/local.json"
REMOTE_JSON="$WORK_DIR/remote.json"
ANALYSIS_JSON="$WORK_DIR/analysis.json"

# Convert path to Windows format if running in Git Bash on Windows
# Use forward slashes to avoid Python string escaping issues
to_python_path() {
  if command -v cygpath > /dev/null 2>&1; then
    cygpath -w "$1" | sed 's/\\/\//g'
  else
    echo "$1"
  fi
}

printf "%b🏷️  GitHub Labels Sync%b\n" "$BLUE" "$NC"
printf "%b──────────────────────────────────────────────%b\n" "$CYAN" "$NC"

# ── 0. Prerequisites ──────────────────────────────────────────────────────────
printf "\n%b🔍 Checking prerequisites...%b\n" "$BLUE" "$NC"

for tool in gh python3; do
  if ! command -v "$tool" > /dev/null 2>&1; then
    printf "  %b❌ Required tool not found: %s%b\n" "$RED" "$tool" "$NC"
    exit 1
  fi
done

if ! python3 -c "import yaml" 2>/dev/null; then
  printf "  %b❌ Python 'yaml' module missing. Install via: pip install -r scripts/marketplace_ci/requirements.txt%b\n" "$RED" "$NC"
  exit 1
fi

if ! gh auth status > /dev/null 2>&1; then
  printf "  %b❌ GitHub CLI not authenticated. Run: gh auth login%b\n" "$RED" "$NC"
  exit 1
fi

if [ ! -f "$LABELS_FILE" ]; then
  printf "  %b❌ Labels file not found: %s%b\n" "$RED" "$LABELS_FILE" "$NC"
  exit 1
fi

printf "  ✅ All prerequisites satisfied\n"

# ── 1. Parse local labels from labels.yml ─────────────────────────────────────
printf "\n%b📄 Reading local labels from .github/labels.yml...%b\n" "$BLUE" "$NC"

python3 - "$(to_python_path "$LABELS_FILE")" "$(to_python_path "$LOCAL_JSON")" << 'PYEOF'
import yaml, json, sys
from collections import Counter

labels_file, output_file = sys.argv[1], sys.argv[2]
with open(labels_file) as f:
    data = yaml.safe_load(f)

labels = []
for entry in data.get('labels', []):
    labels.append({
        'name':        entry['name'],
        'color':       entry.get('color', '').upper().lstrip('#'),
        'description': entry.get('description', '') or ''
    })

names = [label['name'] for label in labels]
duplicates = [name for name, count in Counter(names).items() if count > 1]
if duplicates:
    print("  ❌ Duplicate label names found in .github/labels.yml:")
    for name in duplicates:
        print(f"     - {name}")
    sys.exit(1)

with open(output_file, 'w') as f:
    json.dump(labels, f)

print(f"  ✅ Parsed {len(labels)} local labels")
PYEOF

LOCAL_COUNT=$(python3 -c "import json; print(len(json.load(open('$(to_python_path "$LOCAL_JSON")'))))")

# ── 2. Fetch remote labels from GitHub ────────────────────────────────────────
printf "\n%b🌐 Fetching remote labels from GitHub...%b\n" "$BLUE" "$NC"

RAW_REMOTE="$WORK_DIR/remote_raw.json"
ERROR_FILE="$WORK_DIR/gh_error.txt"
if ! gh label list --json name,color,description --limit 1000 > "$RAW_REMOTE" 2> "$ERROR_FILE"; then
  printf "  %b❌ Failed to fetch remote labels. Check your gh authentication and repo access.%b\n" "$RED" "$NC"
  cat "$ERROR_FILE"
  exit 1
fi

# Check if output is empty (no labels exist yet)
if [ ! -s "$RAW_REMOTE" ]; then
  printf "  %b⚠️  No labels found on remote (empty repository). Creating empty list.%b\n" "$YELLOW" "$NC"
  echo "[]" > "$RAW_REMOTE"
fi

# Verify the output is valid JSON
if ! python3 -c "import json; json.load(open('$(to_python_path "$RAW_REMOTE")'))" 2>/dev/null; then
  printf "  %b❌ GitHub CLI returned invalid JSON. Error output:%b\n" "$RED" "$NC"
  cat "$RAW_REMOTE"
  if [ -s "$ERROR_FILE" ]; then
    cat "$ERROR_FILE"
  fi
  exit 1
fi

python3 - "$(to_python_path "$RAW_REMOTE")" "$(to_python_path "$REMOTE_JSON")" << 'PYEOF'
import json, sys

raw_file, output_file = sys.argv[1], sys.argv[2]
with open(raw_file) as f:
    labels = json.load(f)

normalized = []
for l in labels:
    normalized.append({
        'name':        l['name'],
        'color':       l.get('color', '').upper().lstrip('#'),
        'description': l.get('description', '') or ''
    })

with open(output_file, 'w') as f:
    json.dump(normalized, f)

print(f"  ✅ Fetched {len(normalized)} remote labels")
PYEOF

REMOTE_COUNT=$(python3 -c "import json; print(len(json.load(open('$(to_python_path "$REMOTE_JSON")'))))")

# ── 3. Analyze differences ────────────────────────────────────────────────────
python3 - "$(to_python_path "$LOCAL_JSON")" "$(to_python_path "$REMOTE_JSON")" "$(to_python_path "$ANALYSIS_JSON")" << 'PYEOF'
import json, sys

local_file, remote_file, analysis_file = sys.argv[1], sys.argv[2], sys.argv[3]

with open(local_file)  as f: local_labels  = {l['name']: l for l in json.load(f)}
with open(remote_file) as f: remote_labels = {l['name']: l for l in json.load(f)}

remote_only = [name for name in remote_labels if name not in local_labels]
local_only  = [name for name in local_labels  if name not in remote_labels]

diffs = []
for name, local in local_labels.items():
    if name in remote_labels:
        remote = remote_labels[name]
        color_diff = local['color'] != remote['color']
        desc_diff  = local['description'] != remote['description']
        if color_diff or desc_diff:
            diffs.append({
                'name':          name,
                'local_color':   local['color'],
                'remote_color':  remote['color'],
                'local_desc':    local['description'],
                'remote_desc':   remote['description'],
                'color_changed': color_diff,
                'desc_changed':  desc_diff
            })

with open(analysis_file, 'w') as f:
    json.dump({
        'remote_only': remote_only,
        'local_only':  local_only,
        'diffs':       diffs,
        'local_labels':  local_labels,
    }, f)
PYEOF

REMOTE_ONLY_COUNT=$(python3 -c "import json; print(len(json.load(open('$(to_python_path "$ANALYSIS_JSON")'))['remote_only']))")
LOCAL_ONLY_COUNT=$(python3 -c  "import json; print(len(json.load(open('$(to_python_path "$ANALYSIS_JSON")'))['local_only']))")
DIFFS_COUNT=$(python3 -c       "import json; print(len(json.load(open('$(to_python_path "$ANALYSIS_JSON")'))['diffs']))")

# ── 4. Warn and exit if remote has labels not defined locally ─────────────────
if [ "$REMOTE_ONLY_COUNT" -gt 0 ]; then
  printf "\n%b⚠️  WARNING: The following labels exist on remote but are NOT defined locally:%b\n" "$YELLOW" "$NC"
  python3 - "$(to_python_path "$ANALYSIS_JSON")" << 'PYEOF'
import json, sys
data = json.load(open(sys.argv[1]))
for name in data['remote_only']:
    print(f"  ⚠️  {name}")
PYEOF
  printf "\n%b  These labels must be added to .github/labels.yml before syncing.%b\n" "$YELLOW" "$NC"
  printf "%b  ❌ Sync aborted. Add the missing labels locally first.%b\n\n" "$RED" "$NC"
  exit 1
fi

printf "\n%b✅ No remote-only labels found. Safe to proceed.%b\n" "$GREEN" "$NC"

# ── 5 & 6. Status: labels to create ──────────────────────────────────────────
printf "\n%b📋 Status: Labels to create on remote (%s)%b\n" "$BLUE" "$LOCAL_ONLY_COUNT" "$NC"

if [ "$LOCAL_ONLY_COUNT" -eq 0 ]; then
  printf "  ✅ All local labels already exist on remote. Nothing to create.\n"
else
  python3 - "$(to_python_path "$ANALYSIS_JSON")" << 'PYEOF'
import json, sys
data = json.load(open(sys.argv[1]))
for name in data['local_only']:
    l = data['local_labels'][name]
    print(f"  + {name}  (#{l['color']})")
PYEOF
fi

# ── 7. Create missing labels on remote ────────────────────────────────────────
if [ "$LOCAL_ONLY_COUNT" -gt 0 ]; then
  printf "\n%b➕ Creating %s missing label(s) on remote...%b\n" "$BLUE" "$LOCAL_ONLY_COUNT" "$NC"
  CREATED=0
  FAILED=0

  while IFS= read -r line; do
    IFS=$'\t' read -r NAME COLOR DESC < <(
      printf '%s' "$line" | python3 -c "import json,sys; l=json.loads(sys.stdin.read()); print(l['name'], l['color'], l['description'], sep='\t')"
    )

    if gh label create "$NAME" --color "$COLOR" --description "$DESC" > /dev/null 2>&1; then
      printf "  %b✅ Created: %s%b\n" "$GREEN" "$NAME" "$NC"
      CREATED=$((CREATED + 1))
    else
      printf "  %b❌ Failed:  %s%b\n" "$RED" "$NAME" "$NC"
      FAILED=$((FAILED + 1))
    fi
  done < <(python3 - "$(to_python_path "$ANALYSIS_JSON")" << 'PYEOF'
import json, sys
data = json.load(open(sys.argv[1]))
for name in data['local_only']:
    print(json.dumps(data['local_labels'][name]))
PYEOF
)

  printf "\n%b📋 Create summary: %s created, %s failed%b\n" "$BLUE" "$CREATED" "$FAILED" "$NC"
fi

# ── 9 & 10. Status: labels with color/description diffs ──────────────────────
printf "\n%b📋 Status: Labels with color/description differences (%s)%b\n" "$BLUE" "$DIFFS_COUNT" "$NC"

if [ "$DIFFS_COUNT" -eq 0 ]; then
  printf "  ✅ All existing labels are in sync. Nothing to update.\n"
else
  python3 - "$(to_python_path "$ANALYSIS_JSON")" << 'PYEOF'
import json, sys
data = json.load(open(sys.argv[1]))
for d in data['diffs']:
    changes = []
    if d['color_changed']: changes.append(f"color #{d['remote_color']} → #{d['local_color']}")
    if d['desc_changed']:  changes.append(f"description changed")
    print(f"  ~ {d['name']}  ({', '.join(changes)})")
PYEOF
fi

# ── 11. Update labels with diffs ──────────────────────────────────────────────
if [ "$DIFFS_COUNT" -gt 0 ]; then
  printf "\n%b🔄 Updating %s label(s) on remote...%b\n" "$BLUE" "$DIFFS_COUNT" "$NC"
  UPDATED=0
  FAILED_UPDATE=0

  while IFS= read -r line; do
    IFS=$'\t' read -r NAME COLOR DESC < <(
      printf '%s' "$line" | python3 -c "import json,sys; l=json.loads(sys.stdin.read()); print(l['name'], l['local_color'], l['local_desc'], sep='\t')"
    )

    if gh label edit "$NAME" --color "$COLOR" --description "$DESC" > /dev/null 2>&1; then
      printf "  %b✅ Updated: %s%b\n" "$GREEN" "$NAME" "$NC"
      UPDATED=$((UPDATED + 1))
    else
      printf "  %b❌ Failed:  %s%b\n" "$RED" "$NAME" "$NC"
      FAILED_UPDATE=$((FAILED_UPDATE + 1))
    fi
  done < <(python3 - "$(to_python_path "$ANALYSIS_JSON")" << 'PYEOF'
import json, sys
data = json.load(open(sys.argv[1]))
for d in data['diffs']:
    print(json.dumps(d))
PYEOF
)

  printf "\n%b📋 Update summary: %s updated, %s failed%b\n" "$BLUE" "$UPDATED" "$FAILED_UPDATE" "$NC"
fi

# ── 12. Summary ───────────────────────────────────────────────────────────────
printf "\n%b──────────────────────────────────────────────%b\n" "$CYAN" "$NC"
printf "%b📊 Sync Summary%b\n" "$BLUE" "$NC"
printf "  Local labels:    %s\n" "$LOCAL_COUNT"
printf "  Remote labels:   %s\n" "$REMOTE_COUNT"
printf "  Created:         %s\n" "${CREATED:-0}"
printf "  Updated:         %s\n" "${UPDATED:-0}"
printf "  Failed:          %s\n" "$(( ${FAILED:-0} + ${FAILED_UPDATE:-0} ))"

if [ "$(( ${FAILED:-0} + ${FAILED_UPDATE:-0} ))" -eq 0 ]; then
  printf "\n%b✅ Labels are fully in sync with GitHub.%b\n\n" "$GREEN" "$NC"
else
  printf "\n%b⚠️  Sync completed with errors. Check output above.%b\n\n" "$YELLOW" "$NC"
  exit 1
fi
