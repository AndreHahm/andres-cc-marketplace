# Skill Name

## Overview
[Brief description of what this skill does]

## Prerequisites
- Required software/libraries: Python 3.8+, requests library
- Environment variables (required):
  - `GITHUB_TOKEN`: Personal access token from https://github.com/settings/tokens
  - `API_ENDPOINT`: Your API endpoint URL
- Validation: Run `bash scripts/validate-env.sh` to verify setup

## Quick Start
[3-5 step usage with example]

## Common Workflows
- [Workflow 1]
- [Workflow 2]
- [Workflow 3]

## Validation
Run the validation script to test the skill:

```bash
bash scripts/validate-env.sh  # Verify environment setup
bash scripts/validate.sh      # Full skill validation
```

## Error Handling
[How the skill handles failures and what error messages mean]

## Security Notes

This skill requires credentials. Never hardcode them:

**Required environment variables:**
- `API_KEY`: Get from https://service.com/api-keys
- `SECRET_TOKEN`: Get from https://service.com/settings

**Setup:**
```bash
export API_KEY=your_key_here
export SECRET_TOKEN=your_token_here
bash scripts/validate-env.sh  # Verify setup
```

**See `references/secrets-and-credentials.md` for complete security guidance.**

## Troubleshooting
[Common issues and solutions]

## Support
Contact: [Team lead / owner]

## Version History
See [VERSION_HISTORY.md](../VERSION_HISTORY.md)
