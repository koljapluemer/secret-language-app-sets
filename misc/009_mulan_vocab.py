#!/usr/bin/env python3
"""
- Write out [the mulan vocab script](public/009_mulan_vocab.py)
- [this HTML table](public/data_in/mulan_table.html) is the data source
- your data target is a *remote set*; understand previous set generators to learn how to do that (write summaries for them before building the project!!):
  - public/008_vocab_with_img_and_sound_generalized.py
  - public/007_mandarin_character_deck.py
  - public/006_vocab_with_img_and_sound_mandarin.py
- loop the table and for each row pass the data to the OpenAI API. Get schematized data back. Design the best possible prompt. Use examples.
  - get a list of vocab/expressions/parts of speech back, with a list of translations
  - multiple vocab/multiple translations should be their own object, NOT combined like "tree / bush"
  - annotations should be notes (see data schema), NOT added in paranthesis like "run (verb)"
  - should return only sensible vocabulary, i.e. not first names of people
- the output should be jsonl files similar as to what you see generated elsewhere. Schema:
  - src/entities/remote-sets/validation/translationSchema.ts
  - src/entities/remote-sets/validation/vocabSchema.ts
  - src/entities/remote-sets/validation/noteSchema.ts

## Clarification Questions

**API & Configuration:**
- Which OpenAI API model should be used? (GPT-4, GPT-3.5-turbo, etc.)
- Where should OpenAI API credentials be stored? (environment variables, .env file?)
- Should there be rate limiting between API calls?

something fairly cheap. ".env" file as before. no rate limitng

**Data Processing:**
- Should empty/malformed table rows be skipped or logged as errors?
- How should we handle rows where English or Chinese content is missing?
- What's the minimum/maximum length for extractable vocabulary items?
- Should compound words be split or kept as single vocabulary items?

print malformed and skip. YOU do not split ANYTHING. you pass BOTH the english and the zh TO FUCKING OPENAI, the whole fucking table row content, and DESIGN A PROMPT. 

**Output Structure:**
- What language code should be used for Chinese vocabulary? ("cmn", "zh", "zh-CN"?)
- Should the script generate metadata.json like other generators?
- Where should the output files be saved? (directory structure?)
- Should existing files be overwritten or merged?

cmn. yes, generate metadata. follow directory structure of previous scripts. overwritten.

**Vocabulary Extraction Logic:**
- Should the script extract both individual words AND phrases/expressions?
- How should homonyms or words with multiple meanings be handled?
- Should grammatical particles (的, 了, etc.) be included or filtered out?
- What constitutes "sensible vocabulary" - any specific exclusion criteria beyond names?

yes, both individual words AND phrases, BY ASKING THE FUCKING OPENAI API. All of this is completely not in your scope.

**Quality Control:**
- Should there be validation that extracted Chinese matches the English context?
- How should duplicate vocabulary across different dialogue lines be handled?
- Should there be manual review checkpoints or fully automated processing?

no such validation. integrate duplicate vocabulary. if the OpenAi API returns the same vocab multiple time, merge its translations and notes. No "manual checkpoints" but add a debug const at beginning of files that if true it only runs for five rows
"""

import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import openai

# Load environment variables
load_dotenv()

# Configuration
DEBUG = False  # Set to True to process only first 5 rows
TARGET_LANGUAGE = "cmn"  # Mandarin Chinese (ISO 639-3)
# OUTPUT_DIR will be set relative to project root in main()
MAX_RETRIES = 3
SLEEP_BETWEEN_REQUESTS = 1

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mulan_vocab_generation.log', encoding='utf-8'),
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

        # OpenAI client
        self.openai_client = None

    def setup_openai(self):
        """Initialize OpenAI client"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        self.openai_client = openai.OpenAI(api_key=api_key)
        logger.info("OpenAI client initialized")

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

    def create_or_get_note(self, note_content: str) -> str:
        """Create note entry or return existing ID"""
        if note_content in self.note_by_content:
            return self.note_by_content[note_content]

        note_id = self.get_next_note_id()
        self.note_by_content[note_content] = note_id

        note_entry = {
            "id": note_id,
            "content": note_content,
            "showBeforeExercice": False
        }

        self.note_data.append(note_entry)
        return note_id

    def merge_or_create_vocab(self, chinese_content: str, english_translations: List[str], notes: List[str] = None):
        """Merge vocabulary with existing entry or create new one"""
        # Get or create translation IDs
        translation_ids = [self.create_or_get_translation(eng) for eng in english_translations]

        # Get or create note IDs
        note_ids = []
        if notes:
            note_ids = [self.create_or_get_note(note) for note in notes]

        if chinese_content in self.vocab_by_chinese:
            # Merge with existing vocab
            existing_vocab = self.vocab_by_chinese[chinese_content]

            # Merge translations
            existing_translations = set(existing_vocab.get("translations", []))
            existing_translations.update(translation_ids)
            existing_vocab["translations"] = list(existing_translations)

            # Merge notes
            if note_ids:
                existing_notes = set(existing_vocab.get("notes", []))
                existing_notes.update(note_ids)
                existing_vocab["notes"] = list(existing_notes)

            logger.info(f"Merged vocabulary: {chinese_content}")
        else:
            # Create new vocab entry
            vocab_id = self.get_next_vocab_id()

            vocab_entry = {
                "id": vocab_id,
                "language": TARGET_LANGUAGE,
                "content": chinese_content,
                "consideredWord": True,
                "translations": translation_ids
            }

            if note_ids:
                vocab_entry["notes"] = note_ids

            self.vocab_data.append(vocab_entry)
            self.vocab_by_chinese[chinese_content] = vocab_entry

            logger.info(f"Created new vocabulary: {chinese_content}")

    def extract_vocabulary_with_openai(self, english_text: str, chinese_text: str) -> Optional[List[Dict]]:
        """Use OpenAI to extract vocabulary from dialogue pair"""
        prompt = f"""Extract useful vocabulary words and phrases from this English-Chinese dialogue pair.

