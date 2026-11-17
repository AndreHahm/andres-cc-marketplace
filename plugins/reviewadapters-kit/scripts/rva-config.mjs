// Load the shipped defaults and the untracked local override, and decide whether a vendor is enabled.
//
// Only the local file under the reviewed repository can enable a vendor, because enabling one sends
// repository content to that vendor. A git-tracked copy of the local file is refused outright: a
// tracked file can be changed by anyone with write access, including by the change under review. A
// timeout above the shipped value is ignored; a model may come from either file, local wins. The local
// file must also be owned by the current user and not writable by others.
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { ownedAndPrivate } from "./rva-codex-kit.mjs";

const PLUGIN_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
export const LOCAL_CONFIG_RELATIVE = ".claude/reviewadapters-kit.local.json";
// A model never starts with "-", so it cannot be read as a flag by a vendor CLI.
const MODEL_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._/:-]{0,127}$/;

// path.relative, not a prefix test: a prefix of dir + "/" never matches when dir is the filesystem root
// ("/" + "/" is "//"), so a repository at "/" (a container's) would contain nothing.
export function isInside(file, dir) {
  const rel = path.relative(dir, file);
  return rel === "" || (rel.split(path.sep)[0] !== ".." && !path.isAbsolute(rel));
}

// realpathSync.native returns the on-disk letter case, so an in-repo path cannot pass isInside on a
// case-insensitive filesystem by differing only in case.
export function realPath(file) {
  return fs.realpathSync.native(file);
}

// A PATH entry that may be used: absolute (a relative one resolves against the working directory, which
// can be the reviewed checkout) and neither literally nor after resolving symlinks inside untrustedRoot.
function trustedEntry(dir, untrustedRoot) {
  if (!dir || !path.isAbsolute(dir) || isInside(path.resolve(dir), untrustedRoot)) return false;
  try {
    return !isInside(realPath(dir), untrustedRoot);
  } catch {
    return false;
  }
}

// The environment for every git call: the caller's, minus every GIT_* variable (compared without letter
// case, as Windows names are). `-C <dir>` does not override GIT_DIR, GIT_WORK_TREE or GIT_INDEX_FILE (a
// git hook sets them), and GIT_CONFIG_* can inject configuration, so an inherited one could point a call
// at another repository or index.
export function gitEnv() {
  return Object.fromEntries(Object.entries(process.env).filter(([name]) => !name.toUpperCase().startsWith("GIT_")));
}

// Secret-like file names this plugin adds to codex-kit's shared list, which misses them: SSH keys with a
// suffix or a FIDO "_sk" (a separator, then anything, needs no ".*"), PuTTY keys and CLI auth files.
const LOCAL_SECRET_NAMES = [/^id_(rsa|dsa|ecdsa|ed25519)(_sk)?([._-]|$)/i, /\.ppk$/i, /^auth\.json$/i, /^hosts\.ya?ml$/i, /^\.envrc$/i, /^\.pypirc$/i];

// One predicate for every secret-name check (changed files, prepare's secret_paths, the dispatcher's input
// files): codex-kit's list or a local addition. A public key (".pub") is not a secret.
export function isSecretName(name, api) {
  if (api.matchesSecretFilename(name, true)) return true;
  return !/\.pub$/i.test(name) && LOCAL_SECRET_NAMES.some((pattern) => pattern.test(name));
}

// Leading options for every git call: no fsmonitor hook from the repository's own config runs while git
// refreshes the index.
export const GIT_SAFE_OPTIONS = ["-c", "core.fsmonitor=false"];

// The first executable named `binary` on a trusted PATH entry whose real path lies outside
// `untrustedRoot` (the reviewed checkout), so a changed file named like the binary never runs. The PATH
// path itself is returned and run, not its real path: a shim that picks the tool by the name it was
// called as (Volta links every tool to one volta-shim) would break under its real name. Its directory is
// a trusted entry, outside the checkout, so the checkout cannot swap the link.
// Used for git and the vendor CLIs.
export function findBinary(binary, untrustedRoot) {
  for (const dir of (process.env.PATH ?? "").split(path.delimiter)) {
    if (!trustedEntry(dir, untrustedRoot)) continue;
    const candidate = path.join(dir, binary);
    try {
      const target = realPath(candidate);
      fs.accessSync(target, fs.constants.X_OK);
      if (fs.statSync(target).isFile() && !isInside(target, untrustedRoot)) return candidate;
    } catch {
      // Not here; keep looking.
    }
  }
  return null;
}

