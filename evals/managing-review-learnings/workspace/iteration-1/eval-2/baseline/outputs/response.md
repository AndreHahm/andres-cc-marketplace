# Rule-coverage check: "generic tool-call path discards tool-native state"

## Task

Check whether an existing rule in `.claude/rules/*.md` already covers this generalized pattern:

> "folding several distinct sub-cases into one generic tool-call path silently discards
> tool-native state a more specific flag/reason would have preserved" — e.g. using
> `gh issue close --reason "not planned"` even for an actual duplicate, discarding the more
> specific `--duplicate-of` option that `gh` actually offers.

## Method

Read the full contents of all 22 files in `.claude/rules/*.md` in this worktree
(`C:/Dev/Repos/andres-cc-marketplace/.claude/worktrees/analysis-kit-wave3-pr-review-fetcher/.claude/rules/`):

ask-before-config-decisions.md, ask-before-structural-grounding.md, consult-naming-conventions-first.md,
disclose-before-overriding-decisions.md, orphaned-worktree-git-read-fallthrough.md,
plugin-rulebook-enforcement.md, read-and-retrace-skill-chains-before-finalizing.md,
recheck-state-before-side-effecting-action.md, require-declared-plugin-language.md,
require-gitignored-scratch-locations.md, require-inventory-updates-for-new-plugins-and-components.md,
require-security-review-before-new-gate.md, require-tests-for-behavior-changes.md,
resolve-activation-overlap-bidirectionally.md, resweep-closed-scope-lists-on-new-components.md,
route-through-git-kit-lifecycle-skills.md, skill-evaluation-protocol.md,
starting-work-before-first-change.md, test-against-example-plugin.md,
verify-rule-scope-before-lazy-loading.md, verify-scope-declarations-before-finalizing.md,
verify-tool-behavior-before-instructing.md.

Also ran a targeted grep across the directory for terms like "generaliz", "specific flag",
"discards", "collapse", "native state", "more specific" to catch any partial match before
reading full text.

## Finding: No existing rule covers this pattern

None of the 22 rules addresses this specific failure shape — collapsing several distinct
sub-cases into one generic invocation of a tool, thereby discarding a more specific
flag/parameter/reason-code the tool actually exposes for that sub-case. I looked closely at
the three nearest candidates and none of them actually matches:

1. **`verify-tool-behavior-before-instructing.md`** — closest in subject area (tool/API
   behavior), but its actual scope is "does this tool/API/language behave the way memory or an
   intuitive reading of its name suggests" (e.g. `jq -e` exit-status semantics, GitHub Reactions
   API having no commit-SHA field, `gh pr checks` exposing a display name not a file name). It's
   about *mis-modeling* a tool's behavior, not about *under-using* a tool's available
   specificity when several correct, more-specific options exist and a generic one is chosen
   instead. The `gh issue close --reason "not planned"` vs. `--duplicate-of` case isn't a wrong
   belief about behavior — `--reason "not planned"` behaves exactly as documented — it's a
   choice to fold a specific sub-case into a coarser path that happens to also "work."

2. **`recheck-state-before-side-effecting-action.md`** — about re-checking external/async state
   immediately before a side-effecting action, and handling the *full* enum of that state's
   possible values rather than treating it as a pass/fail binary. This is adjacent in flavor
   (it also punishes collapsing several distinct outcomes into a coarser binary), but it's
   scoped specifically to *state staleness before an action* (CI conclusions, PR head SHA,
   bot reactions), not to *tool-call parameter selection* discarding available specificity at
   authoring time. The rule's own "Why" section (PR #51, TOCTOU-class staleness) is a different
   root cause than "chose the generic reason code."

3. **`verify-scope-declarations-before-finalizing.md`** — about scope declarations (filtered
   file lists, exclusion clauses, tool-grant lists) staying consistent with what depends on
   them. Different subject entirely (declarations/grants, not runtime tool-call flag choice).

No rule's "When this applies" section, worked example, or "Why" incident matches the
`--reason`/`--duplicate-of`-style scenario, and no rule generically states "when a tool offers
multiple specific flags/codes for distinct cases, don't default to a single generic one that
loses information."

## Conclusion

**Not covered.** This pattern — folding distinct sub-cases into one generic tool-call path and
silently discarding more-specific, tool-native state a dedicated flag/reason would have
preserved — has no matching rule in `.claude/rules/*.md` in this repo as of this check. It would
be a new rule if the user wants it captured (closest existing rules to model it after, if a new
one is written, are `verify-tool-behavior-before-instructing.md` for the "know the tool's full
flag/parameter surface" angle, and `recheck-state-before-side-effecting-action.md` for the
"don't collapse a multi-value enum into a binary" framing — but neither currently states this
generalized pattern).
