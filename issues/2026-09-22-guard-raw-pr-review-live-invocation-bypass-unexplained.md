## Summary
A live `PreToolUse` invocation of `guard-raw-pr-review.sh` let a should-be-denied raw `gh api
.../comments/{id}/replies` call through, even though feeding the script the exact same command as
JSON input (direct reproduction) correctly denies it — root cause not yet identified, and not
explained by issue #365's own nested-substitution bug.

## Environment
- **Product/Service**: `git-kit`'s `guard-raw-pr-review.sh` `PreToolUse` hook (registered in
  `.claude/hooks/hooks.json` / `plugins/git-kit/hooks/hooks.json`, matcher `^(Bash|PowerShell)$`,
  `timeout: 5`, `onError: "warn"`)
- **Region/Version**: this repo (`andres-cc-marketplace`), observed 2026-09-22 while replying to a
  Codex review finding on PR #372

## Reproduction Steps
1. In a live session, with no `gh-pr-review` marker written in the preceding 60 seconds, run:
   ```
   gh api repos/{owner}/{repo}/pulls/{n}/comments/{id}/replies -F body=@<file>
   ```
   — a literal command: no `$(...)`/backtick substitution, no `;`/`&`/`|` anywhere in the text.
2. Observed: the call succeeded immediately with a valid GitHub API response. No deny, no warning.
3. Separately, fed the guard script the exact JSON a `PreToolUse` hook receives for that same
   command, with no marker file present:
   ```
   echo '{"tool_name":"Bash","tool_input":{"command":"gh api repos/OWNER/REPO/pulls/N/comments/ID/replies -F body=@FILE"}}' \
     | bash guard-raw-pr-review.sh
   ```
   This correctly returned `"permissionDecision": "deny"`.

## Expected Behavior
The live invocation should have produced the same `deny` decision the direct reproduction produces
for the identical command and identical (absent) marker state.

## Actual Behavior
The live invocation allowed the command through with no visible signal of any kind — no denial, no
warning message.

## Error Details
~~~
(none observed — the live call returned a normal, successful gh api JSON response; no hook warning
appeared anywhere in the session output)
~~~

## Impact
**High, not yet confirmed exploitable-at-will.** This is the same class of gap as #83 (a
security-relevant `PreToolUse` guard silently failing open) — but found live during ordinary,
non-adversarial use (replying to a review comment), not a deliberate bypass attempt. Not yet
reproducible on demand: a direct reproduction of the guard script itself, given the identical input,
correctly denies — so the gap is not in the script's own matching logic, but somewhere in whether/how
the live harness invoked or enforced that specific hook for that specific tool call.

## Additional Context

**Ruled out, each verified directly, not assumed:**
1. **Script logic bug** — ruled out. Hand-traced `API_SPAN_PREFIX_RE` → `API_SPANS` extraction →
   `REPLIES_RE` match against the real command text: with no `;`/`&`/`|` byte anywhere, the extracted
   span is the whole command, and `REPLIES_RE` matches it cleanly. Confirmed by direct reproduction
   (Reproduction Steps, step 3).
2. **Not issue #365.** #365's root cause requires a nested `$(...)`/backtick construct whose own body
   contains an unquoted `;`/`&`/`|` byte, truncating the span before it reaches `/replies`. #365's own
   text states a literal, already-resolved-ID command "is correctly matched and would be denied" — the
   command here was exactly that literal shape.
3. **Stale/leftover marker** — ruled out. No `gh-pr-review`-type marker had been written in the
   preceding 60 seconds; the marker-consuming logic only honors a marker whose `guard` field is
   exactly `gh-pr-review`.
4. **Executable bit / mirror drift** (this repo's own recurring `core.fileMode=false` footgun, per
   `commit`'s SKILL.md Testing & Validation notes on `stage-selected-files.sh`/`lint-commit-message.sh`)
   — ruled out. All four copies of the guard script (`.claude/` and `plugins/git-kit/`, in both the
   primary checkout and the worktree used) are byte-identical (`diff` clean) and `100755`/`-rwxrwxr-x`
   in both git's index and on disk.
5. **Sibling-hook interference** (an earlier hook in the same `^(Bash|PowerShell)$` matcher array
   emitting a decision that short-circuits later hooks in the chain) — ruled out. Ran
   `guard-raw-commit.sh`, `guard-raw-pr-ops.sh`, and `guard-raw-branch-create.sh` against the identical
   input; all three exit `0` with no output at all (silent defer).

**Most plausible existing lead (not confirmed as the cause):** issue #83 ("git-kit's 5 PreToolUse
guard hooks fail open on an internal crash (`onError: "warn"`)", closed 2026-08-29) established that
all 5 guard scripts run under `set -euo pipefail` with `onError: "warn"` registrations, so an
unexpected internal failure fails the security gate open. It was closed after a fix added an `ERR`
trap (`trap fail_closed_deny ERR`) plus marker-timestamp hardening (octal-literal and clock-skew
fixes) to `guard-raw-pr-review.sh` — confirmed present in the script's current source. However, that
same trap's own code comment explicitly discloses an uncovered residual: "a fatal expansion error (an
unbound variable, a bad arithmetic expression) is a parse-time error bash treats differently from a
command's exit status, and a missing/non-executable interpreter or a hook timeout kill are outside
this script's control entirely -- all three still fail open under this hook's 'onError': 'warn'
registration." This residual was never promoted to its own tracked issue. A hook timeout (the
registration's own `timeout: 5`) or an interpreter-launch failure would produce exactly the observed
symptom — but this was **not directly confirmed**: no visible timeout warning appeared, and the
direct reproduction of the script completed near-instantly.

**Related, not duplicates:**
- #83 (closed) — same fail-open-on-crash class; established the disclosed-but-never-tracked
  timeout/interpreter residual named above.
- #365 (open) — investigated and ruled out as the direct cause of this observation (see item 2
  above and the analysis comment already posted on that issue), but this gap was discovered while
  investigating it.

This is a new, currently-unexplained live observation, not a duplicate of either — do not close this
as "fixed by #83" or "duplicate of #365" without independently confirming the actual mechanism first.
