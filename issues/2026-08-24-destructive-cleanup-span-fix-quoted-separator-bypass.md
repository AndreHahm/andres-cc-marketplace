## Summary
`guard-raw-destructive-cleanup.sh`'s fix for the chained-command false-positive (commit `ad072a3`, this same session) bounds the force-flag check to each `git worktree remove` invocation's own argument span, cut off at the first literal `;`, `&`, or `|` character. Since this is plain-text regex, not a real shell parser, it can't distinguish a command separator from the same character appearing inside a *quoted* argument — a worktree path deliberately containing `;`/`&`/`|` causes the span to be cut short before a trailing `--force`/`-f` flag, silently allowing the exact command this guard exists to block.

## Environment
- **Product/Service**: `git-kit`'s `guard-raw-destructive-cleanup.sh` PreToolUse hook
- **Region/Version**: this repo, branch `fix/git-kit-downstream-qa`, commit `ad072a3`

## Reproduction Steps
1. Construct a `PreToolUse` hook input for the `Bash` tool with `tool_input.command` set to:
   ```
   git worktree remove "my;path" --force
   ```
2. Pipe it through `guard-raw-destructive-cleanup.sh` (live-verified via `jq`-constructed input, same harness used for this session's other guard test cases).
3. Observe: no deny output — the command is silently allowed.

## Expected Behavior
A `git worktree remove <path> --force` call is denied regardless of what characters the path argument contains, as long as it's genuinely one shell command with a force flag.

## Actual Behavior
`WORKTREE_REMOVE_SPANS=$(echo "$COMMAND" | grep -oE "${GIT_PREFIX}worktree[[:space:]]+remove[^;&|]*" || true)` stops capturing at the first `;`/`&`/`|`, quoted or not. The trailing `--force` in the reproduction command falls outside the captured span and is never checked against `FORCE_FLAG_RE`, so `MATCH` stays `false` and the command passes through.

## Error Details
```
(not applicable -- silent bypass, no error produced)
```

## Impact
**Low-Medium** — same overall risk class as the original `f6d04a2` bypass this session already fixed once, but narrower: exploiting this specific gap requires a worktree path deliberately containing `;`/`&`/`|`, an unusual and deliberately-crafted input, not something a routine `git worktree remove` call would ever produce by accident. This guard is already documented elsewhere in this repo (`route-through-git-kit-lifecycle-skills.md`) as a policy guardrail against *accidental* bypass, not a hardened boundary against a *deliberately adversarial* actor — this finding is consistent with, not a violation of, that stated design intent.

## Additional Context
Found by this session's mandatory pre-PR `cross-model-review` gate (single-model Claude-native mode; Codex dispatch is broken on this Windows environment per issue #78), on its **second** pass — re-run against the diff after the *first* pass's finding (the chained-command false-positive) was fixed and re-committed. This is the same underlying "regex is not a real shell parser" limitation class already tracked in **issue #85** ("git-kit guard scripts: prefix anchor misses `$(...)`/backtick/path-qualified `gh` invocations") — a new, distinct instance directly introduced by `ad072a3`'s own span-bounding fix, not present in either the original pre-`f6d04a2` version or the `f6d04a2` version this session already replaced.

**Deferred, not fixed, per explicit user decision** (2026-08-24): after 2 consecutive fix→re-review rounds on this same guard script within one session (the `f6d04a2` bypass fix, then this span-bounding fix, each closing one bypass while opening a narrower one), the user judged further iteration on this exact script disproportionate for this session and chose to defer rather than attempt a third round. Also carries forward the same missing-required-`security-reviewer`-pass gap already tracked in `issues/2026-08-24-destructive-cleanup-fix-missing-security-review.md` — that issue's scope should be understood to extend to this commit too, since it's the same gate, same unresolved review gap, one commit later.

**To close, in a future session**: either (a) properly relate `;`/`&`/`|`-boundary detection to actual shell quoting (would likely require a real tokenizer, not a regex, to do correctly), or (b) fold this into issue #85's existing tracked limitation and explicitly accept it as a known, documented boundary of this guard's regex-based design given the narrow exploitability and the guard's own stated "policy guardrail, not adversarial-proof" scope.
