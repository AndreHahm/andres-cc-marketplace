// Shared sensitive-filename pattern list. Extracted from
// codex-windows-guardrails/scripts/guarded-dispatch.mjs (which matches
// plugins/git-kit/scripts/scan-staged-files.sh's bash `case` statement,
// case-sensitively there since it handles git path strings that could
// originate from any platform's checkout) so this module has exactly one
// copy inside codex-kit instead of two independently hand-maintained ones.
// Case-insensitive matching is opt-in per caller via matchesSecretFilename's
// second argument, for callers running on a case-insensitive filesystem
// (Windows) that need to catch e.g. ".ENV"/"ID_RSA" too.
export const SECRET_FILENAME_PATTERNS = [
  /^\.env(\..*)?$/,
  /secret/,
  /credential/,
  /\.key$/,
  /\.pem$/,
  /password/,
  /token/,
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

export function matchesSecretFilename(basename, caseInsensitive = false) {
  const flags = caseInsensitive ? "i" : "";
  return SECRET_FILENAME_PATTERNS.find((re) => new RegExp(re.source, flags).test(basename));
}
