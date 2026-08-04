#!/usr/bin/env python3
"""
Usage:
  python compute_score.py <component_input.json>
  python compute_score.py --rollup <rollup_input.json>

Deterministic scoring math for plugin-grader: converts Critical/Major/Minor
finding counts into dimension scores via the generic formula, applies the
fixed 12-dimension weights, and applies hard gates. See
references/output-schema.md for the exact input/output shapes.
"""
import json
import sys

WEIGHTS = {
    "structure_architecture": 0.15,
    "content_quality": 0.15,
    "rule_compliance": 0.12,
    "completeness": 0.12,
    "maintainability": 0.10,
    "robustness": 0.10,
    "simplicity": 0.05,
    "testing": 0.05,
    "uniqueness": 0.05,
    "safety_risk_handling": 0.05,
    "efficiency": 0.03,
    "actionability": 0.03,
}


def generic_formula(critical, major, minor):
    """Critical/Major/Minor -> 0-10, severity classes never cross."""
    if critical >= 1:
        return round(4 - min(4, 2 * critical), 2)
    if major >= 1:
        return round(7 - min(3, 1.5 * major), 2)
    return round(10 - min(3, 0.5 * minor), 2)


def score_dimension(dim_input):
    """A dimension either carries a precomputed 'score' (custom-band
    dimensions: simplicity, testing, efficiency, actionability) or raw
    'counts' (reviewer-backed dimensions, scored via generic_formula)."""
    if "score" in dim_input:
        return float(dim_input["score"])
    counts = dim_input.get("counts", {})
    return generic_formula(
        counts.get("critical", 0),
        counts.get("major", 0),
        counts.get("minor", 0),
    )


def compute_component(data):
    dimensions = data["dimensions"]
    scores = {}
    for dim_name in WEIGHTS:
        dim_input = dimensions.get(dim_name, {"score": 10, "is_na": True})
        score = score_dimension(dim_input)
        if dim_input.get("contradiction_found"):
            score = min(score, 4)
        scores[dim_name] = score

    weighted_total = sum(scores[d] * w for d, w in WEIGHTS.items())

    gates_applied = []
    caps = []

    if scores["rule_compliance"] < 5:
        cap = 6.0
        caps.append(cap)
        gates_applied.append({
            "gate": "A_rule_compliance",
            "reason": f"Rule Compliance scored {scores['rule_compliance']} (< 5)",
            "cap": cap,
        })
    if scores["completeness"] < 4:
        cap = 5.0
        caps.append(cap)
        gates_applied.append({
            "gate": "B_completeness",
            "reason": f"Completeness scored {scores['completeness']} (< 4)",
            "cap": cap,
        })
    if scores["safety_risk_handling"] < 4:
        cap = 4.0
        caps.append(cap)
        gates_applied.append({
            "gate": "C_safety_risk_handling",
            "reason": f"Safety/Risk Handling scored {scores['safety_risk_handling']} (< 4) -- a Critical security finding",
            "cap": cap,
        })
    if scores["testing"] == 0:
        cap = 8.0
        caps.append(cap)
        gates_applied.append({
            "gate": "D_testing",
            "reason": "Testing scored 0. Missing verification.",
            "cap": cap,
        })

    final_score = min(weighted_total, min(caps)) if caps else weighted_total

    return {
        "dimension_scores": {d: round(s, 2) for d, s in scores.items()},
        "weighted_total": round(weighted_total, 1),
        "gates_applied": gates_applied,
        "final_score": round(final_score, 1),
    }


def compute_rollup(data):
    component_scores = data["component_scores"]
    names = list(component_scores.keys())
    values = list(component_scores.values())
    raw = sum(values) / len(values)

    weakest_name = min(component_scores, key=component_scores.get)
    strongest_name = max(component_scores, key=component_scores.get)

    gates_applied = []
    caps = []

    if data.get("activation_critical"):
        cap = 6.0
        caps.append(cap)
        gates_applied.append({
            "gate": "P1_activation_collision",
            "reason": "activation-reviewer found a Critical exact-phrase collision",
            "cap": cap,
        })
    if data.get("consistency_critical"):
        cap = 6.0
        caps.append(cap)
        gates_applied.append({
            "gate": "P2_consistency_contradiction",
            "reason": "consistency-reviewer found a Critical cross-component contradiction",
            "cap": cap,
        })
    if component_scores[weakest_name] < 3:
        cap = 7.0
        caps.append(cap)
        gates_applied.append({
            "gate": "P3_broken_component",
            "reason": f"'{weakest_name}' scored {component_scores[weakest_name]} (< 3)",
            "cap": cap,
        })

    plugin_final = min(raw, min(caps)) if caps else raw

    return {
        "plugin_score_raw": round(raw, 2),
        "weakest_component": {"name": weakest_name, "final_score": component_scores[weakest_name]},
        "strongest_component": {"name": strongest_name, "final_score": component_scores[strongest_name]},
        "plugin_gates_applied": gates_applied,
        "plugin_final_score": round(plugin_final, 1),
        "component_count": len(names),
    }


def main():
    sys.stdout.reconfigure(encoding='utf-8')

    args = sys.argv[1:]
    rollup_mode = "--rollup" in args
    if rollup_mode:
        args.remove("--rollup")

    if len(args) != 1:
        print("Usage: python compute_score.py <component_input.json>")
        print("       python compute_score.py --rollup <rollup_input.json>")
        sys.exit(1)

    with open(args[0], encoding="utf-8") as f:
        data = json.load(f)

    result = compute_rollup(data) if rollup_mode else compute_component(data)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
