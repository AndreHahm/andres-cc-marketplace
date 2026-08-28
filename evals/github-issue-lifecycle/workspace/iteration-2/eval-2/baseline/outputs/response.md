# Marking issue #50 as a sub-issue of issue #40

## Mechanism

Use GitHub's **Sub-issues REST API**, invoked through `gh api` (the `gh issue` CLI subcommands do
not expose sub-issue linking directly, so you can't do this with a plain `gh issue edit` call).
This is GitHub's first-class "sub-issues" relationship (shown as a "Sub-issues" progress list on the
parent issue), not the older convention of writing `- [ ] #50` as a Markdown task-list item in the
issue body — that older convention only creates a lightweight, unofficial link and does not populate
the real sub-issue relationship, progress bar, or hierarchy shown in the UI/API.

The two calls needed:

```bash
# 1. Look up the *internal* database id of issue #50 (not its number)
SUB_ID=$(gh api repos/<owner>/<repo>/issues/50 --jq .id)

# 2. Attach it as a sub-issue of #40, using that internal id
gh api repos/<owner>/<repo>/issues/40/sub_issues \
  -X POST \
  -F sub_issue_id="$SUB_ID"
```

Equivalently, via curl against the REST API:

```bash
curl -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer <token>" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  https://api.github.com/repos/<owner>/<repo>/issues/40/sub_issues \
  -d '{"sub_issue_id": 123456789}'
```

(The UI equivalent is opening issue #40, using the "Sub-issues" section's "Add sub-issue" control,
and searching for #50 by number — the UI does the id lookup for you under the hood.)

## The specific gotcha

**The endpoint takes the sub-issue's internal database `id`, not its issue `number`.**

`POST /repos/{owner}/{repo}/issues/{issue_number}/sub_issues` is called on the **parent** using its
issue *number* (`40`) in the URL path, but the request body field `sub_issue_id` expects the
**child's** internal numeric `id` — the same opaque id GitHub uses internally for the issue object
(returned as `.id` from `GET /repos/{owner}/{repo}/issues/{issue_number}`), which is a different,
much larger number than the human-facing issue number `50` you see in the UI/URL. If you naively pass
`50` as `sub_issue_id` (assuming it behaves like the issue number everywhere else in the API), the
call will either fail outright or — worse — silently link the wrong issue, since `50` could coincidentally
be a valid internal id belonging to some unrelated issue.

So the required two-step sequence is:
1. Resolve #50's real `id` field via a `GET` on that issue.
2. Pass that `id` (not `50`) as `sub_issue_id` in the `POST` to #40's `/sub_issues` endpoint.

A secondary, smaller gotcha when using `gh api` specifically: use `-F` (capital, typed/raw field),
not `-f` (string field), for `sub_issue_id`. `gh api -f` sends the value as a JSON string, while the
API expects a JSON number — some endpoints tolerate the string form via coercion, but it's safer and
matches GitHub's own documented examples to send it as a real integer with `-F`.

## Preconditions worth checking

- Both issues must be in a repository where the "Sub-issues" feature is available (GitHub rolled
  this out broadly in 2025; virtually all repos have it now, but very old/legacy setups could differ).
- You need write access to the repo/issue to attach sub-issues.
- An issue can only be a sub-issue of one parent at a time — if #50 is already a sub-issue of some
  other issue, this call will need to remove/reparent it rather than simply add it.
