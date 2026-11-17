#!/usr/bin/env node
// Run one optional reviewer (agy, pi or devin) on an instruction file and a diff, with no tools and the
// review content inline, and print codex-kit's findings envelope (exit 0) or a typed failure
// { ok: false, category, detail } (exit 2). A usage error prints the same failure shape with category
// "usage" and exits 1.
//
// Linux and macOS only: on Windows it refuses with "unsupported_platform" before writing anything.
// Gates, in order, before anything is sent: codex-kit present and safe to import; vendor enabled in the
// untracked local file (and, for pi, a caller --model the local file allows); secret-named paths
// (target list and diff headers) confirmed by the caller; no single argument over the size cap; vendor CLI
// on PATH. A real run also refuses an unprobed devin or agy version before sending. The contract is
// documented in the review-adapter-dispatch skill.
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadCodexKit, CodexKitUnavailable, ownedAndPrivate } from "./rva-codex-kit.mjs";
import { loadConfig, devSiblingOptIn, MODEL_PATTERN } from "./rva-config.mjs";
import { runVendor, killActiveGroups } from "./rva-run.mjs";
import { VENDORS, PROBED_VERSIONS } from "./rva-vendors.mjs";

const VALUE_FLAGS = new Set(["vendor", "reviewer-type", "dispatch-id", "instruction-file", "diff-file", "target-paths-file", "cwd", "model", "timeout-ms"]);
const BOOLEAN_FLAGS = new Set(["secret-paths-confirmed", "dry-run"]);
const REQUIRED = ["vendor", "reviewer-type", "dispatch-id", "instruction-file", "diff-file", "target-paths-file", "cwd"];
const MAX_INPUT_FILE_BYTES = 8 * 1024 * 1024;
// Linux caps a single command-line argument at 128 KiB. No adapter puts the review content on the command
// line any more (every vendor reads it from a file), so this is a backstop for a future adapter that does.
const MAX_ARGUMENT_BYTES = 120_000;
const VERSION_TIMEOUT_MS = 15_000;

class Failure extends Error {
  constructor(category, detail, exitCode = 2) {
    super(detail);
    this.category = category;
    this.exitCode = exitCode;
  }
}

function usage(detail) {
  return new Failure("usage", detail, 1);
}

export function parseArgs(argv) {
  const options = {};
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!/^--[a-z-]+$/.test(token)) throw usage(`unexpected argument at position ${i + 1}`);
    const name = token.slice(2);
    if (Object.hasOwn(options, name)) throw usage(`--${name} given twice`);
    if (BOOLEAN_FLAGS.has(name)) {
      options[name] = true;
    } else if (VALUE_FLAGS.has(name)) {
      const value = argv[i + 1];
      if (value === undefined || value.startsWith("--")) throw usage(`--${name} needs a value`);
      options[name] = value;
      i += 1;
    } else {
      throw usage(`unknown flag --${name}`);
    }
  }
  for (const name of REQUIRED) {
    if (!Object.hasOwn(options, name)) throw usage(`--${name} is required`);
  }
  return options;
}

// Read a caller-supplied input file without following a final symlink or blocking on a FIFO, and only
// when the file and its directory belong to the current user and nobody else can write them: the
// dispatcher sends this content to a vendor, so it must come from the caller's own private files.
function readRegularFile(file, label) {
  let fd;
  try {
    fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NONBLOCK | (fs.constants.O_NOFOLLOW ?? 0));
  } catch {
    throw usage(`${label} cannot be opened (missing, or a symbolic link)`);
  }
  try {
    const stat = fs.fstatSync(fd);
    if (!stat.isFile()) throw usage(`${label} is not a regular file`);
    if (stat.size > MAX_INPUT_FILE_BYTES) throw usage(`${label} is larger than 8 MiB`);
    if (!ownedAndPrivate(stat) || !ownedAndPrivate(fs.statSync(path.dirname(fs.realpathSync(file))))) {
      throw usage(`${label} or its directory is not owned by you, or is writable by others`);
    }
    const buffer = Buffer.alloc(stat.size);
    let read = 0;
    while (read < stat.size) {
      const n = fs.readSync(fd, buffer, read, stat.size - read, read);
      if (n === 0) break;
      read += n;
    }
    return buffer.subarray(0, read).toString("utf8");
  } finally {
    fs.closeSync(fd);
  }
}