English: {english_text}
Chinese: {chinese_text}

Rules:
- Extract both individual words AND useful phrases/expressions
- Create separate objects for different vocabulary items, don't combine like "tree/bush"
- Don't include proper names of people
- Only include notes if they add genuine value (grammar info, usage context, etc.) - most items should have no notes
- Focus on vocabulary that would be useful for language learners"""

        # JSON schema for structured output
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "vocabulary_extraction",
                "schema": {
                    "type": "object",
                    "properties": {
                        "vocabulary": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "chinese": {"type": "string"},
                                    "english": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    },
                                    "notes": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    }
                                },
                                "required": ["chinese", "english"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["vocabulary"],
                    "additionalProperties": False
                }
            }
        }

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a Chinese language expert helping extract vocabulary for language learners."},
                    {"role": "user", "content": prompt}
                ],
                response_format=response_format,
                temperature=0.3,
                max_tokens=1000
            )

            response_text = response.choices[0].message.content.strip()
            result = json.loads(response_text)
            return result["vocabulary"]

        except Exception as e:
            logger.warning(f"OpenAI API call failed: {e}")
            return None

    def parse_html_table(self, html_file_path: str) -> List[Dict]:
        """Parse HTML table and extract dialogue pairs"""
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, 'html.parser')
        table_rows = soup.find_all('tr')

        dialogue_pairs = []

        for row in table_rows:
            cells = row.find_all('td')

            if len(cells) >= 3:
                timestamp = cells[0].get_text().strip()
                english = cells[1].get_text().strip()
                chinese = cells[2].get_text().strip()

                # Skip malformed rows
                if not english or not chinese:
                    logger.warning(f"Skipping malformed row: timestamp={timestamp}, english='{english}', chinese='{chinese}'")
                    continue

                dialogue_pairs.append({
                    "timestamp": timestamp,
                    "english": english,
                    "chinese": chinese
                })

        logger.info(f"Parsed {len(dialogue_pairs)} dialogue pairs from HTML table")
        return dialogue_pairs

    def process_dialogue_pairs(self, dialogue_pairs: List[Dict]):
        """Process dialogue pairs through OpenAI and create vocabulary entries"""
        pairs_to_process = dialogue_pairs[:5] if DEBUG else dialogue_pairs

        for i, pair in enumerate(pairs_to_process):
            logger.info(f"Processing pair {i+1}/{len(pairs_to_process)}: {pair['timestamp']}")

            vocabulary_items = self.extract_vocabulary_with_openai(
                pair["english"],
                pair["chinese"]
            )

            if vocabulary_items:
                for item in vocabulary_items:
                    try:
                        chinese_content = item["chinese"]
                        english_translations = item["english"]
                        notes = item.get("notes", [])

                        self.merge_or_create_vocab(chinese_content, english_translations, notes)

                    except KeyError as e:
                        logger.warning(f"Malformed vocabulary item: {item}, missing key: {e}")
                    except Exception as e:
                        logger.warning(f"Error processing vocabulary item: {item}, error: {e}")

            # Sleep between requests
            if i < len(pairs_to_process) - 1:
                time.sleep(SLEEP_BETWEEN_REQUESTS)

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
            "title": "Mulan Vocabulary",
            "description": "Vocabulary based on Disney's Mulan dialogue",
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
    """Main function to process Mulan vocabulary"""
    try:
        logger.info("Starting Mulan vocabulary extraction")

        # Initialize processor
        processor = VocabProcessor()
        processor.setup_openai()

        # Get the script directory and project root
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)

        # Parse HTML table
        html_file_path = os.path.join(project_root, "public", "data_in", "mulan_table.html")
        dialogue_pairs = processor.parse_html_table(html_file_path)

        # Process dialogue pairs
        processor.process_dialogue_pairs(dialogue_pairs)

        # Save output files
        output_dir_path = os.path.join(project_root, "public", "sets", TARGET_LANGUAGE, "mulan-vocab")
        processor.save_jsonl_files(output_dir_path)

        logger.info("Mulan vocabulary extraction completed successfully!")
        if DEBUG:
            logger.info("DEBUG mode was enabled - only processed first 5 dialogue pairs")

    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise

if __name__ == "__main__":
    main()