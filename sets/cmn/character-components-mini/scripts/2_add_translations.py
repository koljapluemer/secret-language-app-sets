#!/usr/bin/env python3
"""
Script to add English translations to Chinese vocab entries that don't have translations yet.
Uses DeepL API to translate from Chinese to English.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv
import deepl

# Load environment variables
load_dotenv()

# Paths
SET_DIR = Path(__file__).parent.parent
OUT_DIR = SET_DIR / "out"
VOCAB_FILE = OUT_DIR / "vocab.jsonl"
TRANSLATIONS_FILE = OUT_DIR / "translations.jsonl"

# API client
deepl_client = None

def setup_deepl():
    """Initialize DeepL API client"""
    global deepl_client

    deepl_key = os.getenv('DEEPL_API_KEY')
    if not deepl_key:
        raise ValueError("DEEPL_API_KEY not found in environment variables")

    deepl_client = deepl.Translator(deepl_key)
    print("DeepL API client initialized")

def load_vocab() -> List[Dict]:
    """Load all vocab entries"""
    vocab_list = []
    with open(VOCAB_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                vocab_list.append(json.loads(line))
    return vocab_list

def load_translations() -> Dict[str, Dict]:
    """Load existing translations into a dict keyed by ID"""
    translations = {}
    if TRANSLATIONS_FILE.exists():
        with open(TRANSLATIONS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    trans = json.loads(line)
                    translations[trans['id']] = trans
    return translations

def get_next_translation_id(existing_translations: Dict) -> int:
    """Get the next available translation ID number"""
    if not existing_translations:
        return 1

    # Extract numbers from existing IDs
    max_id = 0
    for trans_id in existing_translations.keys():
        # IDs are like "trans_comp_4E00_0" - extract the last number
        parts = trans_id.split('_')
        if len(parts) > 0:
            try:
                num = int(parts[-1])
                max_id = max(max_id, num)
            except ValueError:
                pass

    return max_id + 1

def translate_with_deepl(text: str) -> Optional[str]:
    """Translate Chinese text to English using DeepL"""
    try:
        result = deepl_client.translate_text(text, target_lang="EN-US")
        return result.text
    except Exception as e:
        print(f"DeepL translation failed for '{text}': {e}")
        return None

def main():
    print("Starting translation addition process...")

    # Setup DeepL API
    setup_deepl()

    # Load data
    print("Loading vocab entries...")
    vocab_list = load_vocab()
    print(f"Loaded {len(vocab_list)} vocab entries")

    print("Loading existing translations...")
    translations = load_translations()
    print(f"Loaded {len(translations)} existing translations")

    # Find vocab entries without translations
    vocab_without_translations = []
    for vocab in vocab_list:
        # Skip if it already has translations
        if vocab.get('translations') and len(vocab['translations']) > 0:
            continue

        # Only process words (not components)
        if vocab.get('consideredWord'):
            vocab_without_translations.append(vocab)

    print(f"Found {len(vocab_without_translations)} vocab entries without translations")

    if not vocab_without_translations:
        print("No vocab entries need translations. Done!")
        return

    # Translate each vocab entry
    new_translations = []
    updated_vocab = []

    for vocab in vocab_without_translations:
        chinese_text = vocab['content']
        print(f"Translating: {chinese_text}")

        english_text = translate_with_deepl(chinese_text)
        if not english_text:
            print(f"  Failed to translate '{chinese_text}', skipping")
            continue

        print(f"  → {english_text}")

        # Create new translation entry
        trans_id = f"trans_{vocab['id']}_0"
        translation = {
            'id': trans_id,
            'content': english_text,
            'notes': []
        }
        new_translations.append(translation)
        translations[trans_id] = translation

        # Update vocab entry
        vocab['translations'] = [trans_id]
        updated_vocab.append(vocab)

    # Write updated translations file
    if new_translations:
        print(f"\nWriting {len(new_translations)} new translations to {TRANSLATIONS_FILE}")
        with open(TRANSLATIONS_FILE, 'a', encoding='utf-8') as f:
            for translation in new_translations:
                f.write(json.dumps(translation, ensure_ascii=False) + '\n')

    # Rewrite vocab file with updated entries
    if updated_vocab:
        print(f"Updating vocab file with {len(updated_vocab)} entries")

        # Read all vocab entries
        all_vocab = load_vocab()

        # Update the ones that need translations
        updated_ids = {v['id'] for v in updated_vocab}
        for i, vocab in enumerate(all_vocab):
            if vocab['id'] in updated_ids:
                # Find the updated version
                for updated in updated_vocab:
                    if updated['id'] == vocab['id']:
                        all_vocab[i] = updated
                        break

        # Write back to file
        with open(VOCAB_FILE, 'w', encoding='utf-8') as f:
            for vocab in all_vocab:
                f.write(json.dumps(vocab, ensure_ascii=False) + '\n')

    print(f"\n✓ Done! Added {len(new_translations)} translations")

if __name__ == '__main__':
    main()
