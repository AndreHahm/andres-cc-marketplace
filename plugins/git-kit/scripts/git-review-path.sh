#!/usr/bin/env bash
# Drop PATH entries inside the repository under review (issue #697).
#
# Sourced first, before any program runs, by cross-model-review's shell helpers. The skill's own
# chain carries the same lines, because it may run nothing from the working tree before the user
# approves it. Only shell built-ins and /usr/bin/readlink are used. An entry is dropped when its directory, or one above
# it, is the checkout, another worktree of the same repository (its `.git` names the same common git
# directory; the main checkout is one) or that git directory, compared by identity for the entry as
# spelled and as resolved, and when it is empty, relative or cannot be entered. It is dropped too
# when one of the programs named below, also with `.exe`, is a link there that leads inside or
# passes through (each step is checked), or one that /usr/bin/readlink cannot read. A link to any other program, a hard
# link, and an entry whose own folder link passes through are not caught.
# shellcheck disable=SC1007,SC2034  # an empty CDPATH is meant; PATH_FILTERED is for the skill's chain
# >>> path filter
_rv_common() { C=; if [ -d "$1/.git" ]; then C=$1/.git; elif [ -f "$1/.git" ]; then IFS= read -r C 2>/dev/null < "$1/.git" || true; C=${C#gitdir: }; C=${C%[[:cntrl:]]}; case $C in /*|[A-Za-z]:*) ;; *) C=$1/$C;; esac; fi; if [ -n "$C" ] && [ -f "$C/commondir" ]; then D=; IFS= read -r D 2>/dev/null < "$C/commondir" || true; D=${D%[[:cntrl:]]}; case $D in /*|[A-Za-z]:*) C=$D;; *) C=$C/$D;; esac; fi; }
_rv_inside() { W=$1; while [ -n "$W" ] && [ -z "$IN" ]; do _rv_common "$W"; if [ "$W" -ef "$ROOT" ] || { [ -n "$OWN" ] && { [ "$W" -ef "$OWN" ] || [ "${C:-/dev/null}" -ef "$OWN" ]; }; }; then IN=1; fi; W=${W%/*}; done; }; ROOT=$(builtin pwd -P); while [ -n "$ROOT" ] && [ ! -e "$ROOT/.git" ] && [ ! -L "$ROOT/.git" ]; do ROOT=${ROOT%/*}; done; ROOT=${ROOT:-$(builtin pwd -P)}; _rv_common "$ROOT"; OWN=$C; PATH_FILTERED=; KEPT=; REST=$PATH:
while [ -n "$REST" ]; do D=${REST%%:*}; REST=${REST#*:}; P=$D; R=; case $D in /*) R=$(CDPATH= builtin cd -P -- "$D" >/dev/null 2>&1 && builtin pwd -P) || R=;; esac; IN=; for A in "$P" "$R"; do case $A in /*) _rv_inside "$A";; esac; done; for A in git bash sh env python3 node codex grep find mktemp basename dirname realpath cat cp mv rm date touch cygpath gh; do for B in "$A" "$A.exe"; do if [ -n "$R" ] && [ -z "$IN" ] && [ -L "$R/$B" ] && [ -e "$R/$B" ]; then L=$R/$B; while [ -z "$IN" ] && [ -L "$L" ]; do T=$(/usr/bin/readlink -- "$L" 2>/dev/null) || T=; case $T in "") IN=1;; /*) L=$T;; *) L=${L%/*}/$T;; esac; _rv_inside "$L"; T=$(CDPATH= builtin cd -P -- "${L%/*}/" >/dev/null 2>&1 && builtin pwd -P) || IN=1; L=$T/${L##*/}; _rv_inside "$L"; done; fi; done; done; if [ -n "$IN" ]; then PATH_FILTERED=1; else case $R in /*) KEPT=$KEPT:$P;; esac; fi; done; PATH=${KEPT#:}
# <<< path filter
[ -n "$PATH" ] || { echo "git-review-path.sh: no PATH entry outside the repository" >&2; exit 2; }
