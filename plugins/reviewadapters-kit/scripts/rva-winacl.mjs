// Windows owner and DACL checks, the counterpart of the POSIX mode-bit checks in rva-codex-kit.mjs
// (issue #770). One Windows PowerShell call reads a batch of paths with plain .NET calls
// ([IO.File]/[IO.Directory]::GetAccessControl, then the raw security descriptor), so no PowerShell module
// is loaded and no access-rule filtering by .NET hides an entry. PowerShell comes from
// %SystemRoot%\System32, never from PATH, and runs from %SystemRoot% with only SystemRoot, windir and the
// system module path in its environment. Paths go in on stdin as base64 lines; only SIDs and numbers come
// back, in a line format parsed strictly here: anything unexpected fails closed.
//
// Trusted principals: the current user, SYSTEM, Administrators, TrustedInstaller, and CREATOR OWNER and
// OWNER RIGHTS (which stand for the owner, itself checked). Anyone else, AppContainer capability SIDs
// included, counts as another user. Deny entries are not subtracted (a grant they would cancel still
// counts), and a missing DACL, a conditional (callback) entry or an entry of another type fails closed.
// Not verified: whether .NET Framework's FileSecurity drops an entry it considers meaningless (an object
// entry on a file, say) before the SDDL is produced, which would hide it from the parser here.
import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const SYSTEM = "S-1-5-18";
const ADMINISTRATORS = "S-1-5-32-544";
const TRUSTED_INSTALLER = "S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464";
const CREATOR_OWNER = "S-1-3-0";
const OWNER_RIGHTS = "S-1-3-4";
const TRUSTED_OTHERS = new Set([SYSTEM, ADMINISTRATORS, TRUSTED_INSTALLER, CREATOR_OWNER, OWNER_RIGHTS]);
const TRUSTED_OWNERS = new Set([SYSTEM, ADMINISTRATORS, TRUSTED_INSTALLER]);

// A SID in string form, S-1-<authority>-<sub>[-<sub>...]: at least two numeric parts after S-1. Checked part by
// part rather than with a repeated group, so no pattern can backtrack.
function isSid(value) {
  const parts = value.split("-");
  return parts.length >= 4 && parts[0] === "S" && parts[1] === "1" && parts.slice(2).every((part) => /^\d+$/.test(part));
}

// Rights that let a holder change a file's content, metadata or permissions, or remove or replace it:
// write data / add file, append data / add subdirectory, write extended attributes, delete child, write
// attributes, delete, write DAC, write owner, access system security, maximum allowed, generic all,
// generic write. The last three grant nothing in a stored entry and are counted anyway.
export const WRITE_RIGHTS = 0x2 | 0x4 | 0x10 | 0x40 | 0x100 | 0x10000 | 0x40000 | 0x80000 | 0x1000000 | 0x2000000 | 0x10000000 | 0x40000000;
// Rights on a directory above a checked path that let a holder rename or remove what it holds, or grant
// themselves that: delete child, delete, write DAC, write owner, generic all. Adding an entry (as
// Authenticated Users may on C:\) cannot replace an existing one, the counterpart of a sticky directory.
export const REPLACE_RIGHTS = 0x40 | 0x10000 | 0x40000 | 0x80000 | 0x10000000;

const ACE_INHERIT_ONLY = 0x08;
const ACE_INHERITS = 0x01 | 0x02;

// No double quote: runPowerShell refuses a script with one.
const ACL_SCRIPT = [
  "$ErrorActionPreference = 'Stop'",
  "$nl = [char]10",
  "$out = [Text.StringBuilder]::new()",
  "[void]$out.Append('ME ' + [Security.Principal.WindowsIdentity]::GetCurrent().User.Value + $nl)",
  "foreach ($line in [Console]::In.ReadToEnd().Split($nl)) {",
  "  $line = $line.Trim()",
  "  if ($line.Length -eq 0) { continue }",
  "  try {",
  "    $p = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($line))",
  "    $parts = [Security.AccessControl.AccessControlSections]'Access, Owner'",
  "    if ([IO.Directory]::Exists($p)) { $sec = [IO.Directory]::GetAccessControl($p, $parts) } else { $sec = [IO.File]::GetAccessControl($p, $parts) }",
  "    $raw = [Security.AccessControl.RawSecurityDescriptor]::new($sec.GetSecurityDescriptorSddlForm($parts))",
  "    if ($null -eq $raw.Owner) { throw 'no owner' }",
  "    $dacl = $raw.DiscretionaryAcl",
  "    [void]$out.Append('ITEM ' + $raw.Owner.Value + ' ' + [int]($null -eq $dacl) + $nl)",
  "    if ($null -ne $dacl) {",
  "      foreach ($ace in $dacl) {",
  "        if ($ace -is [Security.AccessControl.CommonAce]) {",
  "          [void]$out.Append('ACE ' + [int]$ace.AceQualifier + ' ' + [int]$ace.IsCallback + ' ' + $ace.SecurityIdentifier.Value + ' ' + $ace.AccessMask + ' ' + [int]$ace.AceFlags + $nl)",
  "        } else { [void]$out.Append('ACE OTHER' + $nl) }",
  "      }",
  "    }",
  "  } catch { [void]$out.Append('ITEM ERROR' + $nl) }",
  "}",
  "[Console]::Out.Write($out.ToString())"
].join("\n");

