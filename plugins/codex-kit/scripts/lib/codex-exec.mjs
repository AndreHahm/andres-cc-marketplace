import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

// Component #17 — the reusable codex-exec invocation primitive (promoted out
// of internal-reference-only status per scope-expansion gap #1). Ported from
// Wave 3's codex-exec skill's documented behavior: stdin piping (never
// positional), --output-schema/--output-last-message, the stdin-non-TTY hang
// fix, and force-backgrounded-vs-hard-killed timeout handling.
//
// Used by component #18 (codex-review-bridge) and available to any other
// codex-kit component that needs a synchronous, schema-validated codex exec
// call rather than the broker/app-server RPC path.

export const FAILURE_CATEGORIES = Object.freeze({
  CLI_UNAVAILABLE: "cli_unavailable",
  AUTH_UNAVAILABLE: "auth_unavailable",
  UNSUPPORTED_CLI_VERSION: "unsupported_cli_version",
  ISOLATION_PROFILE_UNAVAILABLE: "isolation_profile_unavailable",
  TIMEOUT: "timeout",
  NON_ZERO_EXIT: "non_zero_exit",
  MISSING_FINAL_MESSAGE: "missing_final_message",
  INVALID_JSON: "invalid_json",
  SCHEMA_VALIDATION_FAILURE: "schema_validation_failure",
  SEMANTIC_VALIDATION_FAILURE: "semantic_validation_failure",
  INCOMPLETE_INSPECTION: "incomplete_inspection"
});

function typedFailure(category, detail) {
  return { ok: false, category, detail };
}

function makeScratchFiles(dispatchId) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), `codex-kit-exec-${dispatchId}-`));
  return {
    dir,
    outputSchemaFile: path.join(dir, "schema.json"),
    lastMessageFile: path.join(dir, "last-message.json")
  };
}

/**
 * Run `codex exec` synchronously with stdin piping, an explicit sandbox
 * flag, and bounded timeout. Never passes the prompt positionally.
 *
 * @param {object} opts
 * @param {string} opts.prompt - prompt text, piped via stdin
 * @param {object} opts.schema - JSON Schema object the response must match
 * @param {number} [opts.timeoutMs=240000]
 * @param {string} [opts.cwd]
 * @param {"read-only"|"workspace-write"|"danger-full-access"} opts.sandbox - always explicit, never omitted
 * @param {string} [opts.dispatchId]
 * @returns {Promise<{ok: true, data: object} | {ok: false, category: string, detail: string}>}
 */
export function runCodexExec({ prompt, schema, timeoutMs = 240000, cwd, sandbox, dispatchId = `d${Date.now().toString(36)}` }) {
  if (!sandbox) {
    throw new Error("runCodexExec requires an explicit sandbox mode — never omit it (scope-expansion gap #4).");
  }

  const scratch = makeScratchFiles(dispatchId);

  return new Promise((resolve) => {
    let settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      cleanup();
      resolve(result);
    };
    const cleanup = () => {
      try {
        fs.rmSync(scratch.dir, { recursive: true, force: true });
      } catch {
        // best-effort cleanup
      }
    };

    try {
      fs.writeFileSync(scratch.outputSchemaFile, JSON.stringify(schema, null, 2), "utf8");
    } catch (error) {
      return finish(typedFailure(FAILURE_CATEGORIES.NON_ZERO_EXIT, `Failed writing scratch schema file: ${error.message}`));
    }

    const args = [
      "exec",
      "--sandbox",
      sandbox,
      "--output-schema",
      scratch.outputSchemaFile,
      "--output-last-message",
      scratch.lastMessageFile
    ];

    const child = spawn("codex", args, { cwd, stdio: ["pipe", "pipe", "pipe"] });

    const timer = setTimeout(() => {
      child.kill("SIGTERM");
      finish(typedFailure(FAILURE_CATEGORIES.TIMEOUT, `codex exec exceeded ${timeoutMs}ms`));
    }, timeoutMs);

    let stderr = "";
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });

    child.on("error", (error) => {
      clearTimeout(timer);
      if (error.code === "ENOENT") {
        return finish(typedFailure(FAILURE_CATEGORIES.CLI_UNAVAILABLE, "codex binary not found on PATH"));
      }
      finish(typedFailure(FAILURE_CATEGORIES.NON_ZERO_EXIT, error.message));
    });

    child.on("close", (code) => {
      clearTimeout(timer);
      if (code !== 0) {
        if (/not authenticated|OPENAI_API_KEY/i.test(stderr)) {
          return finish(typedFailure(FAILURE_CATEGORIES.AUTH_UNAVAILABLE, stderr.trim().slice(0, 500)));
        }
        if (/unknown option|unrecognized/i.test(stderr)) {
          return finish(typedFailure(FAILURE_CATEGORIES.UNSUPPORTED_CLI_VERSION, stderr.trim().slice(0, 500)));
        }
        if (/CreateProcessAsUserW|sandbox|permission denied|access is denied/i.test(stderr)) {
          return finish(typedFailure(FAILURE_CATEGORIES.ISOLATION_PROFILE_UNAVAILABLE, stderr.trim().slice(0, 500)));
        }
        return finish(typedFailure(FAILURE_CATEGORIES.NON_ZERO_EXIT, stderr.trim().slice(0, 500) || `exit ${code}`));
      }

      if (!fs.existsSync(scratch.lastMessageFile)) {
        return finish(typedFailure(FAILURE_CATEGORIES.MISSING_FINAL_MESSAGE, "codex exec exited 0 but wrote no --output-last-message file"));
      }

      let raw;
      try {
        raw = fs.readFileSync(scratch.lastMessageFile, "utf8");
      } catch (error) {
        return finish(typedFailure(FAILURE_CATEGORIES.MISSING_FINAL_MESSAGE, error.message));
      }

      let data;
      try {
        data = JSON.parse(raw);
      } catch (error) {
        return finish(typedFailure(FAILURE_CATEGORIES.INVALID_JSON, error.message));
      }

      finish({ ok: true, data });
    });

    // Never positional — always stdin. Redirect an empty stdin close so
    // codex exec never hangs waiting on a non-TTY stdin that's never piped
    // (Wave 3's documented stdin-hang gotcha).
    child.stdin.write(prompt);
    child.stdin.end();
  });
}
