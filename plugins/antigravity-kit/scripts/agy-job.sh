#!/usr/bin/env bash
#
# agy-job.sh — background-job layer over agy-delegate.sh, à la `codex --background`.
# For INTERACTIVE Claude Code sessions: fire a long delegation, keep working, then
# poll :status / fetch :result. (Headless `claude -p` is one-shot — use the wrapper
# synchronously there instead; there is no later turn to collect the result.)
#
# Usage:
#   agy-job.sh start  [agy-delegate options] "task"   # -> prints a JOB_ID, returns now
#   agy-job.sh list                                    # jobs started from this dir
#   agy-job.sh status <id>                             # running | done(rc) | failed
#   agy-job.sh result <id>                             # print stdout (+rc) when finished
#   agy-job.sh cancel <id>                             # terminate a running job
#
# Jobs live under ${ANTIGRAVITY_JOBS:-~/.antigravity-jobs}/<id>/ (out, err, rc, meta).
#
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DELEGATE="${AGY_DELEGATE:-$HERE/agy-delegate.sh}"
REG="${ANTIGRAVITY_JOBS:-$HOME/.antigravity-jobs}"

die() { echo "agy-job: $*" >&2; exit 1; }

# resolve a (possibly abbreviated) id to a job dir
jobdir() {
  [ -n "${1:-}" ] || die "need a job id"
  # Security review finding: the id comes straight from an untrusted slash-command
  # argument ($ARGUMENTS in status.md/result.md/cancel.md) with no validation at that
  # layer -- reject anything that isn't a plain path segment (no '/', no leading '.',
  # no glob metacharacters) before it ever reaches a path construction below.
  case "$1" in
    */*|.*|*[\[\]\*\?]*) die "invalid job id '$1'" ;;
  esac
  local resolved
  if [ -d "$REG/$1" ]; then resolved="$REG/$1"
  else
    local hits; hits=$(ls -d "$REG/$1"* 2>/dev/null)
    [ -n "$hits" ] || die "no such job: $1"
    [ "$(printf '%s\n' "$hits" | grep -c .)" -eq 1 ] || die "ambiguous id '$1'"
    resolved="$hits"
  fi
  # Defense in depth: confirm the resolved path is still a direct child of $REG (a
  # symlink under $REG could otherwise point elsewhere even past the character check).
  local real_reg real_resolved
  real_reg=$(cd "$REG" 2>/dev/null && pwd -P) || die "job registry unavailable: $REG"
  real_resolved=$(cd "$resolved" 2>/dev/null && pwd -P) || die "no such job: $1"
  case "$real_resolved" in
    "$real_reg"/*) : ;;
    *) die "invalid job id '$1'" ;;
  esac
  echo "$resolved"
}

# echoes running | done | failed. (rc is read directly from the file by callers —
# a global set here would NOT survive the `$(job_state ...)` command-substitution subshell.)
job_state() {
  local jd="$1" rc
  if [ -f "$jd/rc" ]; then
    rc="$(cat "$jd/rc")"
    if [ "$rc" = "0" ]; then echo "done"; else echo "failed"; fi
  elif [ -f "$jd/pid" ] && kill -0 "$(cat "$jd/pid")" 2>/dev/null; then
    echo running
  else
    echo failed   # pid gone, no rc recorded = crashed/killed
  fi
}

# Human label for a delegate exit code (mirrors agy-delegate.sh structured codes).
rc_label() {
  case "$1" in
    0)  echo 'ok' ;;
    2)  echo 'agy failed' ;;
    3)  echo 'empty output' ;;
    10) echo 'QUOTA — retry later with --continue' ;;
    11) echo 'AUTH required — run `agy` once interactively' ;;
    12) echo 'TIMEOUT — raise --timeout or narrow scope' ;;
    13) echo 'agy MISSING — install the Antigravity CLI' ;;
    14) echo 'MODEL unavailable — check `agy models` / tier remap' ;;
    # Both denial shapes: agy 1.1.3's soft deny and 1.1.13's hard error.
    15) echo 'PERMISSION denied (soft on 1.1.3+, a hard error by 1.1.13) — add a permissions.allow rule, or --yolo' ;;
    *)  echo 'error' ;;
  esac
}

cmd="${1:-}"; shift || true
case "$cmd" in
  start)
    [ $# -ge 1 ] || die "start needs delegate args, e.g.  start --tier pro \"task\""
    [ -x "$DELEGATE" ] || die "delegate not executable: $DELEGATE"
    id="$(date +%Y%m%d-%H%M%S)-$$-${RANDOM}"
    jd="$REG/$id"; mkdir -p "$jd"
    # Job output (task text, full stdout/stderr) can carry sensitive content -- keep the
    # registry and each job dir readable only by the owner, not the ambient umask default.
    chmod 700 "$REG" "$jd" 2>/dev/null || true
    { echo "id=$id"; echo "cwd=$PWD"; echo "started=$(date -u +%FT%TZ 2>/dev/null || date)";
      echo "task=$(printf '%s' "${!#}" | tr '\n' ' ' | cut -c1-200)"; } > "$jd/meta"
    ( nohup "$DELEGATE" "$@" >"$jd/out" 2>"$jd/err"; echo $? >"$jd/rc" ) >/dev/null 2>&1 &
    pid=$!
    echo "$pid" > "$jd/pid"
    # Best-effort process-start fingerprint, so `cancel` can tell a PID that has been
    # reused by an unrelated process apart from the job it actually started (a PID can
    # be recycled by the OS once the original job process has exited).
    ps -o lstart= -p "$pid" > "$jd/pid_start" 2>/dev/null || true
    disown 2>/dev/null || true
    echo "$id"
    ;;
  list)
    [ -d "$REG" ] || { echo "(no jobs)"; exit 0; }
    found=0
    for jd in "$REG"/*/; do
      [ -d "$jd" ] || continue
      cwd="$(sed -n 's/^cwd=//p' "$jd/meta" 2>/dev/null)"
      [ "${ALL:-0}" = "1" ] || [ "$cwd" = "$PWD" ] || continue
      found=1
      st="$(job_state "$jd")"
      printf '%-32s %-8s %s\n' "$(basename "$jd")" "$st" \
        "$(sed -n 's/^task=//p' "$jd/meta" 2>/dev/null)"
    done
    [ "$found" = "1" ] || echo "(no jobs for $PWD — set ALL=1 to see all)"
    ;;
  status)
    jd="$(jobdir "${1:-}")"; st="$(job_state "$jd")"
    rc="$(cat "$jd/rc" 2>/dev/null || true)"
    echo "job:    $(basename "$jd")"
    sed 's/^/  /' "$jd/meta" 2>/dev/null
    if [ -n "$rc" ]; then echo "  state=$st (rc=$rc: $(rc_label "$rc"))"; else echo "  state=$st"; fi
    sig="$(grep -m1 '^AGY_SIGNAL ' "$jd/err" 2>/dev/null || true)"
    if [ -n "$sig" ]; then echo "  signal=${sig#AGY_SIGNAL }"; fi
    ;;
  result)
    jd="$(jobdir "${1:-}")"; st="$(job_state "$jd")"
    if [ "$st" = "running" ]; then echo "still running — try again later"; exit 2; fi
    rc="$(cat "$jd/rc" 2>/dev/null || true)"
    [ -s "$jd/err" ] && { echo "----- stderr -----" >&2; cat "$jd/err" >&2; }
    cat "$jd/out" 2>/dev/null
    echo "[exit rc=${rc:-?}${rc:+: $(rc_label "$rc")}]" >&2
    ;;
  cancel)
    jd="$(jobdir "${1:-}")"
    if [ -f "$jd/rc" ]; then
      # Already recorded a completion -- the pid file's PID (if the OS has since
      # reused it) no longer belongs to this job, so there is nothing left to signal.
      echo "not running"
      exit 0
    fi
    pid="$(cat "$jd/pid" 2>/dev/null || true)"
    live=0
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      live=1
      if [ -s "$jd/pid_start" ]; then
        now_start="$(ps -o lstart= -p "$pid" 2>/dev/null || true)"
        stored_start="$(cat "$jd/pid_start" 2>/dev/null || true)"
        # A mismatch means the OS has recycled this PID for an unrelated process
        # since the job started -- refuse to signal it.
        [ -n "$now_start" ] && [ "$now_start" = "$stored_start" ] || live=0
      fi
    fi
    if [ "$live" = "1" ]; then
      # Walk the real PID tree (parent->child) rather than relying on process GROUPS:
      # `timeout` (used by agy-delegate.sh to bound the real agy call) puts its OWN
      # monitored command in a fresh process group of its own -- verified live -- so a
      # plain `pkill -P`/`kill` on the recorded pid alone misses that nested
      # timeout/agy subtree entirely, leaving it running (bounded only by timeout's own
      # --kill-after, not by this cancel). Collect every descendant PID first, then
      # signal each one individually -- this reaches the tree regardless of how many
      # times something below re-grouped itself.
      descendants() {
        local all=() frontier=("$1") next
        while [ "${#frontier[@]}" -gt 0 ]; do
          next=()
          for p in "${frontier[@]}"; do
            while IFS= read -r child; do
              [ -n "$child" ] || continue
              all+=("$child"); next+=("$child")
            done < <(ps -Ao pid=,ppid= 2>/dev/null | awk -v p="$p" '$2==p{print $1}')
          done
          frontier=("${next[@]}")
        done
        printf '%s\n' "${all[@]}"
      }
      tree="$pid $(descendants "$pid")"
      for p in $tree; do kill -TERM "$p" 2>/dev/null || true; done
      sleep 0.2
      for p in $tree; do kill -0 "$p" 2>/dev/null && kill -KILL "$p" 2>/dev/null || true; done
      echo "cancelled $(basename "$jd")"
    else
      echo "not running"
    fi
    ;;
  ""|-h|--help|help)
    sed -n '/^# Usage:/,/^# Jobs live/p' "$0" | sed 's/^# \{0,1\}//' ;;
  *) die "unknown subcommand '$cmd' (start|list|status|result|cancel)" ;;
esac
