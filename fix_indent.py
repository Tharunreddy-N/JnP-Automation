#!/usr/bin/env python3
"""Fix indentation in log_history_api.py for the else block inside try"""

with open('utils/log_history_api.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix indentation for lines 1735-1959 (else block content inside try)
# These lines need proper indentation - add 4 spaces to lines that are at 16 spaces
fixed_lines = []
for i, line in enumerate(lines, 1):
    if 1735 <= i <= 1959:  # Inside else block
        stripped = line.lstrip()
        if not stripped:  # Empty line - keep as is
            fixed_lines.append(line)
            continue
        
        indent = len(line) - len(stripped)
        
        # Skip except blocks - they should stay at their current level
        if stripped.startswith('except'):
            fixed_lines.append(line)
            continue
        
        # If line has exactly 16 spaces (same level as else), add 4 more (inside else)
        # But preserve relative indentation for nested blocks
        if indent == 16 and not stripped.startswith('#'):
            # Check if this is part of a nested structure
            # Look ahead to see if there are nested blocks
            fixed_lines.append(' ' * 4 + line)
        elif indent == 20:
            # Already correct (inside nested if/else)
            fixed_lines.append(line)
        elif indent == 24:
            # Already correct (inside nested nested)
            fixed_lines.append(line)
        elif indent == 28:
            # Already correct (inside nested nested nested)
            fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    elif i == 1960:
        # Fix except block - should be at 12 spaces (same as try)
        stripped = line.lstrip()
        if stripped.startswith('except'):
            current_indent = len(line) - len(stripped)
            if current_indent != 12:
                fixed_lines.append(' ' * 12 + stripped)
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    else:
        fixed_lines.append(line)

with open('utils/log_history_api.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("Fixed indentation for else block")
