// Locate codex-kit and import its envelope schema, validator and failure categories.
//
// Importing a module runs its code, so the location is a trust decision. The installed copy comes
// first: the installPath recorded under the key "codex-kit@andres-cc-marketplace" in
// ~/.claude/plugins/installed_plugins.json, and only when that path is absolute. A sibling codex-kit
// next to this plugin (only when this plugin really is a marketplace checkout's
// plugins/reviewadapters-kit) is used only when the caller passes devSibling, which the dispatcher sets from the untracked local file: in a checkout under review, the
// sibling is the reviewed branch's own code. No variable of this plugin's own redirects the import, but
// `~` is os.homedir(), which follows $HOME on POSIX: whoever sets HOME picks the registry read. Before
// importing, every directory from codex-kit's root down to each imported file, and the file itself, must
// be owned by the current user and not writable by group or others. On Windows the same rule is read
// from each path's owner and DACL instead (rva-winacl.mjs).
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
// rva-config.mjs imports ownedAndPrivate from this file; the cycle is safe because neither module calls
// the other's functions while loading.
import { isInside } from "./rva-config.mjs";
import { aclProblem, ancestorProblem, ancestors, readAcls, currentUserSid, REPLACE_RIGHTS, WRITE_RIGHTS } from "./rva-winacl.mjs";

const WINDOWS = process.platform === "win32";

const PLUGIN_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const BRIDGE = "skills/codex-review-bridge/scripts/bridge-invoke.mjs";
const EXEC = "scripts/lib/codex-exec.mjs";
const SECRETS = "scripts/lib/cdx-secret-filenames.mjs";

export class CodexKitUnavailable extends Error {}

const REGISTRY_KEY = "codex-kit@andres-cc-marketplace";

function candidateRoots(devSibling) {
  const roots = [];
  const registry = path.join(os.homedir(), ".claude", "plugins", "installed_plugins.json");
  try {
    const data = JSON.parse(fs.readFileSync(registry, "utf8"));
    const plugins = data?.plugins ?? data;
    const value = plugins && Object.hasOwn(plugins, REGISTRY_KEY) ? plugins[REGISTRY_KEY] : undefined;
    for (const entry of Array.isArray(value) ? value : [value]) {
      if (entry && typeof entry.installPath === "string" && path.isAbsolute(entry.installPath)) roots.push(entry.installPath);
    }
  } catch {
    // No registry, or unreadable: only the opted-in sibling, if any, remains.
  }
  // Only from a real marketplace checkout, plugins/reviewadapters-kit: from a copy elsewhere (this
  // repository's .claude/ mirror, for example, even inside a checkout whose own directory is named
  // plugins) the "sibling" would be a path no plugin occupies, which only planted content could fill.
  if (devSibling && path.basename(PLUGIN_ROOT) === "reviewadapters-kit" && path.basename(path.dirname(PLUGIN_ROOT)) === "plugins") {
    roots.push(path.resolve(PLUGIN_ROOT, "..", "codex-kit"));
  }
  return roots;
}

// Group write is harmless when the group is the user's own private group (umask 002 systems, where
// every checkout is group-writable): same name as the user, the user's primary gid, no other members
// listed in /etc/group, and no other account in /etc/passwd with it as its primary gid. Every /etc/group
// line is read: a second line with the same gid is refused, whatever it lists, since Linux grants a
// supplementary group by gid from every line naming a user. Anything else, including a group /etc/group
// does not list (LDAP), fails closed. Other NSS sources (LDAP, sssd) are not read, so a member they add
// to a gid /etc/group also lists is not seen. `files` exists for the tests.
export function privateGroupGid(files = { passwd: "/etc/passwd", group: "/etc/group" }) {
  if (process.platform === "win32") return null;
  try {
    const gid = process.getgid();
    const user = os.userInfo().username;
    const sharers = fs.readFileSync(files.passwd, "utf8").split("\n")
      .map((line) => line.split(":"))
      .filter((fields) => fields.length > 3 && Number(fields[3]) === gid && fields[0] !== user);
    if (sharers.length > 0) return null;
    let found = false;
    for (const line of fs.readFileSync(files.group, "utf8").split("\n")) {
      const [name, , id, members] = line.split(":");
      if (Number(id) !== gid) continue;
      if (found || name !== user || members?.trim()) return null;
      found = true;
    }
    return found ? gid : null;
  } catch {
    // Unreadable /etc/passwd or /etc/group: no private-group exception.
  }
  return null;
}

