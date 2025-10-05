#!/usr/bin/env python3
"""
Generate HSK1 vocabulary set from HTML table.
- Extracts vocab from public/data_in/hsk1_table.html
- Creates vocab, translations, and notes in JSONL format
- Adds pinyin as notes (extracted from table)
- Splits English translations by comma
- Extracts parenthetical content to notes
- Adds linguistic type headers as notes to following vocab
"""

import os
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup

# Configuration
DEBUG = False  # Set to True to process only first 10 rows
TARGET_LANGUAGE = "cmn"  # Mandarin Chinese (ISO 639-3)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hsk1_vocab_generation.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VocabProcessor:
    """Handles vocabulary extraction and management"""

    def __init__(self):
        self.vocab_data = []
        self.translation_data = []
        self.note_data = []

        # ID counters
        self.vocab_id = 0
        self.translation_id = 0
        self.note_id = 0

        # Deduplication tracking
        self.vocab_by_chinese = {}  # chinese_content -> vocab_entry
        self.translation_by_english = {}  # english_content -> translation_id
        self.note_by_content = {}  # note_content -> note_id

        # Current linguistic type to add as note
        self.current_linguistic_type = None

    def get_next_vocab_id(self):
        self.vocab_id += 1
        return str(self.vocab_id)

    def get_next_translation_id(self):
        self.translation_id += 1
        return str(self.translation_id)

    def get_next_note_id(self):
        self.note_id += 1
        return str(self.note_id)

    def create_or_get_translation(self, english_content: str) -> str:
        """Create translation entry or return existing ID"""
        # Clean up the translation
        english_content = english_content.strip()

        if english_content in self.translation_by_english:
            return self.translation_by_english[english_content]

        translation_id = self.get_next_translation_id()
        self.translation_by_english[english_content] = translation_id

        translation_entry = {
            "id": translation_id,
            "content": english_content
        }

        self.translation_data.append(translation_entry)
        return translation_id

    def create_or_get_note(self, note_content: str, show_before: bool = False, note_type: Optional[str] = None) -> str:
        """Create note entry or return existing ID"""
        if note_content in self.note_by_content:
            return self.note_by_content[note_content]

        note_id = self.get_next_note_id()
        self.note_by_content[note_content] = note_id

        note_entry = {
            "id": note_id,
            "content": note_content,
            "showBeforeExercice": show_before
        }

        if note_type:
            note_entry["noteType"] = note_type

        self.note_data.append(note_entry)
        return note_id

    def extract_parenthetical(self, text: str) -> Tuple[str, List[str]]:
        """Extract content in parentheses and return cleaned text + notes"""
        notes = []
        # Find all parenthetical content
        parenthetical_pattern = r'\s*\([^)]+\)'
        matches = re.findall(parenthetical_pattern, text)

        for match in matches:
            # Extract content without parentheses
            note_content = match.strip()[1:-1].strip()
            if note_content:
                notes.append(note_content)

        # Remove parenthetical content from text
        cleaned_text = re.sub(parenthetical_pattern, '', text).strip()

        return cleaned_text, notes

    def split_translations(self, english_text: str) -> List[str]:
        """Split English translations by comma"""
        # First extract parenthetical content
        cleaned_text, _ = self.extract_parenthetical(english_text)

        # Split by comma
        translations = [t.strip() for t in cleaned_text.split(',') if t.strip()]

        return translations

    def create_vocab_entry(self, chinese: str, pinyin: str, english: str, row_number: int):
        """Create vocabulary entry from table row data"""
        if not chinese or not english:
            logger.warning(f"Skipping row {row_number}: missing Chinese or English")
            return

        # Extract parenthetical notes from English
        cleaned_english, parenthetical_notes = self.extract_parenthetical(english)

        # Split translations by comma
        english_translations = self.split_translations(cleaned_english)

        if not english_translations:
            logger.warning(f"Skipping row {row_number}: no valid translations after processing")
            return

        # Create translation IDs
        translation_ids = [self.create_or_get_translation(eng) for eng in english_translations]

        # Create notes
        note_ids = []

        # Add pinyin note if present
        if pinyin:
            pinyin_id = self.create_or_get_note(pinyin, show_before=True, note_type="pinyin")
            note_ids.append(pinyin_id)

        # Add parenthetical notes
        for note_content in parenthetical_notes:
            note_id = self.create_or_get_note(note_content, show_before=False)
            note_ids.append(note_id)

        # Add linguistic type note if present
        if self.current_linguistic_type:
            linguistic_type_id = self.create_or_get_note(
                self.current_linguistic_type,
                show_before=False,
                note_type="linguistic_type"
            )
            note_ids.append(linguistic_type_id)

        # Check if vocab already exists
        if chinese in self.vocab_by_chinese:
            # Merge with existing vocab
            existing_vocab = self.vocab_by_chinese[chinese]

            # Merge translations
            existing_translations = set(existing_vocab.get("translations", []))
            existing_translations.update(translation_ids)
            existing_vocab["translations"] = list(existing_translations)

            # Merge notes
            if note_ids:
                existing_notes = set(existing_vocab.get("notes", []))
                existing_notes.update(note_ids)
                existing_vocab["notes"] = list(existing_notes)

            logger.info(f"Merged vocabulary: {chinese}")
        else:
            # Create new vocab entry
            vocab_id = self.get_next_vocab_id()

            vocab_entry = {
                "id": vocab_id,
                "language": TARGET_LANGUAGE,
                "content": chinese,
                "consideredWord": True,
                "translations": translation_ids
            }

            if note_ids:
                vocab_entry["notes"] = note_ids

            self.vocab_data.append(vocab_entry)
            self.vocab_by_chinese[chinese] = vocab_entry

            logger.info(f"Created vocabulary: {chinese} ({pinyin}) = {', '.join(english_translations)}")

    def parse_html_table(self, html_file_path: str) -> List[Dict]:
        """Parse HTML table and extract vocabulary rows"""
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, 'html.parser')
        table = soup.find('table')

        if not table:
            logger.error("No table found in HTML")
            return []

        table_rows = table.find_all('tr')
        vocab_rows = []

        for row_idx, row in enumerate(table_rows):
            cells = row.find_all('td')

            if len(cells) < 4:
                continue

            # Extract cell content
            number = cells[0].get_text().strip()
            chinese = cells[1].get_text().strip()
            pinyin = cells[2].get_text().strip()
            english = cells[3].get_text().strip()

            # Check if this is a linguistic type header row
            # Pattern: empty number, bold Chinese (type), empty pinyin/english
            if not number and chinese and not english:
                # Check if Chinese cell contains <strong> tag
                strong_tag = cells[1].find('strong')
                if strong_tag:
                    linguistic_type = strong_tag.get_text().strip()
                    self.current_linguistic_type = linguistic_type
                    logger.info(f"Found linguistic type header: {linguistic_type}")
                    continue

            # Skip rows without actual vocabulary (header rows, etc.)
            if not number or not chinese or not english:
                continue

            vocab_rows.append({
                "number": number,
                "chinese": chinese,
                "pinyin": pinyin,
                "english": english,
                "row_idx": row_idx
            })

        logger.info(f"Parsed {len(vocab_rows)} vocabulary rows from HTML table")
        return vocab_rows

    def process_vocab_rows(self, vocab_rows: List[Dict]):
        """Process vocabulary rows and create entries"""
        rows_to_process = vocab_rows[:10] if DEBUG else vocab_rows

        # Reset linguistic type at start
        self.current_linguistic_type = None

        for row in rows_to_process:
            self.create_vocab_entry(
                chinese=row["chinese"],
                pinyin=row["pinyin"],
                english=row["english"],
                row_number=row["number"]
            )

    def save_jsonl_files(self, output_dir_path: str):
        """Save all collected data to JSONL files"""
        output_dir = Path(output_dir_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save vocab.jsonl
        if self.vocab_data:
            with open(output_dir / "vocab.jsonl", "w", encoding="utf-8") as f:
                for entry in self.vocab_data:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # Save translations.jsonl
        if self.translation_data:
            with open(output_dir / "translations.jsonl", "w", encoding="utf-8") as f:
                for entry in self.translation_data:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # Save notes.jsonl
        if self.note_data:
            with open(output_dir / "notes.jsonl", "w", encoding="utf-8") as f:
                for entry in self.note_data:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # Save metadata.json
        metadata = {
            "title": "HSK1 Vocabulary",
            "description": "Essential Mandarin Chinese vocabulary from HSK Level 1",
            "language": TARGET_LANGUAGE,
            "version": "1.0.0"
        }
        with open(output_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)

        logger.info(f"Saved {len(self.vocab_data)} vocab entries")
        logger.info(f"Saved {len(self.translation_data)} translation entries")
        logger.info(f"Saved {len(self.note_data)} note entries")
        logger.info(f"Files saved to: {output_dir}")

def main():
    """Main function to process HSK1 vocabulary"""
    try:
        logger.info("Starting HSK1 vocabulary extraction")

        # Initialize processor
        processor = VocabProcessor()

        # Get the script directory and project root
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)

        # Parse HTML table
        html_file_path = os.path.join(project_root, "public", "data_in", "hsk1_table.html")
        vocab_rows = processor.parse_html_table(html_file_path)

        # Process vocabulary rows
        processor.process_vocab_rows(vocab_rows)

        # Save output files
        output_dir_path = os.path.join(project_root, "public", "sets", TARGET_LANGUAGE, "hsk1-vocab")
        processor.save_jsonl_files(output_dir_path)

        logger.info("HSK1 vocabulary extraction completed successfully!")
        if DEBUG:
            logger.info("DEBUG mode was enabled - only processed first 10 vocabulary rows")

    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise

if __name__ == "__main__":
    main()
