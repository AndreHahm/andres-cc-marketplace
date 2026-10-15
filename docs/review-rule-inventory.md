# Review rule inventory

Deliverable 1 of #568 Phase 2 (issue #576). It classifies every `plugin-rulebook` rule, the checks the
other review agents run, and every rule id in `scripts/marketplace_ci/review_exceptions.yaml`, by how a
script could decide it. It tells the verifier PRs which rules to implement, and in which family. It is not
a gate: nothing reads it at review time, and `tests/marketplace_ci/test_review_rule_inventory.py` keeps it
equal to the rulebook settings, the review contract and the registry.

## Classes

The class is the `rule_class` the finding envelope carries (`review_contract.RULE_CLASSES`). The gate only
treats `measurement` specially: a model's own `measurement` finding is a notice, a script's blocks like any
other. These definitions are this inventory's working ones, based on how a script would decide the rule:

| Class | A script decides it from |
| --- | --- |
| `line` | the text of one changed line or one frontmatter field, by pattern |
| `measurement` | a number (lines, characters, count) compared with a threshold, before and after the change |
| `graph` | a relation between files, or between a file's frontmatter and its body |
| `judgment` | meaning; a script can at most list candidates |

## Statuses and families

| Status | Meaning |
| --- | --- |
| `phase-2` | a verifier in this issue's scope; the `family` column names which |
| `candidate` | a script can decide it, but it is outside this issue's scope; the owner decides (see Open questions) |
| `existing` | a script or CI job already enforces it; no new verifier, at most finding emission |
| `model` | needs judgment; stays with the model reviewers |
| `disabled` | the rule is switched off in `plugin-rulebook`'s `settings.json` |

Families: `grant-to-body`, `measurement`, `path-and-mirror`, `removed-identifier` (the four in the concept),
plus `structure` and `call-graph`, added to the issue on 2026-10-15 by the owner from the candidates below.

## Rule ids

A rule id is the stable string a verifier puts in `Finding.rule`: lowercase kebab-case, never reused for a
different check. The registry matches `rule` exactly, so each registry `rule` below is a verifier rule id,
not a free label: a script finding with that id and a matching path is the one the entry suppresses. A
rulebook rule that has several independent checks gets one id per check.

## Inventory

