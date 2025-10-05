#!/usr/bin/env python3
"""
Script to add pinyin notes to generated Mulan vocabulary.
Reads vocab from sets/cmn/mulan-vocab/ and adds pinyin as notes.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any
from pinyin import get

def get_next_note_id(existing_notes: List[Dict]) -> str:
    """Get the next available note ID"""
    if not existing_notes:
        return "1"

    max_id = 0
    for note in existing_notes:
        try:
            note_id = int(note["id"])
            max_id = max(max_id, note_id)
        except (ValueError, KeyError):
            continue

    return str(max_id + 1)

def main():
    """Main function to add pinyin notes to Mulan vocabulary"""

    # Get the script directory and project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    # Paths to the generated vocab files
    vocab_dir = os.path.join(project_root, "public", "sets", "cmn", "mulan-vocab")
    vocab_file = os.path.join(vocab_dir, "vocab.jsonl")
    notes_file = os.path.join(vocab_dir, "notes.jsonl")

    if not os.path.exists(vocab_file):
        print(f"Error: vocab.jsonl not found at {vocab_file}")
        print("Please run 009_mulan_vocab.py first to generate the vocabulary.")
        return

    # Load existing vocabulary
    vocab_entries = []
    with open(vocab_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                vocab_entries.append(json.loads(line))

    # Load existing notes
    notes_entries = []
    if os.path.exists(notes_file):
        with open(notes_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    notes_entries.append(json.loads(line))

    print(f"Loaded {len(vocab_entries)} vocabulary entries")
    print(f"Loaded {len(notes_entries)} existing notes")

    # Track new notes to add
    new_notes = []
    vocab_updates = []

    # Process each vocabulary entry
    for vocab_entry in vocab_entries:
        chinese_content = vocab_entry.get("content", "")
        if not chinese_content:
            continue

        # Generate pinyin
        try:
            pinyin_result = get(chinese_content, format="strip", delimiter=" ")
            if pinyin_result and pinyin_result != chinese_content:
                # Create new pinyin note
                note_id = get_next_note_id(notes_entries + new_notes)

                pinyin_note = {
                    "id": note_id,
                    "content": pinyin_result,
                    "showBeforeExercice": True,
                    "noteType": "pinyin"
                }

                new_notes.append(pinyin_note)

                # Update vocab entry to include the pinyin note
                updated_vocab = vocab_entry.copy()
                existing_notes = updated_vocab.get("notes", [])
                existing_notes.append(note_id)
                updated_vocab["notes"] = existing_notes

                vocab_updates.append(updated_vocab)

                print(f"Added pinyin for '{chinese_content}': {pinyin_result}")
            else:
                # No pinyin generated, keep original vocab entry
                vocab_updates.append(vocab_entry)
                print(f"No pinyin generated for '{chinese_content}'")

        except Exception as e:
            print(f"Error generating pinyin for '{chinese_content}': {e}")
            # Keep original vocab entry on error
            vocab_updates.append(vocab_entry)

    # Combine existing and new notes
    all_notes = notes_entries + new_notes

    # Save updated vocab.jsonl
    with open(vocab_file, 'w', encoding='utf-8') as f:
        for vocab_entry in vocab_updates:
            f.write(json.dumps(vocab_entry, ensure_ascii=False) + '\n')

    # Save updated notes.jsonl
    with open(notes_file, 'w', encoding='utf-8') as f:
        for note_entry in all_notes:
            f.write(json.dumps(note_entry, ensure_ascii=False) + '\n')

    print(f"\nCompleted!")
    print(f"Added {len(new_notes)} new pinyin notes")
    print(f"Updated vocab.jsonl with {len(vocab_updates)} entries")
    print(f"Updated notes.jsonl with {len(all_notes)} total notes")

if __name__ == "__main__":
    main()