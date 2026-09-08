import fs from "node:fs";
import path from "node:path";

// Shared sensitive-filename pattern list. Extracted from
// codex-windows-guardrails/scripts/guarded-dispatch.mjs (which matches
// plugins/git-kit/scripts/scan-staged-files.sh's bash `case` statement,
// case-sensitively there since it handles git path strings that could
// originate from any platform's checkout) so this module has exactly one
// copy inside codex-kit instead of two independently hand-maintained ones.
// Case-insensitive matching is opt-in per caller via matchesSecretFilename's
// second argument, for callers running on a case-insensitive filesystem
// (Windows) that need to catch e.g. ".ENV"/"ID_RSA" too.
// Named references (not just positions in the array below) so a caller that
// needs to identify one of these four specific patterns -- e.g.
// codex-windows-guardrails' documentation-about-secrets exemption
// (guarded-dispatch.mjs's isDocumentationAboutSecrets, issue #78) -- can
// compare by object identity instead of reconstructing a string view of the
// pattern (an earlier version of that exemption compared
// `String(matchedPattern)` against a hand-typed `"/secret/"`-shaped string
// Set; that silently breaks -- with no error anywhere -- the moment any of
// these four literals gains a flag or its source text changes here, since
// nothing would tie the two files' representations together). These four are
// deliberately loose bare-substring patterns (no anchor, no extension) --
// unlike every other entry below, which is anchored to an exact filename or
// extension -- which is exactly why a caller might need to treat them
// differently from the rest of the list.
const SECRET_KEYWORD = /secret/;
const CREDENTIAL_KEYWORD = /credential/;
const PASSWORD_KEYWORD = /password/;
const TOKEN_KEYWORD = /token/;

export const SECRET_FILENAME_PATTERNS = [
  /^\.env(\..*)?$/,
  SECRET_KEYWORD,
  CREDENTIAL_KEYWORD,
  /\.key$/,
  /\.pem$/,
  PASSWORD_KEYWORD,
  TOKEN_KEYWORD,
  /^id_rsa$/,
  /^id_ed25519$/,
  /^id_ecdsa$/,
  /^id_dsa$/,
  /^service-account\.json$/,
  /\.p12$/,
  /\.pfx$/,
  /\.jks$/,
  /^\.npmrc$/,
  /^\.pgpass$/,
  /^\.netrc$/
];

// Exported so a caller can identify a match against one of these four
// specific loose patterns via `.includes(matchedPattern)` (reference
// equality against the exact object matchesSecretFilename below returns),
// never by reconstructing and comparing a string form of the pattern.
export const LOOSE_SECRET_FILENAME_PATTERNS = [SECRET_KEYWORD, CREDENTIAL_KEYWORD, PASSWORD_KEYWORD, TOKEN_KEYWORD];

// The non-loose patterns from the list above -- .env, .key/.pem/.p12/.pfx/
// .jks, the SSH/cloud key exact-filenames, .npmrc/.pgpass/.netrc. Computed
// once, filtering LOOSE_SECRET_FILENAME_PATTERNS out by reference (never a
// re-typed literal list) so the two stay in sync automatically.
const STRICT_SECRET_FILENAME_PATTERNS = SECRET_FILENAME_PATTERNS.filter(
  (re) => !LOOSE_SECRET_FILENAME_PATTERNS.includes(re)
);

export function matchesSecretFilename(basename, caseInsensitive = false) {
  const flags = caseInsensitive ? "i" : "";
  return SECRET_FILENAME_PATTERNS.find((re) => new RegExp(re.source, flags).test(basename));
}

// matchesSecretFilename uses .find(), which returns only the FIRST pattern
// (in array order) that matches -- SECRET_FILENAME_PATTERNS lists the four
// loose keyword patterns interleaved with the strict ones, so "the matched
// pattern happens to be loose" does NOT prove no strict pattern also
// applies (e.g. "my-secret.pem" matches SECRET_KEYWORD, at index 1, before
// /\.pem$/ at index 4 is ever tried, even though .pem matches too).
// Security review finding (issue #295, C1): a caller that wants to know
// "does ANY strict pattern also match this basename" -- e.g. before trusting
// a loose-pattern-only exemption -- must check the full strict list
// directly, never infer it from matchesSecretFilename's single return value.
export function matchesAnyStrictSecretFilename(basename, caseInsensitive = false) {
  const flags = caseInsensitive ? "i" : "";
  return STRICT_SECRET_FILENAME_PATTERNS.some((re) => new RegExp(re.source, flags).test(basename));
}

