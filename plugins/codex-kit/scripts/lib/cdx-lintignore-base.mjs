import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

// Trusted-base ignore-file consultation for codex-windows-guardrails' whole-
// repo secret scan (guarded-dispatch.mjs).
//
// WHY THIS EXISTS: cdx-secret-filenames.mjs's isExemptedBySecretlintignore is
// deliberately exact-full-path-only and reads the WORKING-TREE
// .secretlintignore (issue #295, C1 + its documented trust-boundary
// limitation). Both choices protect an unsandboxed danger-full-access
// dispatch from a directory-scale entry exempting an untracked `.env`, and
// from a PR branch editing its own exemptions. They also meant a file whose
// CONTENT legitimately looks secret-shaped (a redactor's own smoke test, a
// fixture with fake credentials) could never be cleared at all: every
// exemption still ends in a content scan that such a file fails by design.
//
// WHAT THIS ADDS (two helpers sharing one trusted base):
//
// 1. createBaseVerifier -- a second, strictly narrower exemption tier with
//    full gitignore syntax (anchored `/dir`, `*`, `**`, `!` negation -- git
//    itself does the matching) that is safe because it never trusts the
//    working tree:
//      a. The patterns come from `.secretlintignore` as committed at the
//         merge base with the default branch, never from the checkout -- a
//         branch cannot add its own exemption to THIS tier. (The older
//         exact-path tier in cdx-secret-filenames.mjs still reads the
//         working-tree file and always content-scans what it exempts: the
//         disclosed limit of issue #295.)
//      b. The candidate file must exist at the same path in that base commit
//         as a regular file (mode 100644/100755, never a symlink) AND its
//         current content must hash to the base blob, hashed with the BASE's
//         .gitattributes (a branch cannot pick a filter/ident rewrite that
//         makes an edited file collide with the base blob). An edited,
//         untracked, or newly-added file is never exempted, which is also
//         what makes a directory-scale entry safe (the original C1 exploit
//         was an UNTRACKED `.env` under a directory entry; an untracked file
//         has no base blob).
//      c. Matching is evaluated in a throwaway empty repo that carries only
//         the base patterns as its `.gitignore`, with global/system git
//         config and templates disabled, so this repo's own `.gitignore`
//         (whose `!.agents/`/`!.claude/` negations otherwise win over
//         core.excludesFile) and the user's global excludes stay out of the
//         verdict.
//    The caller still independently rejects any strict-pattern filename
//    (matchesAnyStrictSecretFilename) before using a true result.
//
// 2. gitignoreUnchangedSinceBase -- the scan skips untracked files the
//    repository ignores; that skip is only trustworthy if the .gitignore
//    files that define it are the base's, since a branch under review could
//    otherwise add `*` and blind the scan to every untracked file on the
//    reviewer's disk. This reports whether any tracked .gitignore differs
//    from the base (or the base is unknown); the caller then scans everything.
//
// Every git call uses an ABSOLUTE git executable resolved from PATH only
// (gitExecutable). On Windows, libuv resolves a bare program name against
// the child's working directory first -- live-verified with a stand-in
// `git.exe` in the cwd when NoDefaultCurrentDirectoryInExePath is unset --
// so a branch under review could otherwise commit its own git.exe at the
// repo root and have the gate run it before any guard.
//
// Fails closed: if the base cannot be resolved (no origin remote, shallow
// clone without the merge base, git missing) both helpers degrade to the
// stricter behaviour and the caller falls back to the existing exact-path
// tier unchanged.
//
// Known limitations: a new or changed entry only takes effect once it is in
// the base, i.e. after merge; as in gitignore itself, a file under an
// excluded directory cannot be re-included by a `!` entry; and if `origin`
// is itself attacker-controlled (a contributor clone of a fork) the "trusted"
// base is too, bounded by the byte-identical-to-base requirement above.

const MAX_BUFFER = 64 * 1024 * 1024;
const REGULAR_FILE_MODES = new Set(["100644", "100755"]);
// Remote-tracking names only; keeps an option-shaped ref from reaching git.
const SAFE_REF = /^origin\/[A-Za-z0-9._/-]+$/;

const STRIPPED_GIT_ENV = new Set([
  "GIT_DIR",
  "GIT_WORK_TREE",
  "GIT_INDEX_FILE",
  "GIT_COMMON_DIR",
  "GIT_OBJECT_DIRECTORY",
  "GIT_ALTERNATE_OBJECT_DIRECTORIES",
  "GIT_CONFIG_PARAMETERS",
  "GIT_CONFIG_COUNT"
]);

const cachedGit = new Map();

