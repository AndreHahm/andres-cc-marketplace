#!/usr/bin/env python3
"""
Initialize Claude Code plugin directory structure.

Creates a new plugin with proper structure, minimal manifest, and README template.

Usage:
    python init_plugin.py                      # Interactive mode
    python init_plugin.py my-plugin           # With plugin name
    python init_plugin.py my-plugin --description "Plugin description"
"""

import argparse
import json
import os
import sys
from pathlib import Path


def validate_plugin_name(name):
    """Validate plugin name follows kebab-case convention."""
    if not name:
        return False, "Plugin name cannot be empty"

    if ' ' in name:
        return False, "Plugin name cannot contain spaces (use hyphens)"

    if '_' in name:
        return False, "Plugin name should use kebab-case (hyphens, not underscores)"

    if name != name.lower():
        return False, "Plugin name should be lowercase"

    if not name.replace('-', '').isalnum():
        return False, "Plugin name should only contain lowercase letters, numbers, and hyphens"

    return True, ""


def prompt_yes_no(question, default=True):
    """Prompt for yes/no answer."""
    default_str = "Y/n" if default else "y/N"
    response = input(f"{question} ({default_str}): ").strip().lower()

    if not response:
        return default

    return response in ['y', 'yes']


def create_plugin_structure(plugin_name, description, author_name, author_email, components):
    """Create plugin directory structure with minimal configuration."""
    plugin_path = Path(plugin_name)

    # Check if directory already exists
    if plugin_path.exists():
        print(f"✗ Error: Directory '{plugin_name}' already exists")
        return False

    try:
        print(f"\nCreating plugin structure for '{plugin_name}'...")
        print("=" * 50)

        # Create main plugin directory
        plugin_path.mkdir(parents=True)
        print(f"✓ Created {plugin_name}/")

        # Create .claude-plugin directory
        claude_plugin_dir = plugin_path / ".claude-plugin"
        claude_plugin_dir.mkdir()
        print(f"✓ Created .claude-plugin/")

        # Create minimal plugin.json
        manifest = {"name": plugin_name}
        if description:
            manifest["description"] = description
        if author_name:
            manifest["author"] = {"name": author_name}
            if author_email:
                manifest["author"]["email"] = author_email

        manifest_path = claude_plugin_dir / "plugin.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        print(f"✓ Created .claude-plugin/plugin.json")

        # Create component directories
        for component in components:
            component_dir = plugin_path / component
            component_dir.mkdir()
            print(f"✓ Created {component}/")

        # Create README.md
        readme_content = generate_readme(plugin_name, description, components)
        readme_path = plugin_path / "README.md"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        print(f"✓ Created README.md")

        # Success message
        print("\n" + "=" * 50)
        print("✓ Plugin structure created successfully!")
        print("\nNext steps:")
        print(f"  1. cd {plugin_name}")

        if 'skills' in components:
            print(f"  2. Add your skills to {plugin_name}/skills/")
        if 'commands' in components:
            print(f"  3. Add your commands to {plugin_name}/commands/")
        if 'agents' in components:
            print(f"  4. Add your agents to {plugin_name}/agents/")

        print(f"  5. Generate complete manifest:")
        print(f"     python path/to/generate_manifest.py {plugin_name}/")
        print(f"  6. Validate plugin:")
        print(f"     python path/to/validate_plugin.py {plugin_name}/")

        return True

    except Exception as e:
        print(f"\n✗ Error creating plugin structure: {e}")
        # Cleanup on failure
        if plugin_path.exists():
            import shutil
            shutil.rmtree(plugin_path)
        return False


def generate_readme(plugin_name, description, components):
    """Generate README.md template."""
    readme = f"""# {plugin_name}

{description or "Description of what this plugin does."}

## Components

"""

    if 'skills' in components:
        readme += """### Skills

List of skills included in this plugin:

- **skill-name**: Brief description

"""

    if 'commands' in components:
        readme += """### Commands

Custom slash commands:

- `/command-name`: What it does

"""

    if 'agents' in components:
        readme += """### Agents

Specialized agents:

- **agent-name**: Capabilities

"""

    readme += """## Installation

### From Marketplace

```bash
/plugin marketplace add your-username/your-marketplace-repo
/plugin install """ + plugin_name + """
```

### From Local Path

```bash
/plugin install ./path/to/""" + plugin_name + """
```

## Usage

[Provide usage examples and instructions]

## Configuration

[Document any configuration options]

## Contributing

[Contributing guidelines if applicable]

## License

[Your license here - e.g., MIT, Apache-2.0]
"""

    return readme


def interactive_mode():
    """Run interactive plugin initialization."""
    print("Claude Code Plugin Initializer")
    print("=" * 50)
    print()

    # Get plugin name
    while True:
        plugin_name = input("Plugin name (kebab-case): ").strip()
        is_valid, error_msg = validate_plugin_name(plugin_name)
        if is_valid:
            break
        print(f"✗ {error_msg}")
        print()

    # Get description
    description = input("Description (optional): ").strip()

    # Get author info
    author_name = input("Author name (optional): ").strip()
    author_email = ""
    if author_name:
        author_email = input("Author email (optional): ").strip()

    # Get components
    print("\nComponents to include:")
    components = []
    if prompt_yes_no("Include skills directory?", default=True):
        components.append("skills")
    if prompt_yes_no("Include commands directory?", default=False):
        components.append("commands")
    if prompt_yes_no("Include agents directory?", default=False):
        components.append("agents")

    # Create structure
    return create_plugin_structure(plugin_name, description, author_name, author_email, components)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Initialize Claude Code plugin structure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python init_plugin.py                           # Interactive mode
  python init_plugin.py my-plugin                # Create plugin with name
  python init_plugin.py my-plugin \\
    --description "My plugin" \\
    --author "Your Name" \\
    --email "you@example.com" \\
    --components skills,commands
        """
    )

    parser.add_argument('plugin_name', nargs='?', help='Plugin name (kebab-case)')
    parser.add_argument('--description', help='Plugin description')
    parser.add_argument('--author', help='Author name')
    parser.add_argument('--email', help='Author email')
    parser.add_argument('--components', help='Components to include (comma-separated: skills,commands,agents)', default='skills')

    args = parser.parse_args()

    # Interactive mode if no plugin name provided
    if not args.plugin_name:
        success = interactive_mode()
        sys.exit(0 if success else 1)

    # Command-line mode
    plugin_name = args.plugin_name

    # Validate plugin name
    is_valid, error_msg = validate_plugin_name(plugin_name)
    if not is_valid:
        print(f"✗ Error: {error_msg}")
        sys.exit(1)

    # Parse components
    components = [c.strip() for c in args.components.split(',') if c.strip()]
    valid_components = {'skills', 'commands', 'agents'}
    invalid = set(components) - valid_components
    if invalid:
        print(f"✗ Error: Invalid components: {', '.join(invalid)}")
        print(f"Valid components: {', '.join(valid_components)}")
        sys.exit(1)

    # Create structure
    success = create_plugin_structure(
        plugin_name,
        args.description,
        args.author,
        args.email,
        components
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()