// --- .secretlintignore consultation (issue #295) ---
//
// Deliberately EXACT-FULL-PATH-ONLY (an optional leading `/` is stripped,
// then the entire pattern must equal the entire repo-relative path) --
// NOT a general gitignore engine, and specifically NOT supporting a glob,
// a directory-prefix match, or a bare filename matched at any depth, even
// though .secretlintignore's own syntax is gitignore-compatible and does
// support all three there. This is narrower than gitignore semantics on
// purpose (security review finding, issue #295, C1): an earlier version of
// this function matched a `/tests`-shaped entry against anything *under*
// that directory, and a `*.ext`-shaped entry against any matching basename
// anywhere -- for THIS function's one caller (guarded-dispatch.mjs, gating
// an unsandboxed danger-full-access Codex process), that meant a single
// directory-scale .secretlintignore entry (e.g. `/.claude`) silently
// exempted every file under it, including a real, untracked `.env` inside
// a session worktree (`.claude/worktrees/*/`) -- a STRICT pattern match
// that must never be exemption-eligible regardless of location. Requiring
// an exact full-path match keeps every currently-real .secretlintignore
// entry working (they're all already exact paths) while removing that
// blast radius entirely: only a file explicitly, individually named in
// .secretlintignore -- never a whole directory or an extension class --
// can ever be exempted here. Comments (`#`) and blank lines are skipped.
// A `!`-negated exact-path entry IS honored, per real gitignore "last
// matching rule wins" semantics (Codex PR review finding, issue #295): a
// `.secretlintignore` listing `foo.py` then later `!foo.py` must end up
// NOT exempting `foo.py` -- an earlier version of this function returned
// on the first match found, so the later negation was silently never
// reached. Also NOT implemented via `git check-ignore`: that command always
// additionally consults real `.gitignore` files found in the working tree,
// with no flag to suppress that -- which is exactly the conflation this
// function exists to avoid (guarded-dispatch.mjs's walkFiles has its own
// documented design requiring it to see gitignored files like `.env`, so
// treating bare .gitignore membership as a skip signal here would reverse
// that).
//
// Callers must ALSO independently confirm no STRICT pattern matches the
// basename (matchesAnyStrictSecretFilename above) before treating a true
// result from this function as safe to exempt -- see that function's own
// header for why a "loose" match from matchesSecretFilename does not
// prove a strict one doesn't also apply. This function only answers "is
// this exact path listed", nothing about which pattern(s) matched it.
//
// Known limitation (security review, issue #295, informational): this
// reads the WORKING-TREE .secretlintignore unconditionally, with no
// trusted-base-SHA verification -- unlike security.yml's own CI job, which
// deliberately restores .secretlintignore from the PR's base SHA before
// ever reading it, specifically because a PR could otherwise weaken its
// own secret scan. A locally-run reviewer (e.g. codex-audit-loop against
// an untrusted, unmerged branch) has no such check today: that branch's
// own .secretlintignore edit is trusted as-is. Applying the same
// restore-from-base pattern locally needs a live `gh api`/network call
// this offline-capable script doesn't otherwise make -- left as a known,
// disclosed follow-up rather than folded into this fix.
let cachedPatterns = null;
let cachedRepoRoot = null;

function loadSecretlintignorePatterns(repoRoot) {
  if (cachedRepoRoot === repoRoot && cachedPatterns) {
    return cachedPatterns;
  }
  const patterns = [];
  let raw;
  try {
    raw = fs.readFileSync(path.join(repoRoot, ".secretlintignore"), "utf8");
  } catch {
    raw = "";
  }
  for (const rawLine of raw.split(/\r?\n/)) {
    // trimEnd only -- gitignore does not strip LEADING whitespace from a
    // pattern (a pattern " foo" matches a path literally named " foo"),
    // only trailing whitespace not itself escaped.
    const line = rawLine.trimEnd();
    if (!line || line.startsWith("#")) continue;
    patterns.push(line);
  }
  cachedRepoRoot = repoRoot;
  cachedPatterns = patterns;
  return patterns;
}

export function isExemptedBySecretlintignore(repoRoot, relativePath) {
  // A `..`-laden relativePath must never satisfy this exemption, matching
  // the same defense-in-depth guard isDocumentationAboutSecrets already
  // carries in guarded-dispatch.mjs for the identical reason.
  if (relativePath.startsWith("..")) return false;
  const patterns = loadSecretlintignorePatterns(repoRoot);
  if (patterns.length === 0) return false;
  const normalized = relativePath.split(path.sep).join("/");
  // Codex PR review finding (issue #295): gitignore semantics are "last
  // matching rule wins", including a `!`-negated rule re-including a path
  // an earlier rule already listed. An earlier version of this loop
  // `return true`d on the FIRST matching pattern, so a `.secretlintignore`
  // containing both `secret-helper.py` and a later `!secret-helper.py`
  // (a legitimate way to explicitly revoke an earlier exemption) was
  // silently ignored -- the file stayed wrongly exempt. Iterating the
  // whole list and keeping only the LAST match's verdict fixes this while
  // still supporting only exact-path entries (no glob) per this
  // function's own scope.
  let exempted = false;
  for (const pattern of patterns) {
    const negated = pattern.startsWith("!");
    const body = negated ? pattern.slice(1) : pattern;
    if (body.includes("*") || body.includes("?")) continue; // no globs
    const anchored = body.startsWith("/") ? body.slice(1) : body;
    if (anchored === normalized) {
      exempted = !negated;
    }
  }
  return exempted;
}
