import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { terminateProcessTree } from "./cdx-process.mjs";

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

const AUTH_FAILURE_PATTERN = /not authenticated|OPENAI_API_KEY|401 Unauthorized|Missing bearer/i;
const UNSUPPORTED_OPTION_PATTERN = /unknown option|unrecognized/i;
// Concrete sandbox-failure shapes, not the bare words "sandbox" / "permission
// denied" / "access is denied": those also appear in non-isolation errors (an
// API 403 "permission denied for model ...").
export const ISOLATION_FAILURE_PATTERN =
  /CreateProcessAsUserW|\bbwrap\b|landlock|seccomp|sandbox (?:failed|error|denied|unavailable)|failed to (?:set up|create|start)[^\n]{0,200}sandbox|(?:sandbox|bwrap)[^\n]{0,200}(?:permission denied|access is denied)|failed to create unified exec process:\s*helper_/i;

// The slice of stderr the failure patterns are tested against -- not the whole
// stream. Once a session starts, Codex prints a banner ("sandbox: read-only",
// ...) and echoes the full reviewer prompt (which carries the PR diff), so words
// like "sandbox" or "OPENAI_API_KEY" can appear in every failing run, whatever
// the cause (a model at capacity or rejected for the account matched "sandbox"
// and was reported as a sandbox failure -- issue #544). Codex's own cause is on
// its `ERROR:` lines, unindented; the echoed prompt's diff lines are always
// prefixed, so only the unindented ones count -- from anywhere in the stream,
// since output after the error can run past any fixed window. Known, accepted
// residual: the model's own tool output (a file it `cat`s), and probably its own
// streamed narration (unverified), is printed unindented too, so a column-0
// `ERROR:` line inside a file Codex reads can count; that
// existed before issue #545 and only matters when the run also exits non-zero.
// Codex's tracing-log lines (`<ISO-8601 Z timestamp> ERROR <target>: ...`, real
// Windows Codex 0.162.1 stderr, issue #545) are a separate, narrower scope: they
// can copy repo paths and command text, so only specific spawn-failure shapes
// (TRACING_ISOLATION_PATTERN) are read from them, never the bare keywords. The
// same tool-output residual applies to this form: a column-0 tracing-shaped line
// inside a file Codex prints counts too, when the run also exits non-zero.
// With no `ERROR:` line the remaining text may be the echoed prompt, which must
// not decide a category (an echoed `landlock` mention would otherwise trigger the
// privilege-widening isolation fallback), so the default is an empty scope. Only
// positive evidence that nothing was echoed lifts that: no session banner AND a
// short stderr (an argument error is a few lines; an echoed reviewer prompt is
// kilobytes). Relying on the banner alone would fail open the day Codex rewords
// it, so a reworded banner with a long echo still fails closed. Known limit: a
// reworded banner with a prompt under the size cap is read as pre-session.
const PRE_SESSION_MAX_CHARS = 2000;
const TRACING_ERROR_LINE_PATTERN = /^\d{4}-\d{2}-\d{2}T[\d:.]+Z ERROR /;
// Only specific spawn-failure shapes, not the bare landlock/seccomp/bwrap words
// the plain-ERROR scope also accepts, and not "sandbox error/failed/..." either:
// a tracing line can carry a repo path or a command (`rg "sandbox error" src`).
// "unified exec process" alone is generic (fd/pty exhaustion fails the same way), so the `helper_`
// marker of the sandbox helper seen in the one real capture is required; tied to that single sample.
// `CreateProcessAsUserW` alone is not enough either: a tracing line can quote a command that merely
// names the API or even the phrase (`rg "CreateProcessAsUserW failed" docs`), so the real error's
// numeric code must follow it (`CreateProcessAsUserW failed: 1920`, KNOWN_ISSUES.md).
// This stops incidental matches, not a model that deliberately picks a failing command whose text
// contains the exact string: the real control against that is the human gate in front of any
// no-sandbox run (plugin-auditor's second confirmation, cross-model-review's up-front consent).
const TRACING_ISOLATION_PATTERN = /CreateProcessAsUserW failed:\s*\d+|failed to create unified exec process:\s*helper_/i;