// The PATH a vendor gets: only the trusted entries, so an interpreter its CLI starts (a
// "#!/usr/bin/env node" script, say) is not found inside the reviewed checkout either.
export function trustedPath(untrustedRoot) {
  return (process.env.PATH ?? "").split(path.delimiter).filter((dir) => trustedEntry(dir, untrustedRoot)).join(path.delimiter);
}

// The nearest directory at or above `start` that holds a .git entry (a directory, or a file in a
// worktree), found without running git: it is the root git must come from outside of.
export function enclosingRepoRoot(start) {
  for (let dir = start; ; dir = path.dirname(dir)) {
    if (fs.existsSync(path.join(dir, ".git"))) return dir;
    if (path.dirname(dir) === dir) return null;
  }
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

export class LocalFileRefused extends Error {}

const NOT_PRIVATE = "the local file or its .claude directory is not owned by you, or is writable by others, so it cannot enable anything";
const FILE_FLAGS = fs.constants.O_RDONLY | fs.constants.O_NONBLOCK | (fs.constants.O_NOFOLLOW ?? 0);

// Open the file inside the .claude directory that was checked, not whatever the path names a moment
// later: the directory is opened (never through a symlink) and checked on its handle, and on Linux the
// file is opened through that handle (/proc/self/fd/<n>/<name>, the equivalent of openat). Elsewhere the
// file is opened by path and the path must still name the checked directory afterwards; a swap there and
// back between the two steps is not caught. The options exist for the tests only: afterDirCheck runs
// between the directory check and the file open, and byPath forces the non-Linux path.
export function openInCheckedDir(file, { afterDirCheck, byPath = false } = {}) {
  const dir = path.dirname(file);
  let dirFd;
  try {
    dirFd = fs.openSync(dir, fs.constants.O_RDONLY | (fs.constants.O_DIRECTORY ?? 0) | (fs.constants.O_NOFOLLOW ?? 0));
  } catch {
    throw new LocalFileRefused("the .claude directory cannot be opened (a symbolic link, or unreadable), so the local file cannot enable anything");
  }
  try {
    const dirStat = fs.fstatSync(dirFd);
    if (!dirStat.isDirectory() || !ownedAndPrivate(dirStat)) throw new LocalFileRefused(NOT_PRIVATE);
    const viaHandle = `/proc/self/fd/${dirFd}`;
    const useHandle = !byPath && process.platform === "linux" && fs.existsSync(viaHandle);
    afterDirCheck?.();
    let fd;
    try {
      fd = fs.openSync(useHandle ? path.join(viaHandle, path.basename(file)) : file, FILE_FLAGS);
    } catch {
      throw new LocalFileRefused("the local file cannot be opened (a symbolic link, or unreadable), so it cannot enable anything");
    }
    if (!useHandle) {
      let same = false;
      try {
        const now = fs.lstatSync(dir);
        same = now.dev === dirStat.dev && now.ino === dirStat.ino;
      } catch {
        // The directory is gone: not the one that was checked.
      }
      if (!same) {
        fs.closeSync(fd);
        throw new LocalFileRefused("the .claude directory changed while the local file was opened, so it cannot enable anything");
      }
    }
    return fd;
  } finally {
    fs.closeSync(dirFd);
  }
}

// The local file is opened once, without following a final symlink or blocking on a FIFO, and checked
// on the open handle, so it cannot be swapped between the check and the read. It enables egress, so it
// and its .claude directory must belong to the current user and be writable by nobody else, the same
// rule the dispatcher's input files and codex-kit's files follow.
function readLocalJson(file) {
  const fd = openInCheckedDir(file);
  try {
    const stat = fs.fstatSync(fd);
    if (!stat.isFile() || stat.size > 64 * 1024) throw new LocalFileRefused("the local file is not a regular file of at most 64 KiB, so it cannot enable anything");
    if (!ownedAndPrivate(stat)) throw new LocalFileRefused(NOT_PRIVATE);
    return JSON.parse(fs.readFileSync(fd, "utf8"));
  } finally {
    fs.closeSync(fd);
  }
}

// Tracked under any letter case: on a case-insensitive filesystem (macOS, Windows) a committed
// ".claude/ReviewAdapters-Kit.local.json" opens under the lowercase name, while an exact pathspec would
// call it untracked. Any git error, or no git outside the repository, cannot prove the file is untracked,
// so it counts as tracked.
function isTracked(repoRoot, relative) {
  const git = findBinary("git", repoRoot);
  if (!git) return true;
  try {
    const out = execFileSync(git, [...GIT_SAFE_OPTIONS, "-C", repoRoot, "ls-files", "-z", "--", `:(icase)${relative}`], { encoding: "utf8", env: gitEnv(), stdio: ["ignore", "pipe", "ignore"], timeout: 10_000 });
    return out.length > 0;
  } catch {
    return true;
  }
}

// The file must exist under exactly this name, in a real (not symlinked) .claude directory.
function exactLocalFile(repoRoot) {
  const dir = path.join(repoRoot, path.dirname(LOCAL_CONFIG_RELATIVE));
  try {
    if (!fs.lstatSync(dir).isDirectory()) return false;
    const name = path.basename(LOCAL_CONFIG_RELATIVE);
    return fs.readdirSync(dir).includes(name) && fs.lstatSync(path.join(dir, name)).isFile();
  } catch {
    return false;
  }
}

// Read the untracked local file, or say why it cannot be used. Shared by the vendor allow-list and the
// dev-sibling codex-kit opt-in, so both get the same tracked-copy refusal.
function readLocal(repoRoot) {
  const localFile = path.join(repoRoot, LOCAL_CONFIG_RELATIVE);
  if (!exactLocalFile(repoRoot)) return { local: null, reason: "not enabled in the untracked local file" };
  if (isTracked(repoRoot, LOCAL_CONFIG_RELATIVE)) {
    return { local: null, reason: "the local file is tracked by git (or git could not prove it is untracked), so it cannot enable anything" };
  }
  try {
    const local = readLocalJson(localFile);
    if (!local || typeof local !== "object" || Array.isArray(local)) return { local: null, reason: "the local file is not a JSON object" };
    return { local, reason: "" };
  } catch (error) {
    if (error instanceof LocalFileRefused) return { local: null, reason: error.message };
    return { local: null, reason: "the local file is not valid JSON" };
  }
}

// The sibling codex-kit in a marketplace checkout is the reviewed branch's own code, so importing it is
// opt-in for this repository's own development only.
export function devSiblingOptIn(repoRoot) {
  return readLocal(repoRoot).local?.dev_sibling_codex_kit === true;
}

export function loadConfig(repoRoot, vendor) {
  const shipped = readJson(path.join(PLUGIN_ROOT, "reviewadapters-kit.settings.json"));
  if (!Number.isInteger(shipped?.timeout_ms) || shipped.timeout_ms <= 0) throw new Error("the shipped timeout_ms is not a positive integer");
  const shippedVendor = shipped.vendors?.[vendor] ?? {};
  const result = {
    enabled: false,
    reason: "not enabled in the untracked local file",
    allowUnprobedVersion: false,
    allowedModels: [],
    timeoutMs: shipped.timeout_ms,
    model: typeof shippedVendor.model === "string" && MODEL_PATTERN.test(shippedVendor.model) ? shippedVendor.model : undefined
  };
  const { local, reason } = readLocal(repoRoot);
  if (!local) {
    result.reason = reason;
    return result;
  }
  const localVendor = local.vendors?.[vendor] ?? {};
  if (typeof localVendor.model === "string" && MODEL_PATTERN.test(localVendor.model)) result.model = localVendor.model;
  if (Number.isInteger(local.timeout_ms) && local.timeout_ms > 0 && local.timeout_ms < result.timeoutMs) {
    result.timeoutMs = local.timeout_ms;
  }
  if (localVendor.enabled === true) {
    result.enabled = true;
    result.reason = "enabled in the untracked local file";
  }
  // Running a vendor version whose isolation flags were never verified widens what may leave the
  // machine, so only the local file can allow it, per vendor.
  if (localVendor.allow_unprobed_version === true) result.allowUnprobedVersion = true;
  // Extra models a caller's --model may pick (pi): an egress choice, so only from the local file.
  if (Array.isArray(localVendor.models)) {
    result.allowedModels = localVendor.models.filter((m) => typeof m === "string" && MODEL_PATTERN.test(m));
  }
  return result;
}

export { MODEL_PATTERN };
