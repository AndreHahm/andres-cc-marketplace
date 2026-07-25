#!/usr/bin/env python3
"""
Skill Repairer - Automatically diagnoses and fixes common skill issues

Usage:
    repair_skill.py <skill-name>
    repair_skill.py --diagnose <skill-name>
    repair_skill.py --list-issues

Examples:
    repair_skill.py ts-foundation-restorer
    repair_skill.py --diagnose my-broken-skill
    repair_skill.py --list-issues
"""

import sys
import yaml
from pathlib import Path
from quick_validate import diagnose_skill_issues


def fix_frontmatter_format(skill_path):
    """
    Fix common frontmatter format issues.

    Args:
        skill_path: Path to skill directory

    Returns:
        bool: Success status
    """
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return False

    try:
        content = skill_md.read_text(encoding='utf-8')
        original_content = content

        # Fix common frontmatter issues
        if not content.startswith('---'):
            content = '---\n' + content
            print("  Added missing frontmatter delimiter")

        # Extract and fix frontmatter
        frontmatter_end = content.find('---', 3)
        if frontmatter_end == -1:
            # Add closing delimiter
            first_line_end = content.find('\n')
            if first_line_end != -1:
                content = content[:first_line_end] + '\n---\n' + content[first_line_end:]
                frontmatter_end = content.find('---', 3)
                print("  Added missing frontmatter closing delimiter")

        if frontmatter_end != -1:
            frontmatter_text = content[3:frontmatter_end].strip()

            try:
                frontmatter = yaml.safe_load(frontmatter_text)

                # Ensure required fields exist
                if not isinstance(frontmatter, dict):
                    frontmatter = {}

                skill_name = skill_path.name

                if 'name' not in frontmatter:
                    frontmatter['name'] = skill_name
                    print("  Added missing 'name' field")

                if 'description' not in frontmatter:
                    frontmatter['description'] = f"Skill for {skill_name.replace('-', ' ')}"
                    print("  Added missing 'description' field")

                # Rebuild content with fixed frontmatter
                new_frontmatter = yaml.dump(frontmatter, default_flow_style=False)
                new_content = '---\n' + new_frontmatter + '---' + content[frontmatter_end + 3:]

                # Write back if changed
                if new_content != original_content:
                    skill_md.write_text(new_content, encoding='utf-8')
                    print("  ✅ Fixed frontmatter format")
                    return True

            except yaml.YAMLError as e:
                print(f"  ❌ Could not parse frontmatter: {e}")
                return False

        return False

    except Exception as e:
        print(f"  ❌ Error fixing frontmatter: {e}")
        return False


def repair_skill(skill_name, skills_base_path):
    """
    Diagnose and repair a skill.

    Args:
        skill_name: Name of the skill to repair
        skills_base_path: Base path for skills directory

    Returns:
        bool: Success status
    """
    skill_path = skills_base_path / skill_name

    print(f"🔧 Repairing skill: {skill_name}")
    print(f"   Path: {skill_path}")
    print()

    # Run diagnosis
    print("🔍 Running diagnosis...")
    diagnosis = diagnose_skill_issues(skill_path)

    if not diagnosis["issues"]:
        print("✅ No issues found - skill appears healthy")
        return True

    print(f"Found {len(diagnosis['issues'])} issue(s) to fix:")
    for issue in diagnosis["issues"]:
        print(f"  - {issue['category']}: {issue['message']}")

    print()

    # Fix issues
    fixes_applied = 0

    for issue in diagnosis["issues"]:
        category = issue["category"]
        print(f"🔧 Fixing {category}...")

        if category == "existence":
            print("  ❌ Cannot fix missing directory - skill doesn't exist")
            continue

        elif category == "structure":
            # Create missing SKILL.md
            if not (skill_path / "SKILL.md").exists():
                print("  Creating missing SKILL.md...")
                skill_path.mkdir(parents=True, exist_ok=True)
                # Could create a template here, but for now just report
                print("  ⚠️  SKILL.md missing - manual creation required")
                continue

        elif category == "frontmatter":
            if fix_frontmatter_format(skill_path):
                fixes_applied += 1

    print()
    print(f"🎉 Repair complete! Applied {fixes_applied} fix(es)")

    # Re-validate
    print("🔍 Re-validating skill...")
    new_diagnosis = diagnose_skill_issues(skill_path)
    if not new_diagnosis["issues"]:
        print("✅ All issues resolved!")
        return True
    else:
        print(f"⚠️  {len(new_diagnosis['issues'])} issue(s) remain:")
        for issue in new_diagnosis["issues"]:
            print(f"  - {issue['category']}: {issue['message']}")
        return False


def list_all_skill_issues(skills_base_path):
    """
    List all skills with issues in the skills directory.

    Args:
        skills_base_path: Base path for skills directory
    """
    print("🔍 Scanning all skills for issues...")
    print()

    skills_with_issues = []
    skill_count = 0

    for skill_dir in skills_base_path.iterdir():
        if skill_dir.is_dir():
            skill_count += 1
            diagnosis = diagnose_skill_issues(skill_dir)

            if diagnosis["issues"]:
                skills_with_issues.append((skill_dir.name, diagnosis))

    print(f"Found {len(skills_with_issues)} skill(s) with issues out of {skill_count} total:")
    print()

    for skill_name, diagnosis in skills_with_issues:
        print(f"📋 {skill_name}:")
        for issue in diagnosis["issues"]:
            severity_icon = "❌" if issue["type"] == "critical" else "⚠️"
            print(f"  {severity_icon} {issue['category']}: {issue['message']}")
        print()

    if not skills_with_issues:
        print("✅ All skills appear healthy!")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  repair_skill.py <skill-name>")
        print("  repair_skill.py --diagnose <skill-name>")
        print("  repair_skill.py --list-issues")
        print()
        print("Examples:")
        print("  repair_skill.py ts-foundation-restorer")
        print("  repair_skill.py --diagnose my-broken-skill")
        print("  repair_skill.py --list-issues")
        sys.exit(1)

    # Determine skills base path (should be ../skills/, not the current skill directory)
    script_path = Path(__file__).resolve()
    skills_base_path = script_path.parent.parent.parent  # Go up three levels to skills/ directory

    command = sys.argv[1]

    if command == "--list-issues":
        list_all_skill_issues(skills_base_path)

    elif command == "--diagnose":
        if len(sys.argv) < 3:
            print("Error: --diagnose requires skill name")
            sys.exit(1)

        skill_name = sys.argv[2]
        skill_path = skills_base_path / skill_name

        print(f"🔍 Diagnosing skill: {skill_name}")
        diagnosis = diagnose_skill_issues(skill_path)

        print()
        print("Diagnosis Results:")
        if diagnosis["issues"]:
            for issue in diagnosis["issues"]:
                severity_icon = "❌" if issue["type"] == "critical" else "⚠️"
                print(f"  {severity_icon} {issue['category'].upper()}: {issue['message']}")
                print(f"     Solution: {issue['solution']}")
        else:
            print("  ✅ No issues found")

        if diagnosis["warnings"]:
            print()
            print("Warnings:")
            for warning in diagnosis["warnings"]:
                print(f"  ⚠️  {warning}")

        if diagnosis["suggestions"]:
            print()
            print("Suggestions:")
            for suggestion in diagnosis["suggestions"]:
                print(f"  💡 {suggestion}")

    elif command.startswith("-"):
        print(f"Error: Unknown option: {command}")
        sys.exit(1)

    else:
        # Repair skill
        skill_name = command
        success = repair_skill(skill_name, skills_base_path)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()