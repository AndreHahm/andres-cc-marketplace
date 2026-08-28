# Rule-Coverage Check (Phase 3 of `managing-review-learnings`)

## Candidate

> Folding several distinct sub-cases into one generic tool-call path silently discards
> tool-native state a more specific flag/reason would have preserved (e.g. `gh issue close
> --reason "not planned"` used even for actual duplicates, discarding `--duplicate-of`).

## Method

Per `managing-review-learnings` Phase 3, I searched `.claude/rules/*.md` by subject/keyword rather
than relying on whether any existing doc entry already cross-references a rule. Checks run:

1. Read every file returned by `Glob('.claude/rules/*.md')` (22 files total) — either already
   provided in full via system context, or read directly (`skill-evaluation-protocol.md`, which
   wasn't in that context).
2. `Grep` across `.claude/rules/` for direct-hit terms: `gh issue close`, `duplicate-of`,
   `not planned`, `--reason`, `tool-native`, `native state`, `sub-case(s)`, `collapse.*case`,
   `generic.*path` — no matches.
3. Broader conceptual sweep for `closing`, `close reason`, `issue metadata`, `state loss`,
   `preserv` — no matches.
4. A wide keyword pass (`reason|flag|generic|discard|specific|collaps|fold`) hit most files only
   incidentally (common English words like "specific"/"generic" appearing in unrelated contexts —
   e.g. "specific file(s)", "generic 'see also'"), not the actual pattern.

## Result: No existing rule covers this shape

None of the 22 rules in `.claude/rules/*.md` address "choosing an overly generic tool
call/parameter that silently discards more specific, tool-native state a narrower flag/reason
would have preserved." The closest neighbors, and why each falls short of this specific shape:

- **`verify-tool-behavior-before-instructing.md`** — covers verifying how a tool/API *actually
  behaves* before writing an instruction that depends on it (e.g. `jq -e`'s exit-status semantics,
  the Reactions API having no commit-SHA field). This is about correctness of an assumption
  regarding tool mechanics, not about picking the right *specific* parameter/flag among several
  valid ones when a coarser one is also technically valid but throws away information.
- **`verify-scope-declarations-before-finalizing.md`** — covers keeping a scope
  declaration (filtered file list, exclusion clause, tool-grant list) internally consistent with
  what depends on it. Different subject (internal consistency of a declared scope), not
  under/over-specific tool-call selection.
- **`recheck-state-before-side-effecting-action.md`** — covers re-checking *external async state*
  immediately before a side-effecting action (staleness/TOCTOU), and handling a value's full state
  space rather than a pass/fail binary. Adjacent in spirit ("handle the full enum, don't
  collapse it"), but scoped specifically to re-checking state that can change between observation
  and action — not to choosing a generic vs. specific tool call/flag when writing an instruction.
- **`disclose-before-overriding-decisions.md`** — covers not silently overriding/bypassing an
  already-made `AskUserQuestion` decision or skipping a documented gate/phase. Unrelated axis
  (approval-checkpoint bypass vs. tool-call specificity).

None of these — nor any other rule in the directory — states the actual candidate pattern: that a
tool call offering several distinct, more-specific reason/flag options should not be collapsed
into one generic path when a specific one applies and would preserve more state.

## Conclusion

**No existing `.claude/rules/*.md` file governs this systemic gap.** Per Phase 3 of
`managing-review-learnings`, this candidate is not dropped by the rule-coverage check and would
proceed to Phase 4 (batch-confirm + `github-issue-lifecycle` dispatch) if this were a live run
against a real `mining-review-learnings` report.
