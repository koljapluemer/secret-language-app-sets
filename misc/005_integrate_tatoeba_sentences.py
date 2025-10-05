#!/usr/bin/env python3
"""
Script to fetch English sentences with target language translations from the Tatoeba API
and generate JSONL files in the proper format for Linguanodon.
"""

import requests
import json
import time
import logging
import urllib.parse
import re
from typing import Dict, List, Any
from pathlib import Path

# Constants
SOURCE_LANGUAGE = 'eng'  # English
TARGET_LANGUAGE = 'rus'
OUTPUT_DIR = f'sets/{TARGET_LANGUAGE}/tatoeba-sentences'
MAX_SENTENCES = 250  # Maximum number of new sentences to download
DEBUG_ABORT_AFTER_FIRST_PAGE = False  # Set to True to abort after first API call for debugging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tatoeba_api_responses.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Data storage
vocab_data = []
translation_data = []
link_data = []

# Existing content tracking
existing_translations = set()

# ID counters
vocab_id = 0
translation_id = 0
link_id = 0

def get_next_vocab_id():
    global vocab_id
    vocab_id += 1
    return str(vocab_id)

def get_next_translation_id():
    global translation_id
    translation_id += 1
    return str(translation_id)


def get_next_link_id():
    global link_id
    link_id += 1
    return str(link_id)

def create_link(label, url, owner=None, owner_link=None, license=None):
    """Create a link entry and return its ID"""
    link_entry = {
        "id": get_next_link_id(),
        "label": label,
        "url": url
    }
    if owner:
        link_entry["owner"] = owner
    if owner_link:
        link_entry["ownerLink"] = owner_link
    if license:
        link_entry["license"] = license
    
    link_data.append(link_entry)
    return link_entry["id"]


def create_translation(content):
    """Create a translation entry and return its ID, or return existing ID if duplicate content"""
    # Check if translation with this content already exists
    for existing in translation_data:
        if existing["content"] == content:
            return existing["id"]
    
    # Create new translation
    translation_entry = {
        "id": get_next_translation_id(),
        "content": content
    }
    
    translation_data.append(translation_entry)
    return translation_entry["id"]

