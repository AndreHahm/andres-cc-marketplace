#!/usr/bin/env bash
# Drop PATH entries inside the repository under review (issue #697).
#
# Sourced first, before any program runs, by cross-model-review's shell helpers. The skill's own
# chain carries the same lines, because it may run nothing from the working tree before the user
# approves it. Only shell built-ins and /usr/bin/readlink are used. An entry is dropped when its directory, or one above
# it, is the checkout, another worktree of the same repository (its `.git` names the same common git
# directory; the main checkout is one) or that git directory, compared by identity for the entry as
# spelled and as resolved, and when it is empty, relative or cannot be entered, or holds a control
# character as spelled or as resolved. It is dropped too
# when one of the programs named below, also with `.exe`, is a link there that leads inside or
# passes through (each step is checked), or one that /usr/bin/readlink cannot read or that leads to
# a name holding a control character. Every captured path keeps its trailing newlines (the `echo x`
# sentinel) and `.git`/`commondir` are read whole, with only one final line feed removed. A
# carriage return is kept on purpose, so the control-character check below treats it as inside:
# stricter than git, so a CRLF `.git` or `commondir` in the checkout stops the chain. A checkout at
# `/`, another worktree of this repository at `/`, or a git directory at `/` keeps no entry (the
# walk tests `/` as its own last step, since stripping a name from `/usr` leaves ""). A checkout
# or git directory path holding a control character keeps no entry, and a folder whose git
# directory path holds one counts as inside. An unreadable or empty `.git` file or `commondir`
# is treated the same way, and so is a checkout path that cannot be read at all (`pwd -P` failed).
# A link to any other program, a hard
# link, and an entry whose own folder link passes through are not caught.
# shellcheck disable=SC1007,SC2034  # an empty CDPATH is meant; PATH_FILTERED is for the skill's chain
# >>> path filter
_rv_common() { C=; if [ -d "$G/.git" ]; then C=$G/.git; elif [ -f "$G/.git" ]; then IFS= read -r -d '' C 2>/dev/null < "$G/.git" || true; C=${C#gitdir: }; C=${C%$'\n'}; [ -n "$C" ] || C=$'\x01'; case $C in /*|[A-Za-z]:*) ;; *) C=$G/$C;; esac; fi; if [ -n "$C" ] && [ -f "$C/commondir" ]; then D=; IFS= read -r -d '' D 2>/dev/null < "$C/commondir" || true; D=${D%$'\n'}; [ -n "$D" ] || D=$'\x01'; case $D in /*|[A-Za-z]:*) C=$D;; *) C=$C/$D;; esac; fi; }
_rv_inside() { while [ -n "$W" ] && [ -z "$IN" ]; do G=$W; _rv_common; case $C in *[[:cntrl:]]*) IN=1;; esac; if [ "$W" -ef "$ROOT" ] || { [ -n "$OWN" ] && { [ "$W" -ef "$OWN" ] || [ "${C:-/dev/null}" -ef "$OWN" ]; }; }; then IN=1; fi; W=${W%/*}; done; [ -n "$IN" ] || { G=; _rv_common; case $C in *[[:cntrl:]]*) IN=1;; esac; if [ -n "$OWN" ] && { [ / -ef "$OWN" ] || [ "${C:-/dev/null}" -ef "$OWN" ]; }; then IN=1; fi; }; }; CWD=$(builtin pwd -P && echo x) && CWD=${CWD%?x} || CWD=; ROOT=$CWD; while [ -n "$ROOT" ] && [ ! -e "$ROOT/.git" ] && [ ! -L "$ROOT/.git" ]; do ROOT=${ROOT%/*}; done; [ -n "$ROOT" ] || if [ -e /.git ] || [ -L /.git ]; then ROOT=/; else ROOT=$CWD; fi; G=$ROOT; _rv_common; OWN=$C; PATH_FILTERED=; KEPT=; REST=$PATH:; case $ROOT$OWN in *[[:cntrl:]]*) REST=;; esac; [ -n "$ROOT" ] || REST=; case $ROOT in /) [ -e /.git ] || [ -L /.git ] && REST=;; esac
while [ -n "$REST" ]; do D=${REST%%:*}; REST=${REST#*:}; P=$D; R=; case $D in /*) R=$(CDPATH= builtin cd -P -- "$D" >/dev/null 2>&1 && builtin pwd -P && echo x) && R=${R%?x} || R=;; esac; IN=; case $P$R in *[[:cntrl:]]*) IN=1;; esac; for A in "$P" "$R"; do case $A in /*) W=$A; _rv_inside;; esac; done; for A in git bash sh env python3 node codex grep find mktemp basename dirname realpath cat cp mv rm date touch cygpath gh; do for B in "$A" "$A.exe"; do if [ -n "$R" ] && [ -z "$IN" ] && [ -L "$R/$B" ] && [ -e "$R/$B" ]; then L=$R/$B; while [ -z "$IN" ] && [ -L "$L" ]; do T=$(/usr/bin/readlink -- "$L" 2>/dev/null && echo x) && T=${T%?x} || T=; case $T in ""|*[[:cntrl:]]*) IN=1;; /*) L=$T;; *) L=${L%/*}/$T;; esac; W=$L; _rv_inside; T=$(CDPATH= builtin cd -P -- "${L%/*}/" >/dev/null 2>&1 && builtin pwd -P && echo x) && T=${T%?x} || IN=1; case $T in *[[:cntrl:]]*) IN=1;; esac; L=$T/${L##*/}; W=$L; _rv_inside; done; fi; done; done; if [ -n "$IN" ]; then PATH_FILTERED=1; else case $R in /*) KEPT=$KEPT:$P;; esac; fi; done; PATH=${KEPT#:}
# <<< path filter
[ -n "$PATH" ] || { echo "git-review-path.sh: no PATH entry outside the repository" >&2; exit 2; }
