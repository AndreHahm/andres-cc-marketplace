#!/usr/bin/env node
// Functional regression test for this repo's two issue-labeling mechanisms:
// the keyword-regex step in workflows/issue-opened-labeler.yml (t:/p:
// labels) and the github/issue-labeler config in .github/issue-labeler.yml
// (a: labels). Extracts the real regex patterns directly from those source
// files -- rather than hand-duplicating them here -- so this test can't
// silently drift from what actually ships; a parser mismatch fails loudly
// instead of testing stale copies. Run with: node .github/scripts/test-issue-auto-labeling.js
'use strict';
const fs = require('fs');
const path = require('path');

const GITHUB_DIR = path.resolve(__dirname, '..');

function extractKeywordPatterns() {
  const yml = fs.readFileSync(path.join(GITHUB_DIR, 'workflows/issue-opened-labeler.yml'), 'utf8');
  const start = yml.indexOf('const patterns = [');
  const end = yml.indexOf('];', start);
  if (start === -1 || end === -1) {
    throw new Error('Could not locate the patterns array in issue-opened-labeler.yml -- this test is out of sync with the workflow file');
  }
  const block = yml.slice(start, end);
  // Capture pattern/flags separately and build via `new RegExp(...)` --
  // never eval() a string parsed out of a file this repo's own PRs can
  // modify (Codacy finding: an eval() on file-derived content is a real
  // code-execution risk regardless of how trusted the source normally is;
  // `new RegExp` can at worst build a slow pattern, never run arbitrary JS).
  const entryRe = /\{\s*label:\s*'([^']+)',\s*regex:\s*\/((?:\\.|[^/\\])*)\/([a-z]*)\s*\}/g;
  const patterns = [];
  let m;
  while ((m = entryRe.exec(block))) {
    const [, label, source, flags] = m;
    patterns.push({ label, regex: new RegExp(source, flags) });
  }
  if (patterns.length !== 6) {
    throw new Error(`Extracted ${patterns.length} keyword patterns, expected 6 -- parser likely out of sync with the workflow file`);
  }
  return patterns;
}

function extractAreaPatterns() {
  const yml = fs.readFileSync(path.join(GITHUB_DIR, 'issue-labeler.yml'), 'utf8');
  const lines = yml.split('\n');
  const patterns = [];
  let currentLabel = null;
  for (const line of lines) {
    const labelMatch = line.match(/^"([^"]+)":\s*$/);
    if (labelMatch) {
      currentLabel = labelMatch[1];
      continue;
    }
    const regexMatch = line.match(/^\s*-\s*'\/((?:\\.|[^/\\])*)\/([a-z]*)'\s*$/);
    if (regexMatch && currentLabel) {
      const [, source, flags] = regexMatch;
      // `new RegExp` from parsed file content (Codacy finding) -- accepted,
      // not removed: this is the whole point of extracting real patterns
      // instead of hand-duplicating them (see this function's own purpose).
      // Lower risk than eval() (worst case is a slow pattern via ReDoS, not
      // code execution), and this script isn't wired into any CI gate that
      // would run it against an unreviewed PR's content automatically.
      patterns.push({ label: currentLabel, regex: new RegExp(source, flags) });
      currentLabel = null;
    }
  }
  if (patterns.length !== 5) {
    throw new Error(`Extracted ${patterns.length} area patterns, expected 5 -- parser likely out of sync with .github/issue-labeler.yml`);
  }
  return patterns;
}

