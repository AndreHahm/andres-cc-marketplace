# Baseline Response: Filing a Bug Issue in a Repo With No Priority-Label Taxonomy

## Scenario

`acme/widgets` has no defined priority-label taxonomy at all. A user reports a straightforward bug and
asks to file it as a new GitHub issue. The question is specifically about what happens around priority
labeling, and whether the missing taxonomy blocks or delays filing.

## What I'd actually do

1. **Gather the bug details from the user.** Confirm I have enough to write a useful issue: a clear
   title, steps to reproduce, expected vs. actual behavior, and any relevant environment/version info. If
   something critical is missing (e.g., no repro steps at all), I'd ask for it — but that's a content gap,
   not a labeling gap, and is unrelated to priority.

2. **Check what labels actually exist on the repo**, e.g. via `gh label list --repo acme/widgets` or by
   looking at the repo's Issues page. "No defined priority-label taxonomy" doesn't necessarily mean the
   repo has zero labels — it likely has generic ones like `bug`, `enhancement`, `documentation` from
   GitHub's default set, just nothing like `priority: high/medium/low` or `P0/P1/P2`.

3. **Draft the issue body** in standard GitHub-flavored markdown: a short summary, a "Steps to Reproduce"
   section, "Expected behavior," "Actual behavior," and an environment/version block if relevant. Nothing
   unusual here — this is a straightforward bug report.

4. **File the issue** via `gh issue create --repo acme/widgets --title "..." --body "..."`, applying
   whatever *non-priority* labels genuinely fit and already exist (most commonly just `bug`, if that
   label exists in the repo). I would not invent a `bug` label if one doesn't exist, and I would not
   guess at a taxonomy that isn't there.

## Does the issue end up with a priority label?

**No.** Since the repo has no priority-label taxonomy, there is nothing correct to apply. I would not:

- Invent an ad hoc priority label (e.g., unilaterally creating and applying `priority: high`) — that's a
  repo-governance decision (what levels exist, what they mean, who decides) that belongs to the
  maintainers, not something an issue-filer should silently create as a side effect of filing one bug.
- Guess at severity using someone else's convention (e.g., assuming GitHub's default `P0`-style labels
  exist) without verifying they're actually present in this repo.
- Leave the issue unfiled while waiting for a priority decision.

So the issue ships with its normal content labels (if any exist and apply) and **no priority label**,
because none exists to apply.

## Does the missing taxonomy block or delay filing?

**No.** Filing the issue and having a priority taxonomy are two independent concerns. A straightforward
bug report is valuable to have on record immediately — reproducible, triaged content-wise, and
discoverable — regardless of whether it's been assigned a priority level yet. Priority is something a
maintainer or triager typically assigns after the fact anyway (often during a triage meeting or backlog
grooming pass), so it's normal for a freshly filed issue to sit unprioritized for a while even in repos
that *do* have a taxonomy.

Blocking on priority would be actively harmful: it would either delay getting a real bug into the
tracker (bad — the bug exists whether or not it's labeled), or push me toward inventing a taxonomy
unilaterally (worse — that's a decision affecting every future issue in the repo, made by the wrong
person at the wrong time, without any maintainer buy-in).

## What I would tell the user

After filing, I'd note explicitly: "I filed this as issue #N with the `bug` label. This repo doesn't
currently define priority labels (e.g., P0/P1/P2 or priority:high/medium/low), so I didn't add one — let
me know if you'd like me to propose a simple taxonomy, or if there's an existing convention elsewhere
(a project board, a CONTRIBUTING doc) I should follow instead." This surfaces the gap without silently
papering over it, but keeps it as a follow-up decision rather than a precondition for filing.

## Summary

- Priority label applied: **no** — none exists to apply, and I wouldn't invent one unilaterally.
- Filing blocked or delayed by the missing taxonomy: **no** — filing proceeds normally with whatever
  labels genuinely exist; the priority gap is surfaced to the user as a follow-up item, not a blocker.
