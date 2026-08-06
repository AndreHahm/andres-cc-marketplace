#!/usr/bin/env python3
"""
Skill Validation Utilities

Provides validation functions for skill structure and frontmatter metadata.
Used by package_skill.py and repair_skill.py scripts.
"""

import sys
from pathlib import Path
import yaml


def validate_skill_frontmatter(skill_path):
    """
    Validate SKILL.md YAML frontmatter format and required fields.

    Args:
        skill_path: Path to skill directory

    Returns:
        tuple: (is_valid, error_message)
    """
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return False, "SKILL.md not found"

    try:
        content = skill_md.read_text(encoding='utf-8')

        # Check for YAML frontmatter
        if not content.startswith('---'):
            return False, "SKILL.md must start with YAML frontmatter (---)"

        # Extract frontmatter
        try:
            frontmatter_end = content.find('---', 3)
            if frontmatter_end == -1:
                return False, "YAML frontmatter not properly closed"

            frontmatter_text = content[3:frontmatter_end].strip()
            frontmatter = yaml.safe_load(frontmatter_text)

        except yaml.YAMLError as e:
            return False, f"Invalid YAML in frontmatter: {e}"

        # Check required fields
        if not isinstance(frontmatter, dict):
            return False, "Frontmatter must be a dictionary"

        required_fields = ['name', 'description']
        for field in required_fields:
            if field not in frontmatter:
                return False, f"Missing required field: {field}"
            if not frontmatter[field] or not str(frontmatter[field]).strip():
                return False, f"Field '{field}' cannot be empty"

        # Validate skill name format
        name = frontmatter['name']
        if not isinstance(name, str):
            return False, "Field 'name' must be a string"

        if len(name) > 100:
            return False, "Skill name too long (max 100 characters)"

        # Validate description
        description = frontmatter['description']
        if not isinstance(description, str):
            return False, "Field 'description' must be a string"

        if len(description) < 10:
            return False, "Description too short (min 10 characters)"

        return True, "Frontmatter validation passed"

    except Exception as e:
        return False, f"Error reading SKILL.md: {e}"


def validate_skill_structure(skill_path):
    """
    Validate skill directory structure.

    Args:
        skill_path: Path to skill directory

    Returns:
        tuple: (is_valid, error_message)
    """
    if not skill_path.exists():
        return False, "Skill directory does not exist"

    if not skill_path.is_dir():
        return False, "Skill path is not a directory"

    # Check for SKILL.md
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return False, "SKILL.md not found"

    # Check for expected subdirectories (optional but common)
    optional_dirs = ['scripts', 'references', 'assets']
    for dir_name in optional_dirs:
        dir_path = skill_path / dir_name
        if dir_path.exists() and not dir_path.is_dir():
            return False, f"'{dir_name}' exists but is not a directory"

    return True, "Structure validation passed"


def validate_skill(skill_path):
    """
    Comprehensive skill validation: structure and frontmatter.

    Claude Code discovers skills purely by scanning for SKILL.md — there is
    no registry file to validate against.

    Args:
        skill_path: Path to skill directory

    Returns:
        tuple: (is_valid, message)
    """
    skill_path = Path(skill_path).resolve()

    # Validate structure
    structure_valid, structure_msg = validate_skill_structure(skill_path)
    if not structure_valid:
        return False, f"Structure error: {structure_msg}"

    # Validate frontmatter
    frontmatter_valid, frontmatter_msg = validate_skill_frontmatter(skill_path)
    if not frontmatter_valid:
        return False, f"Frontmatter error: {frontmatter_msg}"

    return True, "Skill validation passed"


def diagnose_skill_issues(skill_path):
    """
    Comprehensive diagnostic for skill issues.

    Args:
        skill_path: Path to skill directory

    Returns:
        dict: Diagnostic report with issues and suggestions
    """
    skill_path = Path(skill_path).resolve()
    skill_name = skill_path.name

    diagnosis = {
        "skill_name": skill_name,
        "skill_path": str(skill_path),
        "issues": [],
        "warnings": [],
        "suggestions": []
    }

    # Check basic existence
    if not skill_path.exists():
        diagnosis["issues"].append({
            "type": "critical",
            "category": "existence",
            "message": "Skill directory does not exist",
            "solution": f"Create skill directory at {skill_path}"
        })
        return diagnosis

    # Validate structure
    structure_valid, structure_msg = validate_skill_structure(skill_path)
    if not structure_valid:
        diagnosis["issues"].append({
            "type": "critical",
            "category": "structure",
            "message": structure_msg,
            "solution": "Fix skill directory structure"
        })

    # Validate frontmatter
    frontmatter_valid, frontmatter_msg = validate_skill_frontmatter(skill_path)
    if not frontmatter_valid:
        diagnosis["issues"].append({
            "type": "critical",
            "category": "frontmatter",
            "message": frontmatter_msg,
            "solution": "Fix SKILL.md YAML frontmatter"
        })

    # Add suggestions based on what's missing
    if not diagnosis["issues"]:
        diagnosis["suggestions"].append("Skill appears to be healthy")

    return diagnosis


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) != 2:
        print("Usage: python quick_validate.py <path/to/skill>")
        sys.exit(1)

    skill_path = sys.argv[1]
    is_valid, message = validate_skill(skill_path)

    if is_valid:
        print(f"✅ {message}")
        sys.exit(0)
    else:
        print(f"❌ {message}")
        sys.exit(1)