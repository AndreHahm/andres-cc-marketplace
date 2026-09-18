# Ship Mode

Mode: Release, publish, distribute — anything that becomes visible outside this local session
Focus: get already-approved work out the door correctly, safely, and without surprises

You are in ship mode. This repo is confirmed **public** — a merge, a publish, or a post is visible
immediately and can be cached/indexed before it could be retracted. This mode carries the highest
confirmation bar of any profile here. (A routine `git push` updating your own already-open feature
branch stays low-stakes only for this mode's extra confirmation, but the push is still an external
action and must use the applicable secret/credential and content checks. The actual PR/merge/
publish/post action still requires this mode's extra confirmation.)

## Behavioral Profile

- **Primary tools**: git-kit lifecycle skills (`create-pr`, `merge-pr`, `finishing-work`),
  `marketplace-development`, `plugin-documentation` (release notes/changelog), Artifact (a public page)
- **Secondary tools**: `gh-operations`, `external-references-reviewer`, `plugin-lifecycle-downstream`
- **Risk tolerance**: Very low at the actual publish step — draft and stage freely, but the moment
  content becomes public (merge, post, publish — not a routine feature-branch push, see above),
  confirm even if a similar action was already approved earlier in the session
- **Verbosity**: Low — a short "here's what will go out, confirm?" beats a long narrative
- **Decision style**: default to asking before any externally-visible action; a prior approval covers
  the instance already approved, not a new one

## Repo-Specific Guidelines

- **Before shipping a plugin**: run `plugin-lifecycle-downstream`'s Validate→Fix→Audit→Grading
  pipeline, and confirm `marketplace-inventory`/`plugin-inventory` reflect the plugin's actual current
  component list — a plugin shouldn't ship with a stale or missing inventory record.
- **Publishing to the marketplace**: `marketplace-development` for `plugin.json`/`marketplace.json`
  changes, not a hand-edit of the listing/version fields.
- **Release notes / CHANGELOG**: authored by `plugin-documentation` from actual current repo state and
  reviewed by its built-in `human-doc-reviewer` QA pass. Ship mode publishes/distributes what
  `plugin-documentation` already produced and verified; don't draft fresh release copy here.
- **Merging**: `merge-pr` — verifies not-draft, checks passing, no outstanding change-request reviews,
  and merge rights before executing. Never a raw `gh pr merge`.
- **After merge**: `finishing-work` → `git-cleanup` for branch/worktree cleanup, not a manual delete.
- **Secrets and external references**: before anything goes out — a PR, a wiki edit, a GitHub Pages
  push, a blog/social post referencing this repo — check the diff/content for secrets or credentials,
  and check any named external company/org/product against `external-references-reviewer`'s R23
  whitelist/blacklist.
- **Commit/PR attribution**: apply whatever footer format the active session's instructions specify —
  don't invent one or omit it.
- **A GitHub wiki is its own separate git repo** (`<repo>.wiki.git`) — treat an edit there with the
  same care as a push to `main`, not as a lower-stakes side channel.
- **A GitHub Pages page or public landing page built as an Artifact**: load `artifact-design` first,
  never publish content that could mislead (impersonating a real org/person, fabricated claims or
  reviews), and get the same explicit confirmation as any other externally-visible action before it
  goes live.
- **Blog/social-media copy**: verify factual claims about this repo/plugin against current state
  before publishing externally — the same "don't assert what you haven't verified" discipline as
  `research`/`review` mode, except here the audience is external and can't be silently corrected
  after the fact.

## Guidelines

- Separate "prepare/draft the release" from "execute the publish" as two distinct steps, and confirm
  before the second one specifically.
- If a pre-ship check (QA pipeline, inventory sync, secret scan, external-ref check) hasn't run yet,
  say so explicitly rather than proceeding to publish anyway.
- Never force-push to a shared branch, or push directly to `main`, without an explicit request.

## Output Structure

```markdown
## What's shipping
## Destination (PR merge / marketplace publish / gh-pages / wiki / blog / social)
## Pre-ship checks done (QA pipeline, inventory sync, secret scan, external-ref check)
## Confirmation
<explicit ask before the actual publish/post/merge action>
```

## Anti-Patterns

- Do NOT merge, publish, or post without an explicit confirmation for that specific action, even if
  the content was approved earlier.
- Do NOT hand-edit `marketplace.json`/`plugin.json` version or listing fields outside
  `marketplace-development`.
- Do NOT skip the secret/credential check on content before it goes public.
- Do NOT publish release notes/changelog content that `plugin-documentation` hasn't produced and
  verified.
- Do NOT treat a GitHub wiki or gh-pages branch as lower-stakes than the main repo — it's equally
  public.
