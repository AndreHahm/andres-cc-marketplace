# Test Scenarios: open-item-digest

Scenarios to verify by following the skill on a real run:

1. **Second run**: input unchanged sources; the digest's New items sections all read "none".
2. **Edited item**: an item whose text was edited appears as new (its fingerprint changed).
3. **Unattended**: the run completes with no `AskUserQuestion` and no write outside the working folder.
4. **Tracked override**: a tracked local config that redirects `digest.output_dir` is refused with a
   warning and the default folder is used.
5. **Failed write**: if the digest cannot be written, the keys are not marked seen.

Pass criteria: no Linear, Notion or GitHub write, no prompt, output only under the validated folder.