def load_existing_data():
    """Load existing data from files to avoid duplicates"""
    global vocab_id, translation_id, link_id, existing_translations
    
    output_dir = Path(OUTPUT_DIR)
    
    # Load existing translations to check for duplicates
    translations_file = output_dir / "translations.jsonl"
    if translations_file.exists():
        logger.info(f"Loading existing translations from {translations_file}")
        with open(translations_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    entry = json.loads(line.strip())
                    existing_translations.add(entry["content"])
                    # Update ID counter to avoid conflicts
                    if "id" in entry:
                        translation_id = max(translation_id, int(entry["id"]))
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON on line {line_num} in translations.jsonl: {e}")
                except (KeyError, ValueError) as e:
                    logger.warning(f"Invalid entry on line {line_num} in translations.jsonl: {e}")
        
        logger.info(f"Found {len(existing_translations)} existing translations")
    
    # Load existing vocab to update ID counter
    vocab_file = output_dir / "vocab.jsonl"
    if vocab_file.exists():
        logger.info(f"Updating vocab ID counter from {vocab_file}")
        with open(vocab_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    entry = json.loads(line.strip())
                    if "id" in entry:
                        vocab_id = max(vocab_id, int(entry["id"]))
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON on line {line_num} in vocab.jsonl: {e}")
                except (KeyError, ValueError) as e:
                    logger.warning(f"Invalid entry on line {line_num} in vocab.jsonl: {e}")
    
    # Load existing links to update ID counter
    links_file = output_dir / "links.jsonl"
    if links_file.exists():
        logger.info(f"Updating link ID counter from {links_file}")
        with open(links_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    entry = json.loads(line.strip())
                    if "id" in entry:
                        link_id = max(link_id, int(entry["id"]))
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON on line {line_num} in links.jsonl: {e}")
                except (KeyError, ValueError) as e:
                    logger.warning(f"Invalid entry on line {line_num} in links.jsonl: {e}")

def create_vocab(language, content, considered_character=None, considered_sentence=None, considered_word=None, translations=None, links=None, related_vocab=None):
    """Create a vocab entry and return its ID, or return existing ID if duplicate content+language"""
    # Check if vocab with this content+language already exists
    for existing in vocab_data:
        if existing["content"] == content and existing["language"] == language:
            # Update existing entry with new relationships
            if translations:
                if "translations" not in existing:
                    existing["translations"] = []
                for trans_id in translations:
                    if trans_id not in existing["translations"]:
                        existing["translations"].append(trans_id)
            
            if links:
                if "links" not in existing:
                    existing["links"] = []
                for link_id in links:
                    if link_id not in existing["links"]:
                        existing["links"].append(link_id)
            
            if related_vocab:
                if "relatedVocab" not in existing:
                    existing["relatedVocab"] = []
                for vocab_id in related_vocab:
                    if vocab_id not in existing["relatedVocab"]:
                        existing["relatedVocab"].append(vocab_id)
            
            return existing["id"]
    
    # Create new vocab entry
    vocab_entry = {
        "id": get_next_vocab_id(),
        "language": language,
        "content": content
    }
    if considered_character is not None:
        vocab_entry["consideredCharacter"] = considered_character
    if considered_sentence is not None:
        vocab_entry["consideredSentence"] = considered_sentence
    if considered_word is not None:
        vocab_entry["consideredWord"] = considered_word
    if translations:
        vocab_entry["translations"] = translations
    if links:
        vocab_entry["links"] = links
    if related_vocab:
        vocab_entry["relatedVocab"] = related_vocab
    
    vocab_data.append(vocab_entry)
    return vocab_entry["id"]

def fetch_sentences_from_tatoeba():
    """
    Fetch sentences from Tatoeba API and return raw sentence data.
    Stops when we have enough sentences to meet MAX_SENTENCES after filtering duplicates.
    """
    base_url = "https://api.tatoeba.org/unstable/sentences"
    all_sentences = []
    page_count = 0
    new_sentences_found = 0
    params = {
        'lang': SOURCE_LANGUAGE,
        'trans:lang': TARGET_LANGUAGE,
        'sort': 'words',
        'limit': 20,
        'word_count': '3-6'
    }
    after_value = None
    
    logger.info(f"=== Starting Tatoeba API requests (need {MAX_SENTENCES} new sentences) ===")
    
    while new_sentences_found < MAX_SENTENCES:
        page_count += 1
        logger.info(f"Fetching page {page_count}...")
        
        if page_count == 1:
            logger.debug(f"Request URL: {base_url}")
            logger.debug(f"Request params: {params}")
            response = requests.get(base_url, params=params)
        else:
            query = f"lang={SOURCE_LANGUAGE}&trans:lang={TARGET_LANGUAGE}&sort=words&limit=20&word_count=3-6&after={after_value}"
            full_url = f"{base_url}?{query}"
            logger.debug(f"Request URL: {full_url}")
            response = requests.get(full_url)
        
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Response data: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        sentences = data.get('data', [])
        logger.info(f"Page {page_count}: fetched {len(sentences)} sentences")
        
        # Only add new (non-duplicate) sentences
        new_sentences_in_batch = []
        for sentence in sentences:
            source_text = sentence.get('text', '').strip()
            if source_text and source_text not in existing_translations:
                new_sentences_in_batch.append(sentence)
        
        logger.info(f"Page {page_count}: {len(new_sentences_in_batch)} new sentences (not duplicates)")
        new_sentences_found += len(new_sentences_in_batch)
        all_sentences.extend(new_sentences_in_batch)
        
        if DEBUG_ABORT_AFTER_FIRST_PAGE:
            logger.info("DEBUG: Aborting after first API call as requested.")
            break
        
        paging = data.get('paging', {})
        next_url = paging.get('next')
        logger.info(f"Next URL: {next_url}")
        
        if not next_url or len(sentences) == 0:
            logger.info(f"No more pages available. Total sentences fetched: {len(all_sentences)}")
            break
        
        match = re.search(r'after=([^&]+)', next_url)
        if match:
            after_value = urllib.parse.unquote(match.group(1))
            logger.info(f"Next page will use after={after_value}")
        else:
            logger.error("Could not extract 'after' value from next_url. Stopping pagination.")
            break
        
        logger.info("Sleeping 1 second before next page...")
        time.sleep(1)
    
    logger.info(f"Successfully fetched {len(all_sentences)} new sentences")
    return all_sentences

def process_tatoeba_sentences(sentences):
    """Process Tatoeba sentences and create vocab/translation/note/link entries"""
    logger.info("Processing Tatoeba sentences into structured data...")
    
    # Create shared link for Tatoeba
    tatoeba_link_id = create_link(
        "tatoeba.org",
        "https://tatoeba.org",
        None,  # No specific owner
        None,  # No owner link
        "CC BY 2.0"  # Tatoeba's license
    )
    
    processed_count = 0
    
    for sentence in sentences:
        try:
            # Extract source sentence info
            source_text = sentence.get('text', '').strip()
            source_id = sentence.get('id')
            source_owner = sentence.get('owner')
            source_license = sentence.get('license')
            
            if not source_text:
                continue
            
            # Find target language translation FIRST
            target_text = None
            target_owner = None
            target_license = None
            target_id = None
            
            translations = sentence.get('translations', [])
            for translation_group in translations:
                for translation in translation_group:
                    if translation.get('lang') == TARGET_LANGUAGE:
                        target_text = translation.get('text', '').strip()
                        target_owner = translation.get('owner')
                        target_license = translation.get('license')
                        target_id = translation.get('id')
                        break
                if target_text:
                    break
            
            if not target_text:
                logger.debug(f"No {TARGET_LANGUAGE} sentence found for English: {source_text}")
                continue
            
            # Only create links AFTER we know we have both sentences
            # Create source sentence link
            source_link_id = create_link(
                f"Tatoeba #{source_id}",
                f"https://tatoeba.org/en/sentences/show/{source_id}" if source_id else "https://tatoeba.org",
                source_owner,
                f"https://tatoeba.org/en/user/profile/{source_owner}" if source_owner else None,
                source_license
            )
            
            # Create target sentence link
            target_link_id = create_link(
                f"Tatoeba #{target_id}",
                f"https://tatoeba.org/en/sentences/show/{target_id}" if target_id else "https://tatoeba.org",
                target_owner,
                f"https://tatoeba.org/en/user/profile/{target_owner}" if target_owner else None,
                target_license
            )
            
            # Create translation entry for source language sentence
            source_translation_id = create_translation(source_text)
            
            # Create vocab entry ONLY for target language sentence
            target_vocab_id = create_vocab(
                language=TARGET_LANGUAGE,
                content=target_text,
                considered_sentence=True,  # These are full sentences
                translations=[source_translation_id],
                links=[target_link_id, tatoeba_link_id]
            )
            
            # Add to existing translations so we don't fetch it again in future runs
            existing_translations.add(source_text)
            
            processed_count += 1
            if processed_count % 50 == 0:
                logger.info(f"Processed {processed_count} sentence pairs...")
                
        except Exception as e:
            logger.error(f"Error processing sentence: {e}")
            continue
    
    logger.info(f"Successfully processed {processed_count} new sentence pairs")

def save_jsonl_files():
    """Save all collected data to JSONL files (append mode)"""
    # Create directory structure
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not vocab_data and not translation_data and not link_data:
        logger.info("No new data to save")
        return
    
    # Save vocab.jsonl (append mode)
    with open(output_dir / "vocab.jsonl", "a", encoding="utf-8") as f:
        for entry in vocab_data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    # Save translations.jsonl (append mode)
    with open(output_dir / "translations.jsonl", "a", encoding="utf-8") as f:
        for entry in translation_data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    # Save links.jsonl (append mode)
    with open(output_dir / "links.jsonl", "a", encoding="utf-8") as f:
        for entry in link_data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    logger.info(f"Appended {len(vocab_data)} vocab entries")
    logger.info(f"Appended {len(translation_data)} translation entries")
    logger.info(f"Appended {len(link_data)} link entries")
    logger.info(f"Files saved to: {output_dir}")

def main():
    """Main function to fetch data and generate JSONL files."""
    try:
        # Load existing data to avoid duplicates
        load_existing_data()
        
        # Fetch sentences from Tatoeba API
        sentences = fetch_sentences_from_tatoeba()
        if not sentences:
            logger.error("No sentences fetched. Exiting.")
            return
        
        # Process sentences into structured data
        process_tatoeba_sentences(sentences)
        
        # Save data to JSONL files
        save_jsonl_files()
        
        logger.info("Successfully completed Tatoeba sentence integration!")
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise

if __name__ == "__main__":
    main()