// Codex echoes the prompt it was sent, verbatim, into stderr. This process wrote that
// prompt itself, so remove exactly that text first: an `ERROR:` line inside the echoed
// (untrusted) prompt can then neither force nor hide a classification. If Codex ever
// alters the echo, nothing matches and the rules below apply to the unstripped text.
// Line endings are normalized on both sides first: on Windows Codex may echo the prompt
// with CRLF while this process built it with LF, which would otherwise make the strip a no-op.
function withoutPromptEcho(stderr, prompt) {
  const text = stderr.replace(/\r\n/g, "\n");
  const needle = typeof prompt === "string" ? prompt.replace(/\r\n/g, "\n").trim() : "";
  return needle ? text.split(needle).join("") : text;
}

function tracingErrorScope(stderr, prompt = "") {
  return withoutPromptEcho(stderr, prompt)
    .split(/\r?\n/)
    .filter((line) => TRACING_ERROR_LINE_PATTERN.test(line))
    .join("\n");
}

export function failureScope(stderr, prompt = "") {
  const text = withoutPromptEcho(stderr, prompt);
  const errorLines = text.split(/\r?\n/).filter((line) => line.startsWith("ERROR:"));
  if (errorLines.length > 0) {
    return errorLines.join("\n");
  }
  const preSession = !/^OpenAI Codex v\S+/m.test(text) && text.length <= PRE_SESSION_MAX_CHARS;
  return preSession ? text : "";
}

// Auth is checked first, ahead of isolation: a benign "could not find
// bubblewrap... sandbox prerequisites" fallback warning can appear ahead of a
// real 401 auth failure, and its use of the word "sandbox" would otherwise
// misreport an expired/invalid API key as a sandbox failure.
export function classifyNonZeroExit(stderr, prompt = "") {
  const scope = failureScope(stderr, prompt);
  if (AUTH_FAILURE_PATTERN.test(scope)) {
    return FAILURE_CATEGORIES.AUTH_UNAVAILABLE;
  }
  if (UNSUPPORTED_OPTION_PATTERN.test(scope)) {
    return FAILURE_CATEGORIES.UNSUPPORTED_CLI_VERSION;
  }
  if (ISOLATION_FAILURE_PATTERN.test(scope) || TRACING_ISOLATION_PATTERN.test(tracingErrorScope(stderr, prompt))) {
    return FAILURE_CATEGORIES.ISOLATION_PROFILE_UNAVAILABLE;
  }
  return FAILURE_CATEGORIES.NON_ZERO_EXIT;
}

// Ported pattern set (not the file itself -- codex-kit stays JS per
// require-declared-plugin-language.md) from analysis-kit's
// scripts/anls_redact_secrets.py, applied to the raw Codex stderr tail before it
// is placed in a typed-failure `detail` -- that detail is persisted verbatim
// into CI reports (scripts/marketplace_ci/review.py), and an auth failure's
// stderr has been confirmed to genuinely reach this path (commit 91a6478).
// See anls_redact_secrets.py's own comment for why a generic high-entropy
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
  /\bgithub_pat_[A-Za-z0-9_]{22,}\b/g,
  /\bxox[baprs]-[A-Za-z0-9-]+\b/g,
  /\bsk-[A-Za-z0-9-]{20,}\b/g,
  /\bAIza[0-9A-Za-z_-]{35}\b/g,
  /\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*\b/g,
  /-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----/g
];

