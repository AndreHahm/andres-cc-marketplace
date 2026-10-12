import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { runCommand } from "./cdx-process.mjs";
import { redactSecrets } from "./codex-exec.mjs";

// A real model turn that runs a command takes longer than a one-word reply (a Windows run took
// roughly ten seconds before the command step failed), so this is well above the old 15s.
const PROBE_TIMEOUT_MS = 90000;

// Pure decision over a finished probe run -- exported so a smoke test can exercise every branch
// without spawning Codex. `token` is a random value that appears ONLY in the probe file, never in
// the prompt, so Codex can report it only by actually running a command that reads the file.
export function evaluateProbeResult(result, token) {
  if (result.error) {
    return { viable: false, detail: redactSecrets(result.error.message) };
  }

  const stdout = result.stdout ?? "";
  const combined = redactSecrets(`${stdout}\n${result.stderr ?? ""}`).trim();

  if (result.status !== 0) {
    return { viable: false, detail: combined.slice(0, 500) || `exit ${result.status}` };
  }

  // Exit 0 is not proof: on Windows with Codex 0.162.1 a sandbox that cannot start a process
  // still exits 0 and only says so in its final message (issue #545). Requiring the token is what
  // closes that gap (issue #549).
  if (!stdout.includes(token)) {
    return {
      viable: false,
      detail:
        "the read-only sandbox exited 0 but Codex could not read the probe file by running a command" +
        ` (its answer: ${redactSecrets(stdout.trim()).slice(0, 300) || "empty"})`
    };
  }

  return { viable: true, detail: "read-only sandbox ran a command and read the probe file" };
}

// Actually attempts a read-only sandboxed Codex call that must run a command, rather than assuming
// sandbox modes work (scope-expansion gap #5) -- on Windows, Codex's read-only/workspace-write
// sandbox fails to start any process (see plugin-devkit's KNOWN_ISSUES.md), leaving
// danger-full-access as the only mode that ran on the versions tested. Callers must report the
// result explicitly either way; never fall back to danger-full-access silently (scope-expansion
// gap #4). The probe runs in a throwaway temp directory, not the caller's workspace.
export function checkSandboxViability() {
  const probeDir = fs.mkdtempSync(path.join(os.tmpdir(), "cdx-probe-"));
  try {
    const token = crypto.randomBytes(8).toString("hex");
    fs.writeFileSync(path.join(probeDir, "probe.txt"), `${token}\n`, "utf8");

    // Pipe the prompt via stdin rather than positionally -- a multi-word positional argument gets
    // tokenized by Codex's own arg parser (the same gotcha documented in
    // codex-prompt-protocol/references/cli-reference.md), which surfaced as a real
    // "unexpected argument 'with' found" failure during Phase 5 testing.
    const result = runCommand(
      "codex",
      ["exec", "--sandbox", "read-only", "--skip-git-repo-check"],
      {
        cwd: probeDir,
        input:
          "Run one shell command that prints the contents of the file probe.txt in the current directory, " +
          "then reply with exactly that file's contents and nothing else.",
        timeout: PROBE_TIMEOUT_MS
      }
    );

    return evaluateProbeResult(result, token);
  } finally {
    fs.rmSync(probeDir, { recursive: true, force: true });
  }
}
