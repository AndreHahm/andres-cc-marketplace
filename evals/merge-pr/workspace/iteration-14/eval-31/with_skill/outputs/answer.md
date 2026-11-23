# merge-pr on PR 922 (no flags): two untouched open findings

Simulated exercise. No `gh` or `git` call is made and no repository file is edited.

## Context reached before this point

- Step 1 resolved PR 922 and validated it. Step 1.5's checkout check passed: `isCrossRepository` is
  `false`, and `origin` (from `git remote get-url origin`, never `gh repo view`), the current branch and
  `git rev-parse HEAD` all match step 1.
- The scan found two open findings that nobody deferred. Both were classified against the paginated
  changed-file list (`gh api repos/{owner}/{repo}/pulls/922/files --paginate --jq '.[].filename'`), and
  neither path is in it, so both are **untouched**:
  1. a finding in `plugins/foo/skills/a/SKILL.md`
  2. a finding in `plugins/bar/skills/b/SKILL.md`
- Untouched items are never fixed in this session. The only path for them is a filed issue, and only
  after approval. There are no touched items, so no fix batch and no push happen in step 1.5.

## What I ask, and what I run, before any issue is drafted or filed

**1. One opt-in question (`AskUserQuestion`), before anything is drafted.** Nothing else runs first: no
`Skill(github-issue-lifecycle)`, no dedup search and no draft.

```
AskUserQuestion({
  questions: [{
    header: "Untouched items",
    question: "Step 1.5 found 2 open findings in files PR 922 does not change: (1) plugins/foo/skills/a/SKILL.md, (2) plugins/bar/skills/b/SKILL.md. Draft GitHub issues for them now? Each draft runs Skill(github-issue-lifecycle) once, as a nested run per item (R26), so 2 nested runs.",
    options: [
      { label: "Draft them", description: "Run github-issue-lifecycle per item: dedup check and draft only. No issue is filed until you approve each draft." },
      { label: "Not now", description: "Draft nothing. Both stay open and unfiled and are listed in the summary." }
    ]
  }]
})
```

**2. Only on the exact answer "Draft them"** would these steps follow, per item:
- invoke `Skill(github-issue-lifecycle)`, telling it explicitly to run Workflow 1 through Step 2 (dedup
  check, then draft) and **stop there, without filing**;
- show each draft through `AskUserQuestion` and ask for explicit approval. That question is the approval;
  Workflow 1's own "once the draft is approved" wording is never treated as enough;
- on approval, resume Workflow 1 at Step 3 to file the issue, **skipping its Step 6 (PR-linking)**
  entirely, because the issue concerns a component this PR does not touch;
- on decline, file nothing and report the item as still open and unfiled.

## The user replies with the free text "hmm, maybe later"

That reply is not "Draft them". The rule is "on 'not now', **or any answer other than 'draft them'**,
draft nothing", so the reply counts as a no. What I do:

- I draft nothing and file nothing. I do not invoke `Skill(github-issue-lifecycle)`, run a dedup check
  or ask a second time to talk the user into it. I also do not read the vague reply as half a yes.
- I record both items as **still open and unfiled**. "Maybe later" is the user's own message deferring
  them ("later"), so they also count as explicitly deferred for this invocation. Neither is asked about
  again in a later pass, and neither is fixed. As untouched items they would never be fixed here anyway.
- I give the step-1.5 summary (this check is never skipped silently): nothing was fixed, nothing was
  filed, and two untouched items were left open and unfiled at the user's choice. Each is named:
  `plugins/foo/skills/a/SKILL.md` and `plugins/bar/skills/b/SKILL.md`.
- I continue to **step 1.6 (PR-body currency check)**. It compares `## Open Items` with the real state,
  and that section should list both items as open (deferred, not filed). If either is missing, I propose
  the addition together with any other stale body item in one `AskUserQuestion`. The new text is
  screened, and on approval it goes in as one edit (`gh api -X PATCH .../pulls/922 -F body=@<file>`),
  after the diff and `git-pr-body-waiver-check.py` checks, with the wait baseline recorded first.
  `## Accepted Review Findings` and `## Known CI Failures (Accepted)` are never edited.
- Because these items are deferred and untouched, they do not stop the run. Step 1.5 pushed nothing, so
  I continue to **step 2's readiness checks**. If step 1.6 edited the body, step 2 re-fetches and waits
  for the CI run that edit started. Then steps 3 and 5 follow, and the merge happens only after an
  explicit confirmation.
