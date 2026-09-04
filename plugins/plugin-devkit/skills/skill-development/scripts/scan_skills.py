#!/usr/bin/env python3
"""
Skill Inventory Scanner

Scans all skills in the skills/ directory and generates comprehensive inventory
including metadata, usage statistics, and bundled resources analysis.

Usage:
    python scan_skills.py --output skill_inventory.json
    python scan_skills.py --output inventory.json --verbose
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import re

def parse_frontmatter(content: str) -> Dict[str, Any]:
    """Parse YAML frontmatter from markdown content."""
    frontmatter = {}

    # Look for YAML frontmatter between --- markers
    if content.startswith('---'):
        try:
            # Find the end of frontmatter
            end_idx = content.find('---', 3)
            if end_idx != -1:
                frontmatter_text = content[3:end_idx].strip()

                # Simple YAML parsing for our needs
                for line in frontmatter_text.split('\n'):
                    line = line.strip()
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()

                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]

                        frontmatter[key] = value
        except Exception as e:
            print(f"Warning: Could not parse frontmatter: {e}")

    return frontmatter

def extract_keywords_from_description(description: str) -> List[str]:
    """Extract keywords from skill description."""
    if not description:
        return []

    # Simple keyword extraction - split on common separators and clean up
    keywords = []

    # Split on commas, semicolons, and "and"
    parts = re.split(r'[,;]|\s+and\s+', description.lower())

    for part in parts:
        # Remove common stop words and clean up
        cleaned = re.sub(r'\b(the|a|an|for|to|with|by|in|on|at|or|of|that|this|it|is|are|was|were|be|been|have|has|had|do|does|did|will|would|could|should|may|might|must|can|shall)\b', '', part)
        cleaned = re.sub(r'[^\w\s-]', '', cleaned).strip()

        if len(cleaned) >= 3:  # Only keep words 3+ characters
            keywords.append(cleaned)

    return list(set(keywords[:20]))  # Limit to 20 unique keywords

def scan_skill_directory(skill_path: Path) -> Optional[Dict[str, Any]]:
    """Scan a single skill directory and extract metadata."""
    skill_name = skill_path.name

    # Skip hidden directories and common non-skill directories
    if skill_name.startswith('.') or skill_name in ['__pycache__', 'node_modules', 'archive']:
        return None

    skill_info = {
        'name': skill_name,
        'path': str(skill_path),
        'exists': True,
        'has_skill_md': False,
        'frontmatter': {},
        'bundled_resources': {
            'scripts': [],
            'references': [],
            'assets': [],
            'other': []
        },
        'file_count': 0,
        'total_size_bytes': 0,
        'last_modified': None
    }

    try:
        # Get directory stats
        stat_info = skill_path.stat()
        skill_info['last_modified'] = datetime.fromtimestamp(stat_info.st_mtime).isoformat()

        # Scan for SKILL.md
        skill_md_path = skill_path / 'SKILL.md'
        if skill_md_path.exists():
            skill_info['has_skill_md'] = True

            # Read and parse SKILL.md
            try:
                with open(skill_md_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Parse frontmatter
                frontmatter = parse_frontmatter(content)
                skill_info['frontmatter'] = frontmatter

                # Extract keywords from description if not in frontmatter
                if 'keywords' not in frontmatter and 'description' in frontmatter:
                    frontmatter['keywords'] = extract_keywords_from_description(frontmatter['description'])
                    skill_info['frontmatter'] = frontmatter

                # Store content length for analysis
                skill_info['content_length'] = len(content)

            except Exception as e:
                print(f"Warning: Could not read {skill_md_path}: {e}")
                skill_info['read_error'] = str(e)

        # Scan bundled resources
        for item in skill_path.iterdir():
            if item.name == 'SKILL.md':
                continue

            skill_info['file_count'] += 1

            if item.is_file():
                skill_info['total_size_bytes'] += item.stat().st_size

            if item.is_dir():
                resource_type = item.name.lower()
                if resource_type in ['scripts', 'references', 'assets']:
                    # List files in this resource directory
                    files = []
                    try:
                        for file_item in item.iterdir():
                            if file_item.is_file() and not file_item.name.startswith('.'):
                                files.append({
                                    'name': file_item.name,
                                    'size_bytes': file_item.stat().st_size,
                                    'extension': file_item.suffix
                                })
                                skill_info['total_size_bytes'] += file_item.stat().st_size
                        skill_info['bundled_resources'][resource_type] = files
                    except Exception as e:
                        print(f"Warning: Could not scan {item}: {e}")
                else:
                    skill_info['bundled_resources']['other'].append(item.name)
            elif item.is_file():
                # Direct files in skill root
                skill_info['bundled_resources']['other'].append(item.name)

        # Convert size to KB for readability
        skill_info['total_size_kb'] = round(skill_info['total_size_bytes'] / 1024, 2)

    except Exception as e:
        print(f"Error scanning {skill_path}: {e}")
        skill_info['error'] = str(e)
        skill_info['exists'] = False

    return skill_info

def calculate_usage_stats(skills_inventory: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate summary statistics purely from the scanned inventory.

    Claude Code discovers skills by scanning for SKILL.md — there is no
    registry file, so usage patterns (activation counts, last-used dates,
    categories, emoji) are not tracked and cannot be reported here.
    """
    stats = {
        'total_skills': len(skills_inventory),
        'skills_with_frontmatter': 0,
        'skills_with_scripts': 0,
        'skills_with_references': 0,
        'skills_with_assets': 0,
        'average_file_count': 0,
        'average_size_kb': 0,
        'top_keywords': {},
        'resource_summary': {
            'total_scripts': 0,
            'total_references': 0,
            'total_assets': 0,
            'total_other_files': 0
        }
    }

    keyword_counts = {}
    total_files = 0
    total_size = 0

    for skill in skills_inventory:
        # Count skills with frontmatter
        if skill.get('frontmatter'):
            stats['skills_with_frontmatter'] += 1

        # Count resource types
        if skill['bundled_resources']['scripts']:
            stats['skills_with_scripts'] += 1
            stats['resource_summary']['total_scripts'] += len(skill['bundled_resources']['scripts'])

        if skill['bundled_resources']['references']:
            stats['skills_with_references'] += 1
            stats['resource_summary']['total_references'] += len(skill['bundled_resources']['references'])

        if skill['bundled_resources']['assets']:
            stats['skills_with_assets'] += 1
            stats['resource_summary']['total_assets'] += len(skill['bundled_resources']['assets'])

        stats['resource_summary']['total_other_files'] += len(skill['bundled_resources']['other'])

        # File and size totals
        total_files += skill['file_count']
        total_size += skill.get('total_size_kb', 0)

        # Keyword analysis (extracted from frontmatter description by scan_skill_directory)
        keywords = skill.get('frontmatter', {}).get('keywords', [])
        if isinstance(keywords, str):
            keywords = [keywords]

        for keyword in keywords:
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1

    # Calculate averages
    if stats['total_skills'] > 0:
        stats['average_file_count'] = round(total_files / stats['total_skills'], 2)
        stats['average_size_kb'] = round(total_size / stats['total_skills'], 2)

    # Top keywords (get top 10)
    stats['top_keywords'] = dict(sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10])

    return stats

