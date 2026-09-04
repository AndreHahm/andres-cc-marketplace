# LLM-as-Judge Patterns

Complete implementation reference for LLM-as-a-Judge evaluation: taxonomy, implementation approaches, prompt templates, evaluation patterns, and examples.

**R18 exception (recorded):** several prompt templates and JSON examples below intentionally exceed the rulebook's 30-line code-block threshold — each is a complete, coherent, copy-paste-ready prompt or output schema; splitting one into multiple blocks would break the template it's illustrating.

## Evaluation Taxonomy

LLM-as-a-Judge is not a single technique but a family of approaches, each suited to different evaluation contexts.

**Direct Scoring**: A single LLM rates one response on a defined scale.
- Best for: Objective criteria (factual accuracy, instruction following, toxicity)
- Reliability: Moderate to high for well-defined criteria
- Failure mode: Score calibration drift, inconsistent scale interpretation

**Pairwise Comparison**: An LLM compares two responses and selects the better one.
- Best for: Subjective preferences (tone, style, persuasiveness)
- Reliability: Higher than direct scoring for preferences
- Failure mode: Position bias, length bias

Research from the MT-Bench paper (Zheng et al., 2023) establishes that pairwise comparison achieves higher agreement with human judges than direct scoring for preference-based evaluation.

### Bias Landscape

LLM judges exhibit systematic biases that must be actively mitigated:

**Position Bias**: First-position responses receive preferential treatment. → Evaluate twice with swapped positions.

**Length Bias**: Longer responses rated higher regardless of quality. → Explicit prompting to ignore length.

**Self-Enhancement Bias**: Models rate their own outputs higher. → Use different model families for generation and evaluation.

**Verbosity Bias**: Detailed explanations score higher even when unnecessary. → Criteria-specific rubrics that penalize irrelevant detail.

**Authority Bias**: Confident tone rated higher regardless of accuracy. → Require evidence citation.

### Metric Selection Framework

See `metric-selection.md`'s "Selection Decision Tree" for the canonical task-type-to-metric mapping (not restated here to avoid drift — its ordinal-scale case in particular splits into two sub-cases with different recommended metrics depending on whether you're comparing against human judgments or another automated judge).

Key insight: High absolute agreement matters less than systematic disagreement patterns.

---

## Direct Scoring Implementation

Direct scoring requires three components: clear criteria, a calibrated scale, and structured output format.

**Criteria Definition Pattern**:

```
Criterion: [Name]
Description: [What this criterion measures]
Weight: [Relative importance, 0-1]
```

**Scale Calibration**:
- 1-3 scales: Binary with neutral option, lowest cognitive load
- 1-5 scales: Standard Likert, good balance of granularity and reliability
- 1-10 scales: High granularity but harder to calibrate, use only with detailed rubrics

**Prompt Structure for Direct Scoring**:

```
You are an expert evaluator assessing response quality.

## Task
Evaluate the following response against each criterion.

## Original Prompt
{prompt}

## Response to Evaluate
{response}

## Criteria
{for each criterion: name, description, weight}

## Instructions
For each criterion:
1. Find specific evidence in the response
2. Score according to the rubric (1-{max} scale)
3. Justify your score with evidence
4. Suggest one specific improvement

## Output Format
Respond with structured JSON containing scores, justifications, and summary.
```

**Chain-of-Thought Requirement**: All scoring prompts must require justification before the score. Research shows this improves reliability by 15-25%.

---

## Pairwise Comparison Implementation

Pairwise comparison is inherently more reliable for preference-based evaluation but requires bias mitigation.

**Position Bias Mitigation Protocol**:

1. First pass: Response A in first position, Response B in second
2. Second pass: Response B in first position, Response A in second
3. Consistency check: If passes disagree, return TIE with reduced confidence
4. Final verdict: Consistent winner with averaged confidence

**Prompt Structure for Pairwise Comparison**:

```
You are an expert evaluator comparing two AI responses.

## Critical Instructions
- Do NOT prefer responses because they are longer
- Do NOT prefer responses based on position (first vs second)
- Focus ONLY on quality according to the specified criteria
- Ties are acceptable when responses are genuinely equivalent

## Original Prompt
{prompt}

## Response A
{response_a}

## Response B
{response_b}

## Comparison Criteria
{criteria list}

## Instructions
1. Analyze each response independently first
2. Compare them on each criterion
3. Determine overall winner with confidence level

## Output Format
JSON with per-criterion comparison, overall winner, confidence (0-1), and reasoning.
```

**Confidence Calibration**: Confidence scores should reflect position consistency:
- Both passes agree: confidence = average of individual confidences
- Passes disagree: confidence = 0.5, verdict = TIE

