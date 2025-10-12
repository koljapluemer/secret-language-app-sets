#!/usr/bin/env python3
"""
Converts restaurant menu vocabulary CSV to JSONL format for the Secret Language app.

Input: chatgpt_vocab.csv with columns: chinese, english, pinyin, notes
Output: vocab.jsonl, translations.jsonl, notes.jsonl
"""

import csv
import json
from pathlib import Path

# Paths
SET_DIR = Path(__file__).parent.parent
INPUT_CSV = SET_DIR / "in" / "chatgpt_vocab.csv"
OUTPUT_DIR = SET_DIR / "out"

def parse_csv():
    """Parse the CSV file and return list of entries"""
    entries = []

    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            chinese = row['chinese'].strip() if row['chinese'] else ''
            english = row['english'].strip() if row['english'] else ''
            pinyin = row['pinyin'].strip() if row['pinyin'] else ''
            notes = row.get('notes', '') or ''
            notes = notes.strip() if notes else ''

            # Skip empty rows
            if not chinese:
                continue

            entries.append({
                'chinese': chinese,
                'english': english,
                'pinyin': pinyin,
                'notes': notes
            })

    return entries

def generate_dataset(entries):
    """Generate vocab, translation, and note objects from CSV entries"""
    vocab_list = []
    translation_list = []
    note_list = []

    for idx, entry in enumerate(entries):
        # Generate IDs
        vocab_num = idx + 1
        vocab_id = f"vocab_{vocab_num:03d}"

        # Create pinyin note
        pinyin_note_id = f"note_pinyin_{vocab_num:03d}"
        pinyin_note = {
            'id': pinyin_note_id,
            'content': entry['pinyin']
        }
        note_list.append(pinyin_note)

        # Create vocab entry
        vocab_obj = {
            'id': vocab_id,
            'language': 'cmn',
            'content': entry['chinese'],
            'consideredWord': True,
            'translations': [],
            'transcriptions': [pinyin_note_id]
        }

        # Add misc notes if present
        if entry['notes']:
            misc_note_id = f"note_misc_{vocab_num:03d}"
            misc_note = {
                'id': misc_note_id,
                'content': entry['notes']
            }
            note_list.append(misc_note)
            vocab_obj['notes'] = [misc_note_id]

        # Parse English translations (split by semicolon)
        english_parts = [part.strip() for part in entry['english'].split(';') if part.strip()]

        for trans_idx, english_text in enumerate(english_parts):
            trans_id = f"trans_{vocab_num:03d}_{trans_idx}"
            translation = {
                'id': trans_id,
                'content': english_text,
                'notes': []
            }
            translation_list.append(translation)
            vocab_obj['translations'].append(trans_id)

        vocab_list.append(vocab_obj)

    return vocab_list, translation_list, note_list

def write_jsonl(data, filepath):
    """Write data to JSONL file"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

def main():
    print("Parsing CSV file...")
    entries = parse_csv()
    print(f"Found {len(entries)} vocabulary entries")

    print("Generating dataset...")
    vocab_list, translation_list, note_list = generate_dataset(entries)

    print(f"Generated:")
    print(f"  - {len(vocab_list)} vocab items")
    print(f"  - {len(translation_list)} translations")
    print(f"  - {len(note_list)} notes")

    print("Writing output files...")
    write_jsonl(vocab_list, OUTPUT_DIR / 'vocab.jsonl')
    write_jsonl(translation_list, OUTPUT_DIR / 'translations.jsonl')
    write_jsonl(note_list, OUTPUT_DIR / 'notes.jsonl')

    print(f"\n Conversion complete! Files written to {OUTPUT_DIR}")

if __name__ == '__main__':
    main()