function readTargetPaths(text, api, repoRoot) {
  const body = text.endsWith("\n") ? text.slice(0, -1) : text;
  if (body === "") throw usage("--target-paths-file is empty: no reviewable changes");
  const entries = body.split("\n");
  for (const entry of entries) {
    if (!api.isValidPathToken(entry)) throw usage("a target path entry is empty, padded or has characters outside [A-Za-z0-9._/-]");
    if (!api.isWithin(path.resolve(repoRoot, entry), repoRoot)) throw usage("a target path resolves outside --cwd");
  }
  return entries;
}

// Every file path the diff's own headers name (diff --git, ---/+++, rename/copy from/to), read with hunk
// line counting so a removed line that happens to start with "-- a/" is never taken for a header. The
// dispatcher refuses a diff that names a file missing from the target list: otherwise a deleted file or
// the old side of a rename could be sent without passing the secret-name gate.
export function diffHeaderPaths(diff) {
  const paths = new Set();
  let oldLeft = 0;
  let newLeft = 0;
  const lines = diff.split("\n");
  if (lines.at(-1) === "") lines.pop();
  for (const line of lines) {
    if (oldLeft > 0 || newLeft > 0) {
      const mark = line[0];
      // A line that would take its own side below zero means the hunk is shorter than its header says,
      // so whatever follows could be a header hidden inside the hunk: refuse rather than guess.
      if (mark === " " || line === "") {
        if (oldLeft < 1 || newLeft < 1) return { error: "a hunk has more lines than its @@ header says" };
        oldLeft -= 1;
        newLeft -= 1;
      } else if (mark === "-") {
        if (oldLeft < 1) return { error: "a hunk has more lines than its @@ header says" };
        oldLeft -= 1;
      } else if (mark === "+") {
        if (newLeft < 1) return { error: "a hunk has more lines than its @@ header says" };
        newLeft -= 1;
      } else if (mark !== "\\") {
        return { error: "a hunk has fewer lines than its @@ header says" };
      }
      continue;
    }
    const hunk = /^@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@/.exec(line);
    if (hunk) {
      oldLeft = hunk[1] === undefined ? 1 : Number(hunk[1]);
      newLeft = hunk[2] === undefined ? 1 : Number(hunk[2]);
      continue;
    }
    let match = /^diff --git a\/(\S+) b\/(\S+)$/.exec(line);
    if (match) {
      paths.add(match[1]);
      paths.add(match[2]);
      continue;
    }
    if (line.startsWith("diff --git ")) return { error: "a diff --git header has a quoted or unparsable path" };
    match = /^(?:---|\+\+\+) (.*)$/.exec(line);
    if (match) {
      const value = match[1].replace(/\t.*$/, "");
      if (value === "/dev/null") continue;
      const side = /^[ab]\/(.+)$/.exec(value);
      if (!side) return { error: "a ---/+++ header path has no a/ or b/ prefix" };
      paths.add(side[1]);
      continue;
    }
    match = /^(?:rename|copy) (?:from|to) (.*)$/.exec(line);
    if (match) paths.add(match[1]);
  }
  if (oldLeft > 0 || newLeft > 0) return { error: "the diff ends inside a hunk" };
  if (paths.size === 0) return { error: "the diff names no file in a diff --git or ---/+++ header" };
  return { paths: [...paths] };
}

