# Verify Open Items — commit-SHA regex validation

Per `analyzing-plugin-components`'s Phase 2 "Verify Open Items" procedure: before interpolating any SHA into a `Bash(git log)`/`Bash(git show)` call, the stated SHA must first be validated **as an in-context string comparison** (never via a shell test, which would require interpolating the unvalidated string first) against:

```
^[0-9a-fA-F]{7,64}$
```

i.e. case-insensitive hex, 7–64 characters (Git accepts an uppercased object ID, and a SHA-256 repository's object IDs are 64 hex chars, not 40).

## Item 1 — `5736730DDDCBEFAF487E50CACDB1D3DC7229B078`

- Length: 40 characters (verified by direct count).
- Alphabet: every character is one of `0-9` or `A-F` (letters present: D, C, B, E, F, A — none outside the hex range).
- **Result: PASS.** All-uppercase hex is explicitly fine — the regex is case-insensitive and the skill notes Git itself accepts an uppercased object ID. 40 hex chars is also the expected length for a standard SHA-1 repository's object ID.
- **Would I proceed to `Bash(git log)`/`Bash(git show)`?** Yes. Next step is direct verification — e.g. `git log -1 --format=%H` on the merge target, comparing the actual returned hash length against this artifact's stated 40-char length, then confirm `git show 5736730DDDCBEFAF487E50CACDB1D3DC7229B078` resolves. If it doesn't resolve at all, that triggers the separate "Commit SHA doesn't resolve at all" step.

## Item 2 — `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

- Length: 64 characters (verified by direct count in 8-char blocks).
- Alphabet: every character is one of `0-9` or `a-f` (letters present: e, b, c, f, a — none outside the hex range).
- **Result: PASS.** 64 lowercase hex characters sits exactly at the regex's upper bound (`{7,64}`, inclusive), matching the object-ID length the skill calls out for a SHA-256 repository — consistent with this artifact's stated repo type.
- **Would I proceed to `Bash(git log)`/`Bash(git show)`?** Yes, for the same reason: direct verification against `git log -1 --format=%H`'s actual output length on the SHA-256-format repository, then `git show <sha>` to confirm it resolves.
- Side observation (not part of the regex check itself): this string is bit-for-bit the well-known SHA-256 hash of the empty input — worth flagging as suspicious once re-verified via `git show`, but that doesn't change the outcome of the format check, which is purely syntactic.

## Summary

| Item | Length | Alphabet | Regex result | Proceed to git log/git show? |
|---|---|---|---|---|
| `5736730DDDCBEFAF487E50CACDB1D3DC7229B078` | 40 | hex (upper) | PASS | Yes |
| `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 64 | hex (lower) | PASS | Yes |

Both values pass `^[0-9a-fA-F]{7,64}$` — neither triggers the "do not run the command, record as a malformed reference" branch. Both proceed to direct `Bash(git log)`/`Bash(git show)` verification, with the artifact's stated SHA length cross-checked against each repository's own actual `git log -1 --format=%H` output length.
