## Summary
`commit/SKILL.md`'s trust-boundary check uses a cwd-relative `git ls-files` pathspec that fails open (reports "untracked") when run from any non-repo-root working directory.

## Environment
- **Product/Service**: `git-kit` plugin (this marketplace) — `commit` skill
- **Region/Version**: N/A
- **Browser/OS**: N/A

## Reproduction Steps
1. From the repo root, run `git ls-files --error-unmatch .claude/marketplace-sync.json` — exits `0` (matches, file is tracked).
2. From a subdirectory (e.g. `plugins/git-kit`), run the same command — fails: `error: pathspec '.claude/marketplace-sync.json' did not match any file(s) known to git`, exits `1`.
3. From the same subdirectory, run `git ls-files --error-unmatch :/.claude/marketplace-sync.json` (root-anchored `:/` pathspec) — exits `0`, matches correctly.
4. Read `plugins/git-kit/skills/commit/SKILL.md`'s step 2 ("Trust check (security)") — it runs `git ls-files --error-unmatch .claude/git-kit.local.json` (the same bare, cwd-relative form as step 2 above) and documents a non-zero exit as "the file is untracked (safe to trust for the fields below)".

## Expected Behavior
The trust-boundary check should correctly identify a tracked `.claude/git-kit.local.json` as tracked (and therefore untrusted for `commit_confirm_before_commit`, `commit_auto_stage`, `commit_auto_push`, `push_auto_pr`) regardless of the invoking shell's current working directory.

## Actual Behavior
Running `/commit` from any subdirectory of the repo causes the cwd-relative `git ls-files --error-unmatch .claude/git-kit.local.json` check to report "no match" (exit `1`) even when `.claude/git-kit.local.json` is genuinely tracked — which step 2's own documented interpretation reads as "untracked, safe to trust." This silently disables the entire trust boundary: a tracked (and therefore untrusted, per the skill's own security model) local settings file's overrides for `commit_confirm_before_commit`, `commit_auto_stage`, `commit_auto_push`, and `push_auto_pr` would be wrongly honored instead of falling back to the git-tracked `git-kit.settings.json` defaults.

## Error Details
~~~
error: pathspec '.claude/marketplace-sync.json' did not match any file(s) known to git
Did you forget to 'git add'?
~~~

## Impact
**High** — a real fail-open condition in a security-relevant gate, triggerable simply by running `/commit` from a non-repo-root working directory (an ordinary, non-adversarial way to invoke Claude Code), not a contrived edge case. No active exploit was demonstrated in this write-up (that would additionally require a tracked, malicious `.claude/git-kit.local.json` already present in the repo), but the boundary meant to catch exactly that is the one shown here to fail silently.

## Additional Context
Found during PR #101's review (2026-08-22, https://github.com/AndreHahm/andres-cc-marketplace/pull/101), by a self-dispatched `security-reviewer` pass while fixing the identical bug class in `handling-review-findings/SKILL.md`'s own analogous trust-boundary check (fixed there in commit `8be897b` on that PR). `commit/SKILL.md` was not modified by PR #101, so this fix was deliberately deferred as out-of-scope rather than bundled into that PR.

Suggested fix: change `commit/SKILL.md` step 2's check to the root-anchored form:

```
git ls-files --error-unmatch :/.claude/git-kit.local.json
```

— exactly the fix already applied to `handling-review-findings/SKILL.md`'s own equivalent check.
