#!/usr/bin/env python3
"""
Script to fix duplicate notes and translations in vocab.jsonl.

Deduplicates notes by (noteType, content) and translations by (content).
Updates vocab.jsonl to reference the deduplicated IDs.
"""

import json
from collections import defaultdict
from pathlib import Path


def load_jsonl(filepath):
    """Load JSONL file into a list of dictionaries."""
    items = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def save_jsonl(filepath, items):
    """Save list of dictionaries to JSONL file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')


def deduplicate_notes(notes):
    """
    Deduplicate notes by (noteType, content).

    Returns:
        - deduplicated_notes: list of unique notes
        - id_mapping: dict mapping old IDs to new IDs
    """
    # Track unique notes by (noteType, content)
    # noteType might be None, so we use .get() with default None
    unique_notes = {}
    id_mapping = {}

    for note in notes:
        note_id = note['id']
        content = note['content']
        note_type = note.get('noteType', None)

        # Create key for deduplication
        key = (note_type, content)

        if key not in unique_notes:
            # First occurrence - keep this note
            unique_notes[key] = note
            id_mapping[note_id] = note_id
        else:
            # Duplicate - map to the first occurrence's ID
            canonical_id = unique_notes[key]['id']
            id_mapping[note_id] = canonical_id

    # Return deduplicated notes (values from unique_notes dict)
    deduplicated_notes = list(unique_notes.values())

    print(f"Notes: {len(notes)} -> {len(deduplicated_notes)} (removed {len(notes) - len(deduplicated_notes)} duplicates)")

    return deduplicated_notes, id_mapping


def deduplicate_translations(translations):
    """
    Deduplicate translations by content.

    Returns:
        - deduplicated_translations: list of unique translations
        - id_mapping: dict mapping old IDs to new IDs
    """
    unique_translations = {}
    id_mapping = {}

    for translation in translations:
        trans_id = translation['id']
        content = translation['content']

        # Create key for deduplication (just content for translations)
        key = content

        if key not in unique_translations:
            # First occurrence - keep this translation
            unique_translations[key] = translation
            id_mapping[trans_id] = trans_id
        else:
            # Duplicate - map to the first occurrence's ID
            canonical_id = unique_translations[key]['id']
            id_mapping[trans_id] = canonical_id

    # Return deduplicated translations
    deduplicated_translations = list(unique_translations.values())

    print(f"Translations: {len(translations)} -> {len(deduplicated_translations)} (removed {len(translations) - len(deduplicated_translations)} duplicates)")

    return deduplicated_translations, id_mapping


def update_vocab_references(vocab, note_id_mapping, trans_id_mapping):
    """
    Update vocab entries to reference deduplicated note and translation IDs.
    Also removes duplicate IDs from the arrays.
    """
    for entry in vocab:
        # Update notes references
        if 'notes' in entry:
            old_note_ids = entry['notes']
            # Map to new IDs and remove duplicates while preserving order
            new_note_ids = []
            seen = set()
            for old_id in old_note_ids:
                new_id = note_id_mapping.get(old_id, old_id)
                if new_id not in seen:
                    new_note_ids.append(new_id)
                    seen.add(new_id)
            entry['notes'] = new_note_ids

        # Update translation references
        if 'translations' in entry:
            old_trans_ids = entry['translations']
            # Map to new IDs and remove duplicates while preserving order
            new_trans_ids = []
            seen = set()
            for old_id in old_trans_ids:
                new_id = trans_id_mapping.get(old_id, old_id)
                if new_id not in seen:
                    new_trans_ids.append(new_id)
                    seen.add(new_id)
            entry['translations'] = new_trans_ids

    return vocab


def update_translation_notes(translations, note_id_mapping):
    """
    Update translation entries to reference deduplicated note IDs.
    Also removes duplicate IDs from the notes arrays.
    """
    for entry in translations:
        # Update notes references in translations
        if 'notes' in entry:
            old_note_ids = entry['notes']
            # Map to new IDs and remove duplicates while preserving order
            new_note_ids = []
            seen = set()
            for old_id in old_note_ids:
                new_id = note_id_mapping.get(old_id, old_id)
                if new_id not in seen:
                    new_note_ids.append(new_id)
                    seen.add(new_id)
            entry['notes'] = new_note_ids

    return translations


def main():
    # Define file paths
    base_dir = Path(__file__).parent.parent / 'out'
    vocab_path = base_dir / 'vocab.jsonl'
    notes_path = base_dir / 'notes.jsonl'
    translations_path = base_dir / 'translations.jsonl'

    print(f"Loading files from {base_dir}...")

    # Load all files
    vocab = load_jsonl(vocab_path)
    notes = load_jsonl(notes_path)
    translations = load_jsonl(translations_path)

    print(f"Loaded {len(vocab)} vocab entries, {len(notes)} notes, {len(translations)} translations")

    # Deduplicate notes
    print("\nDeduplicating notes...")
    deduplicated_notes, note_id_mapping = deduplicate_notes(notes)

    # Deduplicate translations
    print("\nDeduplicating translations...")
    deduplicated_translations, trans_id_mapping = deduplicate_translations(translations)

    # Update translation notes to reference deduplicated note IDs
    print("\nUpdating translation notes...")
    updated_translations = update_translation_notes(deduplicated_translations, note_id_mapping)

    # Update vocab references
    print("\nUpdating vocab references...")
    updated_vocab = update_vocab_references(vocab, note_id_mapping, trans_id_mapping)

    # Save updated files
    print("\nSaving updated files...")
    save_jsonl(notes_path, deduplicated_notes)
    save_jsonl(translations_path, updated_translations)
    save_jsonl(vocab_path, updated_vocab)

    print("\nDone! Files updated successfully.")


if __name__ == '__main__':
    main()