const cache = new Map();
let currentSid;

// %SystemRoot%, only when it is a drive path and equals %windir%: a UNC or drive-less value is refused.
export function systemRoot() {
  const root = process.env.SystemRoot;
  const windir = process.env.windir;
  if (!root || !/^[A-Za-z]:\\/.test(root) || !windir || root.toLowerCase() !== windir.toLowerCase()) return null;
  return root;
}

// Windows PowerShell under %SystemRoot%, or null when SystemRoot is unusable or the file is missing.
export function powershellPath() {
  const root = systemRoot();
  if (!root) return null;
  const file = path.win32.join(root, "System32", "WindowsPowerShell", "v1.0", "powershell.exe");
  return fs.existsSync(file) ? file : null;
}

// Run a fixed script in Windows PowerShell with a minimal environment, from %SystemRoot%. Returns the
// spawnSync result, or null when PowerShell is unavailable. The script goes in as -Command and must hold
// no double quote (Node's argument quoting would have to escape it); data goes in on stdin, never into
// the script text. -EncodedCommand was tried and printed nothing when started from Node (2026-11-17).
export function runPowerShell(script, input = "") {
  const ps = powershellPath();
  if (!ps || script.includes('"')) return null;
  const root = systemRoot();
  const env = { SystemRoot: root, windir: root, PSModulePath: path.win32.join(root, "System32", "WindowsPowerShell", "v1.0", "Modules") };
  return spawnSync(ps, ["-NoProfile", "-NonInteractive", "-Command", script], { input, env, cwd: root, encoding: "utf8", timeout: 60_000, windowsHide: true });
}

// Read owner and DACL for every path not already cached (real paths, as the callers pass them). A path
// that could not be read, or whose descriptor is not one this module understands, is cached as
// { error: true }; a failed or garbled PowerShell call throws. `fresh` re-reads every path, still in one
// call, for a check that must see the permissions as they are now, not as an earlier check found them.
export function readAcls(paths, { fresh = false } = {}) {
  if (fresh) for (const file of paths) cache.delete(file);
  const missing = [...new Set(paths)].filter((file) => !cache.has(file));
  if (missing.length > 0) {
    const input = missing.map((file) => Buffer.from(file, "utf8").toString("base64")).join("\n");
    const run = runPowerShell(ACL_SCRIPT, input);
    if (!run) throw new Error("Windows PowerShell was not found under %SystemRoot%");
    if (run.status !== 0) throw new Error("the ACL check could not run");
    const { me, items } = parseAclOutput(run.stdout);
    if (items.length !== missing.length) throw new Error("the ACL check returned unexpected output");
    currentSid = me;
    missing.forEach((file, i) => cache.set(file, items[i]));
  }
  return paths.map((file) => cache.get(file));
}

