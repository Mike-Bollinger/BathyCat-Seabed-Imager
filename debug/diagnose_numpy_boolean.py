#!/usr/bin/env python3
"""
NumPy Boolean Evaluation Diagnostic Tool
========================================

This script scans Python files for potential NumPy array boolean evaluation issues
that could cause "The truth value of an array with more than one element is ambiguous" errors.
"""

import re
import sys
from pathlib import Path


def scan_for_numpy_boolean_issues(file_path):
    """Scan a Python file for potential NumPy boolean evaluation issues."""
    issues = []
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines, 1):
        line_stripped = line.strip()
        
        # Skip comments and empty lines
        if not line_stripped or line_stripped.startswith('#'):
            continue
        
        # Pattern 1: Direct boolean evaluation of potential arrays
        # if array: or if not array:
        if re.search(r'\bif\s+(?:not\s+)?(?:frame|image|arr|data|array)\s*:', line_stripped):
            if 'is None' not in line_stripped and 'is not None' not in line_stripped:
                issues.append((i, line_stripped, "Direct boolean evaluation of potential array"))
        
        # Pattern 2: Boolean operations with potential arrays
        # if ret and frame: or if frame or other:
        if re.search(r'\bif\s+.*(?:frame|image|arr|data|array)(?:\s+(?:and|or)\s+|\s*(?:and|or)\s+.*)', line_stripped):
            if 'is None' not in line_stripped and 'is not None' not in line_stripped:
                if not re.search(r'\bif\s+.*\(.*is\s+not\s+None.*\)', line_stripped):
                    issues.append((i, line_stripped, "Boolean operation with potential array"))
        
        # Pattern 3: Assignment with boolean operations
        # result = array and something
        if re.search(r'=\s*(?:frame|image|arr|data|array)\s+(?:and|or)', line_stripped):
            issues.append((i, line_stripped, "Assignment with boolean operation on potential array"))
    
    return issues


def main():
    """Main function."""
    print("NumPy Boolean Evaluation Diagnostic Tool")
    print("=" * 50)
    print()
    
    # Scan source files
    src_dir = Path("src")
    if not src_dir.exists():
        print("ERROR: 'src' directory not found. Run from project root.")
        sys.exit(1)
    
    python_files = list(src_dir.glob("*.py"))
    total_issues = 0
    
    for py_file in python_files:
        print(f"Scanning: {py_file}")
        issues = scan_for_numpy_boolean_issues(py_file)
        
        if issues:
            print(f"  ❌ {len(issues)} potential issues found:")
            for line_num, line_content, issue_type in issues:
                print(f"     Line {line_num}: {issue_type}")
                print(f"     Code: {line_content}")
            total_issues += len(issues)
            print()
        else:
            print("  ✅ No issues found")
        print()
    
    print("=" * 50)
    print(f"Scan complete. Total issues found: {total_issues}")
    
    if total_issues == 0:
        print("✅ All files appear to handle NumPy arrays correctly!")
    else:
        print("❌ Issues found that may cause NumPy boolean evaluation errors.")
        print()
        print("Common fixes:")
        print("- Change 'if array:' to 'if array is not None:'")
        print("- Change 'if not array:' to 'if array is None:'")
        print("- Use parentheses: 'if ret and (frame is not None):'")
        print("- Separate checks: 'if not ret:' followed by 'if frame is None:'")
    
    return total_issues


if __name__ == "__main__":
    exit_code = main()
    sys.exit(1 if exit_code > 0 else 0)
