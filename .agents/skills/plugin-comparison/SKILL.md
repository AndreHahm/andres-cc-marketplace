---
name: plugin-comparison
description: >-
  Compares a plugin or plugin component in the current repo against another
  plugin or component — internal to this repo, a locally installed external
  plugin (active or inactive), a locally saved external plugin folder, or a
  public GitHub-hosted plugin/skill/agent/hook/rule. Use when the user asks
  to 'compare this skill to X', 'diff our agent against the installed
  version', 'how does our plugin compare to <external>', or wants a
  side-by-side capability comparison report, written to
  `.Codex/output/plugin-comparison/`.
argument-hint: "[target-a] [target-b]"
allowed-tools: Read Glob Agent Write Bash(date:*)
---

# Plugin Comparison

Compares two plugins or plugin components — one of which is usually, but not necessarily, inside the current repo — and writes a side-by-side capability report.

## Quick Start

1. **Identify both targets** — target A and target B from `$0`/`$1` or the conversation
2. **(Internal-vs-internal only) Cheap low-value signal** — a quick `Read`-based staleness/size check surfaced as a note in the next step, never an auto-downgrade
3. **Ask detail level** — `AskUserQuestion` for Quick / Standard / Deep
4. **Inspect both** — invoke `plugin-inspector` (via `Agent`) once per target, in parallel
5. **Synthesize** — build a side-by-side comparison from the two portfolios
6. **Write the report** — `.Codex/output/plugin-comparison/comparison-<timestamp>.md`

## When to Use

- Comparing an internal skill/agent/command/hook/rule against an external counterpart before adopting patterns from it
- Checking whether a locally installed plugin duplicates or conflicts with something already in this repo
- Evaluating a public GitHub-hosted plugin/skill before installing or forking it
- Comparing two components within the current repo (e.g. two similar reviewer agents) for capability/functionality overlap or redundancy — not for checking whether their activation/trigger descriptions would ambiguously compete for the same request (use `activation-reviewer` for that)

## When NOT to Use

- Single-component quality review → use the matching `*-reviewer` agent (`skill-reviewer`, `hook-reviewer`, etc.)
- Whole-plugin structural/manifest validation → use `plugin-validator`
- Rulebook naming/formatting/tool-scoping compliance → use `plugin-rulebook`
- You only need a single target profiled, not a comparison → invoke the `plugin-inspector` agent directly instead of this skill
- Cross-component drift within one already-related family (e.g. skills that reference each other) → use `consistency-reviewer`, which is built for that instead
- Checking whether two components' activation descriptions risk ambiguous selection → use `activation-reviewer` instead
- Wanting the comparison's findings acted on end-to-end (human-gated fix, test, document, commit) rather than just the comparison report itself → use `plugin-lifecycle-maintenance`'s `enhance-a-plugin` workflow instead; this skill only produces the comparison, never applies anything from it

## Usage

```text
/plugin-comparison <target-a> <target-b>
```

Each target may be given as:
- A component name resolvable in the current repo (e.g. `skill-reviewer`, `rules-review`)
- An installed plugin name (e.g. `some-plugin` — checked against `~/.Codex/plugins/installed_plugins.json`)
- An absolute local path to a plugin folder or component file
- A GitHub reference: `owner/repo`, `owner/repo@ref`, or `owner/repo@ref/path/to/component`

If either target is omitted or ambiguous, use `AskUserQuestion` to ask the user directly before proceeding — do not guess at a GitHub repo or install path.

## Processing Flow

### 1. Resolve Target A

