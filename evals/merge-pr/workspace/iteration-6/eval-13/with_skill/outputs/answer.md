# Merge-Rights Check — Tier 1 Owner Comparison

## Scenario

- `$ARGUMENTS` resolves (per SKILL.md step 1) to PR url `https://github.com/acme-org/acme-repo/pull/42`.
- The current local checkout's own git remote points at a completely different repository: `andrehahm/andres-cc-marketplace`.
- Tier 1 of `references/merge-rights-check.md` needs an `{owner}` value to compare the current actor's login against.

## Answer

**Compare against `acme-org`** — the owner from the PR's own already-resolved `url` field from step 1. Do **not** use whatever `gh repo view` would report for the current checkout (`andrehahm`/`andres-cc-marketplace`).

## Why

Both SKILL.md and the merge-rights-check reference file are explicit and consistent on this point:

1. **SKILL.md step 1** already resolves `{owner}/{repo}` from the PR's own `url` field and instructs: "never from a separate `gh repo view`, which resolves to the current checkout's own repository and is wrong whenever `$ARGUMENTS` named a PR in a different repository than this checkout." That is exactly the situation here — `$ARGUMENTS` names a PR in `acme-org/acme-repo`, but the local checkout is `andrehahm/andres-cc-marketplace`.

2. **SKILL.md step 3** explicitly says to pass step 1's already-resolved `{owner}/{repo}` "into every tier of that procedure" — the reference file's Tiers 1 and 3 "rely on this instead of re-deriving it via a fresh `gh repo view`."

3. **references/merge-rights-check.md**'s own preamble restates this even more directly: `{owner}/{repo}` is "always the value SKILL.md's step 1 already resolved from the PR's own `url` field — never re-derive it here via a fresh `gh repo view`." It calls out that `gh repo view` with no argument "resolves to the current checkout's own repository, which is wrong whenever this procedure is checking a PR in a different repository than the current checkout — the exact scenario SKILL.md's step 1 calls out ('a maintainer without the PR's branch checked out can still use this skill on someone else's PR')."

4. **Tier 1 itself** says: "Compare against `{owner}` (step 1's resolved value, not a fresh `gh repo view`)."

This scenario is the textbook case the skill's authors anticipated and wrote explicit guardrails against: a maintainer running `merge-pr` against someone else's PR (in a different repo than their local checkout) must not accidentally compare their login against the wrong repository's owner. Using `andrehahm`/`andres-cc-marketplace` here would be a bug — it would evaluate whether the actor owns the *local checkout's* repo, not whether they own (or have rights on) the *PR's actual* repo, `acme-org/acme-repo`.

## Concrete Tier 1 execution

```bash
gh api user --jq '.login'
```

Compare the result (case-insensitive) against `acme-org` (not `andrehahm`). If they match, the result is `MERGE ALLOWED` and Tiers 2–3 are skipped. If they don't match (which is the likely real-world case here, since `acme-org` is presumably not this user's own account), proceed to Tier 2 (CODEOWNERS match) and, if needed, Tier 3 (collaborator permission via `gh api repos/acme-org/acme-repo/collaborators/{username}/permission`) — both of which also use `acme-org/acme-repo`, never the local checkout's repo.