---

## Rubric Generation

Well-defined rubrics reduce evaluation variance by 40-60% compared to open-ended scoring.

### Rubric Components

1. **Level descriptions**: Clear boundaries for each score level
2. **Characteristics**: Observable features that define each level
3. **Examples**: Representative outputs for each level (when possible)
4. **Edge cases**: Guidance for ambiguous situations
5. **Scoring guidelines**: General principles for consistent application

### Strictness Calibration

- **Lenient**: Lower bar for passing scores, appropriate for encouraging iteration
- **Balanced**: Fair, typical expectations for production use
- **Strict**: High standards, appropriate for safety-critical or high-stakes evaluation

### Domain Adaptation

Rubrics should use domain-specific terminology:
- A "code readability" rubric mentions variables, functions, and comments
- Documentation rubrics reference clarity, accuracy, completeness
- Analysis rubrics focus on depth, accuracy, actionability

---

## Evaluation Pipeline Design

Production evaluation systems require multiple layers:

```
┌─────────────────────────────────────────────────┐
│                 Evaluation Pipeline              │
├─────────────────────────────────────────────────┤
│                                                   │
│  Input: Response + Prompt + Context               │
│           │                                       │
│           ▼                                       │
│  ┌─────────────────────┐                         │
│  │   Criteria Loader   │ ◄── Rubrics, weights    │
│  └──────────┬──────────┘                         │
│             │                                     │
│             ▼                                     │
│  ┌─────────────────────┐                         │
│  │   Primary Scorer    │ ◄── Direct or Pairwise  │
│  └──────────┬──────────┘                         │
│             │                                     │
│             ▼                                     │
│  ┌─────────────────────┐                         │
│  │   Bias Mitigation   │ ◄── Position swap, etc. │
│  └──────────┬──────────┘                         │
│             │                                     │
│             ▼                                     │
│  ┌─────────────────────┐                         │
│  │ Confidence Scoring  │ ◄── Calibration         │
│  └──────────┬──────────┘                         │
│             │                                     │
│             ▼                                     │
│  Output: Scores + Justifications + Confidence     │
│                                                   │
└─────────────────────────────────────────────────┘
```

---

## Scaling Evaluation

For high-volume evaluation:

1. **Panel of LLMs (PoLL)**: Use multiple models as judges, aggregate votes
   - Reduces individual model bias
   - More expensive but more reliable for high-stakes decisions

2. **Hierarchical evaluation**: Fast cheap model for screening, expensive model for edge cases
   - Cost-effective for large volumes
   - Requires calibration of screening threshold

3. **Human-in-the-loop**: Automated evaluation for clear cases, human review for low-confidence
   - Best reliability for critical applications
   - Design feedback loop to improve automated evaluation

---

## Detailed Examples

### Example 1: Direct Scoring for Accuracy

**Input**:
```
Prompt: "What causes seasons on Earth?"
Response: "Seasons are caused by Earth's tilted axis. As Earth orbits the Sun,
different hemispheres receive more direct sunlight at different times of year."
Criterion: Factual Accuracy (weight: 1.0)
Scale: 1-5
```

**Output**:
```json
{
  "criterion": "Factual Accuracy",
  "score": 5,
  "evidence": [
    "Correctly identifies axial tilt as primary cause",
    "Correctly explains differential sunlight by hemisphere",
    "No factual errors present"
  ],
  "justification": "Response accurately explains the cause of seasons with correct
scientific reasoning. Both the axial tilt and its effect on sunlight distribution
are correctly described.",
  "improvement": "Could add the specific tilt angle (23.5°) for completeness."
}
```

### Example 2: Pairwise Comparison with Position Swap

**Input**:
```
Prompt: "Explain machine learning to a beginner"
Response A: [Technical explanation with jargon]
Response B: [Simple analogy-based explanation]
Criteria: ["clarity", "accessibility"]
```

**First Pass (A first)**:
```json
{ "winner": "B", "confidence": 0.8 }
```

**Second Pass (B first)**:
```json
{ "winner": "A", "confidence": 0.6 }
```
(Note: Winner is A because B was in first position)

**Mapped Second Pass**:
```json
{ "winner": "B", "confidence": 0.6 }
```

**Final Result**:
```json
{
  "winner": "B",
  "confidence": 0.7,
  "positionConsistency": {
    "consistent": true,
    "firstPassWinner": "B",
    "secondPassWinner": "B"
  }
}
```

### Example 3: Rubric Generation

**Input**:
```
criterionName: "Code Readability"
criterionDescription: "How easy the code is to understand and maintain"
domain: "software engineering"
scale: "1-5"
strictness: "balanced"
```

