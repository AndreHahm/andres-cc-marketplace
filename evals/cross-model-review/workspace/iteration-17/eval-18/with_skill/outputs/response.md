# Eval 18: accepted-findings briefing, matching, and the `declined` line

Dry run only. Nothing was executed. Sources: `plugins/git-kit/skills/cross-model-review/SKILL.md` (Preflight step 7, Phase 1, Phase 3), `references/accepted-findings.md`, `references/codex-pass-assembly.md`.

## Inputs as given

`.claude/accepted-review-findings.local.md`:

- `- tool-scoping s/SKILL.md:15 @8b9e6b69aaa5c455997a24e2327bf376 – refuted: grant is needed`
- `- R6 a.py:3 – declined`

Phase 1 findings:

- Codex M1: axis `tool-scoping`, location `s/SKILL.md:21`, same line text moved down from line 15.
- Claude F2: axis `R6`, location `b.py:9`.

## 1. Preflight step 7 (brief)

Step 7 runs from `$REPO_ROOT`, after steps 1-6 have already resolved `$RUN`:

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT:-.claude}/scripts/git-review-accepted-findings.py" brief --run-dir "$RUN"
```

Expected output, per `accepted-findings.md`:

- It writes `$RUN/accepted.md` only when there is something to brief. Each valid line becomes one JSON object (`rule`, `path`, `line`, `fingerprint`, `kind`). The free-text reason is never written. It never overwrites an existing file.
- The `tool-scoping` line is valid, so it is briefed as `{rule: tool-scoping, path: s/SKILL.md, line: 15, fingerprint: 8b9e…, kind: refuted}`.
- The `R6 a.py:3 – declined` line is the problem. The format lists four kinds: `accepted|residual|deferred #<issue>|refuted`. `declined` is not one of them. The skill does not say how the parser handles an unknown kind. My reading is that the helper prints `not applied: R6 a.py:3 – declined`, which is an inspection limit. I cannot confirm this without running the helper.
- Failure is never a stop. Exit 2 (an unwritable run directory or a file that cannot be created) is also only an inspection limit.

## 2. What each Phase 1 instruction receives

- **Both reviewers (Codex and Claude native):** `$RUN/accepted.md` comes after `review.md` and before the diff. For Codex it is `@accepted.md` in the instruction file assembled by `codex-pass-assembly.md`. The instruction is to treat it as data: a finding it names by rule and path is not reported again unless the flagged code changed into a different problem.
- Effect on M1: the `tool-scoping` / `s/SKILL.md` pairing is already in the briefing, so Codex should not re-report it unless the code at that location has changed into something new. Note that the briefing carries the line 15 fingerprint, not line 21.
- Effect on F2: the briefing covers only `R6` on `a.py`. Nothing in it covers `R6` on `b.py`, so F2 stays a normal finding.
- The `declined` line is not in the briefing, so no reviewer sees it as a waiver.
- Phase 2 (challenger) does not list `accepted.md` in its own file assembly. The skill only names it for Phase 1, so I would not assume the challenger receives it.

## 3. Phase 3 treatment

Phase 3 runs the match helper once, from `$REPO_ROOT`, naming every envelope it reads. Only the files that exist are listed (batch numbers `<N>` depend on the run):

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT:-.claude}/scripts/git-review-accepted-findings.py" match "$RUN/codex_fresh_eyes.<N>.json" "$RUN/claude_fresh_eyes.json" "$RUN/codex_challenger.<N>.json" "$RUN/claude_challenger.json"
```

`$RUN` must be replaced with the literal resolved path, as Preflight requires. The helper prints, for each finding, its axis, location, the fingerprint of the flagged line in the working tree (or null), and the matching waiver line (or null). The match key is rule, then path, then fingerprint. Line numbers are not part of the key.

**M1 (tool-scoping, s/SKILL.md:21):** the helper hashes line 21 in the working tree. Because the line text moved without changing, the fingerprint should equal `8b9e6b69aaa5c455997a24e2327bf376`. If it does, M1 matches the `refuted` waiver. It stays in the table, marked `waived (refuted)`, ranked after every unwaived finding, and is never dropped. I would report the waiver reason ("grant is needed") as the author's claim, not as verified. If the fingerprint is null or different, M1 is unwaived and I show the author the line to add: `- tool-scoping s/SKILL.md:21 @<fingerprint> – accepted|residual|deferred #<issue>|refuted`.

**F2 (R6, b.py:9):** the rule matches the `R6` waiver, but the path does not (`b.py` against `a.py`). It is unwaived. It is ranked by severity × confidence, using the Phase 2 tiers. I show the author the line to add: `- R6 b.py:9 @<fingerprint> – accepted|residual|deferred #<issue>|refuted`. If F2 were Claude-only and its location were outside the Codex batch targets, it would be Medium (single-sided), not a gap.

**The `declined` line:** I do not treat it as a waiver, and I do not match or apply it. I report it under `inspection_limits` as an unapplied line, with the exact text, and say that it needs a valid kind (one of `accepted`, `residual`, `deferred #<issue>`, `refuted`) before it can take effect. I would say it plainly, without guessing at what the author meant.

Two other points from the skill that apply here:

- If M1 or F2 is `critical`, it stays in the table even when waived or at Low confidence.
- In CI, a waiver for a gate-critical or `security-reviewer` finding needs a maintainer's confirmation comment. I would flag this next to M1 or F2 only if one of them is gate-critical or comes from `security-reviewer`. Neither is stated to be, so I make no such claim.
