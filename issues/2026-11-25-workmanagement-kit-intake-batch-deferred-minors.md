## Summary
Follow-up for the Minor findings deferred from PR #505 (intake batch, query and update) in workmanagement-kit

## Environment
- **Product/Service**: `workmanagement-kit`: `plugins/workmanagement-kit/scripts/wmgt_batch_hash.py`, the intake batch contract, `linear-work-management`
- **Region/Version**: N/A (code read again on 2026-11-25)
- **Browser/OS**: item 3 applies to Windows only

## Reproduction Steps
Found by review and by reading the code; none was reproduced at runtime.

1. **Lost manifest entry.** Run `hash` on two submissions in the same folder at the same time. `_register` reads the manifest, then writes through one fixed temporary name (`manifest.wmgt.tmp`), so one entry can be lost.
2. **Linked scratch root.** Call `purge` with a `scratch_root` that is a symlink or has a linked ancestor. Only `wmgt-intake` itself is checked for being a link; everything above it is followed by `realpath`.
3. **Check-then-use windows.** `purge` checks the folder and then resolves it, and on Windows `_unlink_in_dir` checks a path name and then calls `os.remove`.
4. **No Windows junction test.** `wmgt_test_batch_hash.py` covers symlinks only, although `_is_link_or_junction` handles junctions.
5. **Replay of created indexes.** After a purge followed by recreating an identical file, or after context compaction, indexes that were already written can be delegated again while the approval still looks current. `create` batches only; the batch contract discloses it.
6. **Ambiguous wording.** `linear-work-management`'s `SKILL.md` says "already-validated delegation" and "what `plugin-integration-intake` validated", which can be read as trusting a request's own claim to have been validated.

## Expected Behavior
1. Unique temporary name, and a re-read check so that no entry is lost
2. A linked `scratch_root` or ancestor is refused, or the limit is documented
3. The windows are narrowed where the platform allows, or documented
4. A junction test on Windows
5. A consumed-hash record that survives `purge` (needs a small state design)
6. Wording that makes clear the skill checks the delegation itself

## Actual Behavior
As described above. For item 1 the effect is a scratch file that is left behind; a file is never wrongly deleted.

## Impact
**Low** - no known wrong write or wrong deletion. Item 5 is the one with a user-visible effect (duplicate Issues), and only in a session that replays an approved batch.

## Additional Context
- Deferred from PR #505 and planned to be filed together with package 3c.
- Still unverified against a live connector: whether `save_issue` creates an unknown label by name, and whether it accepts a string `priority`. Both are checks for the activation session.
- Not included: a repository slug that starts with a dot is refused (documented as intended), a hard-linked submission is already refused by `hash`, and the two `SKILL.md` files near the 300-line soft limit need no change by themselves.
