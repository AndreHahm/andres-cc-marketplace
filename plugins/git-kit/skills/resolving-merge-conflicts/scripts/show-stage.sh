#!/bin/bash
# Prints a conflicted file's content at merge stage 2 (ours) or 3 (theirs).
# Exists so the skill's allowed-tools grant never exposes raw `git show` --
# `git show`/`git log`/`git diff` all accept `--output=<file>`, which under a
# wildcard Bash(git show:*) grant would let the caller write to any path the
# process can reach. This script's positional args become ref content, never
# additional git flags, so that path doesn't exist here.
# Usage: ./show-stage.sh <2|3> <file>

set -euo pipefail

stage="${1:-}"
file="${2:-}"

case "$stage" in
    2|3) ;;
    *)
        echo "Usage: show-stage.sh <2|3> <file>  (2=ours, 3=theirs)" >&2
        exit 1
        ;;
esac

if [[ -z "$file" ]]; then
    echo "Usage: show-stage.sh <2|3> <file>  (2=ours, 3=theirs)" >&2
    exit 1
fi

git show ":${stage}:${file}"
