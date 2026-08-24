#!/usr/bin/env node
// Smoke test: scripts/lib/secret-filenames.mjs and its use in
// scripts/lib/git.mjs's formatUntrackedFile (via the exported
// collectReviewContext), which /codex-kit:review and
// /codex-kit:adversarial-review both build their Codex payload from.
//
// Confirms the fix: an untracked, non-gitignored secret-named file (e.g.
// id_rsa, secrets.json) is skipped by filename before its content is ever
// embedded in the review context sent to Codex -- git ls-files
// --others --exclude-standard removes the common gitignored .env case, but
// not this one.
//
// Run from plugins/codex-kit/: node scripts/smoke-tests/git-untracked-secret-screen.mjs

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { matchesSecretFilename } from "../lib/secret-filenames.mjs";
import { collectReviewContext } from "../lib/git.mjs";

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

function git(args, cwd) {
  return execFileSync("git", args, { cwd, stdio: ["ignore", "pipe", "pipe"], encoding: "utf8" });
}

console.log("=== matchesSecretFilename: unit-level pattern checks ===");
{
  check("id_rsa matches", Boolean(matchesSecretFilename("id_rsa")));
  check(".env matches", Boolean(matchesSecretFilename(".env")));
  check(".env.local matches", Boolean(matchesSecretFilename(".env.local")));
  check("secrets.json matches (contains 'secret')", Boolean(matchesSecretFilename("secrets.json")));
  check("README.md does not match", !matchesSecretFilename("README.md"));
  check(".ENV does not match case-sensitively by default", !matchesSecretFilename(".ENV"));
  check(".ENV matches when caseInsensitive is requested", Boolean(matchesSecretFilename(".ENV", true)));
}

console.log("\n=== collectReviewContext: an untracked secret file's content is never embedded ===");
{
  const repoRoot = fs.mkdtempSync(path.join(os.tmpdir(), "codex-kit-secret-screen-smoke-"));
  try {
    git(["init", "-q"], repoRoot);
    git(["config", "user.email", "smoke@test.local"], repoRoot);
    git(["config", "user.name", "Smoke Test"], repoRoot);
    fs.writeFileSync(path.join(repoRoot, "README.md"), "# scratch repo\n");
    git(["add", "README.md"], repoRoot);
    git(["commit", "-q", "-m", "initial"], repoRoot);

    const secretContent = "AKIA_FAKE_SECRET_VALUE_THAT_MUST_NOT_LEAK";
    fs.writeFileSync(path.join(repoRoot, "id_rsa"), secretContent);
    fs.writeFileSync(path.join(repoRoot, "notes.txt"), "ordinary untracked file, safe to include");

    const context = collectReviewContext(repoRoot, { mode: "working-tree" });
    const combined = JSON.stringify(context);

    check("the secret file's actual content never appears anywhere in the collected context", !combined.includes(secretContent));
    check("the ordinary untracked file's content DOES appear (screen isn't over-broad)", combined.includes("ordinary untracked file"));
    check("the secret file is named in the context, with a skip marker, not silently dropped", /id_rsa[\s\S]*skipped: filename matches sensitive-filename pattern/.test(combined));
  } finally {
    fs.rmSync(repoRoot, { recursive: true, force: true });
  }
}

console.log(`\n=== Results: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);
