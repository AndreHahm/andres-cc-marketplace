import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { terminateProcessTree } from "./process.mjs";

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

// Ported pattern set (not the file itself -- codex-kit stays JS per
// require-declared-plugin-language.md) from analysis-kit's
// scripts/redact_secrets.py, applied to the raw Codex stderr tail before it
// is placed in a typed-failure `detail` -- that detail is persisted verbatim
// into CI reports (scripts/marketplace_ci/review.py), and an auth failure's
// stderr has been confirmed to genuinely reach this path (commit 91a6478).
// See redact_secrets.py's own comment for why a generic high-entropy
// catch-all was deliberately left out (over-redacts legitimate path-shaped
// text): this pattern set is intentionally conservative, matching only
// known header/prefix/env-var shapes.
const SECRET_PATTERNS = [
  /\bauthorization\s*[:=]\s*.+$/gim,
  // Requires "bearer" directly followed by a token-length (20+ char)
  // token-shaped run, not just the bare word -- the prior
  // /\bbearer\b\s*[:=]?\s*.+$/gim redacted the rest of ANY line merely
  // containing "bearer" (e.g. prose like "the bearer of this document"),
  // which is both an over-redaction bug and untested for that case.
  /\bbearer\s+[A-Za-z0-9\-._~+/]{20,}=*/gi,
  /^\s*[A-Za-z_][A-Za-z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD|API)[A-Za-z0-9_]*\s*=\s*.+$/gim,
  /\bAKIA[0-9A-Z]{16}\b/g,
  /\bgh[pousr]_[A-Za-z0-9]{36,}\b/g,
  /\bxox[baprs]-[A-Za-z0-9-]+\b/g,
  /\bsk-[A-Za-z0-9-]{20,}\b/g,
  /\bAIza[0-9A-Za-z_-]{35}\b/g,
  /\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*\b/g,
  /-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----/g
];

