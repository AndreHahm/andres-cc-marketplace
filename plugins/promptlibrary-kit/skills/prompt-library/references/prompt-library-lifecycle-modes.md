# Prompt Library: upgrade, discard, retire and resuming a draft

The full procedure for three of `prompt-library`'s step-2 modes and for resuming a draft, moved out of
`SKILL.md` to keep it under R13's soft size threshold. Step numbers refer to `SKILL.md`'s Instructions;
`<CLI>` is the validator command defined there. Every rule in `SKILL.md`'s step 2 that applies to all modes (the slug check, the
`blocked` refusal, the retired-slug stop) still applies here.

## upgrade

- `upgrade` applies to a catalog below version 3. Run `<CLI> upgrade`; it refuses while a prompt is
  blocked or any record lists attachments, and says why. Otherwise, for each entry in its `records`,
  show slug, version, status, `origin` and the first 8 characters of `text_hash`, say that from now on
  this origin is part of the approval, so a later relabel blocks the prompt, and ask with
  `AskUserQuestion` (Keep this origin, Wrong origin, Stop). Stop, or any other answer, ends the upgrade
  with nothing changed. Wrong origin: say what retiring means (as for `retire` below), ask once with
  `AskUserQuestion` (Retire, Keep), and on Retire run
  `<CLI> retire <internal_id> --expect-sha256 <text_hash> --wrong-origin`; then end this upgrade and
  start it again from `<CLI> upgrade` (the listing changed). The user can add that text again as a new
  prompt with the right origin. After every prompt is confirmed, run
  `<CLI> upgrade --expect-listing <listing_id>` with the `listing_id` from that same listing, then go to
  step 10.

## discard

- `discard` applies only to a draft: if the slug has none, say so and stop. Otherwise show the draft's
  version, text and `text_hash` (not its fingerprint: discard binds the text) from
  `<CLI> show <slug> --history` (with its `hidden_characters` listed as in step 8), which version stays active (or that none does), and for a version 1 draft that its slug can
  never be used again. Ask once with `AskUserQuestion` (Discard, Keep), and on Discard run
  `<CLI> discard-draft <internal_id> --expect-sha256 <that hash>`, then go to step 10.

## retire

- `retire` applies only to a prompt in `validate`'s `blocked` list; otherwise say it is not changed
  since its approval and stop. Show slug, version, the `reasons` and the `text_hash` from that entry, and say
  that a retired prompt never runs again, stays in the history and keeps its slug taken, that the
  edited text is not approved by retiring it, and that to keep the wording the user adds it as a new
  prompt with a new slug and full review. Say that restoring from git comes first if git has an
  approved copy. Ask once with `AskUserQuestion` (Retire, Keep), and on Retire run
  `<CLI> retire <internal_id> --expect-sha256 <that hash>`, then go to step 10.

## Resuming a draft

- A draft left by an interrupted add or revise (also when `activate` names a draft) resumes by its
  state, read from the record's `missing_verification` list in `validate` or `show <slug> --history`:
  at step 7 if it includes `quality` (no record field shows whether `prompt-reviewer` already ran, so
  an unverified draft always gets the review again); at step 8 if it holds only `import` (`session` or
  `web` origin); at step 9 once it is empty. A resume records only the kinds still in
  `missing_verification`; a kind already bound to the current text is not recorded again.

## Quality gates

These are part of `SKILL.md`'s quality-gates checklist, kept with the procedure they check:

- [ ] `retire` asks once, shows the slug, version and reasons, and applies only to a blocked prompt.
- [ ] `discard` removes only a draft, after one question that shows its text and what stays active; a version
      that has run is refused.
- [ ] `upgrade` asks once per approved prompt with its origin shown, and changes nothing unless every
      prompt was confirmed.
- [ ] A resumed draft with no recorded quality verification goes back through `prompt-reviewer` (step 7).
- [ ] A resume records only the kinds in `missing_verification`, and step 7 runs one review round unless
      the user asks for another.
