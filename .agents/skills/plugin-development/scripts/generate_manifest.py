#!/usr/bin/env python3
"""
Generate or update plugin.json manifest.

Creates a valid plugin.json file with comprehensive metadata.

Usage:
    python generate_manifest.py /path/to/plugin          # Interactive
    python generate_manifest.py /path/to/plugin --update # Update existing
    python generate_manifest.py /path/to/plugin --template standard
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


TEMPLATES = {
    'minimal': ['name'],
    'standard': ['name', 'version', 'description', 'author'],
    'complete': ['name', 'version', 'description', 'author', 'homepage', 'repository', 'license', 'keywords']
}


def validate_plugin_name(name):
    """Validate plugin name follows kebab-case."""
    if not name:
        return False, "Name cannot be empty"
    if ' ' in name or '_' in name:
        return False, "Use kebab-case (lowercase with hyphens)"
    if name != name.lower():
        return False, "Name must be lowercase"
    return True, ""


def validate_version(version):
    """Validate semantic version format."""
    if not version:
        return True, ""  # Optional
    pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$'
    if re.match(pattern, version):
        return True, ""
    return False, "Version must follow semver (e.g., 1.0.0, 2.1.3-beta)"


def validate_email(email):
    """Validate email format."""
    if not email:
        return True, ""  # Optional
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        return True, ""
    return False, "Invalid email format"


def validate_url(url):
    """Validate URL format."""
    if not url:
        return True, ""  # Optional
    if url.startswith('http://') or url.startswith('https://'):
        return True, ""
    return False, "URL must start with http:// or https://"


def load_existing_manifest(plugin_path):
    """Load existing plugin.json if it exists."""
    manifest_path = plugin_path / ".claude-plugin" / "plugin.json"
    if manifest_path.exists():
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"⚠ Warning: Existing plugin.json has invalid JSON")
            return {}
    return {}


def prompt_with_validation(prompt_text, validator=None, default="", allow_empty=True):
    """Prompt user with validation."""
    while True:
        if default:
            response = input(f"{prompt_text} [{default}]: ").strip()
            if not response:
                response = default
        else:
            response = input(f"{prompt_text}: ").strip()

        if not response and allow_empty:
            return ""

        if not response and not allow_empty:
            print("✗ This field is required")
            continue

        if validator:
            is_valid, error_msg = validator(response)
            if not is_valid:
                print(f"✗ {error_msg}")
                continue

        return response


def interactive_manifest_generation(plugin_path, existing_manifest, template_fields):
    """Generate manifest interactively."""
    print(f"\nGenerating plugin.json for {plugin_path.name}")
    print("=" * 60)
    print("Press Enter to skip optional fields or accept defaults")
    print()

    manifest = {}

    # Name (required)
    if 'name' in template_fields:
        default_name = existing_manifest.get('name', plugin_path.name)
        name = prompt_with_validation(
            "Plugin name",
            validator=validate_plugin_name,
            default=default_name,
            allow_empty=False
        )
        manifest['name'] = name

    # Version (recommended)
    if 'version' in template_fields:
        default_version = existing_manifest.get('version', '1.0.0')
        version = prompt_with_validation(
            "Version",
            validator=validate_version,
            default=default_version
        )
        if version:
            manifest['version'] = version

    # Description (recommended)
    if 'description' in template_fields:
        default_desc = existing_manifest.get('description', '')
        description = prompt_with_validation("Description", default=default_desc)
        if description:
            manifest['description'] = description

    # Author (recommended)
    if 'author' in template_fields:
        existing_author = existing_manifest.get('author', {})
        author_name = prompt_with_validation(
            "Author name",
            default=existing_author.get('name', '')
        )
        if author_name:
            author = {'name': author_name}

            author_email = prompt_with_validation(
                "Author email",
                validator=validate_email,
                default=existing_author.get('email', '')
            )
            if author_email:
                author['email'] = author_email

            author_url = prompt_with_validation(
                "Author URL",
                validator=validate_url,
                default=existing_author.get('url', '')
            )
            if author_url:
                author['url'] = author_url

            manifest['author'] = author

    # Homepage (optional)
    if 'homepage' in template_fields:
        homepage = prompt_with_validation(
            "Homepage URL",
            validator=validate_url,
            default=existing_manifest.get('homepage', '')
        )
        if homepage:
            manifest['homepage'] = homepage

    # Repository (optional)
    if 'repository' in template_fields:
        repository = prompt_with_validation(
            "Repository URL",
            validator=validate_url,
            default=existing_manifest.get('repository', '')
        )
        if repository:
            manifest['repository'] = repository

    # License (optional)
    if 'license' in template_fields:
        default_license = existing_manifest.get('license', 'MIT')
        license_id = prompt_with_validation("License", default=default_license)
        if license_id:
            manifest['license'] = license_id

    # Keywords (optional)
    if 'keywords' in template_fields:
        existing_keywords = existing_manifest.get('keywords', [])
        default_keywords = ', '.join(existing_keywords) if existing_keywords else ''
        keywords_str = prompt_with_validation(
            "Keywords (comma-separated)",
            default=default_keywords
        )
        if keywords_str:
            keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
            if keywords:
                manifest['keywords'] = keywords

    # Component paths (optional, advanced)
    print("\nComponent paths (optional - press Enter for defaults):")
    print("Use relative paths starting with ./ (e.g., ./skills/)")
    print()

    skills_path = prompt_with_validation(
        "Skills path",
        default=existing_manifest.get('skills', '')
    )
    if skills_path:
        manifest['skills'] = skills_path

    commands_path = prompt_with_validation(
        "Commands path",
        default=existing_manifest.get('commands', '')
    )
    if commands_path:
        manifest['commands'] = commands_path

    agents_path = prompt_with_validation(
        "Agents path",
        default=existing_manifest.get('agents', '')
    )
    if agents_path:
        manifest['agents'] = agents_path

    return manifest


def save_manifest(plugin_path, manifest):
    """Save manifest to plugin.json."""
    claude_plugin_dir = plugin_path / ".claude-plugin"
    claude_plugin_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = claude_plugin_dir / "plugin.json"

    try:
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, sort_keys=False)
            f.write('\n')  # Add newline at end

        print(f"\n✓ Saved to {manifest_path}")
        return True
    except Exception as e:
        print(f"\n✗ Error saving manifest: {e}")
        return False


def validate_manifest(manifest):
    """Validate generated manifest."""
    errors = []

    # Required field
    if 'name' not in manifest:
        errors.append("Missing required field: name")

    # Validate name format
    if 'name' in manifest:
        is_valid, error = validate_plugin_name(manifest['name'])
        if not is_valid:
            errors.append(f"Invalid name: {error}")

    # Validate version if present
    if 'version' in manifest:
        is_valid, error = validate_version(manifest['version'])
        if not is_valid:
            errors.append(f"Invalid version: {error}")

    # Validate author email if present
    if 'author' in manifest and isinstance(manifest['author'], dict):
        if 'email' in manifest['author']:
            is_valid, error = validate_email(manifest['author']['email'])
            if not is_valid:
                errors.append(f"Invalid author email: {error}")

    # Validate URLs
    for url_field in ['homepage', 'repository']:
        if url_field in manifest:
            is_valid, error = validate_url(manifest[url_field])
            if not is_valid:
                errors.append(f"Invalid {url_field}: {error}")

    return errors


def print_manifest_preview(manifest):
    """Print formatted manifest preview."""
    print("\n" + "=" * 60)
    print("Generated plugin.json:")
    print("=" * 60)
    print(json.dumps(manifest, indent=2))
    print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate plugin.json manifest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_manifest.py my-plugin/              # Interactive
  python generate_manifest.py my-plugin/ --update     # Update existing
  python generate_manifest.py my-plugin/ --template standard
  python generate_manifest.py my-plugin/ --template complete

Templates:
  minimal  - Only required fields (name)
  standard - Recommended fields (name, version, description, author)
  complete - All fields with examples
        """
    )

    parser.add_argument('plugin_path', help='Path to plugin directory')
    parser.add_argument('--update', action='store_true', help='Update existing manifest')
    parser.add_argument('--template', choices=['minimal', 'standard', 'complete'],
                        default='standard', help='Manifest template')

    args = parser.parse_args()

    # Validate plugin path
    plugin_path = Path(args.plugin_path)
    if not plugin_path.exists():
        print(f"✗ Error: Plugin directory does not exist: {plugin_path}")
        sys.exit(1)

    if not plugin_path.is_dir():
        print(f"✗ Error: Path is not a directory: {plugin_path}")
        sys.exit(1)

    # Load existing manifest if updating
    existing_manifest = {}
    if args.update or (plugin_path / ".claude-plugin" / "plugin.json").exists():
        existing_manifest = load_existing_manifest(plugin_path)
        if existing_manifest:
            print(f"✓ Loaded existing manifest")

    # Get template fields
    template_fields = TEMPLATES[args.template]

    # Generate manifest interactively
    manifest = interactive_manifest_generation(plugin_path, existing_manifest, template_fields)

    # Print preview
    print_manifest_preview(manifest)

    # Validate
    errors = validate_manifest(manifest)
    if errors:
        print("\n✗ Validation errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    print("\n✓ Validation: All checks passed")

    # Save
    success = save_manifest(plugin_path, manifest)

    if success:
        print("\nNext steps:")
        print(f"  1. Review {plugin_path}/.claude-plugin/plugin.json")
        if not (plugin_path / "skills").exists() and not (plugin_path / "commands").exists():
            print(f"  2. Add components (skills, commands, agents)")
        print(f"  3. Validate: python validate_plugin.py {plugin_path}/")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()