// Exported so a smoke test can exercise the pattern set directly, matching
// the existing findSchemaViolation export pattern below.
export function redactSecrets(text) {
  let result = text;
  for (const pattern of SECRET_PATTERNS) {
    result = result.replace(pattern, "[REDACTED]");
  }
  return result;
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
    // additionalProperties: false is a real constraint several schemas in
    // this plugin declare specifically to bound what a model can pad its
    // response with -- it was previously declared but never checked here,
    // so an extra, unrequested key survived local validation silently.
    if (schema.additionalProperties === false) {
      const allowed = new Set(Object.keys(schema.properties ?? {}));
      for (const key of Object.keys(value)) {
        if (!allowed.has(key)) {
          return `${pathLabel}: unexpected property "${key}" not permitted by additionalProperties: false`;
        }
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

// --- Windows npm-shim spawning -------------------------------------------
//
// npm-installed CLI tools on Windows (`codex`, and any other global npm
// binary) are `.cmd` shims, not directly-executable `.exe` files.
// `spawn("codex", args, { shell: false })` fails ENOENT because Node's
// CreateProcess-based lookup does not try PATHEXT extensions for a bare
// command name the way a real shell does (confirmed via a live dispatch,
// 2026-08-17: `codex` resolves fine in bash via `which`, but the identical
// bare name fails ENOENT here). Spawning the resolved `.cmd` path directly,
// still with `shell: false`, instead throws a *synchronous* EINVAL -- Node
// refuses to launch a `.bat`/`.cmd` file without going through a shell
// (hardening from CVE-2024-27980: Windows' own CreateProcess silently
// routes any `.cmd` target through `cmd.exe` regardless of what Node does,
// so the arguments must be escaped for cmd.exe's own metacharacter
// grammar, not just for a normal EXE's argv parser -- also confirmed live).
//
// `shell: true` on its own does NOT do this safely: Node builds the actual
// command line for `shell: true` by joining the args with spaces and
// handing it to cmd.exe with no per-argument escaping at all. Confirmed
// live (2026-08-17): `spawn(process.execPath, [scriptPath, "foo & echo
// INJECTED > injected.txt & echo bar"], { shell: true })` actually created
// `injected.txt` -- the embedded `&` was interpreted by cmd.exe as a
// command separator -- and `process.execPath` itself ("C:\Program
// Files\nodejs\node.exe") was silently mis-split on its own space. `args`
// below includes `scratch.outputSchemaFile`/`scratch.lastMessageFile`
// (paths that can legitimately contain a space -- an ordinary Windows
// username with a space is enough, nothing adversarial required) and an
// optional caller-suppliable `model`, so naive `shell: true` is not safe
// for this call site.
//
// The fix (ported from `cross-spawn`, a widely-used, MIT-licensed
// implementation of exactly this problem -- fetched and verified 2026-08-17
// from github.com/moxystudio/node-cross-spawn `lib/util/escape.js` and
// `lib/parse.js`'s `parseNonShell`, not reimplemented from memory): resolve
// the shim's real path ourselves, and if it isn't directly executable
// (extension isn't `.exe`/`.com`), build one fully-escaped command-line
// string and invoke it via `cmd.exe /d /s /c "<escaped command line>"` with
// `windowsVerbatimArguments: true` -- which tells Node not to apply its own
// per-argv-element quoting on top of ours (that would double-escape and
// break it). `escapeWindowsCommand`/`escapeWindowsArgument` below are a
// direct port of cross-spawn's algorithm (itself based on
// https://qntm.org/cmd) -- getting Windows cmd.exe escaping right from
// scratch is a well-documented source of real vulnerabilities, so this
// reuses a battle-tested implementation rather than a fresh one.
const WIN32_META_CHARS = /([()\][%!^"`<>&|;, *?])/g;
const WIN32_DIRECTLY_EXECUTABLE = /\.(?:com|exe)$/i;

function escapeWindowsCommand(command) {
  return command.replace(WIN32_META_CHARS, "^$1");
}

function escapeWindowsArgument(arg) {
  let escaped = String(arg);
  // Sequence of backslashes followed by a double quote: double up all the
  // backslashes and escape the double quote.
  escaped = escaped.replace(/(?=(\\+?)?)\1"/g, '$1$1\\"');
  // Sequence of backslashes followed by the end of the string (which will
  // become a double quote next): double up all the backslashes.
  escaped = escaped.replace(/(?=(\\+?)?)\1$/, "$1$1");
  escaped = `"${escaped}"`;
  escaped = escaped.replace(WIN32_META_CHARS, "^$1");
  return escaped;
}

// `command` must be a bare executable name with no extension and no path
// separators -- every PATH directory is searched for `<command><ext>` for
// each PATHEXT extension in turn, so a name that already carries an
// extension (e.g. "codex.cmd") or a separator never matches, even if that
// exact file exists. Returns the resolved absolute path, or null if
// `command` isn't found anywhere on PATH under any PATHEXT extension.
// Non-Windows platforms never call this -- `codex` is directly executable
// everywhere else.
function resolveWindowsExecutable(command) {
  const pathExt = (process.env.PATHEXT || ".COM;.EXE;.BAT;.CMD").split(";").filter(Boolean);
  const pathDirs = (process.env.PATH || process.env.Path || "").split(path.delimiter).filter(Boolean);
  for (const dir of pathDirs) {
    for (const ext of pathExt) {
      const candidate = path.join(dir, `${command}${ext.toLowerCase()}`);
      if (fs.existsSync(candidate)) return candidate;
    }
  }
  return null;
}

// Builds the { command, args, options } triple to actually spawn. On any
// platform other than win32, returns the inputs unchanged. `resolved: false`
// means `command` wasn't found anywhere on PATH -- the caller should report
// this the same way an ENOENT from a direct spawn attempt would. `platform`
// defaults to `process.platform` but is injectable (same pattern as
// `lib/process.mjs`'s `terminateProcessTree`) so a smoke test can exercise
// the win32 branch on any CI runner, not just a real Windows machine.
function buildSpawnInvocation(command, args, options, platform = process.platform) {
  if (platform !== "win32") {
    return { command, args, options, resolved: true };
  }

  // Defense in depth (flagged by security review, 2026-08-17): every
  // current caller already constrains its own args to a safe charset
  // (bridge-invoke.mjs validates dispatchId/model against
  // ^[A-Za-z0-9._-]{1,64}$; the scratch file paths below can't contain a
  // `"` since Windows itself forbids that character in a filename), so
  // this never actually rejects anything today -- but this module is
  // documented above as a reusable primitive "available to any other
  // codex-kit component," and a future caller might not validate as
  // carefully. `"` is the one character that can defeat the quote-run
  // escaping rule in escapeWindowsArgument if it reaches here already
  // containing cmd.exe-meaningful content the caller expected POSIX-shell
  // semantics for; `\r`/`\n`/NUL aren't neutralized by the meta-char set
  // at all. Reject rather than silently attempt to escape them.
  const unsafeArg = args.find((arg) => /["\r\n\0]/.test(String(arg)));
  if (unsafeArg !== undefined) {
    return { resolved: false, reason: "unsafe_argument", detail: `argument contains a disallowed character (", CR, LF, or NUL): ${JSON.stringify(String(unsafeArg))}` };
  }

  const resolvedPath = resolveWindowsExecutable(command);
  if (!resolvedPath) {
    return { resolved: false, reason: "not_found" };
  }

  if (WIN32_DIRECTLY_EXECUTABLE.test(resolvedPath)) {
    return { command: resolvedPath, args, options: { ...options, shell: false }, resolved: true };
  }

  const commandLine = [escapeWindowsCommand(resolvedPath)].concat(args.map((arg) => escapeWindowsArgument(arg))).join(" ");

  return {
    command: path.join(process.env.SystemRoot || "C:\\Windows", "System32", "cmd.exe"),
    args: ["/d", "/s", "/c", `"${commandLine}"`],
    options: { ...options, shell: false, windowsVerbatimArguments: true },
    resolved: true
  };
}

// Exported so a smoke test can exercise the escaping/resolution logic
// directly, without needing a real npm-shim install on the test machine.
export { escapeWindowsArgument, escapeWindowsCommand, resolveWindowsExecutable, buildSpawnInvocation };

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

    const invocation = buildSpawnInvocation("codex", args, { cwd, stdio: ["pipe", "pipe", "pipe"] });
    if (!invocation.resolved) {
      if (invocation.reason === "unsafe_argument") {
        return finish(typedFailure(FAILURE_CATEGORIES.NON_ZERO_EXIT, invocation.detail));
      }
      return finish(typedFailure(FAILURE_CATEGORIES.CLI_UNAVAILABLE, "codex binary not found on PATH"));
    }
    const child = spawn(invocation.command, invocation.args, invocation.options);

    const timer = setTimeout(() => {
      // On the Windows .cmd-shim path (see buildSpawnInvocation above), the
      // direct child is cmd.exe, not codex -- child.kill() only reaches
      // cmd.exe, leaving the grandchild `codex` process running under
      // whatever --sandbox mode it was given, orphaned the moment
      // finish()'s cleanup() below deletes the scratch dir out from under
      // it. Same hazard lib/app-server.mjs already documents and solves
      // for its own shell:true spawn (see its "Use terminateProcessTree
      // to kill the entire tree" comment) -- flagged by security review,
      // 2026-08-17. terminateProcessTree's taskkill /T /F blocks
      // synchronously, so the tree is dead before finish() runs.
      if (process.platform === "win32") {
        try {
          terminateProcessTree(child.pid);
        } catch {
          // Best-effort -- report the timeout regardless of whether the
          // kill itself succeeded.
        }
      } else {
        child.kill("SIGTERM");
      }
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
      // Same redactSecrets pass as the close-handler's `detail` below -- this
      // detail is persisted into CI reports too (scripts/marketplace_ci/
      // review.py), and error.message can echo back spawn-time context that
      // included user/environment-supplied values.
      finish(typedFailure(FAILURE_CATEGORIES.NON_ZERO_EXIT, redactSecrets(error.message)));
    });

    child.on("close", (code) => {
      clearTimeout(timer);
      if (code !== 0) {
        // Tail, not head: the banner (version/workdir/sandbox mode) is always
        // printed first, so a 500-char head slice showed only that boilerplate
        // and cut off before the actual failure line every time this was hit
        // in practice -- the real error text is near the end of stderr.
        const detail = redactSecrets(stderr).trim().slice(-4000);
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
