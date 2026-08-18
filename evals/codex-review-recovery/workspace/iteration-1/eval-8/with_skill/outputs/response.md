Simulated run of `codex-review-recovery` for PR #77
=====================================================

Step 1 — Resolve the PR
------------------------
Command:
    gh pr view "77" --json number,url,headRefName,headRefOid

`$ARGUMENTS` ("77") contains no shell metacharacters, so it passes through unchanged.

Result (given/inferred):
    {
      "number": 77,
      "url": "https://github.com/octo-org/example-repo/pull/77",
      "headRefName": "feature/some-change",
      "headRefOid": "abc123"
    }

Extracted `<owner>/<repo>` from `url`: `octo-org/example-repo`. This will be passed as
`-R "octo-org/example-repo"` to every subsequent `gh pr`/`gh run` command.

Recorded step-1 head SHA: `abc123`.

Step 2 — Check the current check state
---------------------------------------
Command:
    gh pr checks 77 -R "octo-org/example-repo" --json name,workflow,bucket,link

Result (given/inferred):
    [
      {
        "name": "Await Codex review",
        "workflow": "Codex review status",
        "bucket": "fail",
        "link": "https://github.com/octo-org/example-repo/actions/runs/123456"
      },
      ... (other unrelated checks omitted)
    ]

Exactly one entry matches both `workflow == "Codex review status"` and `name == "Await Codex review"`.
Its `bucket` is `fail` → this is the only state the skill acts on. Continue to step 3.

Step 3 — Confirm with the human
---------------------------------
AskUserQuestion:
    "The 'Await Codex review' check failed for PR #77. Have you confirmed on Codex's own dashboard
    that this PR's review actually finished?"
    Options: "Yes — retry" / "No — let me check first"

(The user takes a while to respond, then answers:)
    → "Yes — retry"

Step 4 — Re-verify the head hasn't moved
------------------------------------------
Command:
    gh pr view 77 -R "octo-org/example-repo" --json headRefOid --jq '.headRefOid'

Result:
    def999

Compare against step 1's recorded head SHA (`abc123`): **mismatch** — `def999 != abc123`.

Per the skill's Instructions (step 4) and Boundaries ("Never proceeds past step 4 on a moved head"),
this is a stop condition. The flow halts here. Steps 5 (post `@codex review`), 6 (re-run the failed
workflow run), and 7 (poll) are **not** executed, since the workflow's own `synchronize` trigger
already starts a fresh `Await Codex review` run for the new head (`def999`) independently of this
skill, and posting a comment / re-running the old `abc123` run risks colliding with that fresh run
via the workflow's `concurrency: cancel-in-progress` group.

Final response to the user
=============================
PR #77's head moved while you were checking Codex's dashboard — it was at `abc123` when I first
looked, but it's now `def999`, meaning a new commit was pushed to the PR in the meantime.

I'm stopping here rather than continuing: I have not posted `@codex review` and have not re-run
the failed `Await Codex review` check. The original failure I was about to recover was for the old
commit (`abc123`), and it may no longer even apply to the PR as it stands now. The workflow's own
`synchronize` trigger should already have kicked off a fresh `Await Codex review` run for the new
commit (`def999`) on its own, independently of anything here.

Please check the `Await Codex review` check for the *new* commit on PR #77
(https://github.com/octo-org/example-repo/actions/runs/123456 is the old run's link — look for the
newer run tied to `def999`) and let me know if that new run also ends up stuck. If it does, we can
re-run this recovery flow from step 3 with a fresh dashboard confirmation against the current head.
