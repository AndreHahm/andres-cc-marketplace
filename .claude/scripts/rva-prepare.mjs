#!/usr/bin/env node
// Prepare the input for one rva-review-diff run, or clean it up afterwards.
//
//   rva-prepare.mjs --cwd <dir> [--range <git-range>]   -> JSON with the files rva-dispatch.mjs needs
//   rva-prepare.mjs --cleanup <dir>                     -> removes a directory this script created
//
// Runs git with fixed argument lists only, so the command needs no general git or Write grant. The
// diff covers tracked changes (staged and unstaged against HEAD, or the given range); untracked files
// are not included. Renames are shown as a deletion plus an addition, so every path whose content the
// diff carries (deleted files and both sides of a rename included) is in the changed-file list and
// passes the secret-name check. A changed path outside [A-Za-z0-9._/-] fails the run: its content
// would otherwise travel without being listed. The reviewer instructions come from this plugin's own
// assets, never from the repository under review.
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadCodexKit, CodexKitUnavailable, ownedAndPrivate } from "./rva-codex-kit.mjs";
import { devSiblingOptIn, findBinary, gitEnv, GIT_SAFE_OPTIONS, isInside, realPath, enclosingRepoRoot } from "./rva-config.mjs";

const PLUGIN_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const PREFIX = "rva-prep-";
const REF = "[A-Za-z0-9._/~^@{}-]+";
// Fixed diff options: no external diff driver or textconv filter from the repository's config runs, no
// rename pairing, and the a/ b/ prefixes the dispatcher's header check expects whatever diff.noprefix,
// diff.mnemonicPrefix or diff.relative say.
const DIFF_OPTIONS = ["--no-color", "--no-ext-diff", "--no-textconv", "--no-renames", "--no-relative", "--submodule=short", "--src-prefix=a/", "--dst-prefix=b/"];
// The command interpolates the printed paths into shell commands inside double quotes, so a path that
// could end the quote or expand there is refused before anything is created.
const SHELL_UNSAFE = /["$`\\\n\r]/;
const MAX_DIFF_BYTES = 8 * 1024 * 1024;
const MAX_INSTRUCTIONS_BYTES = 64 * 1024;
const RANGE_PATTERN = new RegExp(`^${REF}(\\.{2,3}${REF})?$`);

function fail(detail, code = 1) {
  process.stdout.write(`${JSON.stringify({ ok: false, detail })}\n`);
  return code;
}

function git(gitBin, repo, args) {
  return execFileSync(gitBin, [...GIT_SAFE_OPTIONS, "-C", repo, ...args], { encoding: "utf8", env: gitEnv(), maxBuffer: 64 * 1024 * 1024, timeout: 60_000 });
}

function cleanup(dir) {
  let real;
  try {
    real = fs.realpathSync(dir);
  } catch {
    return fail("the directory does not exist");
  }
  const tmp = fs.realpathSync(os.tmpdir());
  const stat = fs.lstatSync(real);
  if (path.dirname(real) !== tmp || !path.basename(real).startsWith(PREFIX) || !stat.isDirectory() || stat.uid !== process.getuid()) {
    return fail("refusing to remove a directory this script did not create");
  }
  fs.rmSync(real, { recursive: true, force: true });
  process.stdout.write(`${JSON.stringify({ ok: true, removed: real })}\n`);
  return 0;
}

async function prepare(cwd, range) {
  if (range !== undefined && (range.startsWith("-") || !RANGE_PATTERN.test(range))) return fail("the range is not a plain git range");
  let cwdReal;
  try {
    cwdReal = realPath(cwd);
  } catch {
    return fail("--cwd does not exist");
  }
  // Never a git from a relative PATH entry or from inside the reviewed checkout (see findBinary). The
  // checkout's root is found by its .git entry, without running git, since --cwd may be a subdirectory.
  const untrustedRoot = enclosingRepoRoot(cwdReal);
  if (!untrustedRoot) return fail("--cwd is not inside a git repository");
  const gitBin = findBinary("git", untrustedRoot);
  if (!gitBin) return fail("git is not on PATH outside the reviewed checkout");
  let repo;
  try {
    repo = realPath(git(gitBin, cwdReal, ["rev-parse", "--show-toplevel"]).trim());
  } catch {
    return fail("--cwd is not inside a git repository");
  }
  if (isInside(realPath(gitBin), repo)) return fail("git is not on PATH outside the reviewed checkout");
  // The reviewer instructions go ahead of the fixed data-only sentence, so they must not come from the
  // checkout under review. The command's step 1 refuses, before any script runs, an empty plugin root or
  // one under $PWD. An in-repository root elsewhere (above $PWD or beside it) is covered only by this check,
  // and only while this script is unchanged: a branch that rewrites it can drop the check.
  const instructions = path.join(PLUGIN_ROOT, "assets", "rva-review-instructions.md");
  let instructionsReal;
  try {
    instructionsReal = realPath(instructions);
  } catch {
    return fail("the plugin's reviewer instructions file is missing");
  }
  if (isInside(realPath(PLUGIN_ROOT), repo) || isInside(instructionsReal, repo)) {
    return fail("this plugin runs from inside the repository under review, so its reviewer instructions could be part of the change; run the command from an installed copy of the plugin");
  }
  // Read once, from one descriptor opened without following a link, and only from a regular file owned
  // by this user that nobody else can write (group write only for the user's private group, the same
  // rule as codex-kit's files), so the checked file is the one copied.
  let instructionText;
  let fd;
  try {
    // O_NONBLOCK: opening a FIFO would otherwise wait for a writer before the regular-file check runs.
    fd = fs.openSync(instructionsReal, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
    const stat = fs.fstatSync(fd);
    if (!stat.isFile() || !ownedAndPrivate(stat)) {
      return fail("the plugin's reviewer instructions file is not a regular file owned by you and writable only by you");
    }
    if (stat.size > MAX_INSTRUCTIONS_BYTES) return fail("the plugin's reviewer instructions file is larger than 64 KiB");
    instructionText = fs.readFileSync(fd, "utf8");
  } catch {
    return fail("the plugin's reviewer instructions file could not be read");
  } finally {
    if (fd !== undefined) fs.closeSync(fd);
  }
  const rangeArgs = range === undefined ? ["HEAD"] : [range];
  let diff;
  let names;
  try {
    diff = git(gitBin, repo, ["diff", ...DIFF_OPTIONS, ...rangeArgs, "--"]);
    names = git(gitBin, repo, ["diff", "--name-only", "-z", "--no-renames", "--no-relative", ...rangeArgs, "--"]).split("\0").filter(Boolean);
  } catch {
    return fail("git could not produce the diff for that range");
  }
  if (diff.trim() === "" || names.length === 0) return fail("no reviewable changes: the diff is empty");
  if (Buffer.byteLength(diff) > MAX_DIFF_BYTES) return fail("the diff is larger than 8 MiB, the dispatcher's input limit");
  const tmp = fs.realpathSync(os.tmpdir());
  if (SHELL_UNSAFE.test(repo) || SHELL_UNSAFE.test(tmp)) {
    return fail("the repository path or the temp directory contains a quote, $, backtick, backslash or newline");
  }
  let api;
  try {
    ({ api } = await loadCodexKit({ devSibling: devSiblingOptIn(repo) }));
  } catch (error) {
    return fail(error instanceof CodexKitUnavailable ? `codex-kit unavailable: ${error.message}` : "codex-kit could not be imported");
  }
  const unsupported = names.filter((name) => !api.isValidPathToken(name));
  if (unsupported.length > 0) {
    return fail(`${unsupported.length} changed file(s) have names outside [A-Za-z0-9._/-]; their content cannot be listed for review, so nothing was prepared`);
  }
  const secretPaths = names.filter((name) => api.matchesSecretFilename(path.basename(name), true));
  // Built from the resolved temp path that was just checked, so every printed path passed the check.
  const dir = fs.mkdtempSync(path.join(tmp, PREFIX));
  const out = {
    ok: true,
    dir,
    repo,
    diff_file: path.join(dir, "diff.patch"),
    target_paths_file: path.join(dir, "changed-files.txt"),
    instruction_file: path.join(dir, "instructions.md"),
    file_count: names.length,
    bytes: Buffer.byteLength(diff),
    secret_paths: secretPaths,
    dispatch_id: `rva-${Date.now().toString(36)}`
  };
  try {
    fs.chmodSync(dir, 0o700);
    fs.writeFileSync(out.diff_file, diff, { mode: 0o600 });
    fs.writeFileSync(out.target_paths_file, `${names.join("\n")}\n`, { mode: 0o600 });
    fs.writeFileSync(out.instruction_file, instructionText, { mode: 0o600 });
  } catch {
    fs.rmSync(dir, { recursive: true, force: true });
    return fail("could not write the prepared files");
  }
  process.stdout.write(`${JSON.stringify(out)}\n`);
  return 0;
}

async function main(argv) {
  // The dispatcher refuses Windows, and cleanup's ownership check needs a POSIX uid: refuse here too,
  // before anything is created, so no prepared diff is left behind in temp storage.
  if (process.platform === "win32") return fail("rva-review-diff runs on Linux and macOS only; nothing was prepared");
  if (argv.length === 2 && argv[0] === "--cleanup") return cleanup(argv[1]);
  if (argv[0] !== "--cwd" || argv[1] === undefined) return fail("usage: --cwd <dir> [--range <git-range>] | --cleanup <dir>");
  if (argv.length === 2) return prepare(argv[1], undefined);
  if (argv.length === 4 && argv[2] === "--range") return prepare(argv[1], argv[3]);
  return fail("usage: --cwd <dir> [--range <git-range>] | --cleanup <dir>");
}

main(process.argv.slice(2)).then((code) => {
  process.exitCode = code;
}, () => {
  process.exitCode = fail("rva-prepare failed unexpectedly");
});
