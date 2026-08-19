# Baseline plan: "run a full retrospective and consolidate the findings, then fix what it finds"

No orchestration skill is being used for this — I'm treating it as a generic multi-phase task and
figuring out the sequence myself, using only: `Skill()` to dispatch the five named analysis-kit
report-producing skills (as ordinary tools, not as a guided workflow), `AskUserQuestion` for the
decisions only the user can make, and standard file/git tools for consolidation and fixing.

## Reasoning about the ambiguity up front

"Run a full retrospective" doesn't specify:
1. **What time/session range** to analyze — every one of the five analysis-kit skills requires a
   user-defined start date/session scope; none of them default silently.
2. **Whether "full" means all five analysis types**, or a subset — the five skills cover different,
   partially-overlapping axes (component quality, tool/framework usage, actor/agent behavior,
   governance/rule conformance, recurring patterns). Running all five is the literal reading of "full,"
   but it's expensive (each is described as a heavy, potentially multi-day pass), so I should confirm
   rather than assume.
3. **How "fix what it finds" should be gated** — CLAUDE.md and this repo's rules are explicit that
   destructive or scope-expanding actions need disclosure/approval, and that behavior changes need
   tests. I should not silently start editing files the moment a report lists a finding.

So the plan opens with clarifying questions rather than immediately firing off five long-running
analyses on a guessed scope — asking first is cheap; re-running a multi-day analysis because the scope
was wrong is not.

## Step-by-step plan

### Step 1 — Ask for the analysis scope (date/session range)

```
AskUserQuestion({
  questions: [
    {
      question: "What time range should the full retrospective cover?",
      header: "Scope: time range",
      multiSelect: false,
      options: [
        {
          label: "Today only",
          description: "2026-08-19 — just the current session/work"
        },
        {
          label: "Last 7 days",
          description: "2026-08-12 through 2026-08-19"
        },
        {
          label: "Last 30 days",
          description: "2026-07-20 through 2026-08-19 — likely captures this repo's recent multi-session build/fix work"
        },
        {
          label: "Custom range",
          description: "I'll type a specific start date or a specific set of session IDs"
        }
      ]
    }
  ]
})
```

### Step 2 — Ask which analyses count as "full"

```
AskUserQuestion({
  questions: [
    {
      question: "Which analysis types should the retrospective include?",
      header: "Scope: analysis types",
      multiSelect: false,
      options: [
        {
          label: "All 5 (full coverage)",
          description: "analyzing-plugin-components, analyzing-tool-and-framework-use, analyzing-actor-behavior, analyzing-governance-and-conflicts, mining-recurring-patterns"
        },
        {
          label: "Core 3",
          description: "analyzing-plugin-components, analyzing-governance-and-conflicts, mining-recurring-patterns — skip tool/framework and actor-behavior analyses"
        },
        {
          label: "Let me pick individually",
          description: "I'll name the specific skills to run"
        },
        {
          label: "Components + patterns only",
          description: "Fastest, most directly actionable pair — skip the other three"
        }
      ]
    }
  ]
})
```

I default-recommend "All 5" as matching the literal word "full," but leave the choice explicit rather
than assuming, since each pass is costly.

### Step 3 — Ask how fixes should be gated

```
AskUserQuestion({
  questions: [
    {
      question: "Once findings are consolidated, how should fixes be applied?",
      header: "Fix approval mode",
      multiSelect: false,
      options: [
        {
          label: "Ask before each fix",
          description: "Safest — one AskUserQuestion per finding before any edit"
        },
        {
          label: "Batch by severity",
          description: "One approval per tier — approve all Critical fixes at once, then all High, etc."
        },
        {
          label: "Auto-apply low-risk, ask for the rest",
          description: "Docs/typos/dead-code fixed automatically; anything touching behavior or safety gates is asked about first"
        },
        {
          label: "Show me the list first, no fixes yet",
          description: "Stop after consolidation — I'll decide what to fix in a follow-up turn"
        }
      ]
    }
  ]
})
```

This is the step most directly required by this repo's own rules: `require-tests-for-behavior-changes.md`
and `disclose-before-overriding-decisions.md` both say a behavior change shouldn't proceed silently, and
"fix what it finds" is exactly this kind of open-ended authorization that needs a stated gating mode
before I start editing files.

### Step 4 — Dispatch each selected analysis-kit skill

Based on Steps 1–2's answers, call each selected skill once, sequentially (each is a heavy pass; I
wouldn't parallelize skill dispatches inside one turn since I need each skill's own follow-up prompts,
if any, answered before starting the next). Example calls, assuming "All 5" + "Last 30 days" were
chosen:

```
Skill({ skill: "analyzing-plugin-components", args: "start_date=2026-07-20 end_date=2026-08-19" })
Skill({ skill: "analyzing-tool-and-framework-use", args: "start_date=2026-07-20 end_date=2026-08-19" })
Skill({ skill: "analyzing-actor-behavior", args: "start_date=2026-07-20 end_date=2026-08-19" })
Skill({ skill: "analyzing-governance-and-conflicts", args: "start_date=2026-07-20 end_date=2026-08-19" })
Skill({ skill: "mining-recurring-patterns", args: "start_date=2026-07-20 end_date=2026-08-19" })
```