// Canonical form (realpath resolves junctions/symlinks and 8.3 short names);
// a path that does not exist cannot be resolved, so it falls back to its
// lexical form -- a PATH entry that does not exist supplies no git.exe anyway.
function canonicalLower(p) {
  try {
    return fs.realpathSync.native(p).toLowerCase();
  } catch {
    return path.resolve(p).toLowerCase();
  }
}

function withinRoot(dirNorm, rootNorm) {
  const rel = path.relative(rootNorm, dirNorm);
  if (rel === "") return true;
  if (path.isAbsolute(rel)) return false;
  // Parent traversal is a whole path SEGMENT (exactly '..', or '..' followed by a separator); a child folder
  // that merely starts with two dots (e.g. "..bin") is inside the root.
  return rel !== ".." && !rel.startsWith(".." + path.sep);
}

// Inside the root by EITHER its lexical or its canonical spelling, so a
// junction or 8.3 alias into the repo cannot be used to name an in-repo folder.
function isInsideRoot(dir, root) {
  const lexical = (p) => path.resolve(p).toLowerCase();
  return withinRoot(lexical(dir), lexical(root)) || withinRoot(canonicalLower(dir), canonicalLower(root));
}

// Absolute path of git, searching PATH only -- never the cwd, never a
// relative or empty PATH entry, and (security re-review M-1) never a PATH
// folder that is the repo root or inside it: an activated `.venv\Scripts` or
// `node_modules\.bin` in the worktree is routinely prepended to PATH, and a
// branch under review can commit a `git.exe` there. Pass the repo root being
// scanned as `excludeRoot`; the answer is cached per root. null when none is
// found (callers fail closed: execFileSync(null, ...) throws, which every
// caller already treats as "git unavailable"). Off Windows the bare name is
// already safe (execvp does not search the cwd for a name without a slash).
export function gitExecutable(excludeRoot) {
  if (process.platform !== "win32") return "git";
  const key = excludeRoot ? path.resolve(excludeRoot).toLowerCase() : "";
  if (cachedGit.has(key)) return cachedGit.get(key);
  let found = null;
  for (const raw of (process.env.PATH || process.env.Path || "").split(path.delimiter)) {
    const dir = raw.replace(/^"|"$/g, "");
    if (!dir || !path.isAbsolute(dir)) continue;
    if (excludeRoot && isInsideRoot(dir, excludeRoot)) continue;
    const candidate = path.join(dir, "git.exe");
    try {
      if (fs.statSync(candidate).isFile()) {
        found = candidate;
        break;
      }
    } catch {
      // not in this directory
    }
  }
  cachedGit.set(key, found);
  return found;
}

export function gitEnv(extra = {}) {
  const env = { ...process.env };
  // An inherited GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE (e.g. from a git hook)
  // would redirect every call to a different repository or index, and an
  // inherited object-store or injected-config variable would change which
  // objects/config git trusts. Windows keeps each key's original case, so
  // match case-insensitively. The caller's own `extra` is applied afterwards.
  for (const key of Object.keys(env)) {
    if (STRIPPED_GIT_ENV.has(key.toUpperCase())) delete env[key];
  }
  // A refs/replace/* object must not substitute the base blob or commit.
  env.GIT_NO_REPLACE_OBJECTS = "1";
  return { ...env, ...extra };
}

// Windows rejects os.devNull ("\\.\nul") as a git config path (verified live);
// "NUL" is what it accepts.
export const NULL_DEVICE = process.platform === "win32" ? "NUL" : "/dev/null";

// Returns trimmed stdout, or null on any failure (non-zero exit, git missing).
function runGit(args, cwd, extraEnv = {}, root = cwd) {
  try {
    return execFileSync(gitExecutable(root), args, {
      cwd,
      env: gitEnv(extraEnv),
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
      windowsHide: true,
      maxBuffer: MAX_BUFFER
    }).trim();
  } catch {
    return null;
  }
}

function resolveDefaultBranchRef(repoRoot) {
  const head = runGit(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], repoRoot);
  const candidates = [head, "origin/main", "origin/master"].filter((ref) => ref && SAFE_REF.test(ref));
  for (const ref of candidates) {
    if (runGit(["rev-parse", "--verify", "--quiet", `${ref}^{commit}`], repoRoot)) return ref;
  }
  return null;
}

export function resolveTrustedBase(repoRoot) {
  const ref = resolveDefaultBranchRef(repoRoot);
  if (!ref) return null;
  const base = runGit(["merge-base", "HEAD", ref], repoRoot);
  return base && /^[0-9a-f]{40,64}$/.test(base) ? base : null;
}