// On Linux a POSIX ACL entry can grant write only when the ACL mask has write, and the mask is what the
// group mode bits show. So group write is the only way an ACL hides write access from these checks, and
// the private-group exception is the only place it would slip through: there, the path must also have no
// extended ACL. Read with the system ls (an alternate-access "+" after the mode string; "." is an SELinux
// context only), and only with GNU coreutils' ls: busybox's prints no marker at all, and others are not
// verified, so any other ls counts as an ACL. A missing ls, an error or unexpected output counts as an ACL
// too (fail closed). The mask argument holds for POSIX ACLs only: NFSv4, CIFS and FUSE permissions do not
// follow the mode bits, here or in the other mode-bit checks. Outside Linux an ACL is never ruled out, so
// the private-group exception is Linux only. macOS ACLs can grant write whatever the mode bits say, so one
// on a path without group write is still not seen. Windows reads owners and DACLs instead (rva-winacl.mjs).
const LS_BINARIES = ["/usr/bin/ls", "/bin/ls"];
let gnuLs;

// The GNU coreutils ls the ACL check reads, or null when there is none (the tests skip on null).
export function findGnuLs() {
  if (gnuLs !== undefined) return gnuLs;
  gnuLs = null;
  for (const bin of LS_BINARIES) {
    try {
      fs.accessSync(bin, fs.constants.X_OK);
      const version = execFileSync(bin, ["--version"], { encoding: "utf8", env: { LC_ALL: "C" }, timeout: 10_000, stdio: ["ignore", "pipe", "ignore"] });
      if (/^ls \(GNU coreutils\) /.test(version)) gnuLs = bin;
    } catch {
      // Missing, or not GNU: try the next one.
    }
    if (gnuLs) break;
  }
  return gnuLs;
}

function mayHaveExtendedAcl(file) {
  if (process.platform !== "linux") return true;
  if (file === undefined) return true;
  const ls = findGnuLs();
  if (!ls) return true;
  try {
    const out = execFileSync(ls, ["-ldL", "--", file], { encoding: "utf8", env: { LC_ALL: "C" }, timeout: 10_000, stdio: ["ignore", "pipe", "ignore"] });
    const mode = out.split(/\s/, 1)[0];
    return !(mode.length === 10 || (mode.length === 11 && mode[10] === "."));
  } catch {
    return true;
  }
}

// A path naming what an open descriptor refers to, for the ACL checks: on Linux the descriptor itself
// (/proc), on Windows the real path it was opened from, which ownedAndPrivate then ties back to the
// descriptor's file id.
export function descriptorPath(fd, file) {
  return WINDOWS ? file : `/proc/${process.pid}/fd/${fd}`;
}

// On Windows: true when `file` still names the file `stat` describes (same volume and file id). A file
// id of 0 (a filesystem that reports none) never matches. The DACL is read by path, so this only ties
// path and handle together because ancestorProblem has made sure no other account can rename or replace
// an entry on the way down to the file.
// The creation time is compared too: Node reports the 64-bit file id as a JavaScript number, which can
// round two ids above 2^53 to the same value.
function sameFile(stat, file) {
  if (!stat.ino) return false;
  try {
    const now = fs.statSync(file);
    return now.dev === stat.dev && now.ino === stat.ino && now.birthtimeMs === stat.birthtimeMs;
  } catch {
    return false;
  }
}

// On Windows: owned by the current user, no other account but SYSTEM, Administrators and TrustedInstaller
// holds a right to write, delete or re-permission it, and no directory above it lets another account
// rename or replace an entry (rva-winacl.mjs). With nobody else able to change the file or swap the path,
// a DACL read by path, or cached from earlier in this run, is the one of the handle. Fails closed when an
// ACL cannot be read.
function windowsPrivate(stat, file) {
  if (!file || !sameFile(stat, file)) return false;
  try {
    const real = fs.realpathSync.native(file);
    const [info] = readAcls([real]);
    if (aclProblem(info, currentUserSid()) !== null || ancestorProblem(real) !== null) return false;
    // The checks above describe `real`; `file` may run through a junction another account can repoint.
    // `real` now has stable directories above it, so the handle must be the file it names.
    return sameFile(stat, real);
  } catch {
    return false;
  }
}

// True when a path belongs to the current user: its uid on POSIX, its owner SID on Windows (`file` is the
// path `stat` came from). Used by prepare's cleanup.
export function ownedByCurrentUser(stat, file) {
  if (!WINDOWS) return stat.uid === process.getuid();
  if (!file || !sameFile(stat, file)) return false;
  try {
    const real = fs.realpathSync.native(file);
    const [info] = readAcls([real]);
    return !info.error && info.owner === currentUserSid() && sameFile(stat, real);
  } catch {
    return false;
  }
}

