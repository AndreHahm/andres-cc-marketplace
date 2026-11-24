#!/usr/bin/env bash
# Drop PATH entries inside the repository under review (issue #697).
#
# Sourced first, before any program runs, by cross-model-review's shell helpers. The skill's own
# chain carries the same lines, because it may run nothing from the working tree before the user
# approves it. Only shell built-ins are used. An entry is dropped when its directory, or one above
# it, is the checkout or (for a linked worktree) the main checkout, compared by identity for the
# entry as spelled and as resolved, and when it is empty, relative or cannot be entered. The main
# checkout is known only when the git directory's grandparent is named .git. An entry outside that
# holds a link to a program inside is not caught. Other worktrees are not known here.
# shellcheck disable=SC1007,SC2034  # an empty CDPATH is meant; PATH_FILTERED is for the skill's chain
# >>> path filter
ROOT=$(builtin pwd -P); while [ -n "$ROOT" ] && [ ! -e "$ROOT/.git" ] && [ ! -L "$ROOT/.git" ]; do ROOT=${ROOT%/*}; done; ROOT=${ROOT:-$(builtin pwd -P)}; MAIN=$ROOT; KEPT=; REST=$PATH:
[ ! -f "$ROOT/.git" ] || { IFS= read -r G < "$ROOT/.git" || true; G=${G#gitdir: }; G=${G%[[:cntrl:]]}; case $G in /*|[A-Za-z]:*) ;; *) G=$ROOT/$G;; esac; G=$(CDPATH= builtin cd -P -- "$G/../.." >/dev/null 2>&1 && builtin pwd -P) || G=; case $G in */.git) MAIN=${G%/.git};; esac; }
while [ -n "$REST" ]; do D=${REST%%:*}; REST=${REST#*:}; R=; case $D in /*) R=$(CDPATH= builtin cd -P -- "$D" >/dev/null 2>&1 && builtin pwd -P) || R=;; esac; IN=; for W in "$D" "$R"; do case $W in /*) ;; *) continue;; esac; while [ -n "$W" ] && [ -z "$IN" ]; do if [ "$W" -ef "$ROOT" ] || [ "$W" -ef "$MAIN" ]; then IN=1; fi; W=${W%/*}; done; done; if [ -n "$IN" ]; then PATH_FILTERED=1; else case $R in /*) KEPT=$KEPT:$D;; esac; fi; done; PATH=${KEPT#:}
# <<< path filter
[ -n "$PATH" ] || { echo "git-review-path.sh: no PATH entry outside the repository" >&2; exit 2; }
