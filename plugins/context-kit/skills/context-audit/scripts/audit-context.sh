#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: audit-context [--flagged] [--top <N>] [--json] [--help]

Static inventory of context-contributing sources: skills, CLAUDE.md files, auto-memory
files, plugins, and MCP servers.

Scans:
  ~/.claude/skills/*/SKILL.md        Size and word count
  ~/.claude/skills/*/rules/*.md      Always-on files (count)
  ~/.claude/skills/*/references/*.md On-demand files (count)
  ~/CLAUDE.md and project CLAUDE.md  Size and word count (recursive)
  ~/.claude/projects/*/memory/*.md   Auto-memory files (footprint only)
  ~/.claude/settings.json            Plugins, MCP servers, and tool counts

For session token/model/tool-usage/frustration-signal analysis, use session-kit's
session-stats skill instead (if installed) — this script only inventories static,
always-on/on-trigger context footprint, not per-session JSONL data.

Options:
  --flagged           Only show items with flags (LARGE, RULES, MCP)
  --top <N>           Number of top entries to show, limits inventory entries by size.
  --json              Output as JSON
  --help              Show this help message

Exit codes:
  0  Success
  1  ~/.claude/skills/ not found
EOF
}

JSON_OUTPUT=false
FLAGGED_ONLY=false
TOP_N=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --json) JSON_OUTPUT=true; shift ;;
    --flagged) FLAGGED_ONLY=true; shift ;;
    --top)
      [[ $# -ge 2 ]] || { echo "--top requires a value" >&2; usage >&2; exit 1; }
      [[ "$2" =~ ^[0-9]+$ ]] || { echo "--top value must be a non-negative integer: $2" >&2; exit 1; }
      TOP_N=$((10#$2))
      shift 2
      ;;
    --help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
  esac
done

SKILLS_DIR="$HOME/.claude/skills"

if [[ ! -d "$SKILLS_DIR" ]]; then
  # shellcheck disable=SC2088  # tilde in user-facing message is intentional
  echo "~/.claude/skills/ not found" >&2
  exit 1
fi

# Helper: get file size in bytes (portable)
file_size() {
  wc -c < "$1" | tr -d ' '
}

# Helper: get word count
word_count() {
  wc -w < "$1" | tr -d ' '
}

# Helper: escape a string for embedding in a JSON string literal. Covers
# backslash, quote, and the control characters most plausible in a real
# filename (newline, tab, carriage return). A literal tab in a source name
# would also break this script's own internal tab-separated entry format
# upstream of this function -- an extremely rare edge case on real
# filesystems, disclosed here rather than reworked into a NUL-delimited
# internal format.
json_escape() {
  local s=$1
  s=${s//\\/\\\\}
  s=${s//\"/\\\"}
  s=${s//$'\r'/\\r}
  s=${s//$'\n'/\\n}
  s=${s//$'\t'/\\t}
  printf '%s' "$s"
}

# Helper: format bytes for display
format_size() {
  local bytes=$1
  if [[ $bytes -ge 1024 ]]; then
    echo "$(( (bytes + 512) / 1024 ))KB"
  else
    echo "${bytes}B"
  fi
}

# ── Static Inventory ─────────────────────────────────────────────

# Collect entries as tab-separated: source \t size_bytes \t words \t loads \t flag
entries=()

# Scan SKILL.md files
for skill_dir in "$SKILLS_DIR"/*/; do
  [[ -d "$skill_dir" ]] || continue
  skill_name=$(basename "$skill_dir")

  skill_file="$skill_dir/SKILL.md"
  if [[ -f "$skill_file" ]]; then
    s=$(file_size "$skill_file")
    w=$(word_count "$skill_file")
    flag="-"
    [[ $w -gt 500 ]] && flag="LARGE"
    entries+=("skills/$skill_name/SKILL.md	$s	$w	on-trigger	$flag")
  fi

  rules_dir="$skill_dir/rules"
  if [[ -d "$rules_dir" ]]; then
    for rule_file in "$rules_dir"/*.md; do
      [[ -f "$rule_file" ]] || continue
      rule_name=$(basename "$rule_file")
      s=$(file_size "$rule_file")
      w=$(word_count "$rule_file")
      entries+=("skills/$skill_name/rules/$rule_name	$s	$w	always-on	RULES")
    done
  fi

  refs_dir="$skill_dir/references"
  if [[ -d "$refs_dir" ]]; then
    for ref_file in "$refs_dir"/*.md; do
      [[ -f "$ref_file" ]] || continue
      ref_name=$(basename "$ref_file")
      s=$(file_size "$ref_file")
      w=$(word_count "$ref_file")
      entries+=("skills/$skill_name/references/$ref_name	$s	$w	on-demand	-")
    done
  fi
done

# CLAUDE.md files — global
if [[ -f "$HOME/CLAUDE.md" ]]; then
  s=$(file_size "$HOME/CLAUDE.md")
  w=$(word_count "$HOME/CLAUDE.md")
  flag="-"
  [[ $s -gt 2048 ]] && flag="LARGE"
  entries+=("CLAUDE.md (global)	$s	$w	always-on	$flag")
fi

# CLAUDE.md files — project root and subdirectories
# Discover all CLAUDE.md files under cwd (depth 3 max) excluding home dir
if [[ "$(pwd)" != "$HOME" ]]; then
  while IFS= read -r claude_file; do
    [[ -z "$claude_file" ]] && continue
    rel_path="${claude_file#"$(pwd)"/}"
    s=$(file_size "$claude_file")
    w=$(word_count "$claude_file")
    flag="-"
    [[ $s -gt 2048 ]] && flag="LARGE"
    if [[ "$rel_path" == "CLAUDE.md" ]]; then
      entries+=("CLAUDE.md (project)	$s	$w	always-on	$flag")
    else
      entries+=("$rel_path	$s	$w	always-on	$flag")
    fi
  done < <(find "$(pwd)" -maxdepth 3 -name "CLAUDE.md" -type f 2>/dev/null)
fi

# Auto-memory files
for mem_dir in "$HOME"/.claude/projects/*/memory/; do
  [[ -d "$mem_dir" ]] || continue
  project_hash=$(basename "$(dirname "$mem_dir")")
  for mem_file in "$mem_dir"*.md; do
    [[ -f "$mem_file" ]] || continue
    mem_name=$(basename "$mem_file")
    s=$(file_size "$mem_file")
    w=$(word_count "$mem_file")
    flag="-"
    [[ $w -gt 300 ]] && flag="LARGE"
    # Shorten project hash for display
    short_hash="${project_hash:0:20}"
    entries+=("memory/${short_hash}…/$mem_name	$s	$w	always-on	$flag")
  done
