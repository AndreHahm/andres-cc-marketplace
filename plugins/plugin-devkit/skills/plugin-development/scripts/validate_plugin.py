#!/usr/bin/env python3
"""
Validate Claude Code plugin structure and compliance.

Comprehensive validation of plugin directory structure, manifests, and components.

Usage:
    python validate_plugin.py /path/to/plugin                  # Full validation
    python validate_plugin.py /path/to/plugin --verbose        # Detailed output
    python validate_plugin.py /path/to/plugin --check structure  # Specific check
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


class ValidationResult:
    """Store validation results."""
    def __init__(self, category):
        self.category = category
        self.errors = []
        self.warnings = []
        self.checks_passed = 0
        self.checks_total = 0

    def add_check(self, passed, message=None):
        """Add a check result."""
        self.checks_total += 1
        if passed:
            self.checks_passed += 1
        else:
            self.errors.append(message or "Check failed")

    def add_warning(self, message):
        """Add a warning."""
        self.warnings.append(message)

    def is_passed(self):
        """Check if all validation passed."""
        return len(self.errors) == 0

    def print_results(self, verbose=False):
        """Print validation results."""
        status = "✓" if self.is_passed() else "✗"
        print(f"\n{status} {self.category} ({'passed' if self.is_passed() else 'failed'}) "
              f"({self.checks_passed}/{self.checks_total} checks)")

        if verbose or not self.is_passed():
            for i, error in enumerate(self.errors, 1):
                print(f"  ✗ ERROR: {error}")

        if self.warnings:
            for warning in self.warnings:
                print(f"  ⚠ WARNING: {warning}")

    def to_dict(self):
        """Machine-readable form for --json output."""
        return {
            "category": self.category,
            "passed": self.is_passed(),
            "checks_passed": self.checks_passed,
            "checks_total": self.checks_total,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


def validate_structure(plugin_path, verbose=False):
    """Validate plugin directory structure."""
    result = ValidationResult("Structure validation")

    # Check .claude-plugin directory exists
    claude_plugin_dir = plugin_path / ".claude-plugin"
    result.add_check(
        claude_plugin_dir.exists(),
        ".claude-plugin/ directory missing"
    )

    # Check plugin.json exists
    manifest_path = claude_plugin_dir / "plugin.json"
    result.add_check(
        manifest_path.exists(),
        ".claude-plugin/plugin.json missing (REQUIRED file)"
    )

    # Check component directories at root (not in .claude-plugin/)
    for component in ['skills', 'commands', 'agents']:
        wrong_location = claude_plugin_dir / component
        if wrong_location.exists():
            result.add_check(
                False,
                f"{component}/ found in .claude-plugin/ (should be at plugin root). "
                f"FIX: Move to {plugin_path}/{component}/"
            )
        else:
            result.add_check(True)  # Correct (not in wrong location)

    # Check directory naming (kebab-case recommended)
    for item in plugin_path.iterdir():
        if item.is_dir() and item.name not in ['.claude-plugin', '.git']:
            if '_' in item.name or item.name != item.name.lower():
                result.add_warning(
                    f"Directory '{item.name}' should use kebab-case (lowercase with hyphens)"
                )

    # Check README exists (recommended)
    readme_path = plugin_path / "README.md"
    if not readme_path.exists():
        result.add_warning("README.md missing (recommended for documentation)")
    else:
        result.add_check(True)

    return result


def validate_manifest(plugin_path, verbose=False):
    """Validate plugin.json manifest."""
    result = ValidationResult("Manifest validation")

    manifest_path = plugin_path / ".claude-plugin" / "plugin.json"

    if not manifest_path.exists():
        result.add_check(False, "plugin.json does not exist")
        return result

    # Check JSON syntax
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        result.add_check(True, "Valid JSON syntax")
    except json.JSONDecodeError as e:
        result.add_check(
            False,
            f"Invalid JSON syntax: {e}. FIX: Check for trailing commas, missing quotes, etc."
        )
        return result

    # Check required field: name
    if 'name' in manifest:
        name = manifest['name']
        result.add_check(True, "Required field 'name' present")

        # Validate name format
        if ' ' in name or '_' in name or name != name.lower():
            result.add_check(
                False,
                f"Plugin name '{name}' should be kebab-case (lowercase with hyphens). "
                f"FIX: Change to '{name.lower().replace('_', '-').replace(' ', '-')}'"
            )
        else:
            result.add_check(True, "Name format valid (kebab-case)")
    else:
        result.add_check(False, "Missing required field: 'name'. FIX: Add \"name\": \"plugin-name\"")

    # Validate version format if present
    if 'version' in manifest:
        version = manifest['version']
        semver_pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$'
        if re.match(semver_pattern, version):
            result.add_check(True, f"Version format valid: {version}")
        else:
            result.add_check(
                False,
                f"Version '{version}' should follow semver (e.g., 1.0.0, 2.1.3-beta). "
                f"FIX: Use format MAJOR.MINOR.PATCH"
            )

    # Check for absolute paths (should be relative)
    path_fields = ['skills', 'commands', 'agents', 'hooks', 'mcpServers']
    for field in path_fields:
        if field in manifest:
            path_value = manifest[field]
            if isinstance(path_value, str):
                if os.path.isabs(path_value):
                    result.add_check(
                        False,
                        f"Field '{field}' has absolute path: {path_value}. "
                        f"FIX: Use relative path starting with './' (e.g., './{field}')"
                    )
                elif not path_value.startswith('./'):
                    result.add_warning(
                        f"Field '{field}' path should start with './' (currently: {path_value})"
                    )

    # Check referenced files exist
    for field in path_fields:
        if field in manifest and isinstance(manifest[field], str):
            ref_path = plugin_path / manifest[field].lstrip('./')
            if not ref_path.exists():
                result.add_warning(
                    f"Referenced path '{manifest[field]}' in field '{field}' does not exist"
                )

    # Validate author structure if present
    if 'author' in manifest:
        author = manifest['author']
        if isinstance(author, dict):
            if 'email' in author:
                email = author['email']
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, email):
                    result.add_warning(f"Author email format may be invalid: {email}")
        elif isinstance(author, str):
            result.add_warning(
                "Author should be an object with 'name' field, not a string. "
                "FIX: Change to {\"name\": \"Your Name\"}"
            )

    # Type-check fields that must be arrays -- wrong type is a load error upstream, not a warning
    for field in ('keywords', 'dependencies'):
        if field in manifest and not isinstance(manifest[field], list):
            result.add_check(
                False,
                f"Field '{field}' must be an array, got {type(manifest[field]).__name__}. "
                f"FIX: Change to a JSON array, e.g. \"{field}\": [...]"
            )

    # Unrecognized top-level fields: Claude Code ignores these and `claude plugin validate`
    # reports them as warnings, not errors -- match that here rather than staying silent.
    # known_fields duplicates references/manifest-reference.md's field list -- if a new
    # field is documented there, add it here too, or this validator will warn on it.
    known_fields = {
        'name', '$schema', 'displayName', 'version', 'description', 'author',
        'homepage', 'repository', 'license', 'keywords', 'defaultEnabled',
        'dependencies', 'userConfig', 'channels', 'skills', 'commands', 'agents',
        'hooks', 'mcpServers', 'outputStyles', 'themes', 'lspServers', 'monitors',
        'experimental', 'settings',
    }
    for field in manifest:
        if field not in known_fields:
            result.add_warning(f"Unrecognized field '{field}' in plugin.json (ignored by Claude Code at load time)")

    return result


def validate_components(plugin_path, verbose=False):
    """Validate plugin components (skills, commands, agents)."""
    result = ValidationResult("Component validation")

    # Validate skills
    skills_dir = plugin_path / "skills"
    if skills_dir.exists():
        skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir()]
        if skill_dirs:
            for skill_dir in skill_dirs:
                skill_md = skill_dir / "SKILL.md"
                if not skill_md.exists():
                    result.add_check(
                        False,
                        f"Skill '{skill_dir.name}' missing SKILL.md file. "
                        f"FIX: Create {skill_md}"
                    )
                else:
                    # Validate YAML frontmatter
                    try:
                        with open(skill_md, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if content.startswith('---'):
                                frontmatter_end = content.find('---', 3)
                                if frontmatter_end > 0:
                                    result.add_check(True, f"Skill '{skill_dir.name}' has frontmatter")
                                else:
                                    result.add_check(
                                        False,
                                        f"Skill '{skill_dir.name}' has incomplete frontmatter (missing closing ---)"
                                    )
                            else:
                                result.add_check(
                                    False,
                                    f"Skill '{skill_dir.name}' missing YAML frontmatter. "
                                    f"FIX: Add frontmatter at top of SKILL.md"
                                )
                    except Exception as e:
                        result.add_check(False, f"Error reading {skill_md}: {e}")

    # Validate commands
    commands_dir = plugin_path / "commands"
    if commands_dir.exists():
        command_files = list(commands_dir.glob("*.md"))
        if command_files:
            for cmd_file in command_files:
                try:
                    with open(cmd_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if content.startswith('---'):
                            result.add_check(True, f"Command '{cmd_file.name}' has frontmatter")
                        else:
                            result.add_warning(
                                f"Command '{cmd_file.name}' missing YAML frontmatter (recommended)"
                            )
                except Exception as e:
                    result.add_warning(f"Error reading {cmd_file}: {e}")

    # Validate agents
    agents_dir = plugin_path / "agents"
    if agents_dir.exists():
        agent_files = list(agents_dir.glob("*.md"))
        if agent_files:
            result.add_check(True, f"Found {len(agent_files)} agent(s)")

    # Check if plugin has any components
    has_skills = (skills_dir.exists() and any(skills_dir.iterdir()))
    has_commands = (commands_dir.exists() and any(commands_dir.glob("*.md")))
    has_agents = (agents_dir.exists() and any(agents_dir.glob("*.md")))

    if not (has_skills or has_commands or has_agents):
        result.add_warning(
            "Plugin has no components (no skills, commands, or agents). "
            "Add components before distributing."
        )

    return result


def validate_2025_compliance(plugin_path, verbose=False):
    """Validate 2025 schema compliance (allowed-tools field in skills)."""
    result = ValidationResult("2025 schema compliance")

    skills_dir = plugin_path / "skills"
    if not skills_dir.exists():
        result.add_warning("No skills directory (2025 compliance check skipped)")
        return result

    skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir()]
    if not skill_dirs:
        result.add_warning("No skills found (2025 compliance check skipped)")
        return result

    for skill_dir in skill_dirs:
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue  # Already reported in component validation

        try:
            with open(skill_md, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.startswith('---'):
                    frontmatter_end = content.find('---', 3)
                    if frontmatter_end > 0:
                        frontmatter = content[3:frontmatter_end]

                        # Check for allowed-tools field
                        if 'allowed-tools:' in frontmatter or 'allowed_tools:' in frontmatter:
                            result.add_check(True, f"Skill '{skill_dir.name}' has allowed-tools field")
                        else:
                            result.add_check(
                                False,
                                f"Skill '{skill_dir.name}' missing 'allowed-tools' field (2025 schema requirement). "
                                f"FIX: Add to SKILL.md frontmatter: allowed-tools: Read, Write, Bash"
                            )
        except Exception as e:
            result.add_warning(f"Error checking 2025 compliance for {skill_dir.name}: {e}")

    return result


def main():
    """Main entry point."""
    sys.stdout.reconfigure(encoding='utf-8')

    parser = argparse.ArgumentParser(
        description="Validate Claude Code plugin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python validate_plugin.py my-plugin/              # Full validation
  python validate_plugin.py my-plugin/ --verbose    # Detailed output
  python validate_plugin.py my-plugin/ --check structure
  python validate_plugin.py my-plugin/ --check manifests
  python validate_plugin.py my-plugin/ --check components
  python validate_plugin.py my-plugin/ --check 2025
  python validate_plugin.py my-plugin/ --json       # Machine-readable output (CI)

Exit codes:
  0 - All validation passed
  1 - Validation failed (errors found)
  2 - Script execution error
        """
    )

    parser.add_argument('plugin_path', help='Path to plugin directory')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--check', choices=['structure', 'manifests', 'components', '2025'],
                        help='Run specific validation check only')
    parser.add_argument('--json', action='store_true',
                        help='Emit a single JSON object instead of human-readable output (for CI)')

    args = parser.parse_args()

    # Validate plugin path
    plugin_path = Path(args.plugin_path)
    if not plugin_path.exists():
        if args.json:
            print(json.dumps({"error": f"Plugin directory does not exist: {plugin_path}"}))
        else:
            print(f"✗ Error: Plugin directory does not exist: {plugin_path}")
        sys.exit(2)

    if not plugin_path.is_dir():
        if args.json:
            print(json.dumps({"error": f"Path is not a directory: {plugin_path}"}))
        else:
            print(f"✗ Error: Path is not a directory: {plugin_path}")
        sys.exit(2)

    if not args.json:
        print(f"Validating plugin: {plugin_path.name}")
        print("=" * 60)

    # Run validation checks
    results = []

    if not args.check or args.check == 'structure':
        results.append(validate_structure(plugin_path, args.verbose))

    if not args.check or args.check == 'manifests':
        results.append(validate_manifest(plugin_path, args.verbose))

    if not args.check or args.check == 'components':
        results.append(validate_components(plugin_path, args.verbose))

    if not args.check or args.check == '2025':
        results.append(validate_2025_compliance(plugin_path, args.verbose))

    # Summary
    total_errors = sum(len(r.errors) for r in results)
    total_warnings = sum(len(r.warnings) for r in results)
    all_passed = all(r.is_passed() for r in results)

    if args.json:
        print(json.dumps({
            "plugin": plugin_path.name,
            "passed": all_passed,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "results": [r.to_dict() for r in results],
        }, indent=2))
        sys.exit(0 if all_passed else 1)

    # Print results
    for result in results:
        result.print_results(args.verbose)

    print("\n" + "=" * 60)
    if all_passed:
        print("RESULT: PASSED")
        print("=" * 60)
        print(f"{total_errors} errors, {total_warnings} warnings")
        print("\n✓ Plugin is ready for distribution!")
    else:
        print("RESULT: FAILED")
        print("=" * 60)
        print(f"{total_errors} errors, {total_warnings} warnings")
        print("\nFix errors above before distributing plugin.")

    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()
