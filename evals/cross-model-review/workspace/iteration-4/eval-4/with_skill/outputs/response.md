# Answer: "Review this before I mark the draft ready" → `cross-model-review`, not `collaborating-on-a-pr`

## Short answer

This request should be handled by **`cross-model-review` itself**. The skill's own text explicitly
anticipates and resolves this exact scenario — a draft PR already existing on the branch does **not**
push the request into `collaborating-on-a-pr`'s territory, because `collaborating-on-a-pr`'s exclusion
is scoped to *GitHub-side review actions*, not to the mere fact that a PR (draft or otherwise) already
exists.

## Why: the skill draws the line on *what kind of review happens*, not on *whether a PR exists*

### 1. "When to Use" names this exact moment

The **When to Use** section (lines 34–39) states:

> "Before a PR is created (draft or ready-to-merge), **or before a draft PR is flipped to ready** — when
> an independent, cross-vendor pass on the current diff is wanted before it becomes visible on GitHub."

"Review this before I mark the draft ready" is a verbatim match for this clause — flipping a draft to
ready is named explicitly as one of the two trigger moments for this skill, on equal footing with
pre-PR-creation review.

This is reinforced in the **Testing & Validation** section's activation list (lines 369–372), which
lists as a required-to-activate example:

> "review this before I flip the draft PR to ready"

So the skill's own test battery treats this phrasing as a positive activation case for itself, not a
case that should be redirected elsewhere.

### 2. "When NOT to Use" excludes GitHub-side actions, not "a PR being open"

The first bullet of **When NOT to Use** (lines 43–48) is the one that could naively seem to apply, since
a draft PR is technically "already open" on GitHub. But its own wording narrows the exclusion precisely
to avoid that naive reading:

> "**Posting an actual GitHub review** (comments, approve, request changes) on an existing PR, **or
> reviewing a PR's already-pushed remote state** — that's `collaborating-on-a-pr`, which has
> GitHub/CODEOWNERS context this skill doesn't touch. This skill never calls `gh`; it only reviews the
> local working diff. **A draft PR already existing for this branch does not exclude this skill** —
> reviewing the local diff before flipping that draft to ready is this skill's own documented purpose
> (see "When to Use"), distinct from posting to or reading the PR's state on GitHub."

This sentence is doing exactly the disambiguation the question asks about: it names the surface fact
("a draft PR already exists") and explicitly states that fact alone is *not* the exclusion trigger. The
actual exclusion criterion is the **action type** — posting a review to GitHub, or reading/reviewing the
PR's already-pushed remote state — not the **existence** of an open PR object.

### 3. The distinguishing criterion, stated plainly

Putting the two sections together, the skill's own resolution rule is:

- **`cross-model-review`** = reviewing the **local working diff** (never calls `gh`, never touches
  GitHub state) — appropriate whether that diff sits behind no PR yet, a draft PR, or a ready PR, as
  long as the *action* is "get a cross-vendor pass on the diff," not "act on GitHub."
- **`collaborating-on-a-pr`** = reviewing/acting on the **PR's already-pushed remote state on GitHub**
  (posting comments, approving, requesting changes) — has GitHub/CODEOWNERS context this skill
  deliberately doesn't have.

"Review this before I mark the draft ready" asks for a pre-flip quality pass on the diff itself, with no
mention of posting anything to GitHub or evaluating what's already pushed — so it falls on the
`cross-model-review` side of that line.

### 4. This exact resolution is also codified as a quality gate

The skill's final **Quality gates** checklist (lines 433–435) restates this as an explicit, checkable
rule of the skill's own correct behavior:

> "Reviewing the local diff before flipping an existing draft PR to ready is never routed to
> `collaborating-on-a-pr` — the "already-open PR" exclusion applies only to posting a GitHub review or
> reading the PR's remote state, not to this skill's own documented local-diff purpose"

This is the clearest single statement in the file: it names the "already-open PR" reading the question
raises, and says explicitly that this reading does not trigger the exclusion.

### 5. Consistent with the frontmatter description

The YAML frontmatter `description` (lines 4–13) mirrors the same boundary at the very top of the file:

> "Use for an adversarial review, a cross-model or second-opinion review, a pre-PR gate, or high-confidence
> findings before opening or readying a PR. Not `collaborating-on-a-pr`'s reviewer actions, nor
> `codex-review-recovery`'s stuck-check recovery (both act on an already-open PR) — this skill never
> posts to or touches GitHub state."

Note the phrasing "before ... readying a PR" (i.e., flipping draft → ready) is listed as an in-scope
trigger for this skill in the same sentence that draws the exclusion against the two other skills — and
the exclusion criterion given is again "act on an already-open PR" / "posts to or touches GitHub state,"
matching the When NOT to Use section's criterion exactly.

## Conclusion

Handle the request with `cross-model-review`. The skill anticipates the "but a draft PR is technically
already open" objection directly and rejects it by name in three places — When to Use (line 36, "before
a draft PR is flipped to ready"), the When NOT to Use bullet's own explicit carve-out (lines 46–48), and
the closing Quality gates checklist (lines 433–435) — all converging on the same rule: the "already-open
PR" exclusion is about the *review action's target* (GitHub's posted/remote PR state) versus the
*local working diff*, not about whether a PR object of any kind (draft included) currently exists for
the branch. Routing this request to `collaborating-on-a-pr` would contradict the skill's own explicit,
repeated instruction.