function gitToplevel(dir) {
  try {
    return fs.realpathSync(execFileSync("git", ["-C", dir, "rev-parse", "--show-toplevel"], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"], timeout: 10_000 }).trim());
  } catch {
    return null;
  }
}

function onPath(binary, repoRoot) {
  for (const dir of (process.env.PATH ?? "").split(path.delimiter)) {
    // A relative entry (".", "bin") would resolve against the reviewed checkout.
    if (!dir || !path.isAbsolute(dir)) continue;
    const candidate = path.join(dir, binary);
    try {
      const stat = fs.statSync(candidate);
      fs.accessSync(candidate, fs.constants.X_OK);
      // A binary inside the reviewed checkout (an absolute bin/ on PATH, from direnv for example) is the
      // reviewed branch's own code: refuse it rather than run it with the diff.
      if (stat.isFile() && !isInside(fs.realpathSync(candidate), repoRoot)) return candidate;
    } catch {
      // Not here; keep looking.
    }
  }
  return null;
}

function isInside(file, dir) {
  return file === dir || file.startsWith(dir + path.sep);
}

function findingsSchema(api) {
  const props = api.ENVELOPE_SCHEMA.properties;
  return {
    type: "object",
    additionalProperties: false,
    required: ["findings", "verdict", "inspection_limits"],
    properties: { findings: props.findings, verdict: props.verdict, inspection_limits: props.inspection_limits }
  };
}

function summarizeArgs(args) {
  return args.map((arg) => (arg.length > 200 ? `<${Buffer.byteLength(arg)} bytes>` : arg));
}

async function cliVersion(binary, cwd, env, timeoutMs) {
  // The probe counts against the run's budget, so it never waits longer than that budget.
  const run = await runVendor({ command: binary, args: ["--version"], cwd, env, timeoutMs: Math.min(VERSION_TIMEOUT_MS, timeoutMs) });
  const line = (run.stdout || run.stderr).split("\n").find((l) => l.trim()) ?? "";
  return /^[\w .()+:/-]{1,80}$/.test(line.trim()) ? line.trim() : "unknown";
}

async function dispatch(options, runDir) {
  const vendorName = options.vendor;
  if (!Object.hasOwn(VENDORS, vendorName)) throw usage("--vendor must be agy, pi or devin");
  const vendor = VENDORS[vendorName];

  let cwdReal;
  try {
    cwdReal = fs.realpathSync(options.cwd);
  } catch {
    throw usage("--cwd does not exist");
  }
  // The allow-list is read from --cwd, so --cwd must be a repository's own root, not any directory.
  const repoRoot = gitToplevel(cwdReal);
  if (repoRoot !== cwdReal) throw usage("--cwd must be the top-level directory of a git repository");

  let loaded;
  try {
    loaded = await loadCodexKit({ devSibling: devSiblingOptIn(repoRoot) });
  } catch (error) {
    if (error instanceof CodexKitUnavailable) throw new Failure("codex_kit_unavailable", error.message);
    throw new Failure("codex_kit_unavailable", "codex-kit could not be imported");
  }
  const { api } = loaded;

  if (!api.isValidToken(options["reviewer-type"])) throw usage("--reviewer-type must match [A-Za-z0-9._-]{1,64}");
  if (!api.isValidToken(options["dispatch-id"])) throw usage("--dispatch-id must match [A-Za-z0-9._-]{1,64}");

  const instructionFile = path.resolve(repoRoot, options["instruction-file"]);
  const instructions = readRegularFile(instructionFile, "--instruction-file");
  const diff = readRegularFile(path.resolve(repoRoot, options["diff-file"]), "--diff-file");
  if (diff.trim() === "") throw usage("--diff-file is empty: no reviewable changes");
  if (diff.includes("\0") || instructions.includes("\0")) throw usage("--diff-file or --instruction-file contains a NUL byte");
  const targetPaths = readTargetPaths(readRegularFile(path.resolve(repoRoot, options["target-paths-file"]), "--target-paths-file"), api, repoRoot);
  if (targetPaths.some((entry) => api.isWithin(fs.realpathSync(instructionFile), path.resolve(repoRoot, entry)))) {
    throw usage("--instruction-file lies inside a target path; reviewer instructions must come from outside the reviewed change");
  }
  const headers = diffHeaderPaths(diff);
  if (headers.error) throw usage(`--diff-file: ${headers.error}`);
  const targetSet = new Set(targetPaths);
  if (headers.paths.some((entry) => !targetSet.has(entry))) {
    throw usage("--diff-file names a file that is not in --target-paths-file; list every changed path, including deleted files and both sides of a rename");
  }

  let config;
  try {
    config = loadConfig(repoRoot, vendorName);
  } catch {
    throw new Failure("dispatcher_error", "the shipped settings file is unreadable or invalid");
  }
  if (!config.enabled) throw new Failure("vendor_not_allowed", `${vendorName}: ${config.reason}`);
  let model = config.model;
  if (options.model !== undefined) {
    if (!MODEL_PATTERN.test(options.model)) throw usage("--model must start with a letter or digit and use only [A-Za-z0-9._/:-]");
    // pi's model picks the company that receives the diff, and how pi resolves an id to a provider is not
    // pinned down, so a caller's --model must be exactly the configured model or one the untracked local
    // file lists in vendors.pi.models.
    if (vendorName === "pi" && options.model !== config.model && !config.allowedModels.includes(options.model)) {
      throw new Failure("vendor_not_allowed", "pi: --model is neither the configured model nor listed in vendors.pi.models in the untracked local file");
    }
    model = options.model;
  }
  if (!model) throw usage(`no model configured for ${vendorName}`);
  let timeoutMs = config.timeoutMs;
  if (options["timeout-ms"] !== undefined) {
    if (!/^[1-9][0-9]{0,8}$/.test(options["timeout-ms"])) throw usage("--timeout-ms must be a positive integer in plain digits");
    const requested = Number(options["timeout-ms"]);
    // A request above the configured limit is lowered to it, never raised past it.
    timeoutMs = Math.min(requested, config.timeoutMs);
  }

  const secretHits = [...new Set([...targetPaths, ...headers.paths])].filter((entry) => api.matchesSecretFilename(path.basename(entry), true));
  if (secretHits.length > 0 && !options["secret-paths-confirmed"]) {
    throw new Failure("secret_paths_unconfirmed", `${secretHits.length} changed path(s) have secret-like names; the caller must confirm before sending`);
  }

  const files = {
    runDir,
    promptFile: path.join(runDir, "prompt.md"),
    schemaFile: path.join(runDir, "schema.json"),
    traceFile: path.join(runDir, "trace.json")
  };
  fs.writeFileSync(files.schemaFile, JSON.stringify(findingsSchema(api)), { mode: 0o600 });
  const args = vendor.invocation({ model, files, timeoutMs, content: { instructions, diff, targetPaths } });
  const largest = Math.max(...args.map((arg) => Buffer.byteLength(arg)));
  if (largest > MAX_ARGUMENT_BYTES) {
    throw new Failure("input_too_large", `one ${vendorName} argument is ${largest} bytes; the cap for a single argument is ${MAX_ARGUMENT_BYTES}`);
  }

  const recipient = typeof vendor.recipient === "function" ? vendor.recipient(model) : vendor.recipient;
  const binary = onPath(vendor.binary, repoRoot);
  if (!binary) throw new Failure("cli_unavailable", `${vendor.binary} is not on PATH outside the reviewed repository`);

  if (options["dry-run"]) {
    return { ok: true, dryRun: true, vendor: vendorName, recipient, model, reach: vendor.reach, command: [vendor.binary, ...summarizeArgs(args)] };
  }

  const env = vendor.env(model);
  const started = Date.now();
  const version = await cliVersion(binary, runDir, env, timeoutMs);
  // The first version-shaped token must equal the probed version, so 1.5.90, 11.5.9 or a newer CLI that
  // prints "2.0.0 (compat 1.5.9)" does not pass for the probed 1.5.9.
  const versionProbed = /\d+(?:\.\d+)+/.exec(version)?.[0] === PROBED_VERSIONS[vendorName];
  // devin's isolation is a list of denied tool names and agy's rests on its headless refusal: a newer
  // version may add a tool neither covers, so it is refused before the diff is sent unless the local file
  // allows it. pi runs with --no-tools, so an unprobed pi only gets a note.
  if (!versionProbed && vendor.refuseUnprobed && !config.allowUnprobedVersion) {
    throw new Failure("unsupported_cli_version", `${vendorName} version "${version}" differs from the probed ${PROBED_VERSIONS[vendorName]}; nothing was sent (allow it with allow_unprobed_version in the untracked local file)`);
  }
  const remaining = timeoutMs - (Date.now() - started);
  if (remaining <= 0) throw new Failure("timeout", `${vendor.binary} --version used the whole ${timeoutMs} ms budget; nothing was sent`);
  const run = await runVendor({ command: binary, args, cwd: runDir, env, timeoutMs: remaining, stdinFile: vendor.stdin ? files.promptFile : undefined });
  if (run.stdinError) throw new Failure("dispatcher_error", `the prompt file for ${vendorName} could not be opened; nothing was sent`);
  if (run.spawnError) throw new Failure("cli_unavailable", `${vendor.binary} could not be started`);
  if (run.timedOut) throw new Failure("timeout", `${vendorName} did not finish within ${timeoutMs} ms; the diff was already sent`);
  if (run.code !== 0) {
    const how = run.code === null ? `was killed by ${run.signal ?? "a signal"}` : `exited ${run.code}`;
    // Redact the whole stream first: truncating first could cut a secret in half and hide it from redaction.
    throw new Failure("non_zero_exit", `${vendorName} ${how}: ${api.redactSecrets(run.stderr).slice(-500)}`);
  }

  const extracted = vendor.extract(run);
  if (extracted.error === "tool_denied") throw new Failure("tool_denied", `${vendorName} tried a refused tool and returned no findings; the diff was already sent`);
  if (extracted.error) throw new Failure(extracted.error, `${vendorName} returned no usable findings block`);

  // A missing nullable `components` key means "single-file finding"; codex's strict schema wants it
  // present as null, which a free-text vendor often leaves out. Nothing else is filled in.
  if (Array.isArray(extracted.value?.findings)) {
    for (const finding of extracted.value.findings) {
      if (finding && typeof finding === "object" && !Object.hasOwn(finding, "components")) finding.components = null;
    }
  }
  const violation = api.findSchemaViolation(extracted.value, findingsSchema(api));
  if (violation) throw new Failure("schema_validation_failure", `${vendorName} returned findings that do not match the envelope schema`);

  const envelope = {
    contract_version: "1",
    dispatch: { id: options["dispatch-id"], reviewer: options["reviewer-type"], backend: vendorName, target_paths: targetPaths },
    provenance: { provider: recipient, model, cli_version: version, execution_profile: "reviewadapters-no-tools" },
    findings: extracted.value.findings,
    verdict: extracted.value.verdict,
    inspection_limits: [...extracted.value.inspection_limits]
  };
  if (!versionProbed) {
    envelope.inspection_limits.push(`${vendorName} version "${version}" differs from the probed ${PROBED_VERSIONS[vendorName]}; its isolation flags were not re-verified`);
  }
  const note = vendor.completionNote?.(files);
  if (note) envelope.inspection_limits.push(note);
  if (api.findSchemaViolation(envelope, api.ENVELOPE_SCHEMA)) throw new Failure("schema_validation_failure", "the assembled envelope does not match codex-kit's schema");
  const semantic = api.semanticallyValidate(envelope, { targetPaths, dispatchId: options["dispatch-id"], reviewerType: options["reviewer-type"], repoRoot });
  if (!semantic.ok) throw new Failure(semantic.category, semantic.detail);
  return envelope;
}

function printFailure(failure) {
  process.stdout.write(`${JSON.stringify({ ok: false, category: failure.category, detail: failure.message })}\n`);
}

export async function main(argv) {
  let runDir;
  // On SIGINT/SIGTERM, kill the vendor's process group and remove the run directory before exiting,
  // instead of leaving both behind.
  const onSignal = (signal) => {
    killActiveGroups();
    if (runDir) fs.rmSync(runDir, { recursive: true, force: true });
    printFailure(new Failure("dispatcher_error", `interrupted by ${signal}; the diff may already have been sent`));
    process.exit({ SIGINT: 130, SIGTERM: 143, SIGHUP: 129 }[signal]);
  };
  const signals = ["SIGINT", "SIGTERM", "SIGHUP"];
  for (const signal of signals) process.once(signal, onSignal);
  try {
    const options = parseArgs(argv);
    // The timeout kills the vendor's process group, which Windows does not have: a hung vendor would never
    // be stopped. Refuse before anything is written or sent.
    if (process.platform === "win32") throw new Failure("unsupported_platform", "the dispatcher runs on Linux and macOS only (its timeout needs POSIX process groups); nothing was sent");
    runDir = fs.mkdtempSync(path.join(os.tmpdir(), "rva-run-"));
    fs.chmodSync(runDir, 0o700);
    const result = await dispatch(options, runDir);
    process.stdout.write(`${JSON.stringify(result)}\n`);
    return 0;
  } catch (error) {
    const failure = error instanceof Failure ? error : new Failure("dispatcher_error", "the dispatcher failed unexpectedly");
    printFailure(failure);
    return failure.exitCode;
  } finally {
    for (const signal of signals) process.removeListener(signal, onSignal);
    if (runDir) fs.rmSync(runDir, { recursive: true, force: true });
  }
}

// fileURLToPath decodes the URL; URL.pathname would keep %20 and other escapes, so a plugin installed
// under a path with a space or non-ASCII character would never run.
function isMainModule() {
  try {
    return Boolean(process.argv[1]) && fs.realpathSync(process.argv[1]) === fs.realpathSync(fileURLToPath(import.meta.url));
  } catch {
    return false;
  }
}

if (isMainModule()) {
  main(process.argv.slice(2)).then((code) => {
    process.exitCode = code;
  });
}
