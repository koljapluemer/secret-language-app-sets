#!/usr/bin/env python3
"""
Ensure pinyin notes are properly attached to the restaurant menu vocabulary set.

The converter (0_convert.py) stores pinyin values in notes and references those note IDs
from vocab.transcriptions. This helper script:
  * validates that each referenced note still exists and has pinyin content
  * marks the note with noteType="pinyin" 
  * adds the note ID to the vocab's notes array so the entry explicitly links to it
The actual transcriptions list is left as-is (it continues to carry note IDs), so the
pinyin text only lives in the note content.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

SET_DIR = Path(__file__).parent.parent
OUT_DIR = SET_DIR / "out"
VOCAB_PATH = OUT_DIR / "vocab.jsonl"
NOTES_PATH = OUT_DIR / "notes.jsonl"


def load_jsonl(path: Path) -> List[Dict]:
    """Read a JSONL file into a list of dictionaries."""
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")

    entries: List[Dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            entries.append(json.loads(line))
    return entries


def write_jsonl(entries: Iterable[Dict], path: Path) -> None:
    """Write iterable of dicts back to JSONL."""
    with path.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def dedupe_preserve_order(items: Iterable[str]) -> List[str]:
    """Deduplicate an iterable while preserving order."""
    seen = set()
    result: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def annotate_pinyin_note(note: Dict) -> bool:
    """Ensure a note dict carries the metadata expected for pinyin notes."""
    changed = False
    if note.get("noteType") != "pinyin":
        note["noteType"] = "pinyin"
        changed = True
    return changed


def attach_pinyin_notes(
    vocab_entries: List[Dict], notes_lookup: Dict[str, Dict]
) -> Tuple[int, int, List[str]]:
    """
    Attach pinyin note references to vocab entries and annotate the notes.

    Returns:
        updated_vocab_count: number of vocab entries whose notes array was updated
        annotated_note_count: number of notes that received pinyin metadata
        missing_note_ids: note IDs that were referenced but missing content
    """
    updated_vocab_count = 0
    annotated_note_count = 0
    missing_note_ids: List[str] = []

    for vocab in vocab_entries:
        transcription_refs = vocab.get("transcriptions", [])
        if not transcription_refs:
            continue

        pinyin_note_ids: List[str] = []
        for ref in transcription_refs:
            if not isinstance(ref, str):
                continue

            note = notes_lookup.get(ref)
            if note is None:
                continue

            content = (note.get("content") or "").strip()
            if not content:
                missing_note_ids.append(ref)
                continue

            if ref.startswith("note_pinyin_") and annotate_pinyin_note(note):
                annotated_note_count += 1

            pinyin_note_ids.append(ref)

        if not pinyin_note_ids:
            continue

        existing_notes = [
            note_id for note_id in vocab.get("notes", []) if isinstance(note_id, str)
        ]
        combined_notes = dedupe_preserve_order(existing_notes + pinyin_note_ids)
        if combined_notes != existing_notes:
            vocab["notes"] = combined_notes
            updated_vocab_count += 1

    return updated_vocab_count, annotated_note_count, missing_note_ids


def main() -> None:
    print("Loading vocab and notes JSONL files...")
    vocab_entries = load_jsonl(VOCAB_PATH)
    notes_entries = load_jsonl(NOTES_PATH)
    notes_lookup = {note["id"]: note for note in notes_entries if "id" in note}

    print(f"Loaded {len(vocab_entries)} vocab entries")
    print(f"Loaded {len(notes_entries)} notes")

    (
        updated_vocab_count,
        annotated_note_count,
        missing_note_ids,
    ) = attach_pinyin_notes(vocab_entries, notes_lookup)

    print(f"Updated {updated_vocab_count} vocab entries with pinyin note references")
    print(f"Annotated {annotated_note_count} notes with pinyin metadata")
    if missing_note_ids:
        unique_missing = dedupe_preserve_order(missing_note_ids)
        print(
            "Warning: missing pinyin content for note IDs: "
            + ", ".join(unique_missing)
        )

    print("Writing updated files...")
    write_jsonl(vocab_entries, VOCAB_PATH)
    write_jsonl(notes_entries, NOTES_PATH)
    print("Done.")


if __name__ == "__main__":
    main()
