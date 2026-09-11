Below is exactly what I'd do to begin development on ENG-310, with a clear flag on which parts are real (this session, this repo) and which are simulated because I don't have live Linear/GitHub/git access right now.

---

**Disclosure up front:** I don't have live Linear or GitHub connectivity in this environment, so I can't actually fetch ENG-310's real details or push a real branch. Everything below that looks like ticket content, commit SHAs, or command output is **illustrative/simulated** — not confirmed real data. I'll narrate the steps I'd take and show what the output would plausibly look like, but treat none of it as verified fact until you or a connected session confirms it.

## Step 1 — Pull the actual issue details

Normally I'd start by fetching ENG-310 from Linear (title, description, acceptance criteria, labels, linked designs, any parent/sub-issues) rather than working from the issue key alone — "accepted and ready to implement" tells me status but not scope. Since I can't reach Linear right now, I don't actually know what ENG-310 is about. I'm not going to invent a plausible-sounding feature description and pretend it's real — that would be worse than saying I don't know.

**What I need from you (or a connected session) before real work starts:**
- ENG-310's title/description/acceptance criteria
- Which repo/component it targets (you said "this repository" — good, that narrows it, but I'd still confirm the issue doesn't span multiple repos)
- Any linked design docs or parent epic for context

## Step 2 — Confirm repo state

This part I *can* actually check, since I do have access to this working directory. Current state: on `main`, clean working tree, HEAD at `591ec32e` (the `workmanagement-kit` fix commits from earlier PR #303 work). So the repo itself is in a normal, buildable starting state.

## Step 3 — Create a branch for the work

Once I know what ENG-310 actually involves, I'd create a feature branch off an up-to-date `main`, named to reflect the issue — something like:

```
git checkout main
git pull origin main
git checkout -b eng-310-<short-slug-of-actual-work>
```

(Simulated example only — `eng-310-short-slug` isn't a real branch name until I know what the issue says.)

## Step 4 — Move the Linear issue to "In Progress"

Normally, once a branch exists and I'm about to start real work, I'd update ENG-310's status in Linear from Accepted/Ready to **In Progress** (and assign it to myself if it isn't already), so the ticket reflects reality rather than sitting stale. I can't perform this write without live Linear access — simulated illustration of what that update would look like:

```
Issue: ENG-310
Status: Accepted → In Progress   (simulated, not applied)
Assignee: (unchanged / andre.hahm@me.com)
```

## Step 5 — Orient in the codebase

Once the branch exists and I know the actual scope, I'd grep/read the relevant area of `workmanagement-kit` (or wherever ENG-310 points) before writing any code — existing patterns, related skills/agents/commands, tests — rather than guessing at conventions.

## Step 6 — Implement, test, commit

Standard loop from there: implement against the issue's acceptance criteria, run/extend tests, commit with a message referencing ENG-310, and open a PR once it's ready — linking back to the Linear issue so the two stay connected.

---

### What's blocking real progress right now

I genuinely can't start step 3 onward correctly without knowing what ENG-310 actually says — I don't want to fabricate a ticket description and start coding against an invented spec. Could you either:

1. Paste ENG-310's title/description/acceptance criteria here, or
2. Confirm you have a connected session (with real Linear/GitHub access) where I should pick this up instead?

Once I have the real issue content, I'll create the actual branch, do the real implementation work, and keep Linear's status in sync as it progresses — not the simulated placeholders shown above.
