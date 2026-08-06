#!/usr/bin/env python3
"""
Package skills into Claude Code plugin format.

Copies skills from source directory to plugin skills/ directory with validation.

Usage:
    python package_skills.py /source/skills /target/plugin     # Package all
    python package_skills.py /source/skills /target/plugin --validate
    python package_skills.py /source/skills /target/plugin --dry-run
    python package_skills.py /source/skills /target/plugin --skills skill1,skill2
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path


class SkillPackager:
    """Package skills into plugin format."""

    def __init__(self, source_dir, plugin_dir, verbose=False):
        self.source_dir = Path(source_dir)
        self.plugin_dir = Path(plugin_dir)
        self.verbose = verbose
        self.skills_packaged = []
        self.skills_warnings = {}
        self.total_size = 0

    def find_skills(self, skill_names=None):
        """Find skills in source directory."""
        if not self.source_dir.exists():
            print(f"✗ Error: Source directory does not exist: {self.source_dir}")
            return []

        all_skills = []
        for item in self.source_dir.iterdir():
            if item.is_dir():
                skill_md = item / "SKILL.md"
                if skill_md.exists():
                    if not skill_names or item.name in skill_names:
                        all_skills.append(item)

        return sorted(all_skills, key=lambda x: x.name)

    def validate_skill_2025(self, skill_dir):
        """Check if skill is 2025 compliant (has allowed-tools field)."""
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            return False, "SKILL.md not found"

        try:
            with open(skill_md, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.startswith('---'):
                    return False, "Missing YAML frontmatter"

                frontmatter_end = content.find('---', 3)
                if frontmatter_end <= 0:
                    return False, "Incomplete YAML frontmatter (missing closing ---)"

                frontmatter = content[3:frontmatter_end]
                if 'allowed-tools:' not in frontmatter and 'allowed_tools:' not in frontmatter:
                    return False, "Missing 'allowed-tools' field (2025 schema)"

                return True, "2025 compliant"
        except Exception as e:
            return False, f"Error reading SKILL.md: {e}"

    def get_directory_size(self, directory):
        """Calculate total size of directory."""
        total = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total += os.path.getsize(filepath)
        return total

    def format_size(self, size_bytes):
        """Format size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def count_files(self, directory):
        """Count total files in directory."""
        count = 0
        for _, _, filenames in os.walk(directory):
            count += len(filenames)
        return count

    def copy_skill(self, skill_dir, target_skills_dir, dry_run=False):
        """Copy a skill to plugin skills directory."""
        target_path = target_skills_dir / skill_dir.name

        if target_path.exists():
            if self.verbose:
                print(f"  ⚠ Skill '{skill_dir.name}' already exists in target, skipping")
            return False

        size = self.get_directory_size(skill_dir)
        file_count = self.count_files(skill_dir)

        if dry_run:
            print(f"  [DRY-RUN] Would copy {skill_dir.name} ({self.format_size(size)}, {file_count} files)")
            return True

        try:
            shutil.copytree(skill_dir, target_path)
            self.total_size += size
            if self.verbose:
                print(f"  ✓ Copied {skill_dir.name} ({self.format_size(size)}, {file_count} files)")
            return True
        except Exception as e:
            print(f"  ✗ Error copying {skill_dir.name}: {e}")
            return False

    def package_skills(self, skills, validate=False, dry_run=False):
        """Package list of skills."""
        if not skills:
            print("No skills found to package")
            return False

        # Create target skills directory
        target_skills_dir = self.plugin_dir / "skills"
        if not dry_run:
            target_skills_dir.mkdir(parents=True, exist_ok=True)

        print(f"\nFound {len(skills)} skill(s) to package")

        # Validate if requested
        if validate:
            print("\nValidating skills (2025 schema compliance)...")
            for skill_dir in skills:
                is_valid, message = self.validate_skill_2025(skill_dir)
                if is_valid:
                    if self.verbose:
                        print(f"  ✓ {skill_dir.name}: {message}")
                else:
                    print(f"  ⚠ {skill_dir.name}: WARNING - {message}")
                    self.skills_warnings[skill_dir.name] = message

            valid_count = len(skills) - len(self.skills_warnings)
            print(f"\nResults: {valid_count} valid, {len(self.skills_warnings)} warning(s)")

        # Package skills
        print("\nPackaging skills...")
        for skill_dir in skills:
            success = self.copy_skill(skill_dir, target_skills_dir, dry_run)
            if success:
                self.skills_packaged.append(skill_dir.name)

        return True

    def update_manifest(self, dry_run=False):
        """Update plugin.json with skills reference (optional)."""
        manifest_path = self.plugin_dir / ".claude-plugin" / "plugin.json"
        if not manifest_path.exists():
            return  # No manifest to update

        if dry_run:
            print("\n[DRY-RUN] Would update plugin.json with skills reference")
            return

        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            # Add skills reference if not present
            if 'skills' not in manifest and self.skills_packaged:
                manifest['skills'] = "./skills/"
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    json.dump(manifest, f, indent=2)
                    f.write('\n')
                if self.verbose:
                    print("\n✓ Updated plugin.json with skills reference")
        except Exception as e:
            print(f"\n⚠ Warning: Could not update plugin.json: {e}")

    def print_summary(self):
        """Print packaging summary."""
        print("\n" + "=" * 60)
        print(f"✓ {len(self.skills_packaged)} skill(s) packaged successfully")
        if self.total_size > 0:
            print(f"✓ Total size: {self.format_size(self.total_size)}")

        if self.skills_warnings:
            print(f"\nWarnings ({len(self.skills_warnings)}):")
            for skill_name, warning in self.skills_warnings.items():
                print(f"  ⚠ {skill_name}: {warning}")
                if "2025 schema" in warning:
                    print(f"    FIX: Add to {skill_name}/SKILL.md frontmatter:")
                    print(f"         allowed-tools: Read, Write, Bash")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Package skills into Claude Code plugin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Package all skills
  python package_skills.py .claude/skills my-plugin/

  # Package with 2025 compliance validation
  python package_skills.py .claude/skills my-plugin/ --validate

  # Package specific skills
  python package_skills.py .claude/skills my-plugin/ \\
    --skills skill1,skill2,skill3

  # Dry run (preview what would be packaged)
  python package_skills.py .claude/skills my-plugin/ --dry-run

  # Verbose output
  python package_skills.py .claude/skills my-plugin/ --verbose
        """
    )

    parser.add_argument('source_dir', help='Source directory containing skills')
    parser.add_argument('plugin_dir', help='Target plugin directory')
    parser.add_argument('--skills', help='Comma-separated list of specific skills to package')
    parser.add_argument('--validate', action='store_true', help='Validate skills for 2025 compliance')
    parser.add_argument('--dry-run', action='store_true', help='Preview without actually copying')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    # Parse skill names if provided
    skill_names = None
    if args.skills:
        skill_names = [s.strip() for s in args.skills.split(',') if s.strip()]

    # Initialize packager
    packager = SkillPackager(args.source_dir, args.plugin_dir, args.verbose)

    # Print header
    print(f"Packaging skills into plugin: {Path(args.plugin_dir).name}")
    print("=" * 60)
    print(f"Source: {args.source_dir}")
    print(f"Target: {args.plugin_dir}")
    if args.dry_run:
        print("[DRY-RUN MODE - No files will be copied]")
    print()

    # Find skills
    print(f"Scanning {args.source_dir} for skills...")
    skills = packager.find_skills(skill_names)

    if not skills:
        if skill_names:
            print(f"✗ No skills found matching: {', '.join(skill_names)}")
        else:
            print(f"✗ No skills found in {args.source_dir}")
        print("\nNote: Skills must have a SKILL.md file to be recognized")
        sys.exit(1)

    # List found skills
    if args.verbose or len(skills) <= 10:
        for skill in skills:
            print(f"  ✓ {skill.name}")
    else:
        for skill in skills[:3]:
            print(f"  ✓ {skill.name}")
        print(f"  ... ({len(skills) - 6} more)")
        for skill in skills[-3:]:
            print(f"  ✓ {skill.name}")

    # Package skills
    success = packager.package_skills(skills, validate=args.validate, dry_run=args.dry_run)

    if not success:
        sys.exit(1)

    # Update manifest
    if not args.dry_run:
        packager.update_manifest(args.dry_run)

    # Print summary
    packager.print_summary()

    # Next steps
    if not args.dry_run:
        print("\nNext steps:")
        if packager.skills_warnings:
            print("  1. Fix warnings (add allowed-tools to skills)")
        print(f"  2. Review {args.plugin_dir}/skills/ directory")
        print(f"  3. Update README.md with skill list")
        print(f"  4. Validate: python validate_plugin.py {args.plugin_dir}/")
        print(f"  5. Test: /plugin install {args.plugin_dir}/ (local test)")

    sys.exit(0)


if __name__ == '__main__':
    main()