done

# Settings: plugins and MCP servers
SETTINGS_FILE="$HOME/.claude/settings.json"
plugin_count=0
mcp_count=0
plugin_names=()
if [[ -f "$SETTINGS_FILE" ]]; then
  # Count enabled plugins from enabledPlugins object
  if command -v jq &>/dev/null; then
    plugin_count=$(jq '[.enabledPlugins // {} | to_entries[] | select(.value == true)] | length' "$SETTINGS_FILE" 2>/dev/null || echo 0)
    while IFS= read -r pname; do
      [[ -n "$pname" ]] && plugin_names+=("$pname")
    done < <(jq -r '.enabledPlugins // {} | to_entries[] | select(.value == true) | .key | split("@")[0]' "$SETTINGS_FILE" 2>/dev/null)
    mcp_count=$(jq '.mcpServers // {} | keys | length' "$SETTINGS_FILE" 2>/dev/null || echo 0)
  else
    # Best-effort, jq-free fallback: scope each count to its own block and
    # require the 4-space indent Claude Code's settings.json uses for a
    # direct child key, so a server's own nested "command"/"args"/"env"
    # keys (6-space indent) aren't miscounted as additional MCP servers.
    plugin_count=$(sed -n '/"enabledPlugins"/,/^  }/p' "$SETTINGS_FILE" 2>/dev/null | grep -cE '^    "[^"]*":' || true)
    plugin_count=${plugin_count:-0}
    mcp_count=$(sed -n '/"mcpServers"/,/^  }/p' "$SETTINGS_FILE" 2>/dev/null | grep -cE '^    "[^"]*":' || true)
    mcp_count=${mcp_count:-0}
  fi
  flag="-"
  [[ $mcp_count -ge 5 ]] && flag="MCP"
  entries+=("settings.json (${plugin_count} plugins, ${mcp_count} MCP)	0	0	always-on	$flag")

  # Add per-plugin entries with estimated tool counts
  # Known tool counts for common plugins (tool descriptions always loaded)
  for pname in "${plugin_names[@]}"; do
    tool_est=2  # default estimate
    case "$pname" in
      playwright) tool_est=22 ;;
      context7) tool_est=2 ;;
      hookify) tool_est=5 ;;
      commit-commands) tool_est=4 ;;
      claude-code-setup) tool_est=2 ;;
      claude-md-management) tool_est=2 ;;
    esac
    pflag="-"
    [[ $tool_est -ge 10 ]] && pflag="HEAVY"
    entries+=("plugin: $pname (~${tool_est} tools)	0	$((tool_est * 50))	always-on	$pflag")
  done
