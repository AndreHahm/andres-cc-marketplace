#!/usr/bin/env python3
"""
Usage: python aggregate_benchmark.py <path/to/iteration-N> [--skill-name <name>]
Reads all eval-N/{with_skill,baseline}/{grading,timing}.json
Outputs: benchmark.json with aggregated stats
"""
import glob
import json
import math
import os
import re
import sys
from datetime import datetime


def ruby_round(value, digits=0):
    """Round half away from zero, matching Ruby's Float#round (Python's
    built-in round() uses banker's rounding, which would silently disagree
    with the Ruby original on exact .5 boundaries)."""
    factor = 10 ** digits
    scaled = value * factor
    if scaled >= 0:
        result = math.floor(scaled + 0.5)
    else:
        result = math.ceil(scaled - 0.5)
    result = result / factor
    return int(result) if digits == 0 else result


def dig(d, *keys):
    """Nested dict lookup that returns None on any missing/non-dict level,
    matching Ruby Hash#dig."""
    current = d
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return None
    return current


def main():
    sys.stdout.reconfigure(encoding='utf-8')

    args = sys.argv[1:]
    iteration_path = args[0] if args else None
    skill_name_override = None
    if '--skill-name' in args:
        idx = args.index('--skill-name')
        if idx + 1 < len(args):
            skill_name_override = args[idx + 1]

    if not iteration_path or not os.path.isdir(iteration_path):
        print('Usage: python aggregate_benchmark.py <path/to/iteration-N> [--skill-name <name>]')
        print('Example: python aggregate_benchmark.py ./evals/skill-development/workspace/iteration-1')
        sys.exit(1)

    # Derive skill_name from the standardized workspace path
    # (./evals/<skill-name>/workspace/iteration-N), or use --skill-name if given.
    derived_skill_name = os.path.basename(
        os.path.dirname(os.path.dirname(os.path.abspath(iteration_path)))
    )
    skill_name = skill_name_override or derived_skill_name
    if not skill_name:
        print("Warning: could not derive skill_name from path; pass --skill-name explicitly")

    # Discover eval directories (eval-1, eval-2, etc.) - only names matching
    # eval-<digits> exactly, so a stray sibling like eval-backup/ or
    # eval-template/ is skipped rather than crashing the eval_id extraction
    # below. Sorted numerically, not lexicographically, so ordering stays
    # correct past eval-9 (a plain string sort would put eval-10 before eval-2).
    eval_dir_re = re.compile(r'eval-(\d+)$')
    eval_dirs = []
    for p in glob.glob(os.path.join(iteration_path, "eval-*")):
        if not os.path.isdir(p):
            continue
        if eval_dir_re.search(os.path.basename(p)):
            eval_dirs.append(p)
    eval_dirs.sort(key=lambda p: int(eval_dir_re.search(os.path.basename(p)).group(1)))

    if not eval_dirs:
        print(f"Error: No eval-<N> directories found in {iteration_path}")
        sys.exit(1)

    # Extract iteration number from path (e.g., iteration-2 -> 2)
    iteration_match = re.search(r'iteration-(\d+)', os.path.basename(iteration_path))
    if not iteration_match:
        print(f"Error: could not parse iteration number from {iteration_path}")
        print("Expected a directory named like 'iteration-1', 'iteration-2', etc.")
        sys.exit(1)
    iteration_num = int(iteration_match.group(1))

    # Initialize benchmark structure
    benchmark = {
        "skill_name": skill_name or "",
        "iteration": iteration_num,
        "timestamp": datetime.now().astimezone().replace(microsecond=0).isoformat(),
        "evals": [],
        "summary": {
            "with_skill_avg_pass_rate": 0.0,
            "baseline_avg_pass_rate": 0.0,
            "improvement": 0.0,
            "avg_tokens_with_skill": 0,
            "avg_tokens_baseline": 0,
            "token_cost": 0,
            "avg_duration_ms_with_skill": 0,
            "avg_duration_ms_baseline": 0,
        },
    }

    # Process each eval directory
    with_skill_pass_rates = []
    baseline_pass_rates = []

    for eval_dir in eval_dirs:
        # eval_dirs is pre-filtered above, so this match is guaranteed.
        eval_id = int(eval_dir_re.search(os.path.basename(eval_dir)).group(1))

        with_skill_grading_path = os.path.join(eval_dir, "with_skill", "grading.json")
        with_skill_timing_path = os.path.join(eval_dir, "with_skill", "timing.json")
        baseline_grading_path = os.path.join(eval_dir, "baseline", "grading.json")
        baseline_timing_path = os.path.join(eval_dir, "baseline", "timing.json")

        # Read grading and timing data
        def load_json(path):
            if os.path.exists(path):
                with open(path, encoding='utf-8') as f:
                    return json.load(f)
            return {}

        with_skill_grading = load_json(with_skill_grading_path)
        with_skill_timing = load_json(with_skill_timing_path)
        baseline_grading = load_json(baseline_grading_path)
        baseline_timing = load_json(baseline_timing_path)

        # Extract metrics
        with_skill_pass_rate = dig(with_skill_grading, 'summary', 'pass_rate') or 0.0
        baseline_pass_rate = dig(baseline_grading, 'summary', 'pass_rate') or 0.0
        with_skill_tokens = with_skill_timing.get('total_tokens') or 0
        baseline_tokens = baseline_timing.get('total_tokens') or 0
        with_skill_duration = with_skill_timing.get('duration_ms') or 0
        baseline_duration = baseline_timing.get('duration_ms') or 0

        # Build eval result
        eval_result = {
            "eval_id": eval_id,
            "with_skill": {
                "pass_rate": with_skill_pass_rate,
                "assertions_passed": dig(with_skill_grading, 'summary', 'assertions_passed') or 0,
                "assertions_total": dig(with_skill_grading, 'summary', 'assertions_total') or 0,
                "avg_tokens": with_skill_tokens,
                "avg_duration_ms": with_skill_duration,
            },
            "baseline": {
                "pass_rate": baseline_pass_rate,
                "assertions_passed": dig(baseline_grading, 'summary', 'assertions_passed') or 0,
                "assertions_total": dig(baseline_grading, 'summary', 'assertions_total') or 0,
                "avg_tokens": baseline_tokens,
                "avg_duration_ms": baseline_duration,
            },
            "delta": {
                "pass_rate": ruby_round(with_skill_pass_rate - baseline_pass_rate, 4),
                "tokens": with_skill_tokens - baseline_tokens,
                "duration_ms": with_skill_duration - baseline_duration,
            },
        }

        benchmark["evals"].append(eval_result)

        # Collect metrics for summary
        with_skill_pass_rates.append(with_skill_pass_rate)
        baseline_pass_rates.append(baseline_pass_rate)

    # Calculate summary statistics
    if with_skill_pass_rates:
        avg_with_skill_pass_rate = ruby_round(sum(with_skill_pass_rates) / len(with_skill_pass_rates), 4)
    else:
        avg_with_skill_pass_rate = 0.0
    if baseline_pass_rates:
        avg_baseline_pass_rate = ruby_round(sum(baseline_pass_rates) / len(baseline_pass_rates), 4)
    else:
        avg_baseline_pass_rate = 0.0
    improvement = ruby_round(avg_with_skill_pass_rate - avg_baseline_pass_rate, 4)

    # For tokens and duration, calculate average across evals
    avg_with_skill_tokens = 0
    avg_baseline_tokens = 0
    avg_with_skill_duration = 0
    avg_baseline_duration = 0

    if benchmark["evals"]:
        eval_count = float(len(benchmark["evals"]))
        with_skill_token_sum = sum(e["with_skill"]["avg_tokens"] for e in benchmark["evals"])
        baseline_token_sum = sum(e["baseline"]["avg_tokens"] for e in benchmark["evals"])
        with_skill_duration_sum = sum(e["with_skill"]["avg_duration_ms"] for e in benchmark["evals"])
        baseline_duration_sum = sum(e["baseline"]["avg_duration_ms"] for e in benchmark["evals"])

        avg_with_skill_tokens = ruby_round(with_skill_token_sum / eval_count, 0)
        avg_baseline_tokens = ruby_round(baseline_token_sum / eval_count, 0)
        avg_with_skill_duration = ruby_round(with_skill_duration_sum / eval_count, 0)
        avg_baseline_duration = ruby_round(baseline_duration_sum / eval_count, 0)

    benchmark["summary"] = {
        "with_skill_avg_pass_rate": avg_with_skill_pass_rate,
        "baseline_avg_pass_rate": avg_baseline_pass_rate,
        "improvement": improvement,
        "avg_tokens_with_skill": avg_with_skill_tokens,
        "avg_tokens_baseline": avg_baseline_tokens,
        "token_cost": avg_with_skill_tokens - avg_baseline_tokens,
        "avg_duration_ms_with_skill": avg_with_skill_duration,
        "avg_duration_ms_baseline": avg_baseline_duration,
        "duration_cost_ms": avg_with_skill_duration - avg_baseline_duration,
    }

    # Write benchmark.json
    benchmark_path = os.path.join(iteration_path, "benchmark.json")
    with open(benchmark_path, 'w', encoding='utf-8') as f:
        json.dump(benchmark, f, indent=2)
        f.write('\n')

    print(f"✓ Benchmark aggregated: {benchmark_path}")
    print('')
    print('Summary:')
    print(f"  Evals processed: {len(benchmark['evals'])}")
    print(f"  With Skill pass rate: {ruby_round(avg_with_skill_pass_rate * 100, 1)}%")
    print(f"  Baseline pass rate: {ruby_round(avg_baseline_pass_rate * 100, 1)}%")
    print(f"  Improvement: +{ruby_round(improvement * 100, 1)} percentage points")

    token_cost = avg_with_skill_tokens - avg_baseline_tokens
    token_cost_str = f"+{token_cost}" if token_cost > 0 else str(token_cost)
    print(f"  Token cost: {token_cost_str}")

    duration_cost = avg_with_skill_duration - avg_baseline_duration
    duration_cost_str = f"+{duration_cost}" if duration_cost > 0 else str(duration_cost)
    print(f"  Duration cost: {duration_cost_str}ms")


if __name__ == "__main__":
    main()
