# Metric Selection for LLM Evaluation

Reference guide for selecting and interpreting evaluation metrics. Covers classification, agreement, and correlation metrics with a decision tree for choosing the right metric per use case.

## Quick Reference: Common Metrics

### Classification Metrics (Pass/Fail Tasks)

**Precision**: Of all responses marked as passing, what fraction truly passed?
- Use when false positives are costly

**Recall**: Of all actually passing responses, what fraction did we identify?
- Use when false negatives are costly

**F1 Score**: Harmonic mean of precision and recall
- Use for balanced single-number summary

### Agreement Metrics (Comparing to Human Judgment)

**Cohen's Kappa**: Agreement adjusted for chance

- > 0.8: Almost perfect agreement
- 0.6-0.8: Substantial agreement
- 0.4-0.6: Moderate agreement
- < 0.4: Fair to poor agreement

### Correlation Metrics (Ordinal Scores)

**Spearman's Rank Correlation**: Correlation between rankings

- > 0.9: Very strong correlation
- 0.7-0.9: Strong correlation
- 0.5-0.7: Moderate correlation
- < 0.5: Weak correlation

### Good Evaluation System Indicators

| Metric | Good | Acceptable | Concerning |
|--------|------|------------|------------|
| Spearman's rho | > 0.8 | 0.6-0.8 | < 0.6 |
| Cohen's Kappa | > 0.7 | 0.5-0.7 | < 0.5 |
| Position consistency | > 0.9 | 0.8-0.9 | < 0.8 |
| Length-score correlation | < 0.2 | 0.2-0.4 | > 0.4 |

---

## Metric Categories

### Classification Metrics

Use for binary or multi-class evaluation tasks (pass/fail, correct/incorrect).

#### Precision

```
Precision = True Positives / (True Positives + False Positives)
```

**Interpretation**: Of all responses the judge said were good, what fraction were actually good?

**Use when**: False positives are costly (e.g., approving unsafe content)

#### Recall

```
Recall = True Positives / (True Positives + False Negatives)
```

**Interpretation**: Of all actually good responses, what fraction did the judge identify?

**Use when**: False negatives are costly (e.g., missing good content in filtering)

#### F1 Score

```
F1 = 2 * (Precision * Recall) / (Precision + Recall)
```

**Interpretation**: Harmonic mean of precision and recall

**Use when**: You need a single number balancing both concerns

### Agreement Metrics

Use for comparing automated evaluation with human judgment.

#### Cohen's Kappa (κ)

```
κ = (Observed Agreement - Expected Agreement) / (1 - Expected Agreement)
```

**Interpretation**: Agreement adjusted for chance
- κ > 0.8: Almost perfect agreement
- κ 0.6-0.8: Substantial agreement
- κ 0.4-0.6: Moderate agreement
- κ < 0.4: Fair to poor agreement

**Use for**: Binary or categorical judgments

#### Weighted Kappa

For ordinal scales where disagreement severity matters.

**Interpretation**: Penalizes large disagreements more than small ones

### Correlation Metrics

Use for ordinal/continuous scores.

#### Spearman's Rank Correlation (ρ)

**Interpretation**: Correlation between rankings, not absolute values
- ρ > 0.9: Very strong correlation
- ρ 0.7-0.9: Strong correlation
- ρ 0.5-0.7: Moderate correlation
- ρ < 0.5: Weak correlation

**Use when**: Order matters more than exact values

#### Kendall's Tau (τ)

**Interpretation**: Similar to Spearman but based on pairwise concordance

**Use when**: You have many tied values

#### Pearson Correlation (r)

**Interpretation**: Linear correlation between scores

**Use when**: Exact score values matter, not just order

### Pairwise Comparison Metrics

#### Agreement Rate

```
Agreement = (Matching Decisions) / (Total Comparisons)
```

**Interpretation**: Simple percentage of agreement

#### Position Consistency

```
Consistency = (Consistent across position swaps) / (Total comparisons)
```

**Interpretation**: How often does swapping position change the decision?

---

## Selection Decision Tree

```
What type of evaluation task?
│
├── Binary classification (pass/fail)
│   └── Use: Precision, Recall, F1, Cohen's κ
│
├── Ordinal scale (1-5 rating)
│   ├── Comparing to human judgments?
│   │   └── Use: Spearman's ρ, Weighted κ
│   └── Comparing two automated judges?
│       └── Use: Kendall's τ, Spearman's ρ
│
├── Pairwise preference
│   └── Use: Agreement rate, Position consistency
│
└── Multi-label classification
    └── Use: Macro-F1, Micro-F1, Per-label metrics
```

---

## Metric Selection by Use Case

### Use Case 1: Validating Automated Evaluation

**Goal**: Ensure automated evaluation correlates with human judgment

**Recommended Metrics**:
1. Primary: Spearman's ρ (for ordinal scales) or Cohen's κ (for categorical)
2. Secondary: Per-criterion agreement
3. Diagnostic: Confusion matrix for systematic errors

### Use Case 2: Comparing Two Models

**Goal**: Determine which model produces better outputs

**Recommended Metrics**:
1. Primary: Win rate (from pairwise comparison)
2. Secondary: Position consistency (bias check)
3. Diagnostic: Per-criterion breakdown

### Use Case 3: Quality Monitoring

**Goal**: Track evaluation quality over time

**Recommended Metrics**:
1. Primary: Rolling agreement with human spot-checks
2. Secondary: Score distribution stability
3. Diagnostic: Bias indicators (position, length)

---

## Interpreting Metric Results

### Warning Signs

1. **High agreement but low correlation**: May indicate calibration issues
2. **Low position consistency**: Position bias affecting results
3. **High length correlation**: Length bias inflating scores
4. **Per-criterion variance**: Some criteria may be poorly defined

### Reporting Template

```markdown
## Evaluation System Metrics Report

### Human Agreement
- Spearman's ρ: 0.82 (p < 0.001) · Cohen's κ: 0.74 · Sample size: 500 evaluations

### Bias Indicators
- Position consistency: 91% · Length-score correlation: 0.12

### Per-Criterion Performance
| Criterion | Spearman's ρ | κ |
|-----------|--------------|---|
| Accuracy | 0.88 | 0.79 |
| Clarity | 0.76 | 0.68 |

### Recommendations
- Monitor "Clarity" — lower agreement may indicate need for rubric refinement
```
