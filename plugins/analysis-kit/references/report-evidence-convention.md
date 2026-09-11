# Report Evidence & Coverage Convention

Shared across every `analysis-kit` skill that persists a report — same cross-skill-reference shape as
`severity-vocabulary.md` and `report-discovery-convention.md`. This file exists so a reader (human or
`reviewing-analysis-findings`) can tell, for any single finding or any whole report, exactly how much of
the requested scope was actually inspected and how much weight a finding's own evidence can bear —
without each skill having to invent its own wording for "how sure am I" and "how much did I actually
read."

This does **not** replace any skill's own finding format (a SWOT quadrant row, a candidate-pattern entry,
a comparison delta) — it adds two small, consistently-shaped pieces on top: one preamble per report, one
metadata block per substantive finding.

## The Coverage Preamble

Every persisted report opens with this block, immediately after the title/header, before the first
analysis section:

```markdown
**Requested scope:** <what the user/caller asked to be covered>
**Inspected scope:** <what was actually read/analyzed — may be narrower than requested>
**Unavailable evidence:** <specific sources that couldn't be reached — "none" if nothing was missing>
**Limitations:** <sampling, partial-read, or inherited-coverage caveats that affect how much this report's findings can be trusted — "none beyond the above" if nothing further applies>
```

**The point of this block is the gap between the first two lines.** A report whose filename implies a
wide date range but whose Inspected scope line says "only the current conversation was directly read"
must say so here, prominently — never silently absorbed into a narrower report that reads as if it
covered the full requested range. If Requested and Inspected scope are identical, say so plainly
("Inspected scope: same as requested — no narrowing") rather than omitting the line.

**Downstream reports preserve upstream limitations — never silently widen them.** A report that consumes
another report's findings (`generating-analysis-recommendations` expanding a finding,
`reviewing-analysis-findings` cross-checking two reports, `running-a-full-retrospective` consolidating
several) inherits the *narrower* of its own coverage and each source report's own stated coverage. Citing
a finding from a report whose Inspected scope was "sampled" as if it were "complete" is exactly the
failure this rule prevents.

## The Finding Evidence Metadata Block

Every substantive finding (not every observation — see "What Counts as Substantive" below) is wrapped in
a `<!-- finding:start -->` / `<!-- finding:end -->` marker pair, with these four fields inside:

```markdown
<!-- finding:start -->
<the finding's own existing format — a SWOT row, a suggestion entry, a candidate-pattern block, etc.>

Evidence origin: direct | inherited | inferred
Coverage: complete | sampled | partial
Confidence: high | medium | low
Evidence source: <report path, session identifier, timestamp/event locator, or repository path>
<!-- finding:end -->
```

**Why explicit boundary markers, not just "somewhere near the finding":** a mechanical validator
(`validate_report.py`) needs an unambiguous span to check "does *this specific finding* carry its own
complete metadata block," not just "does the word 'Evidence origin:' appear somewhere in the document." A
per-document presence check can't tell one annotated finding from ten unannotated ones — the boundary
markers are what let the check be per-finding instead of per-document.

**Field is `Evidence source:`, not bare `Source:`.** `analyzing-plugin-components`' own pre-existing
suggestion format already uses `Source: <Strength | Weakness | ...>` for a completely different thing
(which SWOT quadrant a suggestion came from) — reusing the bare word `Source:` for evidence provenance
would collide with that field inside the same finding block. `Evidence source:` avoids the collision and
matches `Evidence origin:`'s own naming.

**Field meanings:**

- **Evidence origin** — `direct` (this skill itself read the underlying evidence: a transcript, a file, a
  `git` command's live output), `inherited` (carried forward from another report's own finding, not
  independently re-verified this run), or `inferred` (a reasonable conclusion drawn from partial or
  indirect evidence, not a direct observation — e.g. "the absence of a retry log suggests no retry
  occurred," which is weaker than actually having seen a retry-free execution trace).
- **Coverage** — how much of the *relevant* evidence for this specific finding was actually inspected,
  not the whole report's scope (that's the preamble's job): `complete` (all relevant evidence for this
  finding was inspected), `sampled` (a representative subset was inspected and generalized from),
  `partial` (some relevant evidence exists but wasn't reachable or wasn't inspected — state what's
  missing in the finding text itself, not just this field).
- **Confidence** — the finding author's own calibrated confidence that the finding is correct, given the
  evidence actually available: `high`, `medium`, `low`. This is independent of Coverage — a `partial`-coverage
  finding can still carry `high` confidence if the available fragment is unambiguous, and a
  `complete`-coverage finding can carry `low` confidence if the evidence itself is ambiguous.
- **Evidence source** — enough for a reader to independently re-check the finding: a report path
  (`.claude/output/<skill>/<scope-slug>-<timestamp>.md`), a session identifier, a `git` SHA/timestamp, or
  a repository file path. Never a bare absolute path that reveals the local OS username — cite the
  basename or repo-relative path instead, matching every report-producing skill's existing redaction
  discipline.

**Inherited findings identify the upstream report by path.** A finding whose `Evidence origin` is
`inherited` must name the specific source report in its `Evidence source` field — not just "an earlier
report," which gives a reader nothing to re-check.

**A full-coverage claim can never be paired with "only a subset was inspected" language in the same
finding.** If the finding text says evidence was sampled, `Coverage` must say `sampled` or `partial`, not
`complete` — this is a mechanical consistency check any report-producing skill's own self-review can run
before persisting.

