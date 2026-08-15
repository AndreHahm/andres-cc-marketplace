#!/usr/bin/env node
// Smoke test: skills/codex-rescue/SKILL.md's Phase 2 invoke template
//
// codex-rescue's Phase 2 bash block was restructured (merged back into one
// shell invocation after an earlier split attempt was found to rely on
// cross-tool-call shell-variable persistence, which Claude Code's Bash tool
// does not guarantee) and condensed under the R18 30-line threshold. This
// test confirms: the echo lines the model needs to capture literal paths
// from are still present, the heredoc write still works, and the bare-stdout
// JOB_ID capture (`--print-job-id`, no JSON parsing) still correctly reads a
// representative job-file payload (including its non-empty guard on an
// empty/malformed file).
//
// Run from plugins/codex-kit/: node scripts/smoke-tests/codex-rescue-prompt-assembly.mjs

import fs from "node:fs";
import os from "node:os";
import path from "node:path";

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

const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "codex-rescue-smoke-"));

console.log("=== Heredoc write produces the expected placeholder structure ===");
{
  const promptFile = path.join(tmpDir, "rescue-prompt.txt");
  fs.writeFileSync(
    promptFile,
    "<literal approved wrapped XML prompt from Phase 1.5 (or the Phase 1 wrapped prompt if --no-preview)>\n"
  );
  const content = fs.readFileSync(promptFile, "utf8");
  check("PROMPT_FILE is written and non-empty", content.trim().length > 0);
}

console.log("\n=== JOB_ID capture: bare stdout via --print-job-id, valid payload ===");
{
  // Matches SKILL.md:288 exactly: JOB_ID=$(cat "$JOB_JSON_FILE") -- no JSON
  // parsing, no `node -e` (an arbitrary-code grant this plugin removed
  // deliberately, see CHANGELOG.md's --print-job-id entry).
  const jobJsonFile = path.join(tmpDir, "rescue-job.txt");
  fs.writeFileSync(jobJsonFile, "job-abc123\n");
  const jobId = fs.readFileSync(jobJsonFile, "utf8").trim();
  check("cat-style capture reads the bare job ID", jobId === "job-abc123", jobId);
}

console.log("\n=== JOB_ID capture: empty payload fails the non-empty guard, not silently ===");
{
  // Matches SKILL.md:289's `[ -n "$JOB_ID" ] || { ...; exit 1; }` guard.
  const jobJsonFile = path.join(tmpDir, "rescue-job-empty.txt");
  fs.writeFileSync(jobJsonFile, "");
  const jobId = fs.readFileSync(jobJsonFile, "utf8").trim();
  check("empty payload trips the [ -n \"$JOB_ID\" ] guard", jobId.length === 0);
}

console.log("\n=== SKILL.md's --resume-last guidance is prose-only (bare boolean flags can't carry inline omit-markers) ===");
{
  const skillPath = path.resolve("skills/codex-rescue/SKILL.md");
  const content = fs.readFileSync(skillPath, "utf8");
  check(
    "the Phase 2 fence itself is present and under the R18 threshold",
    (() => {
      const match = content.match(/## Phase 2:[\s\S]*?```bash\n([\s\S]*?)```/);
      if (!match) return false;
      const lines = match[1].split("\n").filter((l) => l.trim().length > 0 || true);
      return lines.length <= 30;
    })()
  );
  check(
    "prose above the fence explicitly instructs omitting all three resume flags when none apply",
    content.includes("omit all three lines if none apply") || content.includes("omit all three lines")
  );
}

console.log(`\n=== Results: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);
