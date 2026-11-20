#!/bin/bash
# Runs test-block-dangerous-command.sh once per awk installed here (gawk, mawk, busybox awk), since
# the hook's heredoc filter and flag scanner are awk programs and awks differ (Windows gawk drops
# CRs unless BINMODE is set). When the jq on PATH writes newlines as CRLF (a native Windows
# jq.exe), each awk also runs with a jq that writes LF only, the output a Linux jq gives.
#
# Each variant puts small wrapper scripts named `awk` (and `jq`) first on PATH, in a temporary
# folder that is removed on exit. On Linux, Git Bash and WSL alike, run it from the repository:
#   bash .codex/hooks/tests/test-block-dangerous-command-matrix.sh [path-to-hook]
set -uo pipefail

SUITE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/test-block-dangerous-command.sh"
command -v jq >/dev/null 2>&1 || { echo "FAIL: jq is required" >&2; exit 1; }

WORK=$(mktemp -d)
trap 'rm -r "${WORK}"' EXIT

# wrapper <dir> <name> <command...>: writes <dir>/<name> that runs <command...> "$@".
wrapper() {
    local dir=$1 name=$2
    shift 2
    mkdir -p "${dir}"
    printf '#!/bin/sh\nexec %s "$@"\n' "$(printf '%q ' "$@")" >"${dir}/${name}"
    chmod +x "${dir}/${name}"
}

awks=()
for a in gawk mawk; do
    command -v "${a}" >/dev/null 2>&1 && awks+=("${a}")
done
command -v busybox >/dev/null 2>&1 && busybox awk 'BEGIN{}' 2>/dev/null && awks+=("busybox")
[[ ${#awks[@]} -gt 0 ]] || { echo "FAIL: no gawk, mawk or busybox awk found" >&2; exit 1; }

jq_modes=(native)
if [[ "$(jq -rn '"a\nb"')" == $'a\r\nb' ]]; then
    jq_modes+=(lf)
    wrapper "${WORK}/jq-lf" jq "$(command -v jq)" -b
fi

failed=0
for a in "${awks[@]}"; do
    if [[ "${a}" == busybox ]]; then
        wrapper "${WORK}/awk-${a}" awk "$(command -v busybox)" awk
    else
        wrapper "${WORK}/awk-${a}" awk "$(command -v "${a}")"
    fi
    for mode in "${jq_modes[@]}"; do
        path="${WORK}/awk-${a}:${PATH}"
        [[ "${mode}" == lf ]] && path="${WORK}/jq-lf:${path}"
        echo "== awk=${a} jq=${mode}"
        PATH="${path}" bash "${SUITE}" "$@" || failed=$((failed + 1))
    done
done

[[ "${failed}" -eq 0 ]] || { echo "FAIL: ${failed} variant(s) failed" >&2; exit 1; }
echo "All variants passed."
