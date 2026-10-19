# Author Checklist for New Scripts

For a script that runs `git` or another command. Written from the findings in #581 and PR #579. The
rationale for the `git`-through-`subprocess` items is in `docs/ci.md`, section "Codacy: `git` through
`subprocess` in plugin scripts"; it is not repeated here.

- [ ] **Reuse the script's existing helper** (`_git` in `git-verify-fix-diff.py` and
      `git-review-ledger.py`) instead of a new `subprocess.run` with a command held in a variable. Why a variable
      command is worse: `docs/ci.md`, same section.
- [ ] **Literal subcommand, list arguments, no `shell=True`.** Untrusted text only ever as a later list
      element, after `--` where the command supports it.
- [ ] **Keep a bare `git`** rather than an absolute path (see `docs/ci.md` for why).
- [ ] **Accepted shapes get an inline suppression with a reason**, on the line that opens the call and on
      the import for B404, in the exact form `docs/ci.md` gives. For any finding that is not
      a non-`Security` `Minor`/`Info` or an accepted shape, get approval first (`SKILL.md`, Decision rights).
- [ ] **Tests live in an already-excluded path** (`plugins/**/tests/**`, `tests/**`). A new `.codacy.yml`
      exclusion is a proposal that needs the rung 4 approval (`SKILL.md`), not part of the same unreviewed
      change.
- [ ] **Edit the canonical `plugins/` file only.** The `.claude/` mirror is generated.
- [ ] **No scratch or cache output in a shippable path.** Use the session scratchpad or a gitignored
      directory.
- [ ] **Run the local scan** before `create-pr`, once a config exists (`SKILL.md`, Local pre-PR scan).
- [ ] **After the push, collect again** and confirm the count dropped and the analysis is current.