**Output** (abbreviated):
```json
{
  "levels": [
    {
      "score": 1,
      "label": "Poor",
      "description": "Code is difficult to understand without significant effort",
      "characteristics": [
        "No meaningful variable or function names",
        "No comments or documentation",
        "Deeply nested or convoluted logic"
      ]
    },
    {
      "score": 3,
      "label": "Adequate",
      "description": "Code is understandable with some effort",
      "characteristics": [
        "Most variables have meaningful names",
        "Basic comments present for complex sections",
        "Logic is followable but could be cleaner"
      ]
    },
    {
      "score": 5,
      "label": "Excellent",
      "description": "Code is immediately clear and maintainable",
      "characteristics": [
        "All names are descriptive and consistent",
        "Comprehensive documentation",
        "Clean, modular structure"
      ]
    }
  ],
  "edgeCases": [
    {
      "situation": "Code is well-structured but uses domain-specific abbreviations",
      "guidance": "Score based on readability for domain experts, not general audience"
    }
  ]
}
```

---

## Complete Evaluation Patterns

### Pattern 1: Structured Evaluation Workflow

The most reliable evaluation follows a structured workflow:

```
Define Criteria → Gather Test Cases → Run Evaluation → Mitigate Bias → Interpret Results
```

#### Step 1: Define Evaluation Criteria

```markdown
## Evaluation Criteria for [Command/Skill Name]

### Criterion 1: Instruction Following (weight: 0.30)
- **Description**: Does the output follow all explicit instructions?
- **1 (Poor)**: Ignores or misunderstands core instructions
- **3 (Adequate)**: Follows main instructions, misses some details
- **5 (Excellent)**: Follows all instructions precisely

### Criterion 2: Output Completeness (weight: 0.25)
- **Description**: Are all requested aspects covered?
- **1 (Poor)**: Major aspects missing
- **3 (Adequate)**: Core aspects covered with gaps
- **5 (Excellent)**: All aspects thoroughly addressed

### Criterion 3: Tool Efficiency (weight: 0.20)
- **Description**: Were appropriate tools used efficiently?
- **1 (Poor)**: Wrong tools or excessive redundant calls
- **3 (Adequate)**: Appropriate tools with some redundancy
- **5 (Excellent)**: Optimal tool selection, minimal calls

### Criterion 4: Reasoning Quality (weight: 0.15)
- **Description**: Is the reasoning clear and sound?
- **1 (Poor)**: No apparent reasoning or flawed logic
- **3 (Adequate)**: Basic reasoning present
- **5 (Excellent)**: Clear, logical reasoning throughout

### Criterion 5: Response Coherence (weight: 0.10)
- **Description**: Is the output well-structured and clear?
- **1 (Poor)**: Difficult to follow or incoherent
- **3 (Adequate)**: Understandable but could be clearer
- **5 (Excellent)**: Well-structured, easy to follow
```

#### Step 2: Create Test Cases

```markdown
## Test Cases for /refactor Command

### Simple (Single Operation)
- **Input**: Rename variable `x` to `count` in a single file
- **Expected**: All instances renamed, code still runs

### Medium (Multiple Operations)
- **Input**: Extract function from 20-line code block
- **Expected**: New function created, original call site updated, behavior preserved

### Complex (Cross-File Changes)
- **Input**: Refactor class to use Strategy pattern
- **Expected**: Interface created, implementations separated, all usages updated

### Edge Case
- **Input**: Refactor code with conflicting variable names in nested scopes
- **Expected**: Correct scoping preserved, no accidental shadowing
```

#### Step 3: Run Direct Scoring Evaluation

```markdown
You are evaluating the output of a Claude Code command.

## Original Task
{paste the user's original request}

## Command Output
{paste the full command output including tool calls}

## Evaluation Criteria
{paste your criteria definitions from Step 1}

## Instructions
For each criterion:
1. Find specific evidence in the output that supports your assessment
2. Assign a score (1-5) based on the rubric levels
3. Write a 1-2 sentence justification citing the evidence
4. Suggest one specific improvement

IMPORTANT: Provide your justification BEFORE stating the score. This improves evaluation reliability.

## Output Format
For each criterion, respond with:

### [Criterion Name]
**Evidence**: [Quote or describe specific parts of the output]
**Justification**: [Explain how the evidence maps to the rubric level]
**Score**: [1-5]
**Improvement**: [One actionable suggestion]

### Overall Assessment
**Weighted Score**: [Calculate: sum of (score × weight)]
**Pass/Fail**: [Pass if weighted score ≥ 3.5]
**Summary**: [2-3 sentences summarizing strengths and weaknesses]
```