// The line-anchored dotenv rule above misses an assignment that is not at the
// start of a line, and consuming the rest of a mid-line match would eat
// surrounding prose, so this one replaces only the value and keeps the name
// (group 1). Unlike the line-anchored rule, the noisy words KEY and API must be a
// whole `_`-delimited segment of the name (or part of a known compound such as
// apiKey), so ordinary prose-embedded fields like sortKey=asc are left alone;
// TOKEN, SECRET and PASSWORD may appear anywhere in the name (databasePassword,
// DB_PASSWORD), since they rarely occur in non-secret names. A quoted
// value runs to its closing quote, or to the end of its line when the quote
// is never closed, so a value containing spaces is redacted whole but one stray
// quote cannot swallow the lines after it. The lookahead leaves a value the
// line-anchored rule already replaced alone.
const SECRET_ASSIGNMENT_PATTERN =
  /(\b(?:[A-Za-z0-9_]*(?:TOKEN|SECRET|PASSWORD|PASSWD|APIKEY|ACCESSKEY|AUTHKEY|PRIVATEKEY|SIGNINGKEY)[A-Za-z0-9_]*|(?:[A-Za-z0-9]*_)*(?:KEY|API)(?:_[A-Za-z0-9_]*)?)\s*=\s*)(?!\[REDACTED\])(?:"(?:[^"\\\r\n]|\\[^\r\n]?)*(?:"|(?=[\r\n])|$)|'(?:[^'\\\r\n]|\\[^\r\n]?)*(?:'|(?=[\r\n])|$)|\S+)/gi;

// Exported so a smoke test can exercise the pattern set directly, matching
// the existing findSchemaViolation export pattern below.
export function redactSecrets(text) {
  let result = text;
  for (const pattern of SECRET_PATTERNS) {
    result = result.replace(pattern, "[REDACTED]");
  }
  return result.replace(SECRET_ASSIGNMENT_PATTERN, "$1[REDACTED]");
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
// `lib/cdx-process.mjs`'s `terminateProcessTree`) so a smoke test can exercise
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

// Resolves what `codex` would actually be invoked as, without spawning it --
// used only by runCodexExec's `dryRun` branch below. On win32, delegates to
// buildSpawnInvocation so a dry run resolves through the exact same
// .cmd-shim/cmd.exe-escaping logic a real dispatch would use. On every other
// platform, buildSpawnInvocation always reports resolved: true without
// checking PATH at all -- fine for a real dispatch (a missing binary already
// surfaces correctly via the spawned child's own "error" event, per the
// child.on("error", ...) handler below), but a dry run never spawns anything
// to raise that event, so it needs its own lightweight PATH/executable-bit
// check instead. Not folded into buildSpawnInvocation itself: that would add
// a PATH pre-check to the real (non-dry-run) POSIX dispatch path too, which
// already works correctly today and doesn't need it. `platform` defaults to
// process.platform but is injectable, the same pattern buildSpawnInvocation
// itself already uses, so a smoke test can exercise both branches on any CI
// runner, not just a real Windows machine.
function resolveDryRunInvocation(command, args, cwd, platform = process.platform) {
  if (platform === "win32") {
    return buildSpawnInvocation(command, args, { cwd, stdio: ["pipe", "pipe", "pipe"] }, platform);
  }
  // POSIX PATH search mirrors execvp()'s own semantics, which is what a real
  // (non-dry-run) spawn({cwd}) ultimately resolves through: an empty PATH
  // entry (a leading/trailing/doubled ":") means "search the current
  // directory", and a relative entry resolves against the CHILD's cwd, not
  // this resolving process's own -- a real spawn chdir's into `cwd` before
  // execvp's own PATH search ever runs. The previous version dropped empty
  // entries via .filter(Boolean) and joined a relative `dir` with
  // path.join()+fs.accessSync(), which Node always resolves against
  // process.cwd(), never an arbitrary `cwd` parameter -- both diverged from
  // real dispatch behavior, live-flagged independently by Devin, Codex (with
  // a concrete PATH="." repro), and CodeRabbit (citing Node's own documented
  // child_process PATH/cwd semantics). path.resolve(cwd, dir || ".", command)
  // fixes both: an absolute `dir` still wins outright (path.resolve stops at
  // the last absolute segment), while a relative or empty `dir` resolves
  // against `cwd`.
  //
  // Known, disclosed residual limitation: this does not replicate the OS's
  // own PATH-unset fallback search path (e.g. /usr/bin:/bin on Linux) for
  // the case where process.env.PATH is entirely absent -- that default is
  // platform-specific and not exposed by Node's stdlib, and neither
  // reviewer gave a concrete repro for it (unlike the relative/cwd-mismatch
  // case above). An unset PATH here searches only `cwd` itself, which can
  // diverge from a real dispatch's OS-level default in that narrow case.
  const pathDirs = (process.env.PATH || "").split(path.delimiter);
  for (const dir of pathDirs) {
    const candidate = path.resolve(cwd, dir || ".", command);
    try {
      // isFile() first: X_OK alone only checks permission bits, not file
      // type -- a directory literally named "codex" with the execute bit
      // set (routine, since directories need it for traversal) would
      // otherwise pass this check and be reported as a resolved, invokable
      // command (Devin).
      if (!fs.statSync(candidate).isFile()) continue;
      fs.accessSync(candidate, fs.constants.X_OK);
      return { command: candidate, args, options: { cwd }, resolved: true };
    } catch {
      // Not in this PATH directory -- keep looking.
    }
  }
  return { resolved: false, reason: "not_found" };
}

// Exported for the same smoke-testing reason as the Windows helpers above.
export { resolveDryRunInvocation };

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
 * @param {boolean} [opts.dryRun=false] - when true, builds the real prompt/args and resolves the
 *   `codex` invocation exactly as a real dispatch would, but never spawns it. Returns
 *   `{ok: true, dryRun: true, wouldRun: {...}}` on success, or the same typed failure a real
 *   dispatch would return for a missing binary (`CLI_UNAVAILABLE`) or an unsafe argument
 *   (`NON_ZERO_EXIT`) -- every other failure category (auth, timeout, schema mismatch, ...) can
 *   only occur once Codex actually runs, so a dry run cannot surface those by construction.
 * @returns {Promise<{ok: true, data: object} | {ok: true, dryRun: true, wouldRun: object} | {ok: false, category: string, detail: string}>}
 */
export function runCodexExec({ prompt, schema, timeoutMs = 240000, cwd, sandbox, dispatchId = `d${Date.now().toString(36)}`, model, dryRun = false }) {
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

    if (dryRun) {
      // Default to process.cwd(), matching what a real (non-dry-run) spawn
      // does when `cwd` is omitted (buildSpawnInvocation passes `cwd:
      // undefined` straight through as a spawn option, which Node treats as
      // "inherit the parent's cwd"). runCodexExec's own signature has no
      // default for `cwd` -- omitting it is a documented, legitimate call
      // shape (see this function's JSDoc). Without this, path.resolve(cwd,
      // ...) below throws synchronously on `undefined` (live-flagged, round
      // 2 of PR review): the throw happens outside any try/catch, so it
      // never reaches finish()'s own cleanup -- the scratch schema
      // directory this function already created is left behind, and the
      // caller sees a generic top-level non_zero_exit instead of a properly
      // attributed typed failure.
      const resolvedCwd = cwd || process.cwd();
      const dryInvocation = resolveDryRunInvocation("codex", args, resolvedCwd);
      if (!dryInvocation.resolved) {
        if (dryInvocation.reason === "unsafe_argument") {
          return finish(typedFailure(FAILURE_CATEGORIES.NON_ZERO_EXIT, dryInvocation.detail));
        }
        return finish(typedFailure(FAILURE_CATEGORIES.CLI_UNAVAILABLE, "codex binary not found on PATH"));
      }
      return finish({
        ok: true,
        dryRun: true,
        wouldRun: {
          command: dryInvocation.command,
          args: dryInvocation.args,
          cwd: resolvedCwd,
          sandbox,
          model: model || null,
          timeoutMs,
          dispatchId,
          promptLength: prompt.length,
          prompt: redactSecrets(prompt)
        }
      });
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
      // it. Same hazard lib/cdx-app-server.mjs already documents and solves
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
        const category = classifyNonZeroExit(stderr, prompt);
        return finish(typedFailure(category, category === FAILURE_CATEGORIES.NON_ZERO_EXIT ? detail || `exit ${code}` : detail));
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
