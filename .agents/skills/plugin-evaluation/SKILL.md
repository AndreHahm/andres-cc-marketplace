---
name: plugin-evaluation
description: >-
  Use when designing systematic evaluation methodology for Codex agents and
  commands — constructing weighted rubrics, choosing between direct scoring and
  pairwise comparison, building LLM-as-judge pipelines, or mitigating position,
  verbosity, and self-enhancement bias. NOT for empirical benchmarks with
  timing/token metrics (use skill-tester) or for iterating on skill content
  during development (use skill-development).
allowed-tools: Read Glob Grep
---

# Evaluation Methods for Codex Agents

Evaluation of agent systems requires outcome-focused approaches that account for non-determinism and multiple valid paths. Agents may reach goals through different routes — evaluation should judge whether they achieve right outcomes through reasonable processes, not match exact execution steps.

## Quick Start

1. **Identify what to evaluate** — a command's outputs, an agent's behavior, or a prompt variant
2. **Design test cases** — cover at least two complexity levels: simple (single tool call) and complex (multi-step reasoning)
3. **Choose method** — LLM-as-judge (scale + speed), human evaluation (catches edge cases), or end-state (artifact correctness)
4. **Apply rubric** — instruction following (0.30), completeness (0.25), tool efficiency (0.20), reasoning (0.15), coherence (0.10)
5. **Iterate** — compare before/after scores on the **same** test set; check no dimension regressed

## When to Use

- Testing whether a command or skill produces consistently good outputs
- Validating that context engineering changes improve (not regress) quality
- Scoring agent outputs systematically with LLM-as-judge
- Comparing prompt variants objectively before choosing one
- Detecting or mitigating position bias, verbosity bias, or self-enhancement bias

## When NOT to Use

- Debugging why a single command invocation failed — use `Codex --debug` and troubleshooting instead
- For one-off gut-check tests — evaluation is for systematic, repeatable quality measurement
- For evaluating plugin structure or manifest correctness — use `plugin-development` or `plugin-validator` instead

---

## Core Concepts

Agent evaluation captures multiple quality dimensions: factual accuracy, completeness, citation accuracy, source quality, and tool efficiency. LLM-as-judge provides scalable evaluation while human evaluation catches edge cases.

**Performance Drivers: The 95% Finding**

Research on the BrowseComp evaluation found three factors explain 95% of performance variance:

| Factor | Variance Explained | Implication |
|--------|-------------------|-------------|
| Token usage | 80% | More tokens = better performance |
| Number of tool calls | ~10% | More exploration helps |
| Model choice | ~5% | Better models multiply efficiency |

Evaluate with realistic token constraints. Model upgrades beat token increases. Multi-agent architectures distribute work across separate context windows.

## Evaluation Challenges

**Non-Determinism and Multiple Valid Paths**

Agents may take completely different valid paths to the same goal. Traditional step-by-step evaluation fails.

**Solution**: Evaluate outcomes, not execution paths. Judge whether the agent achieves the right result through a reasonable process.

**Context-Dependent Failures**

Failures often emerge after extended interaction or at specific complexity levels.

**Solution**: Cover a range of complexity levels. Test extended interactions, not just isolated queries.

**Composite Quality Dimensions**

An agent might score high on accuracy but low in efficiency, or vice versa.

**Solution**: Multi-dimensional rubrics with appropriate weighting per use case.

## Evaluation Rubric Design

Default weights: instruction following (0.30), completeness (0.25), tool efficiency (0.20), reasoning (0.15), coherence (0.10). Convert assessments to 0.0–1.0 with weighting. Typical passing thresholds: 0.7 for general use, 0.85 for critical operations.

For per-criterion score bands and rubric generation patterns, see [`references/llm-judge-patterns.md`](references/llm-judge-patterns.md) (Pattern 1, Step 1).

## Evaluation Methodologies

### LLM-as-Judge

Scales to large test sets and provides consistent judgments. Design evaluation prompts that capture the dimensions of interest.

For the full evaluation prompt template, see [`references/llm-judge-patterns.md`](references/llm-judge-patterns.md) (Pattern 1, Step 3).

**Chain-of-Thought Requirement**: Always require justification before the score — improves reliability by 15-25%.

### Human Evaluation

Human evaluation catches what automation misses: hallucinated answers on unusual queries, subtle context misunderstandings, edge cases, qualitative issues with tone or approach. Sample systematically across complexity levels.

### End-State Evaluation

For commands that produce artifacts, evaluate the final output rather than the process: does the code work? Is the configuration valid? Does the output meet requirements?

## Test Set Design

**Sample Selection**: Start small during development — early changes have large impact. Sample from real usage patterns. Add known edge cases. Ensure coverage across complexity levels.