// True when a path is owned by the current user and writable by nobody else (group write allowed only
// for the user's private group, and then only on Linux without an extended ACL). `aclPath` names the
// same file or directory as `stat` (descriptorPath(fd) for an fstat); without it on Linux, group write
// is refused. Used for codex-kit's files, the dispatcher's input files and the local config file.
export function ownedAndPrivate(stat, aclPath, privateGid = privateGroupGid()) {
  if (WINDOWS) return windowsPrivate(stat, aclPath);
  if (stat.uid !== process.getuid()) return false;
  if ((stat.mode & 0o002) !== 0) return false;
  if ((stat.mode & 0o020) === 0) return true;
  return groupWriteIsPrivate(stat, aclPath, privateGid);
}

// True when the group that can write a path is the user's private group, on Linux, with no extended ACL.
// Independent of the path's owner, so a root-owned directory can use it too.
function groupWriteIsPrivate(stat, aclPath, privateGid) {
  return privateGid !== null && stat.gid === privateGid && !mayHaveExtendedAcl(aclPath);
}

// One directory on the temp directory's path: it must belong to this user or root, since its owner can
// always rename an entry in it away and put their own in its place, sticky bit or not. One other users
// can write to also needs the sticky bit, or any of them could do the same (or delete it before cleanup);
// the sticky bit is enough because every entry on the way down belongs to this user or root. Group write
// for the user's own private group does not count as other users (see ownedAndPrivate for the ACL limits).
// True when the directory is unsafe.
export function unsafeDirStat(stat, aclPath, privateGid = privateGroupGid()) {
  if (stat.uid !== process.getuid() && stat.uid !== 0) return true;
  const othersCanWrite = (stat.mode & 0o002) !== 0 || ((stat.mode & 0o020) !== 0 && !groupWriteIsPrivate(stat, aclPath, privateGid));
  return othersCanWrite && (stat.mode & 0o1000) === 0;
}

// True when the temp directory, or any directory above it, fails unsafeDirStat. `tmp` must be the
// resolved path the caller then uses (fs.realpathSync), so no symbolic link on it can be pointed elsewhere
// after the check; a path that is not resolved counts as unsafe. Used by prepare, cleanup and the
// dispatcher's run directory.
export function unsafeTempDir(tmp) {
  if (fs.realpathSync(tmp) !== tmp) return true;
  if (WINDOWS) return unsafeWindowsTempDir(tmp);
  const privateGid = privateGroupGid();
  for (let dir = tmp; ; dir = path.dirname(dir)) {
    if (unsafeDirStat(fs.statSync(dir), dir, privateGid)) return true;
    if (path.dirname(dir) === dir) return false;
  }
}

// Windows has no sticky bit, so the temp directory itself must be private, inheritable rules included
// (whatever is created in it inherits them), and owned by the user, SYSTEM, Administrators or
// TrustedInstaller. A directory above it may let others add entries (C:\ lets Authenticated Users) but
// not delete, rename or re-permission one. Any ACL that cannot be read counts as unsafe.
function unsafeWindowsTempDir(tmp) {
  const chain = [];
  for (let dir = tmp; ; dir = path.dirname(dir)) {
    chain.push(dir);
    if (path.dirname(dir) === dir) break;
  }
  try {
    const infos = readAcls(chain);
    const me = currentUserSid();
    if (aclProblem(infos[0], me, { owner: "trusted", rights: WRITE_RIGHTS, inheritable: true })) return true;
    return infos.slice(1).some((info) => aclProblem(info, me, { owner: "trusted", rights: REPLACE_RIGHTS }) !== null);
  } catch {
    return true;
  }
}

// Appended to the refusals that rest on ownedAndPrivate, which only says yes or no: group write is the
// usual surprise, and an ACL or a missing GNU coreutils ls is otherwise invisible in the message.
export const GROUP_WRITE_NOTE = WINDOWS
  ? "on Windows, an allow rule giving any account but you, SYSTEM, Administrators or TrustedInstaller the right to write, delete or change permissions counts"
  : "group write counts too, unless the group is your private group, on Linux, and GNU coreutils ls shows no extended ACL";

export const UNSAFE_TEMP = WINDOWS
  ? `the temp directory is not private to you, or a directory above it lets another account delete, rename or re-permission its entries; set TMP and TEMP to a private directory (${GROUP_WRITE_NOTE}; the README shows the icacls commands)`
  : `the temp directory, or a directory above it, belongs to another user, or is writable by other users and has no sticky bit; set TMPDIR to a private directory (${GROUP_WRITE_NOTE})`;

export const OUTSIDE_ROOT = "resolves outside the root";

