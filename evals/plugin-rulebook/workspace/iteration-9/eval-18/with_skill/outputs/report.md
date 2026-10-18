# Eval 18 report (blind agent, with_skill)

Skill A: REQUIRED FAIL. `bash -c <path>` is a shell given a command string, so it counts as a direct run, not
interpreter use. The committed mode is 100644, not 100755. Fix: `git update-index --chmod=+x` on the script in
every mirrored copy, including `.claude/`, then re-check with `git ls-files -s`.

Skill B: no finding. `bash -eu -o pipefail <one plain path>` is an interpreter with known-safe options and one
script path. The script is read as a file and needs no executable bit, so mode 100644 is fine. At most an
informational note. No fix needed.
