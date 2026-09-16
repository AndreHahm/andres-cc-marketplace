# Contributing to this repository

First of all, thank you for your interest in contributing to our project!

> This marketplace is still in conception and development — expect structure and conventions to
> shift as it matures.

There are several ways in which you can contribute, beyond writing code. The goal of this document is to provide a high-level overview of how you can get involved and how your contribution will be considered.

## Asking Questions

Do you have a question? Feel free to [open an issue](https://github.com/AndreHahm/andres-cc-marketplace/issues/new).

Project maintainers will be eager to listen from you and help you out. Please, try to compose a clear and concise question. The more information you provide, the better we will be able to help you.

## Reporting Issues

Do you have you identified a reproducible problem in our code? or have a feature request? We want to hear about it! Please follow the next steps:

### Look For an Existing Issue

Sometimes the issue you want to report is being already addressed, or is planned to be addressed soon. Before you create a new issue, please do a search in [open issues](https://github.com/AndreHahm/andres-cc-marketplace/issues) to see if the issue or feature request has already been filed.

If you find your issue already exists, do not hesitate to make relevant comments and add your [reaction](https://github.com/blog/2119-add-reactions-to-pull-requests-issues-and-comments). Please, use a reaction in place of a "+1" comment, we believe it's easy: 👍 for upvoting and 👎 for downvoting.

If you cannot find an existing issue that describes your bug or feature, [create a new issue](https://github.com/AndreHahm/andres-cc-marketplace/issues/new). Please include as much detail as possible.

### Writing Good Bug Reports and Feature Requests

Whenever possible, we ask you to file a single issue per problem and feature request. Please do not enumerate multiple bugs or feature requests in the same issue, as it may be hard to track the progress.

As you can imagine, the more information you can provide, the more likely someone will be successful at reproducing the issue and finding a fix.

### Development Setup

This is a [Claude Code](https://docs.claude.com/en/docs/claude-code) plugin marketplace — there is
no build step for the marketplace itself. To iterate on a plugin locally:

1. Clone this repository.
2. Run this repository's one-time local setup — installing dependencies and the pre-commit git
   hook that gates commits/pushes — per [docs/local-development.md](docs/local-development.md).
   Neither step happens automatically on clone or in CI; skipping it means your commits/pushes
   aren't gated by this repo's own lint/gitleaks/hygiene checks locally.
3. Point Claude Code at your local checkout as a marketplace source (e.g.
   `/plugin marketplace add /path/to/your/clone`) instead of the published one, so your local
   changes are picked up.
4. Edit the plugin under `plugins/<plugin-name>/`, then reload/reinstall it in Claude Code to
   pick up the change.

Each plugin may have its own additional setup (dependencies, scripts) — check that plugin's own
README or CONTRIBUTING.md under `plugins/<plugin-name>/` for specifics.

### Testing & Code Style

Match the existing style in the file you're editing. If your change alters what a skill, agent,
command, hook, or rule actually does (not just prose formatting), it needs to be tested before
it's merged — see the affected plugin's own conventions, or `.claude/rules/require-tests-for-behavior-changes.md`
for what counts as a test in this repository. A brand-new plugin should also declare its
preferred scripting language (Python or JavaScript/TypeScript) in its own README or
CONTRIBUTING.md — see `.claude/rules/require-declared-plugin-language.md`.

### Creating Pull Requests

If you feel brave enough to contribute directly code to the repository, you are more than welcome. Feel free to submit pull requests to this repository, which we will review according to the governance rules of the project.

Branch names follow this repository's `<type>/<description>` convention (e.g. `fix/broken-link`,
`feat/new-skill`).

### Governance

Any contribution you send to us will be addressed by the project maintainers following the governance rules described in the [GOVERNANCE.md](GOVERNANCE.md).

# Thank You!

Your contributions to open source, large or small, make great projects like this possible. Thank you for taking the time to contribute.