// Duplicated from issue-opened-labeler.yml's own stripTemplateBoilerplate --
// small and stable enough that hand-copying (with this comment as the
// tripwire) is a reasonable tradeoff against the complexity of extracting a
// whole function body via text parsing. Keep this in sync if that function
// changes.
function stripTemplateBoilerplate(s) {
  return s
    .replace(/<!--[\s\S]*?-->/g, ' ')
    .replace(/^\s*-\s*\[\s\]\s.*$/gm, ' ')
    .replace(/^#{1,6}\s.*$/gm, ' ');
}

function classify(patterns, text) {
  return patterns.filter((p) => p.regex.test(text)).map((p) => p.label);
}

let failures = 0;
function check(name, actual, expected) {
  const a = JSON.stringify([...actual].sort());
  const e = JSON.stringify([...expected].sort());
  const ok = a === e;
  if (!ok) {
    failures++;
    console.error(`FAIL ${name}: got ${a}, expected ${e}`);
  } else {
    console.log(`OK   ${name}`);
  }
}

const keywordPatterns = extractKeywordPatterns();
const areaPatterns = extractAreaPatterns();

console.log('=== Plural-form regression (PR #324 review, CodeRabbit + Codex) ===');
check('t:bug plural', classify(keywordPatterns, 'There are 3 bugs in this'), ['t: bug']);
check('t:security plural', classify(keywordPatterns, 'Multiple exploits found'), ['t: security']);
check('t:performance plural', classify(keywordPatterns, 'Several regressions and memory leaks'), ['t: performance']);
check('t:documentation plural', classify(keywordPatterns, 'Found two typos'), ['t: documentation']);
check('t:feature plural', classify(keywordPatterns, 'Two feature requests here'), ['t: feature']);
check('p:critical plural', classify(keywordPatterns, 'Multiple blockers found'), ['p: critical']);
check('a:github-actions plural', classify(areaPatterns, 'GitHub Actions caching is broken'), ['a: github-actions']);
check('a:github-actions plural (workflow files)', classify(areaPatterns, 'The workflow files are misconfigured'), ['a: github-actions']);
check('a:ai-setup plural', classify(areaPatterns, 'Several subagents failed'), ['a: ai-setup']);
check('a:tests plural (unit tests)', classify(areaPatterns, 'Unit tests fail on Windows'), ['a: tests']);
check('a:tests plural (test suites)', classify(areaPatterns, 'Test suites time out'), ['a: tests']);
check('a:architecture plural (decisions)', classify(areaPatterns, 'Need some design decisions documented'), ['a: architecture']);
check('a:architecture plural (ADRs)', classify(areaPatterns, 'Multiple ADRs needed'), ['a: architecture']);

console.log('\n=== Round-2 coverage gaps (PR #324 review, Codex) ===');
check('a:github-actions (CI workflow wording)', classify(areaPatterns, 'CI workflow fails on fork PRs'), ['a: github-actions']);
check('a:github-actions (GitHub workflow wording)', classify(areaPatterns, 'GitHub workflow is broken'), ['a: github-actions']);
check('a:tests (bare plural)', classify(areaPatterns, 'Tests fail on Windows'), ['a: tests']);
// Deliberately plural-only -- singular "test" (a verb, not this area's
// noun) must NOT match, since it would false-positive on
// feature_request.md's own boilerplate ("I can help test this feature").
check('a:tests (singular verb form does not match)', classify(areaPatterns, 'I can help test this feature'), []);

console.log('\n=== Original singular cases still work (no regression) ===');
check('t:bug singular', classify(keywordPatterns, 'App crashes on startup with a stack traceback'), ['t: bug']);
check('t:feature singular', classify(keywordPatterns, '[FEATURE] Add dark mode support'), ['t: feature']);
check('t:documentation singular', classify(keywordPatterns, 'README has a typo'), ['t: documentation']);
check('t:security singular', classify(keywordPatterns, 'SQL injection vulnerability (CVE-2026-12345)'), ['t: security']);
check('t:performance singular', classify(keywordPatterns, 'Dashboard is very slow'), ['t: performance']);
check('p:critical singular', classify(keywordPatterns, 'URGENT: production is down, blocker for release'), ['p: critical']);
check('neutral (keyword)', classify(keywordPatterns, 'Just a general question about usage'), []);
check('a:github-actions singular', classify(areaPatterns, 'The pr-auto-label.yml workflow file fails on fork PRs'), ['a: github-actions']);
check('a:ai-setup singular', classify(areaPatterns, "Claude Code's plugin-devkit skill isn't loading"), ['a: ai-setup']);
check('a:dependencies', classify(areaPatterns, 'pyproject.toml pins an old ruff version'), ['a: dependencies']);
check('a:tests singular', classify(areaPatterns, 'pytest suite is flaky in CI'), ['a: tests']);
check('a:architecture singular', classify(areaPatterns, 'Need an ADR for this'), ['a: architecture']);
check('neutral (area)', classify(areaPatterns, 'Just a general question about usage'), []);

console.log('\n=== Template-boilerplate false-positive fix (PR #324 review, Codex, P1) ===');
const KNOWN_ISSUE_TEMPLATES = new Set(['skill_improvement.md', 'bug_report.md', 'feature_request.md']);
function templateBody(name) {
  // Every call site below passes a literal, but Codacy's static analysis
  // can't prove that interprocedurally -- an explicit allowlist makes this
  // provably safe rather than relying on "every caller happens to be a
  // literal today."
  if (!KNOWN_ISSUE_TEMPLATES.has(name)) {
    throw new Error(`templateBody: unexpected template name ${JSON.stringify(name)}`);
  }
  return fs.readFileSync(path.resolve(GITHUB_DIR, `ISSUE_TEMPLATE/${name}`), 'utf8').split(/^---\s*$/m)[2] || '';
}
check('skill_improvement.md scaffolding, stripped', classify(keywordPatterns, stripTemplateBoilerplate(templateBody('skill_improvement.md'))), []);
check('bug_report.md scaffolding, stripped', classify(keywordPatterns, stripTemplateBoilerplate(templateBody('bug_report.md'))), []);
// feature_request.md is a disclosed, accepted residual, not a regression to
// catch here: its own prompt prose ("What problem does this feature
// address?") still contributes t: feature on an unedited issue -- redundant
// with, not contradictory to, that template's own "t: enhancement" label
// (see stripTemplateBoilerplate's own comment in issue-opened-labeler.yml).
check('feature_request.md scaffolding, stripped (known residual, not a bug)', classify(keywordPatterns, stripTemplateBoilerplate(templateBody('feature_request.md'))), ['t: feature']);

console.log('\n=== Checked checkbox still counts (strip only removes UNCHECKED) ===');
check('checked checkbox still matches', classify(keywordPatterns, stripTemplateBoilerplate('- [x] Improve SKILL.md documentation')), ['t: documentation']);

console.log('\n=== HTML comment stripped but real surrounding prose still matches ===');
const realBugReport = stripTemplateBoilerplate(
  '<!-- Severity: Critical/High/Medium/Low + brief explanation. -->\nThis is causing a production outage, extremely urgent.'
);
check('real urgent text still matches despite comment strip', classify(keywordPatterns, realBugReport), ['p: critical']);

console.log(failures === 0 ? '\nALL PASS' : `\n${failures} FAILURE(S)`);
process.exit(failures === 0 ? 0 : 1);
