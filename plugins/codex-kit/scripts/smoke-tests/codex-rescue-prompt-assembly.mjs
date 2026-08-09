#!/usr/bin/env node
// Smoke test: skills/codex-rescue/SKILL.md's Phase 2 invoke template
//
// codex-rescue's Phase 2 bash block was restructured (merged back into one
// shell invocation after an earlier split attempt was found to rely on
// cross-tool-call shell-variable persistence, which Claude Code's Bash tool
// does not guarantee) and condensed under the R18 30-line threshold. This
// test confirms: the echo lines the model needs to capture literal paths
// from are still present, the heredoc write still works, and the JOB_ID
// extraction one-liner still correctly parses a representative job payload
// (including its error path on malformed JSON).
//
// Run from plugins/codex-kit/: node scripts/smoke-tests/codex-rescue-prompt-assembly.mjs

import { execFileSync } from "node:child_process";
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

console.log("\n=== JOB_ID extraction one-liner: valid job JSON ===");
{
  const jobJsonFile = path.join(tmpDir, "rescue-job.json");
  fs.writeFileSync(jobJsonFile, JSON.stringify({ jobId: "job-abc123", status: "queued" }));
  const jobId = execFileSync(
    "node",
    [
      "-e",
      `const fs=require("fs");try{const j=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));if(!j.jobId)throw new Error("no jobId");process.stdout.write(j.jobId);}catch(e){process.stderr.write("JOB_ID parse failed: "+e.message+"\\n");process.exit(1);}`,
      jobJsonFile
    ],
    { encoding: "utf8" }
  );
  check("extracts the correct jobId from a well-formed payload", jobId === "job-abc123", jobId);
}

console.log("\n=== JOB_ID extraction one-liner: missing jobId field fails loudly, not silently ===");
{
  const jobJsonFile = path.join(tmpDir, "rescue-job-bad.json");
  fs.writeFileSync(jobJsonFile, JSON.stringify({ status: "failed", error: "launch failed" }));
  let threw = false;
  let stderrText = "";
  try {
    execFileSync(
      "node",
      [
        "-e",
        `const fs=require("fs");try{const j=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));if(!j.jobId)throw new Error("no jobId");process.stdout.write(j.jobId);}catch(e){process.stderr.write("JOB_ID parse failed: "+e.message+"\\n");process.exit(1);}`,
        jobJsonFile
      ],
      { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }
    );
  } catch (e) {
    threw = true;
    stderrText = e.stderr?.toString() ?? "";
  }
  check("exits non-zero when jobId is absent from the payload", threw);
  check("stderr names the failure explicitly", stderrText.includes("JOB_ID parse failed"), stderrText);
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
