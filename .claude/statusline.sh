#!/bin/bash
# Two-line statusline with visual context progress bar
#
# Line 1: Model and reasoning effort, folder, branch, open PR, push and working-tree state
# Line 2: Progress bar, context % (with a compaction hint from 80%), cost, lines changed,
#         duration, cache hit rate
#
# Context % uses Claude Code's pre-calculated remaining_percentage,
# which accounts for compaction reserves. 100% = compaction fires.
#
# Wired in this repo's .claude/settings.json ("statusLine"). Requires jq.
# Claude Code's statusline docs don't say whether CLAUDE_PROJECT_DIR is set for
# a statusLine command or which directory it runs in, so the entry falls back
# to the current directory when the variable is unset.
#

# Read stdin (Claude Code passes JSON data via stdin)
stdin_data=$(cat)

# Single jq call - extract all values at once
# Prefer pre-calculated remaining_percentage (100 - remaining = used toward compact)
# Fall back to manual calc from raw tokens if not available
IFS=$'\t' read -r current_dir model_name cost lines_added lines_removed duration_ms ctx_used cache_pct < <(
    echo "$stdin_data" | jq -r '[
        .workspace.current_dir // "unknown",
        .model.display_name // "Unknown",
        (try (.cost.total_cost_usd // 0 | . * 100 | floor / 100) catch 0),
        (.cost.total_lines_added // 0),
        (.cost.total_lines_removed // 0),
        (.cost.total_duration_ms // 0),
        (try (
            if (.context_window.remaining_percentage // null) != null then
                (100 - .context_window.remaining_percentage) | floor
            elif (.context_window.context_window_size // 0) > 0 then
                (((.context_window.current_usage.input_tokens // 0) +
                  (.context_window.current_usage.cache_creation_input_tokens // 0) +
                  (.context_window.current_usage.cache_read_input_tokens // 0)) * 100 /
                 .context_window.context_window_size) | floor
            else "null" end
        ) catch "null"),
        (try (
            (.context_window.current_usage // {}) |
            if (.input_tokens // 0) + (.cache_read_input_tokens // 0) > 0 then
                ((.cache_read_input_tokens // 0) * 100 /
                 ((.input_tokens // 0) + (.cache_read_input_tokens // 0))) | floor
            else 0 end
        ) catch 0)
    ] | @tsv' | tr -d '\r'
)

# Bash-level fallback: if jq crashed entirely, extract fields individually
if [ -z "$current_dir" ] && [ -z "$model_name" ]; then
    current_dir=$(echo "$stdin_data" | jq -r '.workspace.current_dir // .cwd // "unknown"' 2>/dev/null)
    model_name=$(echo "$stdin_data" | jq -r '.model.display_name // "Unknown"' 2>/dev/null)
    cost=$(echo "$stdin_data" | jq -r '(.cost.total_cost_usd // 0)' 2>/dev/null)
    lines_added=$(echo "$stdin_data" | jq -r '(.cost.total_lines_added // 0)' 2>/dev/null)
    lines_removed=$(echo "$stdin_data" | jq -r '(.cost.total_lines_removed // 0)' 2>/dev/null)
    duration_ms=$(echo "$stdin_data" | jq -r '(.cost.total_duration_ms // 0)' 2>/dev/null)
    # Windows jq emits CRLF; command substitution strips only the \n
    for v in current_dir model_name cost lines_added lines_removed duration_ms; do
        printf -v "$v" '%s' "${!v%$'\r'}"
    done
    ctx_used=""
    cache_pct="0"
    : "${current_dir:=unknown}"
    : "${model_name:=Unknown}"
    : "${cost:=0}"
    : "${lines_added:=0}"
    : "${lines_removed:=0}"
    : "${duration_ms:=0}"
fi

# Reasoning effort: the documented `effort.level` field (absent when the model has no
# effort parameter), else the CLAUDE_EFFORT environment variable; hidden when neither is set.
effort_level=$(echo "$stdin_data" | jq -r '.effort.level // empty' 2>/dev/null | tr -d '\r')
: "${effort_level:=${CLAUDE_EFFORT:-}}"

# Open PR for the current branch: the documented `pr.number` field, present only while
# Claude Code finds an open PR or merge request. Digits only, so nothing else is printed.
pr_number=$(echo "$stdin_data" | jq -r '.pr.number // empty' 2>/dev/null | tr -d '\r')
[[ "$pr_number" =~ ^[0-9]+$ ]] || pr_number=""

# Git info
if cd "$current_dir" 2>/dev/null; then
    git_branch=$(git -c core.useBuiltinFSMonitor=false branch --show-current 2>/dev/null)
    git_root=$(git -c core.useBuiltinFSMonitor=false rev-parse --show-toplevel 2>/dev/null)
    # One local `git status` call (no network): commits ahead of/behind the upstream as of the
    # last fetch, changed files (staged, unstaged or conflicted) and untracked files.
    if [ -n "$git_root" ]; then
        read -r git_ahead git_behind git_changed git_untracked < <(
            git -c core.useBuiltinFSMonitor=false status --porcelain=v2 --branch 2>/dev/null | awk '
                /^# branch\.ab / { a = substr($3, 2); b = substr($4, 2) }
                /^[12u] /        { c++ }
                /^\? /           { u++ }
                END { print a + 0, b + 0, c + 0, u + 0 }'
        )
    fi
fi

# Build repo path display (folder name only for brevity)
if [ -n "$git_root" ]; then
    repo_name=$(basename "$git_root")
    if [ "$current_dir" = "$git_root" ]; then
        folder_name="$repo_name"
    else
        folder_name=$(basename "$current_dir")
    fi
else
    folder_name=$(basename "$current_dir")
fi

# Generate visual progress bar for context usage
progress_bar=""
bar_width=12

if [ -n "$ctx_used" ] && [ "$ctx_used" != "null" ]; then
    filled=$((ctx_used * bar_width / 100))
    empty=$((bar_width - filled))

    if [ "$ctx_used" -lt 50 ]; then
        bar_color='\033[32m'  # Green (0-49%)
    elif [ "$ctx_used" -lt 80 ]; then
        bar_color='\033[33m'  # Yellow (50-79%)
    else
        bar_color='\033[31m'  # Red (80-100%)
    fi

    progress_bar="${bar_color}"
    for ((i=0; i<filled; i++)); do
        progress_bar="${progress_bar}█"
    done
    progress_bar="${progress_bar}\033[2m"
    for ((i=0; i<empty; i++)); do
        progress_bar="${progress_bar}⣿"
    done
    progress_bar="${progress_bar}\033[0m"

    ctx_pct="ctx ${ctx_used}%"
    # From 80% (red bar) on, prompt a decision; whether compacting or a handoff fits
    # depends on the task, which the status line cannot know.
    if [ "$ctx_used" -ge 80 ]; then
        ctx_pct="${ctx_pct} \033[31m→ /compact or handoff\033[0m"
    fi
else
    ctx_pct=""
fi

# Session time (human-readable)
if [ "$duration_ms" -gt 0 ] 2>/dev/null; then
    total_sec=$((duration_ms / 1000))
    hours=$((total_sec / 3600))
    minutes=$(((total_sec % 3600) / 60))
    seconds=$((total_sec % 60))
    if [ "$hours" -gt 0 ]; then
        session_time="${hours}h ${minutes}m"
    elif [ "$minutes" -gt 0 ]; then
        session_time="${minutes}m ${seconds}s"
    else
        session_time="${seconds}s"
    fi
else
    session_time=""
fi

# Separator
SEP='\033[2m│\033[0m'

# Get short model name (e.g., "Opus" instead of "Claude 3.5 Opus")
short_model=$(echo "$model_name" | sed -E 's/Claude [0-9.]+ //; s/^Claude //')

# LINE 1: [Model · effort] folder | branch
if [ -n "$effort_level" ]; then
    line1=$(printf '\033[37m[%s · %s]\033[0m' "$short_model" "$effort_level")
else
    line1=$(printf '\033[37m[%s]\033[0m' "$short_model")
fi
line1="$line1 $(printf '\033[94m📁 %s\033[0m' "$folder_name")"
if [ -n "$git_branch" ]; then
    line1="$line1 $(printf '%b \033[96m🌿 %s\033[0m' "$SEP" "$git_branch")"
    if [ -n "$pr_number" ]; then
        line1="$line1 $(printf '\033[94m#%s\033[0m' "$pr_number")"
    fi
    # ↑ not pushed, ↓ not pulled, ● changed files, + untracked files; each only when non-zero.
    git_state=""
    [ "${git_ahead:-0}" -gt 0 ] 2>/dev/null && git_state+=" \033[33m↑${git_ahead}\033[0m"
    [ "${git_behind:-0}" -gt 0 ] 2>/dev/null && git_state+=" \033[35m↓${git_behind}\033[0m"
    [ "${git_changed:-0}" -gt 0 ] 2>/dev/null && git_state+=" \033[31m●${git_changed}\033[0m"
    [ "${git_untracked:-0}" -gt 0 ] 2>/dev/null && git_state+=" \033[2m+${git_untracked}\033[0m"
    line1="$line1$(printf '%b' "$git_state")"
fi

# Cost always with two decimals ($1.50, not $1.5); keep the raw value if it isn't a number.
cost=$(LC_ALL=C printf '%.2f' "$cost" 2>/dev/null) || cost=${cost:-0}

# LINE 2: Progress bar | Context % | cost | lines changed | duration | cache hit rate
line2=""
if [ -n "$progress_bar" ]; then
    line2=$(printf '%b' "$progress_bar")
fi
if [ -n "$ctx_pct" ]; then
    if [ -n "$line2" ]; then
        line2="$line2 $(printf '\033[37m%s\033[0m' "$ctx_pct")"
    else
        line2=$(printf '\033[37m%s\033[0m' "$ctx_pct")
    fi
fi
if [ -n "$line2" ]; then
    line2="$line2 $(printf '%b \033[33m$%s\033[0m' "$SEP" "$cost")"
else
    line2=$(printf '\033[33m$%s\033[0m' "$cost")
fi
if [ "$lines_added" -gt 0 ] 2>/dev/null || [ "$lines_removed" -gt 0 ] 2>/dev/null; then
    line2="$line2 $(printf '%b \033[32m+%s\033[0m \033[31m−%s\033[0m' "$SEP" "$lines_added" "$lines_removed")"
fi
if [ -n "$session_time" ]; then
    line2="$line2 $(printf '%b \033[36m⏱ %s\033[0m' "$SEP" "$session_time")"
fi
# Prompt-cache hit rate of the last request; yellow below 70% so a drop stands out.
if [ "$cache_pct" -gt 0 ] 2>/dev/null; then
    if [ "$cache_pct" -lt 70 ]; then
        cache_color='\033[33m'
    else
        cache_color='\033[2m'
    fi
    line2="$line2 $(printf " ${cache_color}cache %s%%\033[0m" "$cache_pct")"
fi

printf '%b\n%b' "$line1" "$line2"
