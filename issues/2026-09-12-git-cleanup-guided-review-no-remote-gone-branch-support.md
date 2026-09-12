## Summary
git-cleanup's new guided manual-review phase (Phase 7) has no safe implementation for `REMOTE_GONE` branches yet — tags are fully covered, branches are deliberately deferred

## Environment
- **Product/Service**: `git-kit` plugin, `git-cleanup` skill (`plugins/git-kit/skills/git-cleanup/scripts/delete-rebase-backup-tags.sh`, `references/guided-manual-review.md`)
- **Region/Version**: this repo (`andres-cc-marketplace`)

## Reproduction Steps
1. Run `/git-cleanup` in a repo with at least one `REMOTE_GONE` branch (remote deleted, work not found in the default branch — Phase 3's own category).
2. Note that Phase 7 (Guided Manual Review) only offers to walk through rebase-backup tags flagged by `delete-rebase-backup-tags.sh --list-review`.
3. The `REMOTE_GONE` branch is still reported in the analysis (as it always was), but no guided evidence/decide/delete flow is offered for it.

## Expected Behavior
`REMOTE_GONE` branches should get the same guided review as rebase-backup tags: raw evidence (unique commits, diff against the default branch), then Delete now / Keep / Skip, with a second confirmation before any delete.

## Actual Behavior
`REMOTE_GONE` branches are excluded from Phase 7 entirely and stay exactly as they were before this feature shipped — reported, left alone, no further help.

## Impact
**Medium** — this is a missing-feature gap, not a live vulnerability. Nothing unsafe shipped: an unsafe draft of the branch-side procedure was caught by a pre-ship security review and never implemented. `REMOTE_GONE` branches simply don't get the same guided-review help tags now have.

## Additional Context

**Why this wasn't implemented:** `delete-rebase-backup-tags.sh`'s tag-side safety relies on an index-only interface — the calling skill never types a raw tag name into a command; it only ever passes back a plain digit index into a snapshot the script itself derives and owns internally. No equivalent mechanism exists for branch names.

The original draft of the branch-side procedure told the calling skill to "capture a branch name into a shell variable" across separate tool calls. But Claude Code's `Bash` tool has no persistent shell state across separate calls, so there was no actual way to follow that instruction without typing the branch name literally into composed command text — reintroducing the exact untrusted-ref-name-in-a-shell-command risk the tag-side index-only design exists to avoid. A pre-ship `security-reviewer` pass caught this before it ever shipped.

**Two candidate designs identified, neither implemented yet:**
1. Extend `delete-rebase-backup-tags.sh` (or a sibling script) with an index-snapshot mode for `REMOTE_GONE` branches, mirroring the tag interface exactly (e.g. `--list-review-branches`, `--branch-diff <index>`, `--branch-force <index>`, `--branch-keep <index>`) — architecturally consistent with the tag side, but a real scope increase.
2. Derive and consume the branch name within a single `Bash` call, using single-quoted assignment (which neutralizes shell metacharacters unconditionally) immediately followed by `git-cleanup`'s own existing `^[A-Za-z0-9._/-]+$` validation (already used for its Phase 5 stale-remote-branch delete) before any use — but this needs care around a git-legal branch name containing a literal single quote (not disallowed by `git check-ref-format`), which naive single-quote-wrapping doesn't handle correctly.

**Suggested fix (not prescriptive):** design, review, and implement one of the two candidate designs above, following the same security-review discipline used for the tag side — a `security-reviewer` pass before shipping any new command-composition path for branch names.

**Current state:** `plugins/git-kit/skills/git-cleanup/references/guided-manual-review.md` has a full "Branches (`REMOTE_GONE`): open design problem — NOT YET IMPLEMENTED" section documenting this in detail. `REMOTE_GONE` branches continue to be reported by Phase 3 exactly as before this feature shipped.
