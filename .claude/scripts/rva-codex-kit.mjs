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
// be owned by the current user and not writable by group or others. On Windows, where these mode bits
// mean nothing, the check is skipped and the caller records that.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
// rva-config.mjs imports ownedAndPrivate from this file; the cycle is safe because neither module calls
// the other's functions while loading.
import { isInside } from "./rva-config.mjs";

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
// listed in /etc/group, and no other account in /etc/passwd with it as its primary gid. Anything else,
// including a group /etc/group does not list (LDAP), fails closed.
export function privateGroupGid() {
  if (process.platform === "win32") return null;
  try {
    const gid = process.getgid();
    const user = os.userInfo().username;
    const sharers = fs.readFileSync("/etc/passwd", "utf8").split("\n")
      .map((line) => line.split(":"))
      .filter((fields) => fields.length > 3 && Number(fields[3]) === gid && fields[0] !== user);
    if (sharers.length > 0) return null;
    for (const line of fs.readFileSync("/etc/group", "utf8").split("\n")) {
      const [name, , id, members] = line.split(":");
      if (Number(id) === gid) return name === user && !members?.trim() ? gid : null;
    }
  } catch {
    // Unreadable /etc/passwd or /etc/group: no private-group exception.
  }
  return null;
}

// True when a path is owned by the current user and writable by nobody else (group write allowed only
// for the user's private group). Used for codex-kit's files and for the dispatcher's input files.
export function ownedAndPrivate(stat, privateGid = privateGroupGid()) {
  if (process.platform === "win32") return true;
  if (stat.uid !== process.getuid()) return false;
  if ((stat.mode & 0o002) !== 0) return false;
  return (stat.mode & 0o020) === 0 || (privateGid !== null && stat.gid === privateGid);
}

export const OUTSIDE_ROOT = "resolves outside the root";

// Checks a file and every directory from it up to root (real paths): each must be owned by the current
// user and not writable by group or others (group write allowed for the user's private group). Returns
// what is wrong ("is not owned by the current user", ...) or null when all are private. Throws when a path
// cannot be resolved. Used for codex-kit's imported files and for prepare's reviewer instructions file.
export function ownedTreeProblem(root, file) {
  if (process.platform === "win32") return null;
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
    if (current === realRoot) return null;
    current = path.dirname(current);
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
    for (const dir of dirs) {
      for (const name of fs.readdirSync(dir)) checkOwnership(root, path.join(dir, name));
    }
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
    return { api, ownershipChecked: process.platform !== "win32" };
  }
  throw new CodexKitUnavailable(devSibling
    ? "codex-kit was not found in installed_plugins.json or next to this plugin (a sibling is used only when this plugin is plugins/reviewadapters-kit in a checkout)"
    : "codex-kit is not installed from andres-cc-marketplace (a sibling checkout is used only with dev_sibling_codex_kit in the untracked local file)");
}
