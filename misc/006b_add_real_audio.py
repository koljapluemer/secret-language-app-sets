#!/usr/bin/env python3
"""
Script to match audio files from hugolpz directory and add them to vocab.jsonl
Copies matching audio files to the audio directory and updates the sounds property
"""

import json
import os
import shutil
from pathlib import Path

# Paths (relative to script location)
VOCAB_FILE = Path("sets/cmn/mandarin-character-deck/vocab.jsonl")
LINKS_FILE = Path("sets/cmn/mandarin-character-deck/links.jsonl")
AUDIO_SOURCE = Path("data_in/hugolpz")
AUDIO_DEST = Path("sets/cmn/mandarin-character-deck/audio")
TEMP_FILE = VOCAB_FILE.with_suffix('.jsonl.tmp')

# License/credit link ID
AUDIO_CREDIT_LINK_ID = "link_hugolpz_audio"

def find_audio_file(content: str, audio_source: Path) -> str | None:
    """
    Find matching audio file for the given content.
    Looks for files named:
    - cmn-{content}.mp3
    - {content}.mp3
    """
    # Try with cmn- prefix
    audio_file = audio_source / f"cmn-{content}.mp3"
    if audio_file.exists():
        return audio_file.name

    # Try without prefix
    audio_file = audio_source / f"{content}.mp3"
    if audio_file.exists():
        return audio_file.name

    return None

def create_links_file():
    """Create links.jsonl with audio credit/license information."""
    link_entry = {
        "id": AUDIO_CREDIT_LINK_ID,
        "label": "Audio: hugolpz/audio-cmn",
        "url": "https://github.com/hugolpz/audio-cmn",
        "owner": "Hugo Lopez, Chen Wang, Yue Tan, Nicolas Vion",
        "license": "CC-BY-SA"
    }

    with open(LINKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(link_entry, f, ensure_ascii=False)
        f.write('\n')

    print(f"Created {LINKS_FILE} with audio credit link")

def main():
    # Create audio destination directory if it doesn't exist
    AUDIO_DEST.mkdir(parents=True, exist_ok=True)

    # Create links.jsonl with audio credit
    create_links_file()

    # Statistics
    total_entries = 0
    matched_entries = 0
    copied_files = 0

    print(f"Processing {VOCAB_FILE}...")
    print(f"Looking for audio in {AUDIO_SOURCE}")
    print(f"Target audio directory: {AUDIO_DEST}")
    print()

    # Process the JSONL file
    with open(VOCAB_FILE, 'r', encoding='utf-8') as infile, \
         open(TEMP_FILE, 'w', encoding='utf-8') as outfile:

        for line in infile:
            total_entries += 1
            entry = json.loads(line.strip())
            content = entry.get('content', '')

            # Find matching audio file
            audio_filename = find_audio_file(content, AUDIO_SOURCE)

            if audio_filename:
                matched_entries += 1
                source_file = AUDIO_SOURCE / audio_filename
                dest_file = AUDIO_DEST / audio_filename

                # Copy file if it doesn't already exist
                if not dest_file.exists():
                    shutil.copy2(source_file, dest_file)
                    copied_files += 1

                # Add filename to sounds array if not already present
                if 'sounds' not in entry:
                    entry['sounds'] = []

                # Check if this filename is already in the sounds array
                existing_filenames = [s.get('filename') for s in entry['sounds']]
                if audio_filename not in existing_filenames:
                    entry['sounds'].append({"filename": audio_filename})

                # Add link to audio credit
                if 'links' not in entry:
                    entry['links'] = []
                if AUDIO_CREDIT_LINK_ID not in entry['links']:
                    entry['links'].append(AUDIO_CREDIT_LINK_ID)

                if matched_entries <= 10:  # Show first 10 matches
                    print(f"✓ {content} -> {audio_filename}")

            # Write updated entry
            json.dump(entry, outfile, ensure_ascii=False)
            outfile.write('\n')

    # Replace original file with updated one
    TEMP_FILE.replace(VOCAB_FILE)

    print()
    print("=" * 60)
    print(f"Total entries processed: {total_entries}")
    print(f"Entries with matching audio: {matched_entries}")
    print(f"Audio files copied: {copied_files}")
    print(f"Match rate: {matched_entries/total_entries*100:.1f}%")
    print("=" * 60)

if __name__ == "__main__":
    main()
