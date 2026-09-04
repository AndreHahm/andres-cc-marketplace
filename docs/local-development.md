# Local Development Setup

One-time setup after cloning this repo.

## Install dependencies

```bash
uv sync --group dev
```

## Install the pre-commit git hook

`.pre-commit-config.yaml` defines the hooks (gitleaks, linters, standard hygiene checks) that gate
commits and pushes in this repo, but `pre-commit install` only writes to `.git/hooks/` in your own
local checkout — it is not something git clones, and no CI job runs it on your behalf. Every clone
needs to run this once:

```bash
uv run pre-commit install
```

This installs hooks for `pre-commit`, `pre-push`, `commit-msg`, `post-checkout`, `post-merge`, and
`post-rewrite` (see `.pre-commit-config.yaml`'s `default_install_hook_types`). Without this step,
`git commit`/`git push` in this checkout are not gated by any of the configured checks, even though
the configuration file itself is present.
