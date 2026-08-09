# Require a Declared Plugin Language

## When this applies

Creating a new plugin in this marketplace, before its first script file is written.

## Rule

A new plugin must declare one preferred scripting language — Python or JavaScript/TypeScript, per
`plugin-rulebook`'s R24 allowed-language whitelist — in its own documentation (README.md or
CONTRIBUTING.md) at creation time. New scripts added to that plugin afterward should stay consistent
with the declared language rather than mixing both across the same plugin.

This is forward-looking only: it governs new plugins and new scripts added going forward. It does not
require auditing or flagging any existing plugin's current language usage — no retroactive sweep is
part of this rule.

## Why

R24 already restricts which languages are allowed repo-wide (Python/Bash/JS-TS), but says nothing about
whether one plugin should stay internally consistent about which of those it uses for its own scripts.
Without a declared language, a plugin can accumulate scripts in both Python and JS/TS over time with no
stated reason, making it harder for a maintainer to know which toolchain to reach for when adding the
next script. Scoped to forward-looking only (2026-08-09 decision) to avoid a large, out-of-scope
inventory pass across every existing plugin's current mixed usage.
