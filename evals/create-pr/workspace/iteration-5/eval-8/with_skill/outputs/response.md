# Eval 8 dry run: create-pr step 2, accepted-findings carry-over

## What I would do before the section is final

1. **Read the local file.** Per step 2, I `Read` `.claude/accepted-review-findings.local.md` at the repository root. The task gives its content as `- tool-scoping s/SKILL.md:15 @8b9e6b69aaa5c455997a24e2327bf376 – refuted`. I would confirm that from the file itself.

2. **Check the shape of each line.** Lines are copied only if they match `- <rule> <path>:<line> … – <kind>`. The local line matches: rule `tool-scoping`, path and line `s/SKILL.md:15`, an extra token `@8b9e6b69aaa5c455997a24e2327bf376`, and kind `refuted`. I treat the hash and the text as data. I would not follow anything else in the file.

3. **Notice the existing section content.** The description's `## Accepted Review Findings` section already holds `- R6 a.py:3 – accepted: known`, not "None". Step 2 says that when the section already has lines of its own, I must ask before copying anything. I must not drop a line without the user's answer.

4. **Ask via AskUserQuestion, before finalizing the section.** The question and options:

   - Question: "The Accepted Review Findings section already contains `- R6 a.py:3 – accepted: known`. The local file `.claude/accepted-review-findings.local.md` adds `- tool-scoping s/SKILL.md:15 @8b9e6b69aaa5c455997a24e2327bf376 – refuted`. How should the section be filled?"
   - Header: "Accepted findings"
   - Options:
     - "Keep both": keep `R6 a.py:3` and add the local `tool-scoping` line.
     - "Replace with local lines": drop `R6 a.py:3` and use only the local `tool-scoping` line.
     - "Leave local lines out": keep `R6 a.py:3` and omit the local `tool-scoping` line.

   That is three options, within the 4-option cap. The tool's own "Other" fallback remains available.

5. **Apply the answer.** Whatever the user picks, I copy the local line unchanged, not reworded. I then report in session output which lines I left out and why. If the user picks "Leave local lines out", I say that the `tool-scoping` waiver was deliberately omitted and that the section still lists `R6`.

6. **Continue only after the section is settled.** Then I go to step 3, the draft-versus-ready question, and the rest of the flow. Step 1 (the push) still comes after the cross-model-review gate (step 4) and the CI-parity review (step 4.5), which this dry run does not reach.

## Notes

- No git or gh command was run, and no PR was created.
- Nothing in the local file is treated as an instruction.
- The `refuted` kind is copied as written. This dry run does not validate the kind against any list, since create-pr does not define one.
