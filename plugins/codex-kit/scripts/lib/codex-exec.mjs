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
  SEMANTIC_VALIDATION_FAILURE: "semantic_validation_failure"
});

function typedFailure(category, detail) {
  return { ok: false, category, detail };
}

// Minimal structural validator against the same `schema` object passed to
// `--output-schema` -- closes a real gap where a parsed response was
// trusted after JSON.parse alone, relying entirely on Codex's own
// enforcement with no local check (SCHEMA_VALIDATION_FAILURE was defined
// but never emitted anywhere). Not a full JSON-Schema implementation --
// checks type, `required` presence, `enum` membership, and recurses into
// `properties`/`items`, which is what this plugin's own schemas actually
// use. Returns the first violation found, or null if the value conforms.
export function findSchemaViolation(value, schema, pathLabel = "$") {
  // Union type (e.g. ["array", "null"] for a nullable-rather-than-absent
  // optional field, required by OpenAI's strict structured-output mode --
  // see ENVELOPE_SCHEMA's `components` field for why "optional" has to be
  // expressed this way instead of omission from `required`). Valid if the
  // value matches `null` (when listed) or any one of the other listed types.
  if (Array.isArray(schema.type)) {
    if (value === null) {
      return schema.type.includes("null") ? null : `${pathLabel}: expected one of [${schema.type.join(", ")}], got null`;
    }
    const matchesSomeType = schema.type.some((t) => t !== "null" && !findSchemaViolation(value, { ...schema, type: t }, pathLabel));
    return matchesSomeType ? null : `${pathLabel}: does not match any type in [${schema.type.join(", ")}]`;
  }
  if (schema.type === "object") {
    if (typeof value !== "object" || value === null || Array.isArray(value)) {
      return `${pathLabel}: expected object, got ${Array.isArray(value) ? "array" : typeof value}`;
    }
    for (const key of schema.required ?? []) {
      if (!Object.prototype.hasOwnProperty.call(value, key)) {
        return `${pathLabel}: missing required property "${key}"`;
      }
    }
    for (const [key, propSchema] of Object.entries(schema.properties ?? {})) {
      if (Object.prototype.hasOwnProperty.call(value, key)) {
        const violation = findSchemaViolation(value[key], propSchema, `${pathLabel}.${key}`);
        if (violation) return violation;
      }
    }
    return null;
  }
  if (schema.type === "array") {
    if (!Array.isArray(value)) {
      return `${pathLabel}: expected array, got ${typeof value}`;
    }
    if (schema.items) {
      for (let i = 0; i < value.length; i += 1) {
        const violation = findSchemaViolation(value[i], schema.items, `${pathLabel}[${i}]`);
        if (violation) return violation;
      }
    }
    return null;
  }
  if (schema.type === "string" && typeof value !== "string") {
    return `${pathLabel}: expected string, got ${typeof value}`;
  }
  if (schema.enum && !schema.enum.includes(value)) {
    return `${pathLabel}: "${value}" is not one of [${schema.enum.join(", ")}]`;
  }
  return null;
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
 * @param {string} [opts.model] - per-call `--model` override; omitted entirely (never a bare `""`)
 *   falls through to whatever `~/.codex/config.toml` resolves. codex-kit never hardcodes a model
 *   name here -- see cli-reference.md's "codex-kit never hardcodes a model name" note. A caller
 *   exposing this to its own environment (e.g. codex-review-bridge reading CODEX_KIT_REVIEW_MODEL)
 *   is responsible for validating the value before passing it through.
 * @returns {Promise<{ok: true, data: object} | {ok: false, category: string, detail: string}>}
 */
export function runCodexExec({ prompt, schema, timeoutMs = 240000, cwd, sandbox, dispatchId = `d${Date.now().toString(36)}`, model }) {
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
    if (model) {
      args.push("--model", model);
    }

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
        // Tail, not head: the banner (version/workdir/sandbox mode) is always
        // printed first, so a 500-char head slice showed only that boilerplate
        // and cut off before the actual failure line every time this was hit
        // in practice -- the real error text is near the end of stderr.
        const detail = stderr.trim().slice(-4000);
        // Checked first, ahead of the sandbox pattern below: a benign
        // "could not find bubblewrap... sandbox prerequisites" fallback
        // warning can appear in stderr ahead of a real 401 auth failure,
        // and its own use of the word "sandbox" previously matched the
        // isolation-profile pattern before this one ever got a chance --
        // misreporting an expired/invalid API key as a sandbox failure.
        if (/not authenticated|OPENAI_API_KEY|401 Unauthorized|Missing bearer/i.test(stderr)) {
          return finish(typedFailure(FAILURE_CATEGORIES.AUTH_UNAVAILABLE, detail));
        }
        if (/unknown option|unrecognized/i.test(stderr)) {
          return finish(typedFailure(FAILURE_CATEGORIES.UNSUPPORTED_CLI_VERSION, detail));
        }
        if (/CreateProcessAsUserW|sandbox|permission denied|access is denied/i.test(stderr)) {
          return finish(typedFailure(FAILURE_CATEGORIES.ISOLATION_PROFILE_UNAVAILABLE, detail));
        }
        return finish(typedFailure(FAILURE_CATEGORIES.NON_ZERO_EXIT, detail || `exit ${code}`));
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

      if (schema) {
        const violation = findSchemaViolation(data, schema);
        if (violation) {
          return finish(typedFailure(FAILURE_CATEGORIES.SCHEMA_VALIDATION_FAILURE, violation));
        }
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