**Evidence origin, Coverage, and Confidence must be exactly one of their listed values — no invented
terms, no blank value.** `validate_report.py` checks this mechanically (case-insensitively, on the first
word of the field's value, so trailing explanatory text after the value is fine). `Evidence source` has
no fixed vocabulary — any non-empty, re-checkable value is accepted.

**Every substantive finding needs its own block — no report-wide "one metadata block covers everything."**
A report with five findings needs five `<!-- finding:start -->`/`<!-- finding:end -->` pairs, each with
its own complete four-field metadata — not one block anywhere in the document. `validate_report.py`
enforces this mechanically per skill (see that script and `report-contracts.json`'s
`requires_evidence_metadata` flag).

## What Counts as "Substantive"

Apply the metadata block to a finding that makes a claim someone could act on or dispute — a SWOT
observation, a candidate pattern, a comparison delta, a compliance verdict, a recommendation. It does
**not** apply to the coverage preamble itself (that's a report-level fact, not a finding), to purely
structural output (an inventory table listing what was found, before any judgment is applied to it), or
to a skill's own process narration ("Phase 2 ran the inventory script").

**A report with zero substantive findings is a legitimate outcome — mark it explicitly, don't fabricate
one.** A clean run (nothing wrong found) shouldn't be forced to invent a placeholder finding just to
satisfy the per-finding metadata check. When a report genuinely has no substantive findings, add
`<!-- no-findings -->` anywhere in the report instead of any `<!-- finding:start -->` block —
`validate_report.py` treats this as satisfying the requirement on its own.

## Backward Compatibility

This convention governs reports written from this convention's adoption forward. An existing persisted
report written before this file existed is not retroactively invalid, and no skill needs to migrate or
re-annotate historical output — see `AKR-NFR-005` (backward compatibility) in
`.draft/_done/analysis-kit/new-dimensions/` for the source requirement. When a skill reads an older report
that lacks this metadata, treat the absence itself as `Coverage: partial` / `Confidence: low` for whatever
it inherits from that report, and say so, rather than assuming the missing fields would have said
`complete`/`high`.

## Per-Skill Application

Every report-producing skill's own notion of "scope" differs in shape — this table maps each skill's
actual scope concept onto the preamble's Requested/Inspected pair, so a skill doesn't have to invent its
own interpretation from scratch.

| Skill | Requested scope | Inspected scope |
|---|---|---|
| `analyzing-plugin-components`, `analyzing-tool-and-framework-use`, `analyzing-actor-behavior`, `analyzing-governance-and-conflicts`, `mining-recurring-patterns` | The date range or `this-conversation`/`today` argument resolved in Phase 1 | Which components/sessions/artifacts in that range were actually read (conversation context only reaches the current session; a wider date range depends on `session_parser.py`/`codex_session_parser.py` actually finding transcripts) |
| `comparing-sessions` | The two sessions/reports named for comparison | Which of the two was read in full vs. read only through a prior report's own findings |
| `comparing-session-to-specification` | The named specification document and session | Which specification sections were actually checked against session evidence — a large spec partially sampled must say so |
| `generating-analysis-recommendations` | The source report (or pasted findings) named as input | Same as requested in the common case — this skill expands existing findings rather than gathering new evidence, so Inspected scope narrows only when the source report itself was only partially read |
| `reviewing-analysis-findings` | The report set named or resolved for cross-check | The reports actually included vs. excluded (see `AKR-009`'s Included/Excluded Reports sections — this preamble and that section describe the same fact from two angles, keep them consistent) |
| `running-a-full-retrospective` | The shared scope confirmed once in Phase 1 | Which analysis types actually ran fresh, were reused from an existing report, or produced an explicit empty contribution — see this skill's own source-report table |
| `mining-review-learnings` | The PR set (explicit list, merge-date range, or "since last cited") | Which PRs' review history was actually fetched, and which had `session-transcript: unavailable` (GitHub history only, no matching transcript found) |
| `managing-review-learnings` | The input `mining-review-learnings` report or user-named finding | Which candidates were actually turned into a proposed diff vs. skipped (already covered, doesn't generalize, etc.) |
| `analyzing-session-outcomes` | The date range or `this-conversation`/`today` argument resolved in Phase 1, plus whether a spec/acceptance-criteria document was supplied | Which goals/criteria were actually evidenced at tier 1-2 vs. only reachable at a weaker tier (3-5) |
| `analyzing-verification-effectiveness` | The date range or `this-conversation`/`today` argument resolved in Phase 1 | Which claimed verifications had independently observable evidence vs. only a narrative claim |
| `analyzing-session-operations` | The date range or `this-conversation`/`today` argument resolved in Phase 1 | Which failure/span events were derivable from transcript content vs. left as unresolved/unknown |
| `analyzing-workflow-usability` | The date range or `this-conversation`/`today` argument resolved in Phase 1 | Which friction instances had enough evidence for a necessary/avoidable/unclear verdict vs. not_measurable |
| `analyzing-security-and-privacy` | The date range or `this-conversation`/`today` argument resolved in Phase 1 | Which threat-model fields were directly observable vs. inferred; sensitive values are never inspected in a way that would need disclosing here |

`starting-an-analysis` is not in this table — it dispatches to the skills above rather than persisting
its own report, so it has no coverage preamble of its own to write.