Parse `$0` (or the conversation, if the command was invoked without arguments). If it names a component or plugin inside the current repo, resolve it with `Glob` to its canonical absolute path. If the name resolves to both a `plugins/plugin-devkit/` copy and a `.Codex/` mirror (the intentional staging-mirror pattern documented in `plugin-rulebook`'s R19 exception), use the `plugins/plugin-devkit/` copy as canonical and note the mirror exists — do not treat it as an error. If Target A isn't clearly identifiable, use `AskUserQuestion` — question: "Which component did you mean for Target A?", options: one per plausible candidate found (plus "Other" to type a path/reference).

### 2. Resolve Target B and Its Source Kind

Parse `$1`. Determine which of the four source kinds it is:

| Signal | Source kind |
|---|---|
| Resolves via `Glob` inside the current repo | Internal |
| Matches a name in `~/.Codex/plugins/installed_plugins.json` | Locally installed external plugin |
| Is an absolute/relative filesystem path that exists but isn't installed | Locally saved external plugin |
| Matches `owner/repo`, `owner/repo@ref`, or a `github.com/...` URL shape | Public GitHub-hosted |

If `$1` doesn't clearly match any of these (e.g. a bare name that isn't in the repo and isn't installed), use `AskUserQuestion` — question: "Which of these best describes Target B?", options: "Internal (repo component)" / "Locally installed plugin" / "Locally saved plugin folder" / "Public GitHub-hosted" — then get the exact path/reference before continuing; do not fabricate a GitHub owner/repo or a local path.

For **locally installed**: read `~/.Codex/plugins/installed_plugins.json` (via `Read`) to find the plugin's `installPath`, marketplace, and enabled/disabled state.

For **GitHub-hosted**: confirm the `owner/repo` shape and note the ref (default `main`/`master` if unspecified — state which one you assumed).

### 2.5. Optional Low-Value Signal (internal-vs-internal only)

When both targets resolved as Internal in Steps 1–2, cheaply estimate whether a full inspection is likely to be low-value *before* spending two `plugin-inspector` dispatches on it: `Read` both target files (needed anyway to know they exist) and note two signals — (a) does Target B's path sit under a gitignored draft directory (`.temp/`, `.draft/`, `.backup/`, or similar)? (b) is Target B's line count roughly half or less of Target A's? If both signals fire, treat this as advisory-only — surface it in Step 3's Quick option description (e.g. "Target B looks like a smaller/draft file relative to Target A — Quick may be sufficient") rather than silently downgrading the detail level or skipping the `AskUserQuestion` gate. The user still chooses; this only makes the cheaper option's rationale visible before they pick.

Skip this step entirely for installed/local-external/GitHub-hosted targets — the heuristic only applies when both files are already local and cheap to `Read` directly.

### 3. Ask Comparison Detail Level

Before inspecting anything, ask the user with `AskUserQuestion`:

- **Question:** "What level of detail should this comparison cover?"
- **Options:**
  - **Quick** — headline capabilities and triggers only; fastest, lowest cost. Best for a first-pass sanity check. (If Step 2.5's low-value signal fired, append its one-line note here.)
  - **Standard (Recommended)** — full side-by-side across functionalities, capabilities, boundaries, rules/conditions, features, scope/domain, and triggers.
  - **Deep** — Standard, plus tool/permission footprint, dependencies, and file:line (or fetched-URL) citations for every claim. Best before adopting patterns from an external source.

Carry the chosen level into both inspector invocations (Step 4) as their `detail level` parameter.

### 4. Inspect Both Targets

Invoke the `plugin-inspector` agent once per target, in a **single message with two parallel `Agent` tool calls** (they're independent). Each prompt must give the agent:

- The target's name/type
- Its source kind (internal / installed / local-external / github) and everything resolved in Steps 1–2 (absolute path, install path + active state, local folder path, or `owner/repo@ref/path`)
- The detail level chosen in Step 3

### 5. Synthesize the Comparison

Using the two returned portfolios (same fixed section order — see `plugin-inspector`'s report format), build:

1. A summary table: one row per portfolio section (Triggers, Scope & Domain, Functionalities & Capabilities, Boundaries, Rules, Conditions & Invocation Modes, Features, plus Tool/Permission Footprint and Dependencies at Deep level), columns for Target A / Target B / Delta.
2. A narrative **Overlap** section — capabilities both targets share.
3. A narrative **Unique to A** / **Unique to B** section.
4. A **Notable Differences** section — behavioral, structural, or scope differences that aren't simple presence/absence (e.g. both validate plugin manifests, but one blocks on errors and the other only warns).
5. A short **Recommendation** paragraph — only if the user's framing implies a decision (adopt/merge/replace/keep both); otherwise omit rather than inventing a verdict.

Do not silently drop a section because one portfolio's inspection was more limited (e.g. a GitHub target where only README.md was fetched) — carry the `Notes / Inspection Limits` content from each portfolio into the report so the reader knows which claims are less certain.

### 6. Write the Report

1. Get a timestamp: `date -u +%Y-%m-%dT%H-%M-%SZ`
2. Write to `.Codex/output/plugin-comparison/comparison-<timestamp>.md` (the directory name is fixed and the filename intentionally generic — not tied to the two target names — so repeated comparisons of different pairs don't require a naming scheme per pair)
3. Append one line to `.Codex/output/plugin-comparison/index.md` (create with a one-line header if it doesn't exist yet): `| <timestamp> | <target-a> | <target-b> | <detail-level> | comparison-<timestamp>.md |`. This exists because the report filename is deliberately generic (step 2) — without an index, finding which report covers which pair means opening every file. Read the file first if it exists, append the new row, then write back; never overwrite existing rows.
4. Confirm the written path to the user

### 7. Suggested Next Step

If the report's Unique to B, Notable Differences, or Recommendation sections contain anything actionable, ask with `AskUserQuestion`: "Run `enhancement-suggestor` against this comparison report for a classified (complexity/risk/benefit) WHAT/WHY/HOW action plan?" — options "Yes — run enhancement-suggestor" / "No — skip for now". If the user picks yes, invoke the `enhancement-suggestor` agent (via `Agent`) against the written report path. Never invoke it without asking first.

## Output Format

The written report follows the fixed structure in `references/comparison-report-template.md` — read it before writing the file so section names and order match exactly.

## Testing & Validation

1. **Both-internal comparison** — compare two components already in this repo; confirm both resolve via `Glob` without asking the user for paths
2. **Installed-plugin path** — compare an internal component against a name present in `~/.Codex/plugins/installed_plugins.json`; confirm the report states active/inactive state
3. **GitHub path** — compare against `owner/repo@ref/path`; confirm the report's Inspection Limits section states which files were actually fetched
4. **Ambiguous target** — omit target B entirely; confirm the skill asks the user rather than guessing
5. **Detail level respected** — choose Quick; confirm the written report omits Deep-only rows (Tool/Permission Footprint, Dependencies) rather than leaving them blank

**Quality gates:**
- [ ] `AskUserQuestion` is invoked for detail level on every run — never skipped or inferred
- [ ] The Step 2.5 low-value signal, when it fires, only annotates the Quick option's description — it never skips the `AskUserQuestion` gate or auto-selects a detail level
- [ ] Both `plugin-inspector` invocations are launched in parallel, not sequentially
- [ ] The Step 7 enhancement-suggestor offer uses `AskUserQuestion`, not a prose-only suggestion — and is never auto-invoked without asking
- [ ] The written report path is always under `.Codex/output/plugin-comparison/`
- [ ] Filename uses the UTC timestamp format, not target names
- [ ] `.Codex/output/plugin-comparison/index.md` gets a new row appended (never overwritten) for every report written — verified independent of the template's optional `## Recommendation` section (index row schema is timestamp/targets/detail-level/filename only; the two don't interact)
- [ ] A staging-mirror duplicate (`.Codex/` vs `plugins/plugin-devkit/`) for Target A is noted, not treated as an error

## Reference Guide

| Resource | Purpose |
|---|---|
| `plugin-inspector` agent | Produces the structured portfolio for one target; invoked twice per comparison |
| `enhancement-suggestor` agent | Turns the written comparison's actionable items into a classified next-step plan (Step 7) |
| `references/comparison-report-template.md` | Exact structure of the written comparison report |
| `~/.Codex/plugins/installed_plugins.json` | Resolves locally installed external plugin targets (name → installPath, marketplace, enabled state) |
| `plugin-rulebook` skill | R19 staging-mirror exception referenced in Step 1 |
