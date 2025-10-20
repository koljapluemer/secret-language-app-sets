#!/usr/bin/env python3
"""
Fix contains field for sentences in vocab.jsonl
For vocab items with consideredSentence=True, rename relatedVocab to contains
"""

import json
from pathlib import Path

def fix_contains():
    # Define paths
    script_dir = Path(__file__).parent
    vocab_file = script_dir.parent / "out" / "vocab.jsonl"

    if not vocab_file.exists():
        print(f"Error: {vocab_file} not found")
        return

    # Read all vocab items
    vocab_items = []
    with open(vocab_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                vocab_items.append(json.loads(line))

    # Process each item
    modified_count = 0
    for item in vocab_items:
        # Check if this is a sentence
        if item.get('consideredSentence', False):
            # If it has relatedVocab, rename it to contains
            if 'relatedVocab' in item:
                item['contains'] = item.pop('relatedVocab')
                modified_count += 1
                print(f"Fixed: {item.get('content', item.get('id', 'unknown'))}")

    # Write back to file
    with open(vocab_file, 'w', encoding='utf-8') as f:
        for item in vocab_items:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print(f"\nDone! Modified {modified_count} vocab items.")

if __name__ == "__main__":
    fix_contains()