**Complexity Stratification**: simple (single tool call), medium (multiple tool calls), complex (many tool calls, ambiguity), very complex (extended interaction, deep reasoning).

## Context Engineering Evaluation

**Testing Prompt Variations**: Run current prompt as baseline, then modified prompt on same cases. Measure quality scores, token usage, efficiency. Identify which changes improved which dimensions.

**Degradation Testing**: Run agents at different context sizes. Identify performance cliffs. Establish safe operating limits.

## Evaluation Pitfalls

**Scoring without justification** → Require evidence-based justification before every score.

**Single-pass pairwise comparison** → Position bias corrupts results. Always swap positions and check consistency.

**Overloaded criteria** → One criterion = one measurable aspect.

**Missing edge case guidance** → Include edge cases in rubrics explicitly.

**Ignoring confidence calibration** → Calibrate confidence to position consistency and evidence strength.

## Decision Framework: Direct vs. Pairwise

```
Is there an objective ground truth?
├── Yes → Direct Scoring
│   └── Examples: factual accuracy, instruction following, format compliance
└── No → Is it a preference or quality judgment?
    ├── Yes → Pairwise Comparison
    │   └── Examples: tone, style, persuasiveness, creativity
    └── No → Reference-based evaluation
        └── Examples: summarization, translation
```

For pairwise: always run two passes with swapped positions. If passes disagree → TIE (position bias detected).

## Guidelines

1. Always require justification before scores — chain-of-thought improves reliability by 15-25%
2. Always swap positions in pairwise comparison — single-pass is corrupted by position bias
3. Match scale granularity to rubric specificity — don't use 1-10 without detailed levels
4. Separate objective and subjective criteria — direct scoring for objective, pairwise for subjective
5. Include confidence scores — calibrate to position consistency and evidence strength
6. Define edge cases explicitly — ambiguous situations cause the most evaluation variance
7. Use domain-specific rubrics — generic rubrics produce generic (less useful) evaluations
8. Validate against human judgments — automated evaluation is only valuable if it correlates
9. Monitor for systematic bias — track disagreement patterns by criterion and response type
10. Design for iteration — evaluation systems improve with feedback loops

## Example: Evaluating a Codex Command

**Test Cases** for a `/refactor` command:
1. Simple: Rename a variable across a single file
2. Medium: Extract a function from existing code
3. Complex: Refactor a class to use a new design pattern
4. Very Complex: Restructure module dependencies

**Evaluation Rubric**: Correctness (does it work?), Completeness (all instances updated?), Style (follows conventions?), Efficiency (unnecessary changes avoided?).

**Iteration**: If evaluation reveals the command often misses instances, add the instruction: "Search the entire codebase for all occurrences." Re-evaluate on same test cases. Compare completeness scores. Check correctness didn't regress.

## Iterative Improvement Workflow

1. **Identify weakness**: Use evaluation to find where agent struggles
2. **Hypothesize cause**: Is it the prompt? The context? The examples?
3. **Modify prompt**: Make targeted changes based on hypothesis
4. **Re-evaluate**: Run same test cases with modified prompt
5. **Compare**: Did the change improve the target dimension?
6. **Check regression**: Did other dimensions suffer?
7. **Iterate**: Repeat until quality meets threshold

---

## Testing & Validation

After designing or running an evaluation:

1. **Justification present** — every score has evidence-based justification written before it (not after)
2. **Pairwise consistency** — if using pairwise: ran both position orders and checked for agreement
3. **Rubric coverage** — all 5 criteria rated on every test case
4. **Complexity coverage** — test cases span at least simple and complex levels
5. **Baseline comparison** — before/after improvement uses the same test set (not a new one)

**Quality gates:**
- [ ] Chain-of-thought justification required before every score
- [ ] Pairwise comparisons run with swapped positions; disagreement → TIE
- [ ] Rubric weights sum to 1.0 (0.30 + 0.25 + 0.20 + 0.15 + 0.10)
- [ ] Test cases cover at least two complexity levels
- [ ] Improvement measurement compares against the same baseline test set
- [ ] At least one dimension validated against human judgment

---

## Reference Guide

| Resource | Purpose |
|---|---|
| `references/bias-mitigation.md` | Position bias, length bias, self-enhancement, verbosity, authority bias — detection and mitigation |
| `references/llm-judge-patterns.md` | Structured workflow, hierarchical, PoLL, confidence calibration, detailed prompt templates, meta-evaluation |
| `references/metric-selection.md` | Classification metrics (precision/recall/F1), agreement (Cohen's κ), correlation (Spearman's ρ), decision tree |
