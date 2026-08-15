# plugin-rulebook Compliance Check -- scratch-test-skill

## Task

Created a scratch test skill at `scratch-test-skill/SKILL.md` with frontmatter
`name: Scratch_Test_Skill` (deliberately violating R4's kebab-case requirement -- contains an
underscore and capital letters), a minimal valid `description`, and a minimal body. Then applied
`plugin-rulebook`'s Compliance Check Procedure against it.

## Compliance Report

Rulebook Compliance: scratch-test-skill (skill)
Path: C:\Dev\Repos\andres-cc-marketplace\.claude\worktrees\plugin-auditor-codex-integration\evals\plugin-rulebook\workspace\iteration-1\eval-1\with_skill\outputs\scratch-test-skill\SKILL.md
  [R19: no duplicates found in project/plugin/user skill locations]
Settings: assets/settings.json [loaded], .claude/plugin-rulebook.config.json [loaded, R23 overrides]
Rules checked: 23 enabled / 27 total

PASS     R1  -- all frontmatter and body content is English
PASS     R2  -- no references/ directory present (N/A)
PASS     R3  -- no references/ directory present (N/A)
FAIL     R4  -- name: "Scratch_Test_Skill" violates kebab-case pattern
               ^[a-z][a-z0-9-]+[a-z0-9]$ (SKILL.md:2) -- contains underscores and
               uppercase letters [REQUIRED]
PASS     R5  -- only name and description present; both standard skill frontmatter fields
PASS     R6  -- no allowed-tools field and no tool invocations in the body (N/A)
PASS     R7  -- no emoji in headings, frontmatter, or step labels
PASS     R8  -- description is 138 chars (> 80) and correctly uses >- block scalar syntax
PASS     R9  -- no credentials, keys, or tokens present
PASS     R10 -- no references/ directory present (N/A)
PASS     R13 -- SKILL.md is 14 lines (<= 100, OK tier)
PASS     R14 -- no references/ directory present (N/A)
PASS     R17 -- no bare URLs in the body
PASS     R18 -- no fenced code blocks present (N/A)
PASS     R19 -- resolved path reported above; no duplicate/shadow copy found
PASS     R20 -- no canonical settings.json value was changed by this task (N/A)
PASS     R21 -- description length 138 chars falls in the 80-1018 OK band;
               no when_to_use frontmatter field present
PASS     R22 -- no argument-hint/arguments field and no $ARGUMENTS/$N/$name usage in body (N/A)
PASS     R23 -- no external company/org/plugin/repo references present (N/A)
PASS     R24 -- no script files or fenced code blocks present (N/A)
PASS     R25 -- not a pipeline/phase-documenting skill (N/A)
PASS     R26 -- no per-item nested LLM/subprocess/multi-agent dispatch documented (N/A)
PASS     R27 -- "Scratch Test Skill" reads as a noun phrase, matching the expected skill
               grammatical form [ADVISORY tier, no finding raised]

Status: FAIL -- 1 blocking violation (R4)
Scope: structure/naming/formatting/frontmatter only -- does not check script or code
correctness (encodings, shell logic, mojibake). Run scripts-reviewer separately for that.

## Rule flagged

R4 -- Naming: Kebab-Case Only [REQUIRED, default: on]

- Why it fires: R4's pattern is ^[a-z][a-z0-9-]+[a-z0-9]$ (lowercase kebab-case only, min 3
  chars). The frontmatter name: Scratch_Test_Skill (SKILL.md line 2) contains two categories of
  violation at once: uppercase letters (S, T, S) and underscores (_) used as word separators
  instead of hyphens. Both are explicitly listed as violation examples in R4's own spec
  (skillDev for camelCase, skill_dev for underscore, Skill-Dev for uppercase -- this name
  combines the underscore and uppercase patterns in one value).
- Severity: REQUIRED -- a blocking violation per the rulebook's severity vocabulary (maps to
  RFC 2119 MUST/MUST NOT). Must be fixed before the component could be finalized or shipped.
- Correct fix: Rename the frontmatter name field (and, per R4's scope, the directory name too,
  for consistency with the resolved component path) to scratch-test-skill -- all lowercase,
  hyphen-separated, matching ^[a-z][a-z0-9-]+[a-z0-9]$. No other rule interacts with this fix:
  R19's path-resolution check would need re-running against a renamed directory if the directory
  itself were also renamed, and R27 (grammatical form) is unaffected since kebab-casing doesn't
  change the noun-phrase shape already established.

## Rules checked but not flagged

All 22 other enabled rules (R1, R2, R3, R5, R6, R7, R8, R9, R10, R13, R14, R17, R18, R19, R20,
R21, R22, R23, R24, R25, R26, R27) returned PASS -- most as genuine N/A (vacuously satisfied,
since this is a deliberately minimal single-file skill with no references/scripts/tools/
arguments/external references), with R8, R13, R19, and R21 as the only rules that had real
content to evaluate against a numeric threshold, all within their OK bands. R27 is worth calling
out specifically: it is enabled and ADVISORY-tier, and was actively evaluated (not skipped) -- it
simply found no mismatch, since "Scratch Test Skill" already reads as a noun phrase rather than a
bare imperative verb.

## Reasoning / method

- Read plugin-rulebook's SKILL.md in full (all 27 rule sections R1-R27) plus assets/settings.json
  (for exact enabled/disabled status, thresholds, and the R4 regex pattern) and
  references/size-rules.md (for R13/R18/R21's precise tiered thresholds rather than relying on
  the summarized tables in SKILL.md alone).
- Deliberately sized the test skill's description at 138 characters using >- block scalar syntax
  specifically so R8 and R21 would both PASS cleanly -- the task asked for a "minimal valid
  description," and R21's own threshold table shows anything under 80 chars would itself trigger
  a Warning/Critical finding, which would have muddied the single-violation (R4-only) signal this
  eval is meant to isolate.
- Confirmed no duplicate scratch-test-skill component exists elsewhere in the repo or under
  ~/.claude/skills/ (R19) before treating the check as authoritative.
- Left scratch-test-skill/ in place at the requested output path, undeleted, per the task
  instructions.