// Checks a file and every directory from it up to root (real paths): each must be owned by the current
// user and not writable by group or others (group write allowed for the user's private group). Returns
// what is wrong ("is not owned by the current user", ...) or null when all are private. Throws when a path
// cannot be resolved. Used for codex-kit's imported files and for prepare's reviewer instructions file.
export function ownedTreeProblem(root, file) {
  if (WINDOWS) return windowsTreeProblem(root, file);
  const uid = process.getuid();
  const privateGid = privateGroupGid();
  const realRoot = fs.realpathSync(root);
  const realFile = fs.realpathSync(file);
  if (!isInside(realFile, realRoot)) return OUTSIDE_ROOT;
  let current = realFile;
  for (;;) {
    const stat = fs.statSync(current);
    if (stat.uid !== uid) return "is not owned by the current user";
    if ((stat.mode & 0o002) !== 0) return "is writable by others";
    if ((stat.mode & 0o020) !== 0 && (privateGid === null || stat.gid !== privateGid)) {
      return "is writable by a group other than the user's private group";
    }
    if ((stat.mode & 0o020) !== 0 && mayHaveExtendedAcl(current)) {
      return "is group-writable, and an extended ACL cannot be ruled out (it has one, there is no GNU coreutils ls, or this is not Linux)";
    }
    if (current === realRoot) return null;
    current = path.dirname(current);
  }
}

// The Windows form of ownedTreeProblem: the same walk, read from owners and DACLs in one batch.
function windowsTreeProblem(root, file) {
  const realRoot = fs.realpathSync(root);
  const realFile = fs.realpathSync(file);
  if (!isInside(realFile, realRoot)) return OUTSIDE_ROOT;
  const chain = [];
  for (let current = realFile; ; current = path.dirname(current)) {
    chain.push(current);
    if (current === realRoot) break;
  }
  const infos = readAcls(chain);
  const me = currentUserSid();
  for (const info of infos) {
    const problem = aclProblem(info, me);
    if (problem) return problem;
  }
  // Above the root too: on Windows a directory another account may rename or replace an entry in would
  // let it swap the whole tree between this walk and the read.
  return ancestorProblem(realRoot, me);
}

// On Windows, read every ACL the walks below need in one PowerShell call rather than one per file.
function prefetchTrees(root, files) {
  try {
    const realRoot = fs.realpathSync(root);
    const all = new Set();
    for (const file of files) {
      for (let current = fs.realpathSync(file); isInside(current, realRoot); current = path.dirname(current)) {
        all.add(current);
        if (current === realRoot) break;
      }
    }
    for (const dir of ancestors(realRoot)) all.add(dir);
    readAcls([...all]);
  } catch {
    // checkOwnership reads and reports each path itself.
  }
}

function checkOwnership(root, file) {
  const problem = ownedTreeProblem(root, file);
  if (problem === OUTSIDE_ROOT) throw new CodexKitUnavailable("an imported file resolves outside codex-kit's root");
  if (problem) throw new CodexKitUnavailable(`a codex-kit path ${problem}`);
}

export async function loadCodexKit({ devSibling = false } = {}) {
  for (const root of candidateRoots(devSibling)) {
    const files = [BRIDGE, EXEC, SECRETS].map((rel) => path.join(root, rel));
    if (!files.every((file) => fs.existsSync(file))) continue;
    // The imported modules pull in siblings (codex-exec.mjs imports cdx-process.mjs and reads
    // cdx-token-shapes.json), so every file in each imported file's directory is checked, not only the
    // three entry points.
    const dirs = new Set(files.map((file) => path.dirname(file)));
    const checked = [...dirs].flatMap((dir) => fs.readdirSync(dir).map((name) => path.join(dir, name)));
    if (WINDOWS) prefetchTrees(root, checked);
    for (const file of checked) checkOwnership(root, file);
    const [bridge, exec, secrets] = await Promise.all(files.map((file) => import(pathToFileURL(fs.realpathSync(file)).href)));
    const api = {
      ENVELOPE_SCHEMA: bridge.ENVELOPE_SCHEMA,
      semanticallyValidate: bridge.semanticallyValidate,
      isValidToken: bridge.isValidToken,
      isValidPathToken: bridge.isValidPathToken,
      isWithin: bridge.isWithin,
      findSchemaViolation: exec.findSchemaViolation,
      redactSecrets: exec.redactSecrets,
      FAILURE_CATEGORIES: exec.FAILURE_CATEGORIES,
      matchesSecretFilename: secrets.matchesSecretFilename
    };
    const missing = Object.entries(api).filter(([, value]) => value === undefined).map(([name]) => name);
    if (missing.length > 0) throw new CodexKitUnavailable(`codex-kit does not export: ${missing.join(", ")}`);
    return { api, ownershipChecked: true };
  }
  throw new CodexKitUnavailable(devSibling
    ? "codex-kit was not found in installed_plugins.json or next to this plugin (a sibling is used only when this plugin is plugins/reviewadapters-kit in a checkout)"
    : "codex-kit is not installed from andres-cc-marketplace (a sibling checkout is used only with dev_sibling_codex_kit in the untracked local file)");
}
