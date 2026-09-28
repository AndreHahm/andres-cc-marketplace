import fs from "node:fs";
import path from "node:path";

export function loadPromptTemplate(rootDir, name) {
  const promptPath = path.join(rootDir, "prompts", `${name}.md`);
  return fs.readFileSync(promptPath, "utf8");
}

export function interpolateTemplate(template, variables) {
  return template.replace(/\{\{([A-Z_]+)\}\}/g, (_, key) => {
    if (!Object.prototype.hasOwnProperty.call(variables, key)) return "";
    return neutralizeClosingTags(String(variables[key]));
  });
}

// Untrusted values (git diffs, session transcripts, arbitrary documents)
// substituted into a template may contain a literal closing tag matching
// the template's own enclosing trust-boundary block (e.g.
// `</repository_context>`, `</claude_response_evidence>`), which would
// let the content escape its declared boundary and be read as task-level
// text instead of evidence -- closes a Critical finding from the
// 2026-08-12 audit. Break any closing-tag-shaped substring generically
// (not scoped to today's specific tag names) so it can no longer match a
// real template delimiter regardless of which tag a caller's template
// happens to use.
// Whitespace-tolerant: a model reads `</repository_context >` or
// `</ repository_context>` as the same closing delimiter a strict XML
// parser would reject, so the exact-match form alone leaves those variants
// unneutralized -- widened after a security review found the gap.
//
// Replacement marker: `(/$1)`, not a backslash-escaped `<\/$1>` -- a
// second security review correctly pointed out that `<\/tag>` is still
// tag-shaped and a model can plausibly still read it as the real closing
// delimiter despite the backslash. `(/$1)` isn't shaped like a delimiter
// at all, matching the same non-tag-shaped marker the shell-side
// neutralization (shared-skill-conventions.md §4) already uses.
function neutralizeClosingTags(value) {
  return value.replace(/<\s*\/\s*([a-zA-Z_][a-zA-Z0-9_-]*)\s*>/g, "(/$1)");
}
