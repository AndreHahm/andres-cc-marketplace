[Context-Mode] ship activated — supersedes any previously active mode.

This is a manual mode switch request, so I'm activating it directly per the skill's dispatch logic
(explicit request always wins over any same-turn hook tag).

**Ship mode** — release, publish, distribute: anything that becomes visible outside this local session.
Focus: get already-approved work out the door correctly, safely, and without surprises.

This repo is confirmed **public** — a merge, publish, or post is visible immediately and can be
cached/indexed before it could be retracted. Ship carries the **highest confirmation bar** of any
context-mode profile. Key points now in effect for the rest of this session:

- **Very low risk tolerance at the actual publish step.** I'll draft and stage freely, but the moment
  something becomes public (merge, post, publish — not a routine feature-branch push, which stays
  `dev`'s scope), I'll confirm explicitly before it happens, even if a similar action was already
  approved earlier in the session.
- **Primary tools**: git-kit's lifecycle skills (`create-pr`, `merge-pr`, `finishing-work`),
  `marketplace-development`, `plugin-documentation` for release notes/changelog, and `Artifact` for any
  public page.
- **Merging** goes through `merge-pr` (readiness + merge-rights checks) — never a raw `gh pr merge`.
- **Before shipping a plugin**: the `plugin-lifecycle-downstream` Validate→Fix→Audit→Grading pipeline,
  plus confirming `marketplace-inventory`/`plugin-inventory` reflect the plugin's actual component list.
- **Secrets/external references**: checked before anything goes out (PR, wiki edit, GitHub Pages push,
  blog/social post) — diff/content scanned for secrets, external references checked against
  `external-references-reviewer`'s R23 whitelist/blacklist.
- I'll separate "prepare/draft the release" from "execute the publish" as two distinct steps, and flag
  explicitly if a pre-ship check (QA pipeline, inventory sync, secret scan, external-ref check) hasn't
  run yet rather than proceeding anyway.
- No force-push to a shared branch and no direct push to `main` without an explicit request.

I'm ready to proceed under ship mode — let me know what you'd like to ship.
