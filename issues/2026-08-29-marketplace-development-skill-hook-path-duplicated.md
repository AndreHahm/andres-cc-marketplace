## Summary
`marketplace-development`'s SKILL.md-embedded `PostToolUse` hooks fail to run — their command paths duplicate the `skills/marketplace-development/` segment, because `${CLAUDE_PLUGIN_ROOT}` resolves to the skill's own directory in this context, not an enclosing plugin root.

## Environment
- **Product/Service**: `plugins/plugin-devkit/skills/marketplace-development/SKILL.md` (and its `.claude/skills/marketplace-development/SKILL.md` mirror)
- **Region/Version**: N/A

## Reproduction Steps
1. Invoke the `marketplace-development` skill and have it `Write`/`Edit` a file (any file — the hook matcher is `Write|Edit` with no path filter).
2. Observe the `PostToolUse:Write` hook errors.

## Expected Behavior
`hooks/post_edit_validate.sh` and `hooks/post_edit_sync_check.sh` (both real, existing files under `.claude/skills/marketplace-development/hooks/`) should run successfully.

## Actual Behavior
Both hooks fail with `No such file or directory`, resolving to:
```
C:/Dev/Repos/andres-cc-marketplace/.claude/skills/marketplace-development/skills/marketplace-development/hooks/post_edit_validate.sh
C:/Dev/Repos/andres-cc-marketplace/.claude/skills/marketplace-development/skills/marketplace-development/hooks/post_edit_sync_check.sh
```
Note `skills/marketplace-development` appearing **twice**. The SKILL.md frontmatter declares:
```yaml
hooks:
  PostToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: "${CLAUDE_PLUGIN_ROOT}/skills/marketplace-development/hooks/post_edit_validate.sh"
```
`${CLAUDE_PLUGIN_ROOT}` clearly resolved to `.claude/skills/marketplace-development` itself (the skill's own directory) in this run, not a higher-level plugin root the template's extra `skills/marketplace-development/` segment assumes.

## Error Details
```
PostToolUse:Write hook error
Failed with non-blocking status code: bash: C:/Dev/Repos/andres-cc-marketplace/.claude/skills/marketplace-development/skills/marketplace-development/hooks/post_edit_validate.sh: No such file or directory
PostToolUse:Write hook error
Failed with non-blocking status code: bash: C:/Dev/Repos/andres-cc-marketplace/.claude/skills/marketplace-development/skills/marketplace-development/hooks/post_edit_sync_check.sh: No such file or directory
```

## Impact
**Low** — `onError`/failure here is non-blocking (per the reported "non-blocking status code"), so no work was lost, but both of `marketplace-development`'s own auto-validation hooks (`claude plugin validate` on marketplace.json writes, and the SKILL.md-edited-but-version-not-bumped warning) have silently never actually run since this skill's hooks were authored, for anyone invoking it via the `.claude/skills/` project mirror.

## Additional Context
`marketplace-development` is the only skill in this repo's own shipped plugins using a SKILL.md-frontmatter-embedded `hooks:` block (confirmed via repo-wide grep; the only other two matches are inside `plugins/git-kit/.temp/to-inspect/` — an unrelated third-party reference plugin being inspected, not a shipped one). Both the canonical (`plugins/plugin-devkit/skills/marketplace-development/SKILL.md`) and mirror (`.claude/skills/marketplace-development/SKILL.md`) copies carry the identical bug.

Likely fix: drop the redundant `skills/marketplace-development/` segment from both `command` paths, i.e. `"${CLAUDE_PLUGIN_ROOT}/hooks/post_edit_validate.sh"` and `"${CLAUDE_PLUGIN_ROOT}/hooks/post_edit_sync_check.sh"` — matching the path shape plugin-devkit's own plugin-level `hooks/hooks.json` already uses successfully (`${CLAUDE_PLUGIN_ROOT}/hooks/rulebook-check.sh`, no extra directory segment). Not yet verified against Claude Code's actual documented semantics for `${CLAUDE_PLUGIN_ROOT}` inside a *skill-level* embedded hook specifically (as opposed to a plugin-level `hooks/hooks.json` entry) — worth confirming before applying the fix, since the two contexts may have different resolution rules.

Found live during this session while creating a PR (branch `chore/bootstrap-marketplace-plugin-inventory`) — the `marketplace-development` skill had been invoked earlier in the same session to attempt registering `example-plugin` (before being redirected to `plugin-development` instead, since `example-plugin` already has its own `plugin.json`).
