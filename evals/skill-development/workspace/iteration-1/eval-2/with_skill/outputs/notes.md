# Notes

Followed skill-development, Convert path (references/slash-command-conversion.md, allowed-tools.md).

- Output: skills/release-notes/SKILL.md (single file; the command was one line, so no references/scripts).
- allowed-tools: original `Bash(git:*, gh:*)` is invalid grouping (a comma inside parentheses is not a separator). Rewrote as `Bash(git:*) Bash(gh:*)`, kept Read and Write. Every grant is used in the body (Phase 2 least-privilege check).
- Added `disable-model-invocation: true` so it stays user-invoked like the command (it overwrites a file).
- Checked `gh pr list --help`: default --limit is 30 and there is no tag filter; the body adds `--limit` and `--search "merged:>=date"` so it really does "since the last tag". Added no-tags handling.
- Description rewritten in third person with trigger phrases.
- Questions I could not ask, and assumptions: (1) placement: assumed plugin-style `skills/release-notes/` as the task specified; (2) keep user-invoke only; (3) Phases 3-5 (evals, description optimization) not run, out of scope here. Original command file left untouched (outside outputs dir); recommend removing it after validation.
- Not run: quick_validate.py, plugin-rulebook.
