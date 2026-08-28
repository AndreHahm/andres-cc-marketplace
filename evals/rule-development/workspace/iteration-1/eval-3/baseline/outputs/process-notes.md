# Process Notes — Baseline (no skill/methodology)

1. Read the real existing rule file at
   `.claude/rules/require-gitignored-scratch-locations.md` (read-only) to capture its current
   content: "When this applies", "Rule" (with the "watch specifically for" paragraph), and "Why"
   (two documented 2026-08-14 incidents: `pytest-cache-files-*` and `.codex-review-instructions/`).
2. Identified where the new case (a script hardcoding a `./tmp/` output directory relative to cwd
   instead of the scratchpad) fits without restructuring the file:
   - Extended the existing "Watch specifically for a default that silently resolves to a shippable
     location" paragraph in the Rule section with the `./tmp/`-style hardcoded relative path as a
     third example alongside the two already there (script default parameter, bare CLI invocation),
     plus a short note that the "tmp" name doesn't make it safe.
   - Added a third numbered incident to the "Why" section's list, describing the `./tmp/` case in the
     same style/detail level as the two existing incidents, and updated the surrounding prose ("Two
     separate real occurrences" -> "Three separate real occurrences across two sessions", "Both had to
     be manually flagged" -> "All three had to be manually flagged").
3. Preserved all existing prose, section structure, and the two original incidents verbatim; only
   added new content, did not remove or reword anything pre-existing beyond the minimal count/pronoun
   updates needed for the new item to read naturally in the same sentences.
4. Wrote the complete updated file to the sandboxed output path (not the real `.claude/rules/`
   directory, per task instructions).
5. Wrote this process-notes file and a timing.json alongside it.

No skills, agents, or other tooling beyond Read/Bash/Write were used, per the task's baseline
instruction.