fi

# Sort entries by size descending
sorted=()
while IFS= read -r line; do
  sorted+=("$line")
done < <(for e in "${entries[@]}"; do echo "$e"; done | sort -t$'\t' -k2 -rn)

# Compute totals
total_always_on_words=0
total_trigger_words=0
trigger_count=0

for entry in "${sorted[@]}"; do
  IFS=$'\t' read -r source size words loads flag <<< "$entry"
  case "$loads" in
    always-on)
      total_always_on_words=$((total_always_on_words + words))
      ;;
    on-trigger)
      total_trigger_words=$((total_trigger_words + words))
      trigger_count=$((trigger_count + 1))
      ;;
  esac
done

avg_trigger_words=0
[[ $trigger_count -gt 0 ]] && avg_trigger_words=$((total_trigger_words / trigger_count))

total_always_on_words=$((total_always_on_words + mcp_count * 200 + plugin_count * 50))

# Apply filters to create display list
display=()
count=0
for entry in "${sorted[@]}"; do
  IFS=$'\t' read -r source size words loads flag <<< "$entry"

  if [[ "$FLAGGED_ONLY" == true && "$flag" == "-" ]]; then
    continue
  fi

  display+=("$entry")
  count=$((count + 1))

  if [[ $TOP_N -gt 0 && $count -ge $TOP_N ]]; then
    break
  fi
done

filtered_count=${#display[@]}
total_count=${#sorted[@]}

# ── Output ───────────────────────────────────────────────────────

if [[ "$JSON_OUTPUT" == true ]]; then
  echo "{"
  echo '  "inventory": ['
  first=true
  for entry in "${display[@]}"; do
    IFS=$'\t' read -r source size words loads flag <<< "$entry"
    [[ "$first" == true ]] && first=false || echo ","
    printf '    {"source": "%s", "size_bytes": %s, "words": %s, "loads": "%s", "flag": "%s"}' \
      "$(json_escape "$source")" "$size" "$words" "$loads" "$flag"
  done
  echo ""
  echo "  ],"
  printf '  "showing": %d, "total_entries": %d,' "$filtered_count" "$total_count"
  echo ""
  printf '  "totals": {"always_on_words": %d, "avg_trigger_words": %d, "skills": %d, "plugins": %d, "mcp_servers": %d}' \
    "$total_always_on_words" "$avg_trigger_words" "$trigger_count" "$plugin_count" "$mcp_count"
  echo ""
  echo "}"
else
  # Markdown table
  if [[ $filtered_count -lt $total_count ]]; then
    echo "Showing $filtered_count of $total_count entries"
    echo ""
  fi

  printf "| %-50s | %7s | %5s | %-10s | %5s |\n" "Source" "Size" "Words" "Loads" "Flag"
  printf "|%-52s|%9s|%7s|%-12s|%7s|\n" "$(printf '%0.s-' {1..52})" "$(printf '%0.s-' {1..9})" "$(printf '%0.s-' {1..7})" "$(printf '%0.s-' {1..12})" "$(printf '%0.s-' {1..7})"

  for entry in "${display[@]}"; do
    IFS=$'\t' read -r source size words loads flag <<< "$entry"
    printf "| %-50s | %7s | %5s | %-10s | %5s |\n" "$source" "$(format_size "$size")" "$words" "$loads" "$flag"
  done

  echo ""
  echo "Totals:"
  echo "  Always-on context: ~${total_always_on_words} words (includes MCP/plugin overhead estimate)"
  echo "  Avg on-trigger cost: ~${avg_trigger_words} words per skill invocation"
  echo "  Skills: $trigger_count | Plugins: $plugin_count | MCP servers: $mcp_count"
fi
