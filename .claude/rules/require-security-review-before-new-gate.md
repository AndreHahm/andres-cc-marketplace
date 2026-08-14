# Require Security Review Before Shipping a New Gate

## What counts as a new security-relevant gate

Any new mechanism whose job is to permit, block, or bypass an action based on a check — an
authentication/authorization check, a permission gate, a bypass-attestation protocol, a
destructive-action guard, a trust-boundary enforcement point, or similar. This does not cover
every change to security-adjacent code — only the introduction of a *new* gate, or a
structural change to an *existing* gate's own pass/fail logic (not, e.g., a wording fix to a
gate's error message).

## When a review is required

Before the first commit that ships a new security-relevant gate (per the definition above),
dispatch the `security-reviewer` agent against the specific file(s) implementing the gate.
This applies whether the gate lives in this repo's own tooling (a hook, a CI script, a
plugin's own guard) or inside a plugin component shipped to others.

## Enforcement

There is no automated hook backing this rule — it is a policy gate, enforced by the author's
own judgment at commit time, the same enforcement model `plugin-rulebook-enforcement.md` uses
for rulebook compliance. Before finalizing a new gate, run `security-reviewer` (directly, or as
part of a broader `plugin-auditor`/`plugin-lifecycle-downstream` pass that already includes it)
and resolve any Critical or Major finding before the gate ships. Don't rely on a later,
unrelated audit pass to catch it — a gate that ships without this review and is never audited
again stays unreviewed indefinitely.

## Why

Two known instances of a security-relevant gate shipping without this review, both fixed only
reactively, in the same session that introduced them:

1. `marketplace-ci`'s SHA-bound bypass-attestation protocol (`docs/ci.md`) shipped with an
   unconditional "applying the label re-triggers the workflow" claim that didn't account for
   GitHub's label-already-present no-op — caught only when a later, unrelated retrospective
   pass happened to notice it, not by any review gate at the time it shipped.
2. `plugin-devkit`'s M9 security work (part of the M0–M12 pipeline redesign) — fixed reactively
   within the same build session, with no dedicated pre-ship security pass distinct from the
   build's own general review.

Neither individual fix was the problem — both were resolved correctly once found. The gap is
in *prevention*: nothing in this repo's existing workflow required a security-focused review
specifically at the point a new gate was introduced, so both gaps persisted from the gate's
first commit until an unrelated audit happened to surface them. This rule closes that gap by
naming the trigger point explicitly (a new gate's first commit) rather than relying on a
general-purpose review to catch it incidentally.
