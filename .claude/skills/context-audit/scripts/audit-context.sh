#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: audit-context [--flagged] [--top <N>] [--json] [--help]

Static inventory of context-contributing sources: skills, CLAUDE.md files, auto-memory
files, plugins, and MCP servers.

Scans (user scope ~/.claude/skills, plus {project}/.claude/skills when present --
either scope alone is enough; the other is skipped, not an error):
  {scope}/skills/*/SKILL.md          Size and word count
  {scope}/skills/*/references/*.md   On-demand files (count)
  {scope}/skills/*/rules/*.md        On-demand skill resource (count) -- NOT the
                                      project's always-on surface, see below
  ~/.claude/rules/**/*.md and {project}/.claude/rules/**/*.md  Always-on files
                                      (count, discovered recursively; a rule scoped by
                                      its own `paths:` frontmatter is on-demand instead)
  ~/.claude/CLAUDE.md and project CLAUDE.md  Size and word count (recursive)
  ~/.claude/projects/<this-project>/memory/*.md  Auto-memory files (footprint only)
  Plugins enabled at any scope (~/.claude/settings.json, {project}/.claude/settings.json,
                                      {project}/.claude/settings.local.json)
  MCP servers from every real source: settings.json, ~/.claude.json (user + this
                                      project's own local scope), {project}/.mcp.json
                                      (team scope), and each enabled plugin's own
                                      .mcp.json / .claude-plugin/plugin.json -- deduplicated
                                      by server name across the first four sources

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
  1  Neither ~/.claude/skills/ nor {project}/.claude/skills/ found
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
      [[ "$2" =~ ^[0-9]{1,9}$ ]] || { echo "--top value must be a non-negative integer: $2" >&2; exit 1; }
      TOP_N=$((10#$2))
      shift 2
      ;;
    --help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
  esac
done

SKILLS_DIR="$HOME/.claude/skills"
PROJECT_SKILLS_DIR="$(pwd)/.claude/skills"

# User scope is optional -- a machine with only project-local skills (no
# ~/.claude/skills/ at all) is a real, supported setup, not an error. Only
# fail if NEITHER scope has anything to scan.
if [[ ! -d "$SKILLS_DIR" && ! -d "$PROJECT_SKILLS_DIR" ]]; then
  # shellcheck disable=SC2088  # tilde in user-facing message is intentional
  echo "Neither ~/.claude/skills/ nor {project}/.claude/skills/ found" >&2
  exit 1
fi

# Helper: get word count and byte size in a single wc invocation instead of two
# separate subprocess spawns -- halves the subprocess count across this script's
# whole scan (one wc call per file instead of two), which is the actual cost
# driver against a real repo with hundreds of scanned files (each spawn measured
# at ~30ms on this platform per compact-track-and-suggest.sh's own comment).
# `wc -w -c` always prints "<words> <bytes>" in that fixed order regardless of
# flag order (GNU wc's own newline/word/byte canonical ordering) -- verified
# directly, not assumed from flag order. Sets the caller's own w/s variables
# directly (via `local -n` nameref) rather than echo+command-substitution, to
# avoid yet another subprocess per call.
file_words_and_size() {
  local -n _fws_w=$2 _fws_s=$3
  read -r _fws_w _fws_s < <(wc -w -c < "$1")
}

# Helper: escape a string for embedding in a JSON string literal. Covers
# backslash, quote, the named short-escapes (newline, tab, carriage return),
# and every other C0 control character (U+0001-U+001F, e.g. backspace,
# form feed) as \u00XX -- a filename can legally contain any of these
# except NUL (U+0000), which can't occur in a filename so isn't handled.
# A literal tab in a source name would also break this script's own
# internal tab-separated entry format upstream of this function -- an
# extremely rare edge case on real filesystems, disclosed here rather
# than reworked into a NUL-delimited internal format.
json_escape() {
  local s=$1
  s=${s//\\/\\\\}
  s=${s//\"/\\\"}
  s=${s//$'\r'/\\r}
  s=${s//$'\n'/\\n}
  s=${s//$'\t'/\\t}
  local out="" i c ord
  for (( i=0; i<${#s}; i++ )); do
    c="${s:i:1}"
    printf -v ord '%d' "'$c" 2>/dev/null || ord=32
    if (( ord < 32 )); then
      printf -v c '\\u%04x' "$ord"
    fi
    out+="$c"
  done
  printf '%s' "$out"
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

# Helper: scan one skills/ directory (user-scope or project-scope) for
# SKILL.md/references. A rules/ subdirectory bundled inside a skill (if one
# exists) is only ever loaded when that skill itself triggers -- it is a
# skill resource, not the project's real always-on rule surface, which is
# .claude/rules/*.md, scanned separately below.
scan_skills_dir() {
  local base_dir=$1
  local label_prefix=$2
  local skill_dir skill_name skill_file refs_dir ref_file ref_name
  local rules_dir rule_file rule_name s w flag

  for skill_dir in "$base_dir"/*/; do
    [[ -d "$skill_dir" ]] || continue
    skill_name=$(basename "$skill_dir")

    skill_file="$skill_dir/SKILL.md"
    if [[ -f "$skill_file" ]]; then
      file_words_and_size "$skill_file" w s
      flag="-"
      [[ $w -gt 500 ]] && flag="LARGE"
      entries+=("${label_prefix}${skill_name}/SKILL.md	$s	$w	on-trigger	$flag")
    fi

    refs_dir="$skill_dir/references"
    if [[ -d "$refs_dir" ]]; then
      for ref_file in "$refs_dir"/*.md; do
        [[ -f "$ref_file" ]] || continue
        ref_name=$(basename "$ref_file")
        file_words_and_size "$ref_file" w s
        entries+=("${label_prefix}${skill_name}/references/$ref_name	$s	$w	on-demand	-")
      done
    fi

    rules_dir="$skill_dir/rules"
    if [[ -d "$rules_dir" ]]; then
      for rule_file in "$rules_dir"/*.md; do
        [[ -f "$rule_file" ]] || continue
        rule_name=$(basename "$rule_file")
        file_words_and_size "$rule_file" w s
        entries+=("${label_prefix}${skill_name}/rules/$rule_name	$s	$w	on-demand	-")
      done
    fi
  done
}

# Scan SKILL.md files -- user scope if present, plus project scope (this
# run's cwd) whenever it has its own .claude/skills/ and isn't the same
# directory as the user scope (e.g. cwd == $HOME). Neither scope is
# mandatory on its own; the guard above already required at least one.
if [[ -d "$SKILLS_DIR" ]]; then
  scan_skills_dir "$SKILLS_DIR" "skills/"
fi

if [[ -d "$PROJECT_SKILLS_DIR" && "$PROJECT_SKILLS_DIR" != "$SKILLS_DIR" ]]; then
  scan_skills_dir "$PROJECT_SKILLS_DIR" "project-skills/"
fi

# Helper: does a rule file's YAML frontmatter declare a `paths:` field? Such
# a rule is conditional -- it only loads when Claude works with a matching
# file -- not always-on, per the official rules specification. A rule with
# no frontmatter, or frontmatter with no `paths:` field, is unconditional.
has_paths_frontmatter() {
  # awk's END block always runs after any exit from the main body (it
  # doesn't short-circuit the script) and its own exit code overrides an
  # earlier one -- so the "found" outcome must be carried via a variable
  # into END, not asserted with an early `exit 0`/`exit 1` directly.
  awk '
    NR==1 && $0=="---" { in_fm=1; next }
    in_fm && $0=="---" { exit }
    in_fm && /^paths:/ { found=1; exit }
    END { exit (found ? 0 : 1) }
  ' "$1"
}

# Helper: scan one .claude/rules/ directory (project-scope or user-scope)
# recursively -- Claude Code itself loads rules from subdirectories like
# rules/frontend/, per the official rules specification, not just the top
# level. A rule is flagged `always-on`/RULES unless its own frontmatter
# scopes it to specific paths, in which case it's `on-demand` instead.
scan_rules_dir() {
  local base_dir=$1
  local label_prefix=$2
  local rule_file rule_name s w

  while IFS= read -r rule_file; do
    [[ -z "$rule_file" ]] && continue
    rule_name="${rule_file#"$base_dir"/}"
    file_words_and_size "$rule_file" w s
    if has_paths_frontmatter "$rule_file"; then
      entries+=("${label_prefix}${rule_name}	$s	$w	on-demand	-")
    else
      entries+=("${label_prefix}${rule_name}	$s	$w	always-on	RULES")
    fi
  done < <(find "$base_dir" -type f -name "*.md" 2>/dev/null)
}

# .claude/rules/*.md -- the project's real always-on rule surface (unlike a
# skill-bundled rules/ directory above, these load into every session
# regardless of which skill, if any, is active) -- except for a rule scoped
# by its own `paths:` frontmatter, which is conditional instead.
PROJECT_RULES_DIR="$(pwd)/.claude/rules"
if [[ -d "$PROJECT_RULES_DIR" ]]; then
  scan_rules_dir "$PROJECT_RULES_DIR" "project-rules/"
fi

# ~/.claude/rules/ -- user-level rules apply to every project on this
# machine (loaded before project rules, which take priority on conflict),
# so they're just as much always-on context as the project's own rules.
USER_RULES_DIR="$HOME/.claude/rules"
if [[ -d "$USER_RULES_DIR" && "$USER_RULES_DIR" != "$PROJECT_RULES_DIR" ]]; then
  scan_rules_dir "$USER_RULES_DIR" "user-rules/"
fi

# CLAUDE.md files — global (the real path is ~/.claude/CLAUDE.md, not ~/CLAUDE.md)
GLOBAL_CLAUDE_MD="$HOME/.claude/CLAUDE.md"
if [[ -f "$GLOBAL_CLAUDE_MD" ]]; then
  file_words_and_size "$GLOBAL_CLAUDE_MD" w s
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
    file_words_and_size "$claude_file" w s
    flag="-"
    [[ $s -gt 2048 ]] && flag="LARGE"
    if [[ "$rel_path" == "CLAUDE.md" ]]; then
      entries+=("CLAUDE.md (project)	$s	$w	always-on	$flag")
    else
      entries+=("$rel_path	$s	$w	always-on	$flag")
    fi
  done < <(find "$(pwd)" -maxdepth 3 -name "CLAUDE.md" -type f 2>/dev/null)
fi

# Auto-memory files -- scoped to the CURRENT project only. Claude Code
# stores each project's memory under ~/.claude/projects/<encoded-cwd>/memory/,
# where <encoded-cwd> replaces every ".", ":", "/", and "\" in the absolute
# project path with "-" (verified against real on-disk project directories
# for this repo, including a worktree path containing a literal "." segment
# -- not guessed, and not the same as scanning every project's memory, which
# would let unrelated projects dominate this session's always-on total).
RAW_CWD=$(pwd -W 2>/dev/null || pwd)
PROJECT_HASH=$(printf '%s' "$RAW_CWD" | sed 's/[.:\/\\]/-/g')
CURRENT_MEMORY_DIR="$HOME/.claude/projects/$PROJECT_HASH/memory"
if [[ -d "$CURRENT_MEMORY_DIR" ]]; then
  for mem_file in "$CURRENT_MEMORY_DIR"/*.md; do
    [[ -f "$mem_file" ]] || continue
    mem_name=$(basename "$mem_file")
    file_words_and_size "$mem_file" w s
    flag="-"
    [[ $w -gt 300 ]] && flag="LARGE"
    entries+=("memory/$mem_name	$s	$w	always-on	$flag")
  done
fi

# Settings: plugins and MCP servers. Plugins can be enabled at user, project
# (tracked), or local (gitignored) scope; MCP servers can come from several
# independent sources beyond settings.json -- verified live against this
# machine's own real ~/.claude.json and this repo's real .claude/settings*
# files rather than assumed.
SETTINGS_FILE="$HOME/.claude/settings.json"
PROJECT_SETTINGS_FILE="$(pwd)/.claude/settings.json"
LOCAL_SETTINGS_FILE="$(pwd)/.claude/settings.local.json"
CLAUDE_JSON="$HOME/.claude.json"
PROJECT_MCP_JSON="$(pwd)/.mcp.json"
CURRENT_PROJECT_KEY=$(pwd -W 2>/dev/null || pwd)

plugin_count=0
mcp_count=0
plugin_names=()
plugin_analysis_available=true
plugin_count_json="0"
plugin_count_display="0"

if [[ -f "$SETTINGS_FILE" || -f "$PROJECT_SETTINGS_FILE" || -f "$LOCAL_SETTINGS_FILE" ]]; then
  if command -v jq &>/dev/null; then
    # Merge enabledPlugins across every scope that exists, precedence
    # user -> project -> local (a later file's value for the same key wins,
    # matching jq's own `add` semantics on an array of objects) -- a plugin
    # enabled only at project or local scope must not be invisible just
    # because ~/.claude/settings.json doesn't mention it.
    enabled_plugins_files=()
    [[ -f "$SETTINGS_FILE" ]] && enabled_plugins_files+=("$SETTINGS_FILE")
    [[ -f "$PROJECT_SETTINGS_FILE" ]] && enabled_plugins_files+=("$PROJECT_SETTINGS_FILE")
    [[ -f "$LOCAL_SETTINGS_FILE" ]] && enabled_plugins_files+=("$LOCAL_SETTINGS_FILE")

    plugin_count=$(jq -s '[.[] | .enabledPlugins // {}] | add | to_entries | map(select(.value == true)) | length' "${enabled_plugins_files[@]}" 2>/dev/null || echo 0)
    while IFS= read -r pname; do
      # Strip a trailing \r: some jq builds (notably native Windows jq.exe
      # piped through a Unix-style shell) write CRLF line endings on this
      # -r/raw-output path, and `read` only strips the \n, leaving a stray
      # \r attached to the plugin name -- breaks the case-match below and
      # would show up literally in the report.
      pname=${pname%$'\r'}
      [[ -n "$pname" ]] && plugin_names+=("$pname")
    done < <(jq -s -r '[.[] | .enabledPlugins // {}] | add | to_entries | map(select(.value == true) | .key | split("@")[0]) | .[]' "${enabled_plugins_files[@]}" 2>/dev/null)
    plugin_count_json="$plugin_count"
    plugin_count_display="$plugin_count"

    # MCP servers, deduplicated by name across every real source (a server
    # defined in more than one scope counts once):
    #  - settings.json's own top-level mcpServers (rare in practice on a
    #    real install, but harmless to keep checking)
    #  - ~/.claude.json's top-level mcpServers (user scope)
    #  - ~/.claude.json's .projects["<absolute-cwd>"].mcpServers (local
    #    scope, private to this project on this machine)
    #  - {project}/.mcp.json's mcpServers (team scope, tracked -- WRAPPED in
    #    an "mcpServers" key, unlike a plugin's own .mcp.json below)
    mcp_server_names=()
    while IFS= read -r name; do
      [[ -n "$name" ]] && mcp_server_names+=("$name")
    done < <(jq -r '.mcpServers // {} | keys[]' "$SETTINGS_FILE" 2>/dev/null)
    if [[ -f "$CLAUDE_JSON" ]]; then
      while IFS= read -r name; do
        [[ -n "$name" ]] && mcp_server_names+=("$name")
      done < <(jq -r '.mcpServers // {} | keys[]' "$CLAUDE_JSON" 2>/dev/null)
      while IFS= read -r name; do
        [[ -n "$name" ]] && mcp_server_names+=("$name")
      done < <(jq -r --arg cwd "$CURRENT_PROJECT_KEY" '.projects[$cwd].mcpServers // {} | keys[]' "$CLAUDE_JSON" 2>/dev/null)
    fi
    if [[ -f "$PROJECT_MCP_JSON" ]]; then
      while IFS= read -r name; do
        [[ -n "$name" ]] && mcp_server_names+=("$name")
      done < <(jq -r '.mcpServers // {} | keys[]' "$PROJECT_MCP_JSON" 2>/dev/null)
    fi
    if [[ ${#mcp_server_names[@]} -gt 0 ]]; then
      mcp_count=$(printf '%s\n' "${mcp_server_names[@]}" | sort -u | wc -l | tr -d ' ')
    fi

    # Plugins can also bundle their own MCP servers via a plugin-root
    # .mcp.json (servers as top-level keys directly -- NOT wrapped in an
    # "mcpServers" key, unlike a project-root .mcp.json above; verified
    # against the official plugin/MCP schema docs) or an inline
    # "mcpServers" field in .claude-plugin/plugin.json (the plugin
    # manifest's real location, not plugin-root) -- both auto-start when
    # the plugin is enabled. These are added on top, never deduplicated
    # against the sources above, since a plugin-provided server's actual
    # tool name is namespaced (mcp__plugin_<name>_<server>__<tool>) and
    # can't collide with a user/project-configured server sharing the same
    # short name. Checks the same install-path patterns this repo's own
    # setup-skill-improver.sh already uses: a direct (non-cached) install,
    # and a marketplace-cache install, which nests one more level than a
    # direct install -- cache/<marketplace>/<plugin>/<version>, not
    # cache/<marketplace>/<plugin> -- at both a single- and double-level
    # marketplace-cache path.
    for pname in "${plugin_names[@]}"; do
      for plugin_dir in \
        "$HOME/.claude/plugins/$pname" \
        "$HOME/.claude/plugins/cache"/*/"$pname"/* \
        "$HOME/.claude/plugins/cache"/*/*/"$pname"/*; do
        [[ -d "$plugin_dir" ]] || continue
        if [[ -f "$plugin_dir/.mcp.json" ]]; then
          n=$(jq 'keys | length' "$plugin_dir/.mcp.json" 2>/dev/null || echo 0)
          mcp_count=$((mcp_count + n))
        fi
        if [[ -f "$plugin_dir/.claude-plugin/plugin.json" ]]; then
          n=$(jq '.mcpServers // {} | keys | length' "$plugin_dir/.claude-plugin/plugin.json" 2>/dev/null || echo 0)
          mcp_count=$((mcp_count + n))
        fi
        break
      done
    done
  else
    # jq-free fallback can reliably count MCP servers from settings.json
    # alone (mcpServers has no per-entry enabled/disabled state -- every
    # top-level key is an active server), but NOT enabled plugins:
    # enabledPlugins entries can be true or false, and grep/sed can't
    # distinguish them without a real JSON parser. Reporting a plugin count
    # here would silently include disabled plugins as active, while
    # plugin_names (and so every per-plugin tool-count entry) stays empty --
    # an inconsistent, misleadingly-confident result. Report it as
    # unavailable instead. Multi-scope plugin merging and the additional MCP
    # sources above (~/.claude.json, project .mcp.json, plugin-bundled) all
    # require a real JSON parser too, so this fallback path stays scoped to
    # settings.json alone, same as before -- a disclosed limitation, not
    # silently wrong.
    plugin_analysis_available=false
    plugin_count_json="null"
    plugin_count_display="unavailable (no jq)"
    if [[ -f "$SETTINGS_FILE" ]]; then
      mcp_count=$(sed -n '/"mcpServers"/,/^  }/p' "$SETTINGS_FILE" 2>/dev/null | grep -cE '^    "[^"]*":' || true)
      mcp_count=${mcp_count:-0}
    fi
  fi
  flag="-"
  [[ $mcp_count -ge 5 ]] && flag="MCP"
  if [[ "$plugin_analysis_available" == true ]]; then
    entries+=("settings.json (${plugin_count} plugins, ${mcp_count} MCP)	0	0	always-on	$flag")
  else
    entries+=("settings.json (plugin count unavailable without jq, ${mcp_count} MCP)	0	0	always-on	$flag")
  fi

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

# Only MCP overhead is added here -- each enabled plugin already has its own
# "plugin: $pname (~N tools)" entry (added above) summed into
# total_always_on_words by the always-on loop, using its actual per-plugin
# tool_est*50 rather than a flat 50; adding plugin_count*50 again here would
# double-count every plugin's overhead.
total_always_on_words=$((total_always_on_words + mcp_count * 200))

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
  printf '  "totals": {"always_on_words": %d, "avg_trigger_words": %d, "skills": %d, "plugins": %s, "mcp_servers": %d}' \
    "$total_always_on_words" "$avg_trigger_words" "$trigger_count" "$plugin_count_json" "$mcp_count"
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
  echo "  Skills: $trigger_count | Plugins: $plugin_count_display | MCP servers: $mcp_count"
fi
