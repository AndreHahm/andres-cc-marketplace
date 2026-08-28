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

export function matchesSecretFilename(basename, caseInsensitive = false) {
  const flags = caseInsensitive ? "i" : "";
  return SECRET_FILENAME_PATTERNS.find((re) => new RegExp(re.source, flags).test(basename));
}