// Strict parser for the script's output. Exported for the tests.
export function parseAclOutput(text) {
  const lines = text.split(/\r?\n/).filter((line) => line !== "");
  const head = /^ME (\S+)$/.exec(lines[0] ?? "");
  if (!head || !isSid(head[1])) throw new Error("the ACL check returned unexpected output");
  const items = [];
  for (const line of lines.slice(1)) {
    const fields = line.split(" ");
    if (fields[0] === "ITEM") {
      if (fields.length === 2 && fields[1] === "ERROR") {
        items.push({ error: true });
      } else if (fields.length === 3 && isSid(fields[1]) && (fields[2] === "0" || fields[2] === "1")) {
        // A null DACL grants everyone everything.
        items.push(fields[2] === "1" ? { error: true } : { owner: fields[1], rules: [] });
      } else {
        throw new Error("the ACL check returned unexpected output");
      }
      continue;
    }
    const item = items[items.length - 1];
    if (fields[0] !== "ACE" || !item) throw new Error("the ACL check returned unexpected output");
    if (item.error) continue;
    const [, qualifier, callback, sid, mask, flags] = fields;
    const valid = fields.length === 6 && (qualifier === "0" || qualifier === "1") && callback === "0"
      && isSid(sid) && /^-?\d+$/.test(mask) && /^\d+$/.test(flags);
    if (!valid) {
      // A callback (conditional) entry, an audit or object entry, or anything malformed: fail closed.
      items[items.length - 1] = { error: true };
      continue;
    }
    item.rules.push({
      allow: qualifier === "0",
      sid,
      rights: Number(mask) >>> 0,
      inheritOnly: (Number(flags) & ACE_INHERIT_ONLY) !== 0,
      inherits: (Number(flags) & ACE_INHERITS) !== 0
    });
  }
  return { me: head[1], items };
}

// The current user's SID, read through PowerShell on first use.
export function currentUserSid() {
  if (currentSid === undefined) readAcls([systemRoot() ?? "C:\\Windows"]);
  return currentSid;
}

// What is wrong with one path's ACL, or null. `owner`: "me" (only the current user) or "trusted" (the
// current user, SYSTEM, Administrators or TrustedInstaller). `rights`: the mask another principal must not
// hold. `inheritable`: also count entries that only reach what is created inside (a directory something
// will be created in). Pure, so the tests can feed it synthetic ACLs.
export function aclProblem(info, me, { owner = "me", rights = WRITE_RIGHTS, inheritable = false } = {}) {
  if (!info || info.error) return "has an ACL that could not be read or is not plain (no DACL, or a conditional entry)";
  const ownerOk = info.owner === me || (owner === "trusted" && TRUSTED_OWNERS.has(info.owner));
  if (!ownerOk) return owner === "me" ? "is not owned by the current user" : "is owned by another user";
  for (const rule of info.rules) {
    if (!rule.allow || rule.sid === me || TRUSTED_OTHERS.has(rule.sid)) continue;
    if ((rule.rights & rights) === 0) continue;
    if (rule.inheritOnly && !(inheritable && rule.inherits)) continue;
    return `grants write, delete or permission changes to another account (${rule.sid})`;
  }
  return null;
}

// The directories above a real path, nearest first, up to the volume root.
export function ancestors(file) {
  const dirs = [];
  for (let dir = path.dirname(file); ; dir = path.dirname(dir)) {
    dirs.push(dir);
    if (path.dirname(dir) === dir) return dirs;
  }
}

// The problem with any directory above `file` that would let another account rename or replace an entry
// on the way down, so the path could be pointed at another file between a check and a read. Its owner
// must be the user, SYSTEM, Administrators or TrustedInstaller.
export function ancestorProblem(file, me = currentUserSid()) {
  const dirs = ancestors(file);
  const infos = readAcls(dirs);
  for (let i = 0; i < dirs.length; i += 1) {
    const problem = aclProblem(infos[i], me, { owner: "trusted", rights: REPLACE_RIGHTS });
    if (problem) return `a directory above it ${problem}`;
  }
  return null;
}

// Make a freshly created directory private to the user: chmod 0700 on POSIX; on Windows a protected DACL
// (no inherited entries) for the user, SYSTEM and Administrators, set with %SystemRoot%\System32\icacls.
// Throws when that fails, so the caller removes the directory instead of filling it.
export function makePrivateDir(dir) {
  if (process.platform !== "win32") {
    fs.chmodSync(dir, 0o700);
    return;
  }
  const root = systemRoot();
  if (!root) throw new Error("SystemRoot is not a usable drive path");
  const me = currentUserSid();
  execFileSync(path.win32.join(root, "System32", "icacls.exe"),
    [dir, "/inheritance:r", "/grant:r", `*${me}:(OI)(CI)F`, `*${SYSTEM}:(OI)(CI)F`, `*${ADMINISTRATORS}:(OI)(CI)F`],
    { cwd: root, env: { SystemRoot: root, windir: root }, stdio: "ignore", windowsHide: true, timeout: 30_000 });
  cache.delete(dir);
  // Read back, inheritable entries included: icacls succeeding is not proof the DACL is the one asked for.
  const [info] = readAcls([dir]);
  if (aclProblem(info, me, { inheritable: true }) !== null) throw new Error("the new directory could not be made private");
}
