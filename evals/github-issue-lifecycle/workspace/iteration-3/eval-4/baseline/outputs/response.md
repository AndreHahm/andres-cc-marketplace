# GitHub Issue Lifecycle — Baseline Response (Dry Run)

## Part A: Filing the "production deploy pipeline down" issue

**1. Clarify/gather details before filing.**
Even though this is urgent, a good issue still needs enough information to be actionable. I'd want to capture:
- What exactly is failing (the pipeline stage, the 500 error's source — CI runner, deploy API, target infra)
- When it started ("right after the last release" — so I'd want the release version/commit/tag if available)
- Reproduction: does every deploy fail, or just some environments?
- Any logs/stack traces/error output available
- Current impact: is production itself down, or just the ability to *deploy* to production (these are different — the report says the *pipeline* is down, not necessarily that live production traffic is affected)

Since this is time-sensitive, I wouldn't block filing the issue on gathering every detail — I'd file immediately with what's known and note follow-ups needed, rather than delay filing while chasing more info.

**2. Check for an existing/duplicate issue first.**
Before creating a new issue, I'd search open issues (e.g. `gh issue list --search "deploy pipeline 500"` or similar) to make sure this isn't already tracked, especially since "right after the last release" suggests other users may have hit it too.

**3. Draft the issue.**
Title: concise and specific, e.g. "Production deploy pipeline fails with 500 error on every deploy (started after latest release)".
Body would include: Summary, Impact (all production deploys blocked), When it started, Steps to reproduce (attempt any deploy), Expected vs actual behavior, Suspected trigger (the last release), Logs/error details if available, and an "Environment" section (production).

**4. Decide labels, including priority.**
This is the key judgment call. Priority labeling isn't usually an automatic/mechanical process unless the repo has a very explicit, documented rubric — normally it's a human (or an agent acting as one) triage decision based on severity/impact heuristics:
- **Scope of impact**: this affects *all* production deploys, not a subset — broad blast radius.
- **Business impact**: an inability to deploy to production is a release-blocking, operational issue — teams can't ship fixes, including a fix for this very problem, until it's resolved.
- **Workaround availability**: none mentioned — "every deploy fails."
- **User-facing vs internal**: it's the deployment tooling, not necessarily the running production service itself, but it blocks the team's ability to respond to *any* other production incident.

Given "completely down," "every deploy fails," and no known workaround, I'd triage this as the highest severity level the repo's label scheme has — typically `priority: critical` (or `P0`, depending on the repo's convention). I'd also add a `bug` label and possibly an `area: ci/cd` or `area: deploy` label if the repo uses area/component labels. If the repo has an "incident" or "outage" label distinct from bug severity, I'd add that too.

I would not invent a new label scheme on the spot — I'd first check what priority labels already exist in the repo (`gh label list`) and use the closest existing match rather than assuming naming like `priority: critical`. For this answer I'll assume a `priority: critical` label already exists, matching common convention.

**5. Create the issue with the label applied at creation time**, rather than creating it bare and labeling separately, since urgency labels ideally accompany the issue from the moment it's filed so on-call/triage processes pick it up immediately.

Exact literal command:

```
gh issue create --title "Production deploy pipeline fails with 500 error on every deploy (started after latest release)" --body "**Summary**: Every production deploy is currently failing with a 500 error. This began immediately after the most recent release went out.

**Impact**: All production deploys are blocked. No known workaround at this time.

**Steps to reproduce**: Attempt any deploy to production; it fails with a 500 error.

**Suspected cause**: Correlates with the timing of the last release — needs investigation to confirm whether the release itself introduced the regression or something else changed concurrently.

**Priority rationale**: Complete production deploy outage, no workaround, blocks the team's ability to ship any fix (including a fix for this issue) — treated as highest severity." --label "priority: critical,bug"
```

(If the repo instead uses a numeric scheme, e.g. `P0`, the `--label` value would be `"P0,bug"` instead — the exact label text depends on what the repository's actual label set defines, which I'd confirm with `gh label list` before running the create command for real.)

If I had already created the issue without a label (e.g. because I filed it first and triaged a moment later), the equivalent follow-up command would be:

```
gh issue edit <ISSUE_NUMBER> --add-label "priority: critical"
```

## Part B: Re-triage lowers severity to High (workaround found)

Once the re-run impact analysis concludes the severity is actually High rather than Critical — because a workaround now exists — the priority label should be **updated to reflect the new assessment, not left as Critical and not silently dropped.** Concretely:

1. **Remove the outdated priority label and add the corrected one** — don't just add the new label on top of the old one, which would leave the issue carrying two conflicting priority labels simultaneously:

```
gh issue edit <ISSUE_NUMBER> --remove-label "priority: critical" --add-label "priority: high"
```

2. **Leave a comment documenting why the label changed** — priority changes, especially downgrades, should be traceable. The comment should state: the workaround that was found, why it reduces urgency from Critical to High, and a pointer to the workaround itself (docs, runbook, or a description) so anyone still hitting the issue isn't stuck. For example:

```
gh issue comment <ISSUE_NUMBER> --body "Re-triaged: severity downgraded from Critical to High. A workaround has been identified (<describe workaround / link>), so production deploys are no longer completely blocked. Root-cause fix is still needed, but this is no longer an all-hands outage. Updated priority label accordingly."
```

3. **What should *not* happen:**
   - The label should not silently stay at Critical after severity has genuinely changed — that misrepresents current urgency to anyone triaging the backlog and can cause over-escalation (e.g. unnecessary paging) going forward.
   - The label change shouldn't happen with zero explanation — an issue's label history flipping from Critical to High with no comment leaves reviewers wondering whether it was an accidental change or a deliberate, evidence-based re-triage.
   - The issue itself should **not** be closed just because it was downgraded — the underlying pipeline bug is still unresolved; only the urgency assessment changed, not the issue's validity or the need to fix it.

4. If the repo tracks a "verified"/"needs investigation" style status separate from priority, I'd leave that alone — this re-triage only touches the priority/severity label, not the issue's workflow status, unless the workaround itself changes what state the issue should be in (e.g. moving it out of an "incident" board column into a normal backlog).
