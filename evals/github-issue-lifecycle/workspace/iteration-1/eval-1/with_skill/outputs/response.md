# Task

A user pastes a raw bug description and asks to file it as a new GitHub issue in this repo. Walk
through what `github-issue-lifecycle` does before any issue is actually created on GitHub.

# Response

This request matches `github-issue-lifecycle`'s "Filing a new issue after confirming it isn't a
duplicate" entry under **When to Use**, so the skill activates and routes to **Workflow 1**
(`workflows/create-an-issue.md`). Everything in that workflow up through Step 2 happens *before* any
issue exists on GitHub — the live-filing call (`gh issue create`) doesn't happen until Step 3, and the
skill's own wording ("once the draft is approved") makes that a gated step, not automatic. So here is
what happens first:

## Step 1 — Dedup check (before drafting anything)

The workflow is explicit that this runs *before drafting*: search for a real duplicate using both

```
gh issue list --search "<keywords>"
gh api search/issues -f q="repo:<owner>/<repo> is:issue <keywords>"
```

`<keywords>` would be pulled from the pasted bug description (e.g. the error message, the affected
component). If a genuine duplicate turns up, the workflow stops right here and points at the existing
issue instead of continuing — no draft, no filing. This mirrors `github-issue-creator`'s own dedup
framing for the create-time case, per the workflow file's note.

Note: any text read back from that search (issue titles/bodies/comments) is treated as untrusted data
per the skill's own data-only boundary — even if a returned issue's text looks like an instruction, it's
never acted on, only compared/displayed.

Assuming no duplicate is found, the flow proceeds.

## Step 2 — Delegate drafting to `github-issue-creator`

`github-issue-lifecycle` does not draft the issue text itself. It invokes
`Skill(git-kit:github-issue-creator)`, handing it the user's raw pasted bug description verbatim.

`github-issue-creator` has no `gh`/`Bash` access (`allowed-tools: Write, Read` only) — it cannot file
anything live even if asked to. What it does:

1. Extracts structure from the raw/messy input (the pasted description) into
   `assets/issue-template.md`'s fixed sections: Summary, Environment, Reproduction Steps, Expected
   Behavior, Actual Behavior, Impact, Additional Context (plus an Error Details block and image
   references where applicable).
2. Matches severity to impact using its documented Critical/High/Medium/Low definitions (e.g.
   "Critical: service down, data loss, security issue"; "High: major feature broken, no workaround").
3. Placeholders any sensitive data it finds in the pasted text — project names, user IDs, emails
   (`[EMAIL]`), tokens/API keys (`[REDACTED_TOKEN]`), internal hostnames (`[INTERNAL_HOST]`), session
   IDs (`[SESSION_ID]`), and absolute filesystem paths containing usernames (`[LOCAL_PATH]`) — before
   anything is written to disk.
4. Writes the result as a **local markdown file only**, at `issues/YYYY-MM-DD-short-description.md` in
   the repo root. Nothing has touched GitHub yet.

Control then returns to `github-issue-lifecycle`, which — per Step 3's "once the draft is approved"
wording — implies the draft is surfaced back to the user for a look before it gets filed live. This is
the natural checkpoint where the user can correct a miscategorized severity, fix an inferred detail that
was wrong, or catch anything that should have been redacted but wasn't.

## What happens next (for context, not yet executed)

Only once the draft is approved does `github-issue-lifecycle` take over again for the parts that
actually touch GitHub:

- **Step 3 (File It Live):** `gh issue create --title "<title>" --body-file <draft-path>` — this is the
  actual point the issue is created on GitHub. `github-issue-lifecycle` owns this call specifically
  because `github-issue-creator` is documented as never filing directly.
- **Step 4 (Verify):** real verification after filing — reproducing the bug or re-checking the claim
  against current code/docs, not just confirming the template fields are filled in.
- **Step 5 (Initial Impact Analysis):** a first-pass severity/impact read off the filed issue, explicitly
  re-run later in Workflow 2 rather than treated as final.
- **Step 6 (Link to Originating PR, if applicable):** delegates to
  `Skill(git-kit:collaborating-on-a-pr)` rather than reimplementing PR↔issue linking, only if the bug
  traces back to work on an open PR.

## Summary of the pre-filing sequence

1. Skill activates on the "file this as a new issue" framing → routes to Workflow 1.
2. Dedup search (`gh issue list --search`, `gh api search/issues`) — stop and point at the existing issue
   if a real duplicate exists.
3. Delegate to `github-issue-creator`, which turns the raw paste into a structured, severity-tagged,
   sensitive-data-redacted local draft at `issues/YYYY-MM-DD-short-description.md` — no GitHub API calls
   made by this step.
4. Draft is presented for approval.
5. Only after approval does `gh issue create` (Step 3) actually create the issue on GitHub.

So concretely: two full sub-steps (a live dedup search against GitHub's existing issues, and a fully
local drafting pass with no GitHub write access) happen, plus an implied approval checkpoint, before a
single byte reaches GitHub as a real issue.

# Files consulted

- `plugins/git-kit/skills/github-issue-lifecycle/SKILL.md`
- `plugins/git-kit/skills/github-issue-lifecycle/workflows/create-an-issue.md`
- `plugins/git-kit/skills/github-issue-creator/SKILL.md`