| Rule id | Origin | Class | Script check | Existing check | Status | Family |
| --- | --- | --- | --- | --- | --- | --- |
| `r1-non-english-text` | R1 | judgment | a non-ASCII scan lists candidates only; language needs reading | `language-reviewer` | model | - |
| `r2-reference-english-primary` | R2 | graph | a `references/<topic>.<lang>.md` with no `references/<topic>.md` | none | candidate | - |
| `r3-reference-variant-parity` | R3 | judgment | a variant covers the same content as its English primary | none | model | - |
| `r4-kebab-case-name` | R4 | line | `name`, directory and reference names match the pattern, length and forbidden words from settings | none | candidate | - |
| `r5-forbidden-frontmatter-field` | R5 | line | `version` in skill or agent frontmatter; the no-op agent fields as advisory | none | candidate | - |
| `r5-r6-ask-user-question-grant` | R5, R6 | graph | `AskUserQuestion` listed in `allowed-tools` is redundant, never a violation or a missing grant | registry entry | phase-2 | grant-to-body |
| `r6-bash-scope` | R6 | line | bare `Bash`, `Bash(*)` or a shell-interpreter grant; for an agent, the reverse (a scoped `Bash(cmd:*)`) | none | phase-2 | grant-to-body |
| `frontmatter-unverifiable` | R6 | line | a changed component file whose frontmatter cannot be read exactly (bad or repeated frontmatter key, merge key, symlink, oversized) | none | phase-2 | grant-to-body |
| `r6-missing-grant` | R6 | graph | a tool or Bash command the body instructs has no matching `allowed-tools` grant | `check_tool_grants.py` (documented false-positive classes) | candidate | - |
| `prompt-library-undeclared-grant` | R6 | graph | `Read`, `Write` and `WebFetch` are deliberately ungranted in the prompt-library skill | registry entry | phase-2 | grant-to-body |
| `r7-emoji-in-structure` | R7 | line | emoji in a heading, frontmatter field or step label | none | candidate | - |
| `r8-description-block-scalar` | R8 | line | a description over 80 characters not written as a `>-` block; a command description of 61 to 80 characters as advisory | none | candidate | - |
| `r9-hardcoded-credential` | R9 | line | secret patterns; a real OS username in a committed fixture path | gitleaks (pre-commit), secretlint (`commit-branch-guard.yml`) | existing | - |
| `r10-reference-file-name` | R10 | line | topic over the length limit or a generic name from settings | none | candidate | - |
| `r11-max-heading-depth` | R11 | line | a heading deeper than `###` | none | disabled | - |
| `r12-code-block-language` | R12 | line | a fenced block without a language | none | disabled | - |
| `r13-skillmd-line-count` | R13 | measurement | SKILL.md lines against the tiers, on the base and on the merge ref | none | phase-2 | measurement |
| `r14-references-nested-directory` | R14 | graph | a subdirectory inside `references/` | none | candidate | - |
| `r14-reference-chain` | R14 | judgment | a reference that needs a second one to be usable | none | model | - |
| `r15-human-documentation-file` | R15 | line | a README, CHANGELOG or INSTALLATION file inside a skill directory | none | disabled | - |
| `r16-progressive-disclosure-order` | R16 | line | `Quick Start` after a workflow section | none | disabled | - |
| `r17-bare-url` | R17 | line | a URL outside a code block that is not a `[text](url)` link | none | candidate | - |
| `r18-code-block-line-count` | R18 | measurement | fenced block lines against the tiers, with a real fence parser (character and length tracked, nested fences) | none | phase-2 | measurement |
| `r19-mirror-drift` | R19 | graph | a `.claude/` copy differs from its `plugins/` source, except a declared divergence | `mirror-parity-check.sh`; CI job `marketplace-parity` | phase-2 | path-and-mirror |
| `mirror-byte-identity` | R19 | graph | a `.claude/` file that is a byte-identical copy of its source is reviewed once, as the canonical file; which finding carries this id is open | registry entry; `collapse_identical_mirrors` in `review.py` | phase-2 | path-and-mirror |
| `r20-stale-sibling-value` | R20 | graph | a canonical value changed in `settings.json` is still stated elsewhere in the tree | `r20-sweep.sh` (rule-count ceiling only) | candidate | - |
| `removed-identifier-leftover` | R20; sibling-sweep rule | graph | an identifier the diff removes or renames is still referenced elsewhere | none | phase-2 | removed-identifier |
| `r21-description-length` | R21 | measurement | `description`, `when_to_use` and combined length against the tiers, from the parsed frontmatter | none | phase-2 | measurement |
| `r21-description-split-hint` | R21 | measurement | a description over 900 characters with a Use-when clause and no `when_to_use` | none | candidate | - |
| `r22-argument-consistency` | R22 | graph | `argument-hint` and `arguments` against the placeholders the body consumes | none | candidate | - |
| `r23-external-reference` | R23 | graph | a reference classified against the whitelist and blacklist, or one that resolves to nothing | `external-references-reviewer` (model) | candidate | - |
| `r24-disallowed-language` | R24 | line | a script extension or a fence tag outside Python, Bash and JavaScript or TypeScript | none | candidate | - |
| `r25-unplanned-overhead-disclosure` | R25 | judgment | whether a documented quick phase discloses its overrun | none | model | - |
| `r26-expensive-action-opt-in` | R26 | judgment | whether an expensive action is gated by an explicit question | none | model | - |
| `r27-component-name-form` | R27 | judgment | the grammatical form of a component name | none | model | - |
| `r28-skill-testing-mandate` | R28 | graph | `evals.json` with the minimum scenarios, or a justification in the testing section | none | candidate | - |
| `r29-testing-section` | R29 | judgment | a `Testing & Validation` heading with positive, negative and pass-criteria subsections, matched by substance; a script cannot read the substance | none | model | - |
| `r30-eval-sample-inline` | R30 | judgment | a worked eval walkthrough left inline | none | model | - |
| `r31-eval-fixture-integrity` | R31 | measurement | zero-match guard, anchored matching and coverage arithmetic in `evals.json` and smoke tests | `check_evals.py` (the iteration-registry check is not in the script) | existing | - |
| `r32-data-only-boundary` | R32 | judgment | whether a skill that reads another component's output carries the boundary statement | none | model | - |
| `r33-component-file-prefix` | R33 | line | a file basename without the plugin's registered prefix | `prefix_check.py`, wired into `check-all` | existing | - |
| `r34-dead-reference` | R34 | judgment | a link that resolves to nothing and is not an illustrative example; a script found 11 on the real tree and 10 were examples, so only a human or model can tell | none | model | - |
| `r34-escaping-path` | R34 | graph | a path that leaves the skill folder into a folder the `.claude/` mirror does not carry | none | phase-2 | path-and-mirror |
| `r35-standard-sections` | R35 | judgment | the standard sections, matched by substance rather than wording; a literal-heading scan found 47 of 150 real skills without a `Quick Start` heading, so it would block on wording | none | model | - |
| `r36-reciprocal-exclusion` | R36 | judgment | whether an exclusion pointer is named back where the domains overlap | none | model | - |
| `r37-executable-bit` | R37 | graph | a directly-invoked script whose git mode in `git ls-files -s` is not `100755` | none | phase-2 | structure |
| `skill-agent-dependency-cycle` | dependency-reviewer | graph | a cycle or an unresolved target in the `Skill()` and `Agent()` call graph | none | phase-2 | call-graph |
| `plugin-manifest-wiring` | plugin-validator | graph | manifest paths and component wiring resolve; scope to confirm when picked up | none | candidate | - |
| `script-code-smell` | scripts-reviewer | line | pattern-detectable defects such as `open()` without an encoding | `python-quality` job (ruff, ty) for Python only | candidate | - |

