import { runCommand } from "./process.mjs";

const PROBE_TIMEOUT_MS = 15000;

// Actually attempts a trivial read-only sandboxed Codex call rather than
// assuming sandbox modes work (scope-expansion gap #5) — on Windows, Codex's
// read-only/workspace-write sandbox can fail with a CreateProcessAsUserW
// access-rights error, leaving danger-full-access as the only working mode.
// Callers must report the result explicitly either way; never fall back to
// danger-full-access silently (scope-expansion gap #4).
export function checkSandboxViability(cwd) {
  // Pipe the prompt via stdin rather than positionally — a multi-word
  // positional argument gets tokenized by Codex's own arg parser (the same
  // gotcha documented in codex-prompt-protocol/references/cli-reference.md),
  // which surfaced as a real "unexpected argument 'with' found" failure
  // during Phase 5 testing against the actual installed Codex CLI.
  const result = runCommand(
    "codex",
    ["exec", "--sandbox", "read-only", "--skip-git-repo-check"],
    { cwd, input: "reply with exactly: ok", timeout: PROBE_TIMEOUT_MS }
  );

  if (result.error) {
    return { viable: false, detail: result.error.message };
  }

  const combined = `${result.stdout}\n${result.stderr}`;
  if (/CreateProcessAsUserW|sandbox|permission denied|access is denied/i.test(combined) && result.status !== 0) {
    return { viable: false, detail: combined.trim().slice(0, 500) };
  }

  if (result.status !== 0) {
    return { viable: false, detail: combined.trim().slice(0, 500) || `exit ${result.status}` };
  }

  return { viable: true, detail: "read-only sandbox executed successfully" };
}