#### Step 4: Mitigate Position Bias in Comparisons

**Pass 1 (A First):**
```markdown
You are comparing two outputs from different prompt variants.

## Original Task
{task description}

## Output A (First Variant)
{output from prompt variant A}

## Output B (Second Variant)
{output from prompt variant B}

## Comparison Criteria
- Instruction Following
- Output Completeness
- Reasoning Quality

## Critical Instructions
- Do NOT prefer outputs because they are longer
- Do NOT prefer outputs based on their position (first vs second)
- Focus ONLY on quality differences
- TIE is acceptable when outputs are equivalent

## Analysis Process
1. Analyze Output A independently: [strengths, weaknesses]
2. Analyze Output B independently: [strengths, weaknesses]
3. Compare on each criterion
4. Determine winner with confidence (0-1)

## Output
Reasoning: [Explain why]
Winner: [A/B/TIE]
Confidence: [0.0-1.0]
```

**Pass 2 (B First):** Repeat but swap the order.

**Interpret Results:**
- Both passes agree → Winner confirmed, average the confidences
- Passes disagree → Result is TIE with confidence 0.5 (position bias detected)

---

### Pattern 2: Hierarchical Evaluation Workflow

For complex evaluations:

```
Quick Screen (cheap model) → Detailed Evaluation (expensive model) → Human Review (edge cases)
```

#### Tier 1: Quick Screen (Use Haiku)

```markdown
Rate this command output 0-10 for basic adequacy.

Task: {brief task description}
Output: {command output}

Quick assessment: Does this output reasonably address the task?
Score (0-10):
One-line reasoning:
```

**Decision rule**: Score < 5 → Fail, Score ≥ 7 → Pass, Score 5-7 → Escalate to detailed evaluation

#### Tier 2: Detailed Evaluation (Use Opus)

Use the full direct scoring prompt from Pattern 1 for borderline cases.

#### Tier 3: Human Review

For low-confidence automated evaluations (confidence < 0.6):

```markdown
## Human Review Request

**Automated Score**: 3.2/5 (Confidence: 0.45)
**Reason for Escalation**: Low confidence, evaluator disagreed across passes

### What to Review
1. Does the output actually complete the task?
2. Are the automated criterion scores reasonable?
3. What did the automation miss?

### Original Task
{task}

### Output
{output}

### Human Override
[ ] Agree with automation
[ ] Override to PASS - Reason: ___
[ ] Override to FAIL - Reason: ___
```

---

### Pattern 3: Panel of LLM Judges (PoLL)

For high-stakes evaluation, use multiple models:

1. **Run 3 independent evaluations** with different prompt framings:
   - Evaluation 1: Standard criteria prompt
   - Evaluation 2: Adversarial framing ("Find problems with this output")
   - Evaluation 3: User perspective ("Would a developer be satisfied?")

2. **Aggregate results**:
   - Take median score per criterion (robust to outliers)
   - Flag criteria with high variance (std > 1.0) for review
   - Overall pass requires majority agreement

**Multi-Judge Prompt Variants:**

```markdown
Standard:    "Evaluate this output against the specified criteria. Be fair and balanced."
Adversarial: "Your role is to find problems with this output. Be critical and thorough."
User:        "Imagine you're a developer who requested this task. Would you be satisfied?"
```

**Agreement Analysis:**

| Criterion | Judge 1 | Judge 2 | Judge 3 | Median | Std Dev |
|-----------|---------|---------|---------|--------|---------|
| Instruction Following | 4 | 4 | 5 | 4 | 0.58 |
| Completeness | 3 | 4 | 3 | 3 | 0.58 |
| Tool Efficiency | 2 | 3 | 4 | 3 | 1.00 ⚠️ |

**⚠️ High variance** on Tool Efficiency suggests the criterion needs clearer definition.

---

### Pattern 4: Confidence Calibration

| Factor | High Confidence | Low Confidence |
|--------|-----------------|----------------|
| Position consistency | Both passes agree | Passes disagree |
| Evidence count | 3+ specific citations | Vague or no citations |
| Criterion agreement | All criteria align | Criteria scores vary widely |
| Edge case match | Similar to known cases | Novel situation |

**Calibration Prompt Addition**:

```markdown
## Confidence Assessment

After scoring, assess your confidence:

1. **Evidence Strength**: How specific was the evidence you cited?
   - Strong: Quoted exact passages, precise observations
   - Moderate: General observations, reasonable inferences
   - Weak: Vague impressions, assumptions

2. **Overall Confidence**: [0.0-1.0]
   - 0.9+: Very confident, clear evidence
   - 0.7-0.9: Confident, minor ambiguity
   - 0.5-0.7: Moderate confidence
   - <0.5: Low confidence, significant uncertainty

Confidence: [score]
Confidence Reasoning: [explain what factors affected confidence]
```

