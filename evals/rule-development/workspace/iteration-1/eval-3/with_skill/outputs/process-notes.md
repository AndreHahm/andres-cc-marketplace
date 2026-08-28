# Process notes — updating require-gitignored-scratch-locations.md

Followed rule-development's "Updating Existing Rules" procedure:

1. **Read the existing rule file first.** Read the real file at
   `.claude/rules/require-gitignored-scratch-locations.md` in full before making any changes (read-only —
   never modified; the updated version was written only to this eval's `outputs/` directory).

2. **Appended, did not overwrite.** Existing "When this applies", "Rule" bullets, and both original "Why"
   incidents (pytest-cache-files, .codex-review-instructions) are preserved verbatim. The new `./tmp/`
   case was added as:
   - An extra sentence appended to the end of the existing "Watch specifically for..." paragraph in the
     Rule section (rather than a new bullet), since it's the same underlying failure mode (a hardcoded/
     default relative path resolving against cwd) just with a different, scratch-sounding directory name.
   - A third numbered incident under "Why", with its own explanation of why the `./tmp/`-looking name is
     misleading (looks safe, isn't unless `.gitignore` actually covers it).
   - The "Why" section's lead-in and closing paragraph were adjusted from "two occurrences in one session"
     to "three occurrences across two sessions" and the closing generalization sentence was extended to
     call out that a scratch-sounding name doesn't make a path safe — this is the minimal edit needed to
     keep the summary consistent with the added third incident, not a rewrite of the surrounding prose.

3. **Preserved manual edits.** No existing wording was reworded or restructured beyond the minimal
   consistency edits noted above (count "two" -> "three", "one session" -> "two sessions").

4. **Redundancy filter re-run.** Ran `Grep` for `\./tmp|scratch|gitignor` across
   `.claude/rules/**/*.md`. Matches: `resolve-activation-overlap-bidirectionally.md` (unrelated — a
   coincidental "scratch" substring hit, topic is activation-overlap resolution, not file locations),
   `require-inventory-updates-for-new-plugins-and-components.md` and `plugin-rulebook-enforcement.md`
   (mention "gitignored" only in passing re: local config files, not scratch/output dirs — no overlap),
   `ask-before-config-decisions.md` (mentions a gitignored local config file, different topic — config
   storage choice, not scratch/cache output). No new overlap introduced by this addition; the rule stays
   the single home for "temp/scratch/cache output landing in a shippable location."

5. **Security self-check re-run.** Scanned the updated file for long hex strings, base64-like blobs, and
   keyword-adjacent literals (key/token/secret/password/credential) and internal URLs. None present — the
   new text only adds a directory name (`./tmp/`) and a description of the incident; no secrets or
   internal-only references were introduced.

6. **`/rules-review` simulation.** `/rules-review` (the `rules-review` skill) was not actually invoked in
   this eval sandbox (no live session to re-run it against real diffs). Simulated its check by manually
   re-reading the updated file end-to-end to confirm: the new example is contrastive-in-spirit with the
   existing two (same shape: hardcoded/default relative path, different literal name), the addition
   doesn't contradict any existing bullet, and the file's structure (When this applies / Rule / Why)
   remains intact and internally consistent after the edit. Flagging this as a simulated check, not an
   actual tool invocation, per the task's sandboxing constraints (no edits to the real
   `.claude/rules/` directory were made).

## Output

Updated file written to:
`evals/rule-development/workspace/iteration-1/eval-3/with_skill/outputs/require-gitignored-scratch-locations.md`

(The real repo file was left untouched, as instructed.)