// true only when a base exists AND no tracked .gitignore (root or nested)
// differs from it -- committed, added, deleted or uncommitted edits all count.
// Untracked .gitignore files (e.g. the one pip/uv write inside .venv) cannot
// come from a branch under review, so they are not compared.
// The pathspec is case-INSENSITIVE on purpose: on NTFS git reads a tracked
// `dir/.GITIGNORE` as an ignore file (verified live: it hid an untracked
// credentials.json), but a plain `:(glob)**/.gitignore` does not match that name.
export function gitignoreUnchangedSinceBase(repoRoot, base = resolveTrustedBase(repoRoot)) {
  if (!base) return false;
  try {
    execFileSync(gitExecutable(repoRoot), ["diff", "--quiet", base, "--", ":(glob,icase)**/.gitignore"], {
      cwd: repoRoot,
      env: gitEnv(),
      stdio: "ignore",
      windowsHide: true
    });
    return true; // exit 0: no difference
  } catch {
    return false; // exit 1 (differs) or any error: scan everything
  }
}

// Returns { base, isExempt(relativePath), dispose() } or null (fail closed).
// `base` is the trusted merge base; pass an already-resolved one (as
// guarded-dispatch.mjs does) so a scan resolves it once, not once per helper.
export function createBaseVerifier(repoRoot, base = resolveTrustedBase(repoRoot)) {
  if (!base) return null;
  // Read the raw blob (runGit trims) so a pattern's trailing escapes survive.
  let ignoreText;
  try {
    ignoreText = execFileSync(gitExecutable(repoRoot), ["show", `${base}:.secretlintignore`], {
      cwd: repoRoot,
      env: gitEnv(),
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
      windowsHide: true,
      maxBuffer: MAX_BUFFER
    });
  } catch {
    return null;
  }

  const matcherEnv = { GIT_CONFIG_GLOBAL: NULL_DEVICE, GIT_CONFIG_NOSYSTEM: "1" };
  const isolated = ["-c", "core.excludesFile=", "-c", "core.ignorecase=false"];
  let matcherDir;
  try {
    matcherDir = fs.mkdtempSync(path.join(os.tmpdir(), "cdx-lintignore-base-"));
    if (runGit(["init", "-q", "--template="], matcherDir, matcherEnv, repoRoot) === null) {
      throw new Error("matcher repo init failed");
    }
    fs.writeFileSync(path.join(matcherDir, ".gitignore"), ignoreText);
  } catch {
    if (matcherDir) fs.rmSync(matcherDir, { recursive: true, force: true });
    return null;
  }

  const matchesBasePatterns = (posixPath) => {
    try {
      execFileSync(gitExecutable(repoRoot), [...isolated, "check-ignore", "-q", "--no-index", "--", posixPath], {
        cwd: matcherDir,
        env: gitEnv(matcherEnv),
        stdio: "ignore",
        windowsHide: true
      });
      return true; // exit 0: ignored
    } catch {
      return false; // exit 1 (not ignored) or any error: fail closed
    }
  };

  return {
    base,
    isExempt(relativePath) {
      try {
        // A path escaping the root, or an absolute one, is never exempt.
        if (!relativePath || relativePath.startsWith("..") || path.isAbsolute(relativePath)) return false;
        const posixPath = relativePath.split(path.sep).join("/");
        const absolutePath = path.join(repoRoot, relativePath);

        // Provenance 1: a regular file in the base commit at this exact path.
        // --full-tree + a returned-path equality check, so a pathspec quirk
        // can never make a different entry stand in for this one.
        const tree = runGit(["ls-tree", "--full-tree", base, "--", posixPath], repoRoot);
        const entry = tree && tree.split("\n")[0].match(/^(\d{6}) blob ([0-9a-f]{40,64})\t(.*)$/);
        if (!entry || !REGULAR_FILE_MODES.has(entry[1]) || entry[3] !== posixPath) return false;

        // Provenance 2: a regular file on disk (never a symlink), same content,
        // hashed with the BASE's attributes. A git too old for --attr-source
        // errors here, which reads as "not exempt".
        if (!fs.lstatSync(absolutePath).isFile()) return false;
        const currentBlob = runGit(
          [`--attr-source=${base}`, "hash-object", `--path=${posixPath}`, "--", absolutePath],
          repoRoot
        );
        if (currentBlob !== entry[2]) return false;

        // Only then does the (base) pattern match decide.
        return matchesBasePatterns(posixPath);
      } catch {
        return false;
      }
    },
    dispose() {
      try {
        fs.rmSync(matcherDir, { recursive: true, force: true });
      } catch {
        // best effort; a leaked temp dir is not a security property
      }
    }
  };
}