---

### Pattern 5: Structured Output Format

```markdown
## Evaluation Results

### Metadata
- **Evaluated**: [command/skill name]
- **Test Case**: [test case ID or description]
- **Evaluator**: [model used]
- **Timestamp**: [when evaluated]

### Criterion Scores

| Criterion | Score | Weight | Weighted | Confidence |
|-----------|-------|--------|----------|------------|
| Instruction Following | 4/5 | 0.30 | 1.20 | 0.85 |
| Output Completeness | 3/5 | 0.25 | 0.75 | 0.70 |
| Tool Efficiency | 5/5 | 0.20 | 1.00 | 0.90 |
| Reasoning Quality | 4/5 | 0.15 | 0.60 | 0.75 |
| Response Coherence | 4/5 | 0.10 | 0.40 | 0.80 |

### Summary
- **Overall Score**: 3.95/5.0
- **Pass Threshold**: 3.5/5.0
- **Result**: ✅ PASS

### Evidence Summary
- **Strengths**: [bullet points]
- **Weaknesses**: [bullet points]
- **Improvements**: [prioritized suggestions]

### Confidence Assessment
- **Overall Confidence**: 0.78
- **Flags**: [any concerns or caveats]
```

---

## Evaluation Workflows

### Workflow: Testing a New Command

1. Write 5-10 test cases spanning complexity levels
2. Run command on each test case, capture full output
3. Quick screen all outputs with Tier 1 evaluation
4. Detailed evaluate failures and borderline cases
5. Identify patterns in failures to guide prompt improvements
6. Iterate prompt based on specific weaknesses found
7. Re-evaluate same test cases to measure improvement

### Workflow: Comparing Prompt Variants

1. Create variant prompts (e.g., different instruction phrasings)
2. Run both variants on identical test cases
3. Pairwise compare with position swapping
4. Calculate win rate for each variant
5. Analyze which cases each variant handles better
6. Decide: pick winner or create hybrid

### Workflow: Regression Testing

1. Maintain test suite of representative cases
2. Before changes: Run evaluation, record baseline scores
3. After changes: Re-run evaluation
4. Compare: Flag regressions (score drops > 0.5)
5. Investigate: Why did specific cases regress?
6. Accept or revert: Based on overall impact

### Workflow: Continuous Quality Monitoring

1. Sample production usage (if available)
2. Run lightweight evaluation on samples
3. Track metrics over time: average scores, failure rate, low-confidence rate
4. Alert on degradation: Score drop > 10% from baseline
5. Periodic deep dive: Monthly detailed evaluation on random sample

---

## Handling Evaluation Failures

### Malformed Output Recovery

When the evaluator produces unparseable or incomplete output:

1. **Mark as invalid** — incorrect output usually indicates hallucinations during thinking
2. **Retry initial prompt without changes** — multiple retries usually produce more consistent results
3. **If still incorrect, flag for human review**: Mark as "evaluation failed, needs manual check"

### Validation Checklist

Before trusting evaluation results:

- [ ] All criteria have scores in valid range (1-5)
- [ ] Each score has a justification referencing specific evidence
- [ ] Confidence score is provided and reasonable
- [ ] No contradictions between justification and assigned score
- [ ] Weighted total calculation is correct

---

## Validating Evaluation Prompts (Meta-Evaluation)

### Calibration Test Cases

| Test Type | Description | Expected Score |
|-----------|-------------|----------------|
| Known-good | Clearly excellent output | 4.5+ / 5.0 |
| Known-bad | Clearly poor output | < 2.5 / 5.0 |
| Boundary | Borderline case | 3.0-3.5 with nuanced explanation |

### Validation Workflow

1. **Known-good test**: If score < 4.0 → Rubric is too strict
2. **Known-bad test**: If score > 3.0 → Rubric is too lenient
3. **Boundary test**: Should produce moderate score (3.0-3.5) with detailed explanation
4. **Consistency test**: Run same evaluation 3 times; variance should be < 0.5

### Position Bias Validation

```markdown
## Position Bias Test

Run this test with IDENTICAL outputs in both positions:

Position A: [Paste output]
Position B: [Paste identical output]

Expected Result: TIE with high confidence (>0.9)

If Result Shows Winner:
- Position bias detected
- Add stronger anti-bias instructions to prompt
- Re-test until TIE achieved consistently
```
