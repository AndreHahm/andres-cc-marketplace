## Summary
A CLI path argument's leading `~` wasn't expanded before use — `Path(args.fixture_file)` preserves a literal `~`, so a quoted invocation like `--fixture-file "~/fixture.json"` reads a relative `~` path instead of resolving against the user's home directory.

## Environment
- **Product/Service**: `analysis-kit` plugin — `pr_review_fetcher.py` (`--fixture-file` CLI argument)
- **Region/Version**: this repo, found during PR #179 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. Run `pr_review_fetcher.py --fixture-file "~/fixture.json"`.
2. `Path(args.fixture_file)` constructs a `Path` object with a literal `~` character, not the resolved home directory.
3. `load_fixture` then attempts to open a file relative to the current working directory named `~/fixture.json`, which doesn't exist (or resolves to the wrong location) — the shell's own `~`-expansion never applies here since the argument was quoted.

## Assumed vs. actual

| Assumed | Actual |
|---|---|
| A `~`-prefixed path argument resolves against the user's home directory | Neither `pathlib.Path` nor `Glob` auto-expand a leading `~` — the caller must explicitly call `.expanduser()` |

## Expected Behavior
A CLI argument accepted as a filesystem path should call `.expanduser()` (or the equivalent) before use if a leading `~` is meant to resolve to the home directory.

## Actual Behavior
A quoted `~`-prefixed fixture path silently failed to resolve to the intended file.

## Impact
[Severity: Low] A usability gap affecting only the `--fixture-file` testing/dev path, not the live-fetch path this skill's own instructions actually invoke. Fixed in `analysis-kit`'s PR #179 (commit `3a7a5b5`): `Path(args.fixture_file).expanduser()` applied before `load_fixture`, covered by a new test using `monkeypatch.setenv("HOME"/"USERPROFILE", ...)`, verified live to actually work in a Windows environment.

## Additional Context
Mined from PR #179's own review history (`coderabbitai[bot]`; 25 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #179` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue. This is a distinct instance of the same broader "tilde isn't auto-expanded" theme this same skill's own Gotchas section already discloses for `Glob` — here affecting `pathlib.Path` instead.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/179#discussion_r3885947295