Each of these, per its own description, persists its report under a predictable path —
`.claude/output/<skill-name>/...` — so after each call I'd note the returned output path rather than
relying on the skill's own chat summary.

### Step 5 — Read every persisted report directly

```
Read({ file_path: "<repo>/.claude/output/analyzing-plugin-components/<latest-report>.md" })
Read({ file_path: "<repo>/.claude/output/analyzing-tool-and-framework-use/<latest-report>.md" })
Read({ file_path: "<repo>/.claude/output/analyzing-actor-behavior/<latest-report>.md" })
Read({ file_path: "<repo>/.claude/output/analyzing-governance-and-conflicts/<latest-report>.md" })
Read({ file_path: "<repo>/.claude/output/mining-recurring-patterns/<latest-report>.md" })
```

(If the exact filenames aren't known in advance, a `Glob` over `.claude/output/*/**.md` sorted by
mtime first, then `Read` on the newest match per skill.)

### Step 6 — Consolidate manually

Without a dedicated cross-report skill, I'd do this by hand:
- Build a single findings table: `finding | source report(s) | severity | affected component/file |
  overlap flag`.
- Flag duplicates: the same underlying issue named by two reports (e.g. a rule-conformance gap that
  both `analyzing-governance-and-conflicts` and `analyzing-plugin-components` independently surface).
- Flag contradictions: two reports drawing opposite conclusions about the same subject — these get
  called out explicitly rather than silently averaged or picked between.
- Group by severity (Critical/High/Medium/Low, or whatever vocabulary the reports themselves use) and
  by target component, since fixes will mostly be scoped per-component.
- Write the consolidated result to a new file, e.g.
  `.claude/output/consolidated-retrospective/<date>-consolidated-findings.md`, via `Write`.

### Step 7 — Present the consolidated list, then fix per the Step 3 answer

- Show the user the consolidated table/summary in-chat.
- Depending on the chosen fix-approval mode:
  - **Ask-before-each**: loop — for each finding, `AskUserQuestion` with options like "Fix now / Skip /
    Explain more / Defer to backlog," then apply via `Edit`/`Write` and re-verify (run relevant
    tests/lint) before moving to the next finding.
  - **Batch by severity**: one `AskUserQuestion` per tier ("Apply all N Critical fixes? / Review each
    one first / Skip this tier / Show diffs before deciding"), then apply the tier as a batch.
  - **Auto-apply low-risk**: apply docs/typo/dead-code fixes directly, and route anything touching
    behavior, a safety gate, or a shared config value through a per-finding `AskUserQuestion` before
    touching it.
  - **List-only**: stop here and wait for the user's next message.
- For any fix that changes actual behavior, this repo's own `.claude/rules/require-tests-for-behavior-changes.md`
  means I would not mark a fix "done" without either writing/running a test or citing the specific
  carve-out (deterministic-script fix, or a prose-only fix restoring already-documented behavior).
- For any fix inside a plugin component (skill/agent/command/hook/rule), `.claude/rules/plugin-rulebook-enforcement.md`
  means I'd run the rulebook check before declaring that component's fix finalized.
- Before the very first actual file edit, `.claude/rules/starting-work-before-first-change.md` means I
  would first ensure a branch/worktree exists for this fix pass (i.e., confirm we're not editing
  directly on `main`) rather than starting to edit immediately after the consolidation step.
- Commits, if any, would go through this repo's own git-kit lifecycle skills (`commit`, `create-pr`)
  per `.claude/rules/route-through-git-kit-lifecycle-skills.md`, rather than raw `git commit`.

## Summary of the concrete first tool calls, in order

1. `AskUserQuestion` — time range (Step 1, 4 options)
2. `AskUserQuestion` — which analyses = "full" (Step 2, 4 options)
3. `AskUserQuestion` — fix-approval mode (Step 3, 4 options)
4. `Skill()` × (3 or 5) — one call per selected analysis-kit skill, sequential (Step 4)
5. `Glob` + `Read` — pull each skill's persisted report (Step 5)
6. `Write` — consolidated findings file (Step 6)
7. Fix loop per the Step 3 answer, gated by `AskUserQuestion` where the chosen mode requires it,
   `Edit`/`Write` for the actual changes, and `Bash`/test commands to verify each fix (Step 7)

## Key risk this plan is guarding against

Because there's no dedicated cross-report reconciliation step available to me here, Step 6's manual
consolidation is the weakest link — a genuine contradiction between two of the five reports could be
missed if I just concatenate findings rather than actually diffing claims against each other. I'd flag
that explicitly to the user as a known limitation of doing this without a purpose-built comparison tool,
rather than presenting the consolidated list with false confidence that it's already reconciled.
