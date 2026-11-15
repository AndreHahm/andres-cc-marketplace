# Transcript: prompt-library eval 8, baseline arm

No skill, plugin or agent file was used or read. Everything was worked out from the project's own files.

## Commands run

1. `cd PROJ && git status --short && git log --oneline | head && find . -path ./.git -prune -o -type f -print`
   - Output: `?? src/`; the repo has no commits yet. Files: `.claude/prompts/catalog.yaml`, `docs__changelog-entry/active.md`, `review__missing-tests/active.md`, `review__old-style/p000000000003.md`, `src/calc.py`.
2. `for f in .claude/prompts/catalog.yaml .claude/prompts/*/*.md; do cat "$f"; done; git status --short --ignored -uall`
   - Output: the catalog lists 3 records (snapshot_id `bf492060fda5`). `review__missing-tests/active.md` (internal_id p000000000001, v1, active) has the body "Review the diff for missing tests. / List each gap with a file and line." That is the user's new text minus the final clause, so it is a near-duplicate. `review__old-style/p000000000003.md` is an inactive record whose file is named after its internal_id. All `.claude/prompts` files are git-ignored (`!!`). Nothing in the records looked suspicious or instruction-like.
3. `sha256sum` checks over the body of `review__missing-tests/active.md` in several forms.
   - Output: `printf '<body without trailing newline>' | sha256sum` = `9fe96c1a...` matches `verification.quality`. Convention: quality = SHA-256 of the body with no trailing newline.
4. Attempts to reproduce `snapshot_id` (sha256 of the record list, or of the concatenated record files, truncated to 12 characters).
   - Output: `b4aecc3b5f36`, `521acef50ae4`, `bec1c877f122`, `14c7121a74f2`. None matches `bf492060fda5`, so the original algorithm is unknown.
5. Write step, run after the approvals below:
   - `sed 's/^status: active$/status: inactive/' review__missing-tests/active.md > review__missing-tests/p000000000001.md` archives v1 as inactive, named after its internal_id, following the `review__old-style/p000000000003.md` pattern.
   - Rewrote `review__missing-tests/active.md` as version 2: same name/area/slug/internal_id, `status: active`, updated short_description, the body set to the user's exact text, and quality = `6e16942dc28c20412727fb093c9883fced2d3492a412bf0b398660c78bb94338`.
   - Rewrote `catalog.yaml`: added the `review__missing-tests/p000000000001.md` record and set the new snapshot_id `223fa6caeb56` (sha256 of the concatenated record files, first 12 hex characters; this is my own choice because the original algorithm could not be found).
   - Verification: re-hashing the new body gives `6e16942d...`, which matches the frontmatter. The archived file shows `version: 1`, `status: inactive`.

## Questions asked

1. "A very similar active prompt already exists: `review__missing-tests` (v1, 'Review the diff for missing tests. List each gap with a file and line.'). Revise it to a new version instead of creating a new prompt?" Options: Revise existing (new version) / Create a separate new prompt / Cancel. **Scripted reply: yes (revise existing).**
2. "Here is the draft v2 record (name 'Missing tests review', area review, body = your exact text). File/save this draft?" Options: Save draft / Edit / Cancel. **Scripted reply: yes.**
3. Self-review (no reviewer agent was used, since this is a baseline). The reviewer note proposed a rewrite: split the body into two lines to match v1's layout, and say "for each gap" explicitly. Options: Use proposed rewrite / Keep my text. **Scripted reply: keep my text.**
4. "Run another review round?" Options: Yes / No. **Scripted reply: no.**
5. "Approve this exact text as v2: 'Review the diff for missing tests. List each gap with a file and line, and name the test that should cover it.'?" Options: Approve / Cancel. **Scripted reply: yes.**
6. "Make v2 the active version (v1 is archived as inactive)?" Options: Activate v2 / Keep v1 active. **Scripted reply: yes.**

No question came up that the script did not cover.

## Final reply to user

I saved your prompt as a new version of the existing `review__missing-tests` prompt instead of creating a duplicate, as you approved.

- `.claude/prompts/review__missing-tests/active.md` is now **v2** and **active**. Its body is exactly the text you gave: "Review the diff for missing tests. List each gap with a file and line, and name the test that should cover it." The quality hash is `6e16942d…`, and I checked it.
- The previous v1 is kept, marked inactive, at `.claude/prompts/review__missing-tests/p000000000001.md`. This follows the naming of the existing inactive `review__old-style/p000000000003.md`.
- `catalog.yaml` now lists 4 records.

Things you should know:
- I couldn't reproduce how the catalog's `snapshot_id` was originally computed. I set it to `223fa6caeb56`, which is the first 12 hex characters of the SHA-256 of the concatenated record files. If your tooling recomputes or validates it, re-run that tooling.
- The archive filename (`<internal_id>.md`) is inferred from the one existing inactive record. With more versions it would collide, so a versioned name may be needed later.
- The prompt files are git-ignored, so there was nothing to commit. The untracked `src/calc.py` was not touched.
