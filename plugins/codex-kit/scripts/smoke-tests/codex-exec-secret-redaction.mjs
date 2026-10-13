#!/usr/bin/env node
// Smoke test: scripts/lib/codex-exec.mjs's redactSecrets
//
// Confirms the conservative, pattern-based secret redaction applied to the
// raw Codex stderr tail before it lands in a typed-failure `detail` -- that
// field is persisted verbatim into CI reports (scripts/marketplace_ci/
// review.py), and a real auth-failure stderr has been confirmed to reach
// this path (commit 91a6478). Pattern set is ported from analysis-kit's
// scripts/anls_redact_secrets.py (see that file's own docstring for the
// rationale behind each pattern and why a generic high-entropy catch-all
// was deliberately left out).
//
// Run from plugins/codex-kit/: node scripts/smoke-tests/codex-exec-secret-redaction.mjs

import { redactSecrets } from "../lib/codex-exec.mjs";

let pass = 0;
let fail = 0;

function check(label, condition, detail = "") {
  if (condition) {
    pass += 1;
    console.log(`PASS  ${label}`);
  } else {
    fail += 1;
    console.log(`FAIL  ${label}${detail ? " -- " + detail : ""}`);
  }
}

console.log("=== Authorization header ===");
{
  const redacted = redactSecrets("some log line\nAuthorization: Bearer abc123def456\nmore log");
  check("the Authorization line is redacted", !redacted.includes("abc123def456"), redacted);
  check("surrounding lines are preserved", redacted.includes("some log line") && redacted.includes("more log"), redacted);
}

console.log("\n=== Bearer token without an explicit header ===");
{
  const redacted = redactSecrets("auth failed, bearer sk-test-token-value-here-1234567890");
  check("the bearer token is redacted", !redacted.includes("sk-test-token-value-here-1234567890"), redacted);
}

console.log("\n=== dotenv-shaped secret line ===");
{
  const redacted = redactSecrets("OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz123456\nnext line unaffected");
  check("the KEY= line is redacted", !redacted.includes("sk-abcdefghijklmnopqrstuvwxyz123456"), redacted);
  check("an unrelated following line survives", redacted.includes("next line unaffected"), redacted);
}

console.log("\n=== dotenv-shaped assignment in the middle of a line (issue #546) ===");
{
  const value = "hunter2" + "abcdef";
  const redacted = redactSecrets(`could not read env DATABASE_PASSWORD=${value} then more`);
  check("the mid-line value is redacted", !redacted.includes(value), redacted);
  check("the name and surrounding prose survive", redacted.startsWith("could not read env DATABASE_PASSWORD=") && redacted.endsWith(" then more"), redacted);
  const quoted = redactSecrets(`failed: API_KEY="two words" and more`);
  check("a quoted mid-line value containing a space is redacted whole", !quoted.includes("two words") && quoted.endsWith(" and more"), quoted);
  const prose = "the password was rotated and the key is stored elsewhere";
  check("prose with no assignment is unchanged", redactSecrets(prose) === prose);
  const sorted = "error while sorting: sortKey=asc then more";
  check("a name that only contains a credential word is not redacted", redactSecrets(sorted) === sorted, redactSecrets(sorted));
  const monkey = "saw monkey=banana today";
  check("a substring match inside another word is not redacted", redactSecrets(monkey) === monkey, redactSecrets(monkey));
  const camel = redactSecrets(`failed with apiKey=${value} again`);
  check("a camelCase compound credential name is redacted", !camel.includes(value), camel);
  const bs = String.fromCharCode(92);
  for (const [label, quote] of [["double", '"'], ["single", "'"]]) {
    const atEnd = redactSecrets(`diag: API_KEY=${quote}two words${bs}`);
    check(`a ${label}-quoted spaced value ending in a lone backslash is redacted whole`, !atEnd.includes("words"), atEnd);
    const beforeNewline = redactSecrets(`diag: DB_PASSWORD=${quote}top secret${bs}\nnext line stays`);
    check(
      `a ${label}-quoted value ending in a backslash before a newline is redacted whole, next line kept`,
      !beforeNewline.includes("secret") && beforeNewline.endsWith("\nnext line stays"),
      beforeNewline
    );
  }
  const escapedQuote = redactSecrets(`diag: DB_PASSWORD="top ${bs}"secret" tail`);
  check("an escaped quote inside a quoted value still redacts through the closing quote", !escapedQuote.includes("secret") && escapedQuote.endsWith(" tail"), escapedQuote);
  for (const [label, text, survivor] of [
    ["LF", "error: API_KEY=\nnext line stays", "next line stays"],
    ["CRLF", "error: API_KEY=\r\nnext line stays", "next line stays"],
    ["a space before the newline", "error: API_KEY= \nnext line stays", "next line stays"],
    ["a newline before the equals sign", "error: API_KEY\n=value tail", "=value tail"],
  ]) {
    const out = redactSecrets(text);
    check(`an assignment's padding never spans a newline (${label})`, out === text || out.includes(survivor), out);
  }
  const tabbed = redactSecrets("error: API_KEY=\tabc123 tail");
  check("tab padding after the equals sign is still redacted", !tabbed.includes("abc123") && tabbed.endsWith(" tail"), tabbed);
  const camelPassword = redactSecrets(`request failed: databasePassword=${value} retrying`);
  check("a camelCase name ending in Password is redacted", !camelPassword.includes(value) && camelPassword.endsWith(" retrying"), camelPassword);
  const accessKey = redactSecrets(`using awsAccessKey=${value} now`);
  check("a camelCase accessKey compound is redacted", !accessKey.includes(value), accessKey);
  const unterminated =redactSecrets('stderr: API_KEY="abc\nlots of other diagnostic text\nmore');
  check(
    "an unterminated quote redacts only the rest of its own line",
    !unterminated.includes("abc") && unterminated.includes("lots of other diagnostic text") && unterminated.endsWith("\nmore"),
    unterminated
  );
}

