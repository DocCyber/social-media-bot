#!/usr/bin/env python3
"""
Pre-commit verification script
Checks for potential secrets before git add/commit
"""

import os
import re
from pathlib import Path

# Patterns that might indicate secrets
SECRET_PATTERNS = [
    r'api[_-]?key.*[:=]\s*["\']?[\w\-]{20,}',
    r'secret.*[:=]\s*["\']?[\w\-]{20,}',
    r'password.*[:=]\s*["\']?[\w\-]{8,}',
    r'token.*[:=]\s*["\']?[\w\-]{20,}',
    r'bearer.*[:=]\s*["\']?[\w\-]{20,}',
    r'xrpc[_-]password',
    r'app[_-]password',
]

# Files that should NEVER be committed
FORBIDDEN_FILES = [
    'keys.json',
    'user_data.csv',
    'last_add_check.txt',
    'engagement_log.txt',
]

# Directories to check
CHECK_DIRS = ['.']

def scan_file(filepath):
    """Scan a file for potential secrets"""
    issues = []

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        for i, pattern in enumerate(SECRET_PATTERNS):
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                issues.append(f"  ⚠️  Pattern {i+1} matched: {pattern[:50]}...")

    except Exception as e:
        pass  # Skip files that can't be read

    return issues

def check_forbidden_files(root_dir):
    """Check for files that should never be committed"""
    found = []

    for forbidden in FORBIDDEN_FILES:
        for filepath in Path(root_dir).rglob(forbidden):
            found.append(str(filepath))

    return found

def main():
    print("=" * 80)
    print("PRE-COMMIT VERIFICATION")
    print("=" * 80)
    print()

    # Check for forbidden files
    print("1. Checking for forbidden files...")
    forbidden = check_forbidden_files('.')

    if forbidden:
        print("  ❌ FOUND FORBIDDEN FILES (should be in .gitignore):")
        for f in forbidden:
            print(f"     - {f}")
    else:
        print("  ✅ No forbidden files found")

    print()

    # Scan Python files for secrets
    print("2. Scanning Python files for hardcoded secrets...")
    py_files = list(Path('.').rglob('*.py'))

    issues_found = False
    for py_file in py_files:
        # Skip archive and backup directories
        if 'archive' in str(py_file) or 'bakup' in str(py_file):
            continue

        issues = scan_file(py_file)
        if issues:
            issues_found = True
            print(f"  ⚠️  {py_file}:")
            for issue in issues:
                print(f"     {issue}")

    if not issues_found:
        print("  ✅ No obvious secrets found in Python files")

    print()

    # Check JSON files
    print("3. Checking JSON files...")
    json_files = list(Path('.').rglob('*.json'))

    dangerous_jsons = []
    for json_file in json_files:
        # Skip archive and backup directories
        if 'archive' in str(json_file) or 'bakup' in str(json_file):
            continue

        # Check if it's a known safe file
        filename = json_file.name
        if filename in ['keys.json', 'package.json', 'tsconfig.json']:
            if filename == 'keys.json':
                dangerous_jsons.append(str(json_file))
        elif any(keyword in filename for keyword in ['state', 'config', 'credentials']):
            # State files might contain sensitive data
            issues = scan_file(json_file)
            if issues:
                dangerous_jsons.append(str(json_file))

    if dangerous_jsons:
        print("  ⚠️  Potentially sensitive JSON files:")
        for f in dangerous_jsons:
            print(f"     - {f}")
    else:
        print("  ✅ No obviously sensitive JSON files")

    print()
    print("=" * 80)

    # Final verdict
    if forbidden or issues_found or dangerous_jsons:
        print("⚠️  WARNINGS FOUND - Review before committing")
        print()
        print("Recommended actions:")
        print("1. Verify .gitignore includes all forbidden files")
        print("2. Check flagged files for hardcoded secrets")
        print("3. Remove any sensitive data before git add")
        print()
        return 1
    else:
        print("✅ NO OBVIOUS ISSUES FOUND")
        print()
        print("Next steps:")
        print("1. git init")
        print("2. git add .")
        print("3. git status  # Verify no secrets staged")
        print("4. git commit -m 'Initial commit'")
        print()
        return 0

if __name__ == '__main__':
    exit(main())
