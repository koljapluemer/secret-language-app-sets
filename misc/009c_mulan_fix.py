#!/usr/bin/env python3
"""
Remove vocab entries that contain Western (Latin) characters from Mulan vocab set.
This fixes an issue where English translations were mistakenly added as Chinese vocab.
"""

import json
import re
from pathlib import Path

def contains_western_chars(text: str) -> bool:
    """Check if text contains any Latin alphabet characters."""
    return bool(re.search(r'[a-zA-Z]', text))

def main():
    vocab_file = Path('sets/cmn/mulan-vocab/vocab.jsonl')

    if not vocab_file.exists():
        print(f"Error: {vocab_file} not found")
        return

    # Read all lines
    with open(vocab_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Filter out entries with Western characters
    filtered_lines = []
    removed_count = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        try:
            data = json.loads(line)
            content = data.get('content', '')

            if contains_western_chars(content):
                print(f"Removing: {content}")
                removed_count += 1
            else:
                filtered_lines.append(line)
        except json.JSONDecodeError:
            print(f"Warning: Could not parse line: {line[:50]}...")
            continue

    # Write back filtered lines
    with open(vocab_file, 'w', encoding='utf-8') as f:
        for line in filtered_lines:
            f.write(line + '\n')

    print(f"\nRemoved {removed_count} entries with Western characters")
    print(f"Kept {len(filtered_lines)} entries")

if __name__ == '__main__':
    main()
