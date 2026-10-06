# Transcript (baseline, dry run)

Operator request: "Quickly check my note-formatter skill, it lives in evals/skill-tester/fixtures/note-formatter."

## Step: locate the skill
Question: Where does the skill live?
Options: use the path given / search the repo
Simulated answer: already located, evals/skill-tester/fixtures/note-formatter (read its SKILL.md; 5 rules, 2 documented validation cases).

## Step: choose testing mode
Question: Which testing mode?
Options: Fast pass/fail, no baseline / Full baseline comparison
Simulated answer: Fast pass/fail, no baseline.

## Step: choose scenarios
Question: Which scenarios?
Simulated answer: (1) mixed feature/bug/docs/refactor list grouped in documented order; (2) bullet without issue number rendered with (#none).

## Step: pressure testing
Question: Pressure testing wanted?
Options: No / Yes
Simulated answer: No.

## Step: write eval files
Created under outputs/evals/note-formatter/:
- evals.json (2 evals, each with prompt, expected_output, files, assertions)
- files/mixed-list.txt (6 bullets, mixed types, deliberately out of order)
- files/no-issue.txt (1 bug bullet, no issue number)
The fixture skill was not modified.

## Next phase (not run)
It would run each eval prompt once with the skill in a sub-agent, save each output, grade it against the assertions (pass/fail per assertion), and report a pass rate per eval. No baseline run, since fast mode was chosen. No agents were launched here.
