## Summary
Redesign the `codex-review` job's trust-boundary gate so a legitimate `scripts/`/`pyproject.toml`/`uv.lock` fix doesn't require a manual bypass attestation on every single PR that touches those paths

## Environment
- **Product/Service**: Claude Code plugin marketplace (`andres-cc-marketplace`), `.github/workflows/marketplace-ci.yml` — the `codex-review` job's "Refuse automated Codex dispatch when this PR modifies its own review-dispatch code (trust boundary)" step (currently around line 645)
- **Region/Version**: n/a (CI workflow)

## Reproduction Steps
1. Open a same-repo PR that changes any file under `scripts/`, or `pyproject.toml`/`uv.lock`.
2. Observe `Codex delta review` unconditionally fails with: *"This PR changes scripts/, pyproject.toml, or uv.lock -- the same code this job dispatches reviewers with and hands to them as evidence on disk... This requires a maintainer to manually review the change and attest a bypass."*
3. The only way to unblock merge is the documented SHA-bound bypass-attestation protocol (comment + `s: codex review bypassed` label, re-attested on every new commit).

## Expected Behavior
A genuinely reviewed, tested, low-risk fix to `scripts/marketplace_ci/` shouldn't need a fresh manual bypass attestation cycle every time it's pushed — there should be a way to get real (not bypassed) automated review coverage for this class of change, or at least reduce the friction of the current all-or-nothing refusal.

## Actual Behavior
The refusal is unconditional and by design — confirmed three ways this session: the job's own error text, `docs/ci.md`'s "Automatic reviewer-scope bypass" section (which explicitly lists `scripts/`/`pyproject.toml`/`uv.lock` as **never** bypass-eligible, "even mixed with otherwise-eligible files"), and the workflow file's own explanatory comment, which states an earlier version of this job *tried* restoring `scripts/`/`pyproject.toml`/`uv.lock` from the trusted base SHA before dispatching (the "obvious" alternative) and **reverted it**, because the dispatched Codex reviewer reads target-path files directly off disk as evidence — restoring from base would silently hide the PR's real changes to those paths from the reviewer rather than reviewing them.

So today there are exactly two states for a PR touching these paths: (a) no review at all (refused, silently unreviewed content, until a maintainer manually attests), or (b) a maintainer manually reviews it themselves and attests a bypass. There's no third option that gets a real automated pass on this class of change.

## Impact
**Medium** — not a security bug (the current behavior is the *safe* default), but a real, recurring maintainer-friction cost: every future fix to `scripts/marketplace_ci/` (a shared, frequently-touched tool) requires this same manual cycle, with no automated safety net beyond the human doing it. Encountered directly this session (PR #349's `sync.py` executable-bit-preservation fix).

## Additional Context
This is a decision-tracking issue — the next step is figuring out whether a redesign is possible/worthwhile, not implementing one now. Some directions to weigh (none prescriptive, and the workflow's own comment already found reason to reject the most obvious one):
1. **Already-rejected**: restore `scripts/`/`pyproject.toml`/`uv.lock` from the base SHA before dispatch — rejected because the reviewer reads target-path files off disk as evidence, so this would hide the PR's real diff from it.
2. Dispatch a *second*, independent reviewer pass that only ever reviews a diff/patch representation of the changed `scripts/` files (never the full checkout), so there's nothing on disk for a tampered dispatch script to lie about — would need a fresh security review of its own before shipping (per `.claude/rules/require-security-review-before-new-gate.md`), since it's itself a new trust-boundary mechanism.
3. Split `scripts/marketplace_ci/` into a narrower, more-trusted "review-dispatch-critical" subset (the actual code that decides/reports review outcomes) vs. a broader "other tooling" set that could get real automated review without the self-evaluation risk — would need care given the workflow's own comment already noted a too-narrow path list let one file "bypass its own review by sitting just outside the guarded path" once before.
4. Accept the current design permanently and instead invest in reducing the *manual* attestation's friction (e.g. a documented one-command helper, or expanding `create-pr --bypass-codex-review`/`merge-pr` to make the cycle less error-prone) rather than trying to get real automated coverage at all.
5. Do nothing — the current cost (a maintainer's own manual review) may already be the right tradeoff for code this security-sensitive.