console.log("\n=== AWS access key ===");
{
  const redacted = redactSecrets("credential: AKIAABCDEFGHIJKLMNOP in use");
  check("the AWS access key is redacted", !redacted.includes("AKIAABCDEFGHIJKLMNOP"), redacted);
}

console.log("\n=== GitHub token ===");
{
  const redacted = redactSecrets("using ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ab for auth");
  check("the GitHub token is redacted", !redacted.includes("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ab"), redacted);
}

console.log("\n=== Fine-grained GitHub token ===");
{
  const token = "github_pat_11ABCDEFG0abcdefghijklmnopqrstuvwxyz_0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  const redacted = redactSecrets(`using ${token} for auth`);
  check("the fine-grained GitHub token is redacted", !redacted.includes(token), redacted);
}

console.log("\n=== Slack token ===");
{
  const redacted = redactSecrets("token xoxb-1234567890-abcdefghijklmnop leaked");
  check("the Slack token is redacted", !redacted.includes("xoxb-1234567890-abcdefghijklmnop"), redacted);
}

console.log("\n=== Generic sk- token ===");
{
  const redacted = redactSecrets("key sk-ant-api03-abcdefghijklmnopqrstuvwxyz01234567 used");
  check("the sk- prefixed token is redacted", !redacted.includes("sk-ant-api03-abcdefghijklmnopqrstuvwxyz01234567"), redacted);
}

console.log("\n=== JWT ===");
{
  const jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U";
  const redacted = redactSecrets(`token: ${jwt}`);
  check("the JWT is redacted", !redacted.includes(jwt), redacted);
}

console.log("\n=== PEM private key block ===");
{
  const pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIBOgIBAAJBAK...\n-----END RSA PRIVATE KEY-----";
  const redacted = redactSecrets(`before\n${pem}\nafter`);
  check("the PEM block is redacted", !redacted.includes("MIIBOgIBAAJBAK"), redacted);
  check("surrounding text is preserved", redacted.includes("before") && redacted.includes("after"), redacted);
}

console.log("\n=== Plain error text with no secret-shaped content is unaffected ===");
{
  const plain = "Error: connection refused on port 8080 while contacting the codex CLI";
  const redacted = redactSecrets(plain);
  check("plain diagnostic text passes through unchanged", redacted === plain, redacted);
}

console.log("\n=== Bare word 'bearer' in prose is not over-redacted ===");
{
  // The bearer pattern previously matched \bbearer\b\s*[:=]?\s*.+$ -- the
  // bare word plus ANY trailing text on the line, which redacted ordinary
  // prose merely containing "bearer" wholesale, not just a real token.
  const prose = "the bearer of this document must sign here";
  const redacted = redactSecrets(prose);
  check("prose containing the bare word 'bearer' passes through unchanged", redacted === prose, redacted);
}

console.log(`\n=== Results: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);