Not rows: `security-reviewer`, `skill-reviewer`, `subagent-reviewer`, `rule-reviewer`, `hook-reviewer`,
`consistency-reviewer` and the rest of the `ROSTER` read meaning, so their findings stay `judgment`.

## Evidence for the phase-2 rows

Findings named in #568 as unstable or out of scope for the changed lines:

- A relative path to a plugin-root file used by many skills was reported as blocking: `r34-escaping-path`.
- A description phrased with "Use when" was reported as blocking: `r21-description-split-hint` is an
  advisory by definition (`minor`).
- An unscoped `git ls-files` grant was reported as blocking: `r6-bash-scope` and `r6-missing-grant`.
- R13 and R18 thresholds were reported at the weak-warning tier as noise on every run:
  `r13-skillmd-line-count` and `r18-code-block-line-count` map the tiers to the contract severity
  (Critical to `critical`, Warning to `major`, Soft and Weak Warning to `minor`) and compare against the base.
- One finding asked for the opposite of `resolve-plugin-root-to-claude-mirror.md`: `mirror-byte-identity`.

## Open questions

These need an owner decision before the matching verifier PR, and are not settled by this inventory:

1. **Candidates (decided 2026-10-15).** 17 rows are `candidate` and stay for a follow-up. The owner added
   `r37-executable-bit` and `skill-agent-dependency-cycle` to this issue, and both are built. `r29-testing-section`
   and `r35-standard-sections` are not scripts: the rulebook matches their headings "by substance", and a literal
   scan found 47 of 150 real skills without a `Quick Start` heading, so a script would block on wording.
2. **Rows no script emits (decided 2026-10-15).** `r6-missing-grant` (a tool the body uses must be in
   `allowed-tools`) is not built and is a `candidate`: `check_tool_grants.py` documents six false-positive
   classes, so a script would block legitimate PRs. `mirror-byte-identity`, `r5-r6-ask-user-question-grant`
   and `prompt-library-undeclared-grant` stay `phase-2` because the registry holds entries under those ids, but
   no script finding carries them: they brief the model reviewers, and a finding with that id would be what an
   entry suppresses. `r20-stale-sibling-value` and `r21-description-split-hint` are candidates (the latter is
   an advisory by definition).
3. **R18 recorded exception (decided).** The verifier does not honor the in-file note, because a PR could
   type one and waive its own finding; a waiver is a registry entry, which is Tier-1 and needs a maintainer
   attestation per exception.
4. **Frontmatter parsing.** `r21-description-length` needs the folded value of a `>-` scalar, so it parses
   YAML (`pyyaml` is already locked) rather than counting raw lines. The verifier modules are Tier-1 and must
   not import other Tier-2 code.
