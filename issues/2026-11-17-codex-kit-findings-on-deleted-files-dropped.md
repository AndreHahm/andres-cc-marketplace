## Summary
codex-kit's shared `semanticallyValidate` drops every finding that cites a file the reviewed diff deletes, because `locateInSemanticScope` requires the cited path to exist on disk.

## Environment
- **Product/Service**: codex-kit (`skills/codex-review-bridge/scripts/bridge-invoke.mjs`), used by codex-kit's own review path and by reviewadapters-kit's dispatcher
- **Region/Version**: main, and PR #759's head `9ce26dc4537c750fe8683d6ec4d82ee46f2fa24b`

## Reproduction Steps
1. Review a diff that deletes a file (for example `removed.py`), with that path in the target-path list.
2. Have the reviewer return a finding that cites `removed.py:1`.
3. Run the envelope through `semanticallyValidate`.

## Expected Behavior
A finding that cites a file deleted by the diff passes validation: the file is part of the change under review, and both rva-prepare.mjs and the dispatcher list deleted files and both rename sides as target paths on purpose.

## Actual Behavior
`locateInSemanticScope` (bridge-invoke.mjs, line 261) ends with `return fs.existsSync(absolute)`, which is false for a deleted file. When every finding cites deleted files, the run fails with `semantic_validation_failure`; when other findings survive, the deleted-file findings are removed and only a generic `inspection_limits` note records the drop. Codex reproduced it on PR #759 with a fake pi response: a valid finding on `removed.py:1` produced `semantic_validation_failure`.

## Error Details
~~~
category: semantic_validation_failure
~~~

## Visual Evidence
None.

## Impact
**High**: a review of a change that deletes a file can lose real findings about that deletion, silently when other findings survive. It affects codex-kit's own review path and every reviewadapters-kit vendor.

## Additional Context
Fix direction: validate a citation against the diff's changed paths, deletion headers included, instead of requiring the file to exist in the working tree, in codex-kit's shared validator, so both callers get it. Out of scope for PR #759, which only consumes the validator.

Found in PR #759 (round 1, Major), raised by three reviewers on the same defect:
- PR: https://github.com/AndreHahm/andres-cc-marketplace/pull/759
- Head SHA: 9ce26dc4537c750fe8683d6ec4d82ee46f2fa24b
- Codex (P2): https://github.com/AndreHahm/andres-cc-marketplace/pull/759#discussion_r4598064503
- Devin (bug): https://github.com/AndreHahm/andres-cc-marketplace/pull/759#discussion_r4598067447
- CodeRabbit (Minor, heavy lift): https://github.com/AndreHahm/andres-cc-marketplace/pull/759#discussion_r4598228131
- Severity: Major (the highest of the reviewers' labels and the described defect)
