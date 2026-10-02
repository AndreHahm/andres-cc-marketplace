# Local Identifiers in Committed Files (R9 extension)

Full detail for R9's second clause. `SKILL.md` carries the rule's statement and a pointer here. Forward-looking,
like R28-R30: checked on newly-created or modified files, not as a sweep of every committed file.

## What is checked

R9 already forbids credentials. This clause adds a second class of leak: a **real local-machine identifier**
committed in a fixture, eval output, recorded report or JSON file — the author's operating-system username
inside an absolute path, and, as a judged case, a real local project directory name. These show up when a command's output is
saved verbatim as an eval fixture or a recorded run (issues #285, #320, #256).

Three path shapes are checked, with their regular expressions in
`assets/settings.json → rules.R9_no_hardcoded_credentials.config.local_identifier_patterns` (not copied here, so
the two cannot drift):

- a POSIX home directory, `/home/<name>/`
- a macOS home directory, `/Users/<name>/`
- a Windows profile path, `C:\Users\<name>` (and its JSON-escaped form with doubled backslashes)

Only these three shapes are matched mechanically. A recorded absolute path in a generated record is the same
kind of leak even when it has no recognizable username, for example a workstation-specific `report_path` that is
not portable across checkouts (issue #256), but there is no pattern for it: the reviewing agent judges it and
reports an ADVISORY. Known limit: a real project directory name after a placeholder username
(`/home/runner/<private-project>/`) is not detected, because the placeholder exempts the whole path. Prefer a
repo-relative path.

## What is not a finding

- A placeholder name: `<user>`, `username`, `you`, `example`, `runner`, `ubuntu`, and the other names in
  `config.placeholder_names`. Synthetic fixture users (`devuser`, `jane`, `jdoe`) belong in that list too.
- An illustrative example the surrounding text presents as one, including a redaction script's own test input —
  its job is to show what gets redacted. Judgment call, the same way R34's illustrative exemption is.
- Mirrored or generated copies of a source file already reported once (`.claude/`, `.agents/`, `.codex/`): report
  the canonical source, not every copy.

## Severity

REQUIRED, like the rest of R9: a real username in one of the three path shapes in a committed fixture is a FAIL. A judged absolute path with no recognizable username is ADVISORY.

## Fix

Replace the real name with a placeholder (`<user>`) or a repo-relative path, then regenerate the fixture or
record. If the identifier is already in git history, rewriting history is a separate decision for the
maintainer; this rule only stops new leaks.