def main():
    parser = argparse.ArgumentParser(description='Scan skills directory and generate inventory')
    parser.add_argument('--output', '-o', required=True, help='Output JSON file path')
    parser.add_argument('--skills-dir', default='skills', help='Skills directory path (default: skills)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    # Resolve paths
    skills_dir = Path(args.skills_dir)
    output_path = Path(args.output)

    if not skills_dir.exists():
        print(f"Error: Skills directory '{skills_dir}' does not exist")
        sys.exit(1)

    print(f"Scanning skills in: {skills_dir}")

    # Scan all skill directories
    skills_inventory = []

    for item in skills_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            skill_info = scan_skill_directory(item)
            if skill_info:
                skills_inventory.append(skill_info)
                if args.verbose:
                    print(f"  Scanned: {skill_info['name']}")

    # Calculate statistics
    stats = calculate_usage_stats(skills_inventory)

    # Create final inventory object
    inventory = {
        'scan_date': datetime.now().isoformat(),
        'scanner_version': '1.0.0',
        'paths': {
            'skills_dir': str(skills_dir)
        },
        'summary': stats,
        'skills': skills_inventory
    }

    # Write output
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(inventory, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Inventory saved to: {output_path}")
        print(f"📊 Scanned {stats['total_skills']} skills")
        print(f"📝 {stats['skills_with_frontmatter']} skills have frontmatter")
        print(f"🔧 {stats['skills_with_scripts']} skills have scripts")
        print(f"📚 {stats['skills_with_references']} skills have references")
        print(f"🎨 {stats['skills_with_assets']} skills have assets")

    except Exception as e:
        print(f"Error writing output: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
