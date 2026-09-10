# Investigation: ENG-204 status changed to "In Review" with no recorded transition

## Scope and honesty check

I do not have a live connection to a real Linear workspace or a real GitHub repo in this
sandbox, and this session has no actual "ENG-204" issue, no actual Wave 2 skill run log, and
no actual PR tied to that issue that I can query. I checked this working directory for any
concrete evidence (git log, file search for "ENG-204" or "linear") and found nothing real to
go on — there is no Linear issue ENG-204 anywhere in this repo's data, and I have no MCP
Linear/GitHub credentials wired to a workspace that would contain it.

So everything below is a **methodology and hypothesis writeup**, not a report of verified
findings. I'm being explicit throughout about what's assumed vs. what I actually checked.
I have not invented any commit SHAs, PR numbers, timestamps, or Linear activity-log entries —
where I reference "a commit" or "a PR" below it's a placeholder for what I'd look at, not a
claim that it exists.

## How I'd actually investigate this, step by step

1. **Pull Linear's own history for the issue first.** Linear keeps a per-issue activity/history
   feed that records every state transition, who/what made it, and the source (manual UI edit,
   API call, GitHub integration, Zapier/automation, etc.). That's the single most authoritative
   place to start, because it will tell me *whether a human did this by hand in the Linear UI*
   before I go looking for a bot or script.
   - If I had Linear API/MCP access to a real workspace, I'd fetch the issue and its activity
     history and look at the specific entry that flipped the status to "In Review": timestamp,
     actor (a real user account vs. an API/OAuth app identity vs. a specific integration name),
     and any linked reference.

2. **Check whether Linear's status changed via its native GitHub integration, not via any
   skill in this session at all.** Linear ships a first-party GitHub integration that can move
   an issue to "In Review" automatically the moment a linked PR is opened or marked ready for
   review (this is a very common default workflow rule: "PR opened → issue → In Review").
   If that integration is enabled on the team/workspace, this explains the transition
   completely and has *nothing to do with any skill in this session* — it would show up in
   Linear's activity log as an actor like "GitHub" or "Linear GitHub Bot," not a human or an
   agent action.
   - This is my leading hypothesis before looking at anything else, because "workflow status
     changed but nothing in session recorded it" is exactly what you'd see if an out-of-band
     integration made the change independently of whatever this session was doing.

3. **Check the GitHub side for a PR that references ENG-204.** If a PR title, branch name, or
   description contains "ENG-204" (a common convention: branch `eng-204-...` or a PR body with
   "Fixes ENG-204" / "Refs ENG-204"), and that PR was opened or moved out of draft during this
   session's work, that's the likely trigger — either via Linear's own GitHub integration (per
   #2) or via some other automation (a GitHub Action, a webhook, a bot) that calls the Linear
   API directly on PR events.
   - I'd run something like `gh pr list --search "ENG-204"` or grep recent commit messages /
     branch names in the relevant repo for "204" or "ENG-204" to find the PR.
   - I did check this specific worktree's git log as a sanity check — recent commits here are
     all `workmanagement-kit` review-fix commits unrelated to any "ENG-204" reference, and nothing
     in this session's actual work touched a Linear issue by that ID. That doesn't rule out a
     *different* repo/PR having triggered it — it just means it wasn't this session's own git
     activity.

4. **Check for other automation surfaces outside "skills in this session."** The premise "no
   Wave 2 skill in this session recorded that transition" only rules out *this session's own
   in-conversation actions*. It does not rule out:
   - A scheduled job / cron / CI step elsewhere that syncs GitHub → Linear.
   - Another person's session (human or another Claude session) that ran a similar workflow
     concurrently and made the Linear call directly.
   - A Linear automation rule unrelated to GitHub at all (e.g., "auto-move to In Review after
     N days in Todo," or a rule tied to a sub-issue/parent-issue state change, or a triage rule).
   - Someone manually dragging the card in the Linear UI or Cmd-K'ing the status change.
   - A different integration entirely (Slack command, Zapier/Make automation, a custom script
     hitting Linear's GraphQL API with a personal API key).

5. **Reconcile timestamps.** Once I have (a) the exact time Linear recorded the transition and
   (b) a timeline of what actually happened in *this* session, I'd line them up. If the Linear
   transition timestamp falls well before this session started, or well after it ended, that
   alone is strong evidence it's unrelated to this session's work. If it falls squarely inside
   this session's active window, that's suspicious and worth a closer look at whether some tool
   call in this session had a side effect that wasn't surfaced back to me in a way I'd recognize
   as "recording" the transition (e.g., a Linear MCP write call whose result I didn't parse
   carefully, or a call made by a sub-agent/parallel session whose output never made it into my
   own transcript).

6. **If I did have reason to believe a skill in this session caused it**, I'd want to see:
   - The actual tool-call transcript for any Linear-write call (an issue update/save call) made
     during this session, with its request payload, to confirm whether "In Review" was set
     explicitly or as a side effect of something else (e.g., updating a different field that
     has a workflow trigger attached).
   - Whether that call was made by a skill that's actually supposed to own status transitions,
     vs. one that shouldn't be touching workflow state at all (a mis-scoped tool call is a
     plausible bug class here, independent of any specific skill's design).

## Most likely explanation (best-effort, unverified)

Given the phrasing of the task — a Linear issue's *workflow status* changed to *"In Review"*,
which is the canonical status GitHub↔Linear integrations set the moment a PR goes up or is
marked ready — my leading, unverified hypothesis is:

> The transition was made by Linear's native GitHub integration (or an equivalent
> repo→Linear automation) reacting to a PR event (opened / marked ready for review) that
> references ENG-204, and it happened independently of any skill invoked inside this
> conversation. "No Wave 2 skill recorded it" is consistent with this: a skill only records
> what it itself does, not what an external integration does as a side effect of a PR that a
> skill (or a person) happened to open.

Secondary, less likely but worth ruling out explicitly:
- A second, concurrent process/session made the change directly via the Linear API without
  going through whatever this session calls "Wave 2 skills."
- A human manually changed the status in the Linear UI, unrelated to any automation.

## What would confirm or rule this out

- Linear issue activity log entry for the transition — actor identity is the deciding fact.
  "GitHub"/integration actor confirms hypothesis #1; a named human account rules it out in
  favor of a manual change; an API-app actor with an unfamiliar name points to a different
  automation than the one this session is aware of.
- Whether a PR referencing ENG-204 exists and its open/ready-for-review timestamp lines up
  with the Linear transition timestamp.
- Whether this session (or a sibling session working the same repo) actually made a Linear
  write call around that time that I haven't correctly attributed.

## What I could not do here

I could not query a real Linear workspace or a real GitHub repo for ENG-204, so none of the
above is a finding — it's the investigation plan and ranked hypotheses I'd pursue with real
tool access, plus the one check I *could* run (searching this local worktree for any trace of
"ENG-204" or session activity that would explain it), which came back empty. If real Linear/
GitHub access is available, step 1 (pull the issue's own activity log and look at the actor on
the specific transition event) is the fastest way to resolve this — it's a single lookup that
settles whether a human, an integration, or something else made the change.
