# R9 local-identifier clause: evals/demo/.../eval-1/with_skill/outputs/report.md

Source: SKILL.md R9 (line 180) and `references/local-identifiers.md`. The patterns and the placeholder-name list live in `assets/settings.json` under `rules.R9_no_hardcoded_credentials.config`. The clause is forward-looking, so it applies to this newly added file.

| # | Path | Finding? | Severity | Fix |
|---|------|----------|----------|-----|
| 1 | `/home/mara/projects/demo/src/app.py` (recorded command output) | Yes | REQUIRED, so FAIL | Replace `mara` with `<user>`, or use a repo-relative path (`src/app.py`). Regenerate the recorded output instead of leaving the verbatim capture. |
| 2 | `/home/user/projects/demo/src/app.py` (same recorded output) | No | None | None required. |
| 3 | `C:\\Users\\mara\\x` (redaction script's test input, in a section explaining what gets redacted) | No (judgment-call exemption) | None | None required. Optional hardening is noted below. |

## Reasoning

1. **`/home/mara/...` is a finding.** It matches the `posix_home` pattern (`/home/<name>/`). `mara` is not in `placeholder_names`, and it sits in recorded output, which is the leak class the rule targets (a command's output saved verbatim, issues #285, #320, #256). A real OS username in a committed eval output is a FAIL, REQUIRED like the rest of R9. The `/home/mara/projects/demo/` part may also be a real local project directory name, which the clause also covers. If the identifier is already in git history, rewriting history is a separate decision for the maintainer. The rule only stops new leaks.
2. **`/home/user/...` is not a finding.** It matches the `posix_home` regex, but `user` is on the placeholder list, and a placeholder name is explicitly "not a finding". The doc also says to prefer repo-relative paths for recorded absolute paths in generated records, so converting it is a harmless optional cleanup. It is not a violation.
3. **`C:\\Users\\mara\\x` is not a finding.** It matches the `windows_profile` pattern, which covers the JSON-escaped doubled-backslash form, and `mara` is not a placeholder. However, the file shows it as a redaction script's test input in a section explaining what gets redacted. The doc exempts an "illustrative example the surrounding text presents as one, including a redaction script's own test input". The doc calls this a judgment call, the same way R34's illustrative exemption is.
   - Optional hardening: if `mara` is a real username (finding 1 suggests it is), swap in a synthetic name such as `jane` so the illustration cannot itself be read as a leak. This is not required under the clause.

## Overall

One FAIL (path 1, REQUIRED). Paths 2 and 3 pass. If the same recorded output is mirrored under `.claude/`, `.agents/` or `.codex/`, report only the canonical source, not each mirror copy.
