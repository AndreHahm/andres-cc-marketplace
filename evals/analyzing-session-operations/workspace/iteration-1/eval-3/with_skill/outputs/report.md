# Session Operations Report -- Performance & Cost

token_time_aggregator.py output: entries_aggregated 3, total_tokens 15000, total_duration_ms 25000, by_level {subagent: {tokens: 15000, duration_ms: 25000, count: 3}}, levels_present [subagent].

scope_note (as printed): "Totals cover only entries supplied... Levels actually present in this run: subagent -- never present a total from a narrower level (e.g. subagent) as if it covered a broader one (e.g. whole_session) that isn't in this list."

Cost discussion: levels_present is [subagent] only -- whole_session is absent. Per the skill's own rule, whole-session cost is unavailable and must not be inferred from the subagent total. No monetary rate was supplied, so cost is stated in tokens/ms only, no dollar conversion offered.

Instrumentation gap: critical_path_analyzer.py not run this pass since no span carries start/end timestamps -- reported as a recommendation, not a fabricated value.

Next: run `generating-analysis-recommendations` on this report.
