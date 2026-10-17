# Adapter Contract

What a provider adapter must provide so a second provider (CodeQL, SonarQube, another) can be added without
changing `resolving-analysis-findings`. No second adapter exists today; this file is the checklist for
writing one, not a promise that one is planned.

An adapter is acceptable only when all of these hold:

1. **Reads a file, runs nothing.** It takes the provider tool's JSON output from a file or stdin and writes
   the record to stdout. It spawns no process, opens no network connection and never opens a path named in
   the findings. The command that produces the JSON is run by the skill, using a documented read form.
2. **Emits the record in `findings-record.md`'s shape**, with the provider's own severity string verbatim and
   `null` for anything the provider does not give. It never invents a value (an issue id, a tool name) to
   fill a field.
3. **Fails closed.** An input shape it was not verified against exits 2 with a message and writes nothing to
   stdout. A partial record would feed wrong numbers to a decision.
4. **Was verified against real output.** The adapter's fixtures are redacted or synthetic copies of output
   the real tool produced, and the provider status table in `SKILL.md` gets a dated "verified" row. A
   provider whose output has not been seen stays "planned".
5. **Documents its read commands and its write commands.** Every flag that changes remote state is listed as
   forbidden to this skill, as `codacy-adapter.md` does for Codacy.
6. **Carries a smoke test** in `scripts/` that runs in-process on the fixtures (no subprocess) and checks the
   fail-closed paths. Each skill owns its smoke test. `resolving-analysis-findings`' test looks this skill up
   by directory name, so renaming this skill means updating that test; an adapter added later should keep
   its adapter checks in this skill's test, separate from the SKILL.md checks.

Not in an adapter's job: deciding what a finding means, mapping severities across providers, or writing to
the provider.
