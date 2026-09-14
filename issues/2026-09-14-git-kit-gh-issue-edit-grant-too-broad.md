## Summary
`Bash(gh issue edit:*)` in `github-issue-lifecycle` reaches title/body/assignee/milestone edits, not just the `p:` label reconciliation it's meant for — enforcement is prose-only, not tool-scoped.

## Environment
- **Product/Service**: `git-kit` plugin, `github-issue-lifecycle` skill
- **Region/Version**: git-kit 1.0.0-alpha.5

## Reproduction Steps
1. Inspect `plugins/git-kit/skills/github-issue-lifecycle/SKILL.md`'s `allowed-tools` grant: `Bash(gh issue edit:*)`.
2. Run `gh issue edit --help` — confirms it also accepts `--title`, `--body`, `--add-assignee`/`--remove-assignee`, `--milestone`, not just `--add-label`/`--remove-label`.
3. Note the skill's own Boundaries section states the actual bound is "the documented workflow steps" only — a prose convention, not something the tool-scoping syntax itself enforces.

## Expected Behavior
The grant should be narrow enough (or wrapped) that a misdirected or prompt-injected run genuinely cannot edit an issue's title/body/assignee/milestone — only its `p:` labels.

## Actual Behavior
Claude Code's `Bash(cmd:*)` scoping syntax can only narrow by command prefix, not by flag — so `Bash(gh issue edit:*)` cannot be restricted to `--add-label`/`--remove-label` alone without an enforcing wrapper script. The skill's Boundaries section documents this as a known limitation ("the actual bound is the documented workflow steps, not the grant itself"), consistent with the same tradeoff already accepted for this file's other broad grants (`Bash(gh api repos/*/issues/*:*)`, unscoped `Write`).

## Error Details
~~~
N/A -- not a runtime error, a permission-scoping gap.
~~~

## Visual Evidence
N/A

## Impact
**Major** (per CodeRabbit's automated review) — a misdirected or prompt-injected agent run could modify public issue metadata (title, body, assignee, milestone) beyond this skill's intended purpose. Currently accepted as a disclosed, consistent tradeoff (the same pattern already used for this file's other broad grants), not silently unaddressed.

## Additional Context
- Suggested fix direction (from the finding): route label updates through a label-only helper/API boundary, or enforce an argument allowlist, before granting this permission — a new script component that would need its own `plugin-rulebook` (R6 tool-scoping) and `.claude/rules/require-security-review-before-new-gate.md` `security-reviewer` pass.
- Broader pattern: the same file's own Boundaries section carries the identical prose-only-bound caveat for `Bash(gh api repos/*/issues/*:*)` and unscoped `Write` — worth deciding whether a general wrapper-script convention is warranted for `git-kit`'s guard scripts, rather than fixing this one grant in isolation.
- Suggested labels: `p: medium`, `t: security`, `a: ai-setup`

## Review Finding Source
- PR: https://github.com/AndreHahm/andres-cc-marketplace/pull/326
- Head SHA at time of finding: `dd1d9c95702687e328ef99b0eff5a16d243f7423`
- Review thread: https://github.com/AndreHahm/andres-cc-marketplace/pull/326#discussion_r4008587574
- Reviewer: CodeRabbit (automated)
- Severity: Major/Security ("Heavy lift")
