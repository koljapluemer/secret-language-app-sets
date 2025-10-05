#!/usr/bin/env python3

import json
import re
from bs4 import BeautifulSoup
import os
from pathlib import Path

# Data storage
vocab_data = []
translation_data = []
note_data = []

# ID counters
vocab_id = 0
translation_id = 0
note_id = 0

def get_next_vocab_id():
    global vocab_id
    vocab_id += 1
    return str(vocab_id)

def get_next_translation_id():
    global translation_id
    translation_id += 1
    return str(translation_id)

def get_next_note_id():
    global note_id
    note_id += 1
    return str(note_id)

def clean_text(text):
    """Clean text by stripping whitespace and handling empty strings"""
    return text.strip() if text else ""

def process_english_word(english_text):
    """Process English word: lowercase, handle slashes, extract parentheses"""
    if not english_text:
        return "", ""
    
    # Handle slashes - ignore everything after slash
    if '/' in english_text:
        english_text = english_text.split('/')[0].strip()
    
    # Extract parentheses content for notes
    note_content = ""
    parentheses_match = re.search(r'\(([^)]+)\)', english_text)
    if parentheses_match:
        note_content = parentheses_match.group(1).strip()
        # Remove parentheses and content from the main text
        english_text = re.sub(r'\s*\([^)]*\)', '', english_text).strip()
    
    # Convert to lowercase
    english_text = english_text.lower()
    
    return english_text, note_content

def process_arabic_word(arabic_text):
    """Process Arabic word: handle slashes"""
    if not arabic_text:
        return ""
    
    # Handle slashes - ignore everything after slash
    if '/' in arabic_text:
        arabic_text = arabic_text.split('/')[0].strip()
    
    return arabic_text.strip()

def extract_pronunciation(pronunciation_text):
    """Extract pronunciation from em tags"""
    if not pronunciation_text:
        return ""
    
    # Remove em tags and clean
    pronunciation = re.sub(r'<[^>]+>', '', pronunciation_text).strip()
    return pronunciation

def create_note(content, note_type=None, show_before_exercise=None):
    """Create a note entry and return its ID"""
    if not content:
        return None
    
    note_entry = {
        "id": get_next_note_id(),
        "content": content
    }
    if note_type:
        note_entry["noteType"] = note_type
    if show_before_exercise is not None:
        note_entry["showBeforeExercice"] = show_before_exercise
    
    note_data.append(note_entry)
    return note_entry["id"]

def create_translation(content, notes=None):
    """Create a translation entry and return its ID"""
    if not content:
        return None
        
    translation_entry = {
        "id": get_next_translation_id(),
        "content": content
    }
    if notes:
        translation_entry["notes"] = notes
    
    translation_data.append(translation_entry)
    return translation_entry["id"]

def create_vocab(language, content, considered_character=None, considered_sentence=None, considered_word=None, notes=None, translations=None, priority=None):
    """Create a vocab entry and return its ID"""
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
    if priority is not None:
        vocab_entry["priority"] = priority
    if notes:
        vocab_entry["notes"] = notes
    if translations:
        vocab_entry["translations"] = translations
    
    vocab_data.append(vocab_entry)
    return vocab_entry["id"]

def parse_html_table():
    """Parse the HTML table and extract vocabulary data"""
    html_file = "data_in/1000_common_levantine.html"
    
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    
    # Find the table
    table = soup.find('table')
    if not table:
        raise ValueError("No table found in HTML file")
    
    # Find all data rows (skip header)
    rows = table.find('tbody').find_all('tr')
    
    for priority, row in enumerate(rows, 1):
        cells = row.find_all('td')
        if len(cells) != 3:
            continue
        
        english_cell = cells[0]
        arabic_cell = cells[1]
        pronunciation_cell = cells[2]
        
        # Extract text content
        english_raw = clean_text(english_cell.get_text())
        arabic_raw = clean_text(arabic_cell.get_text())
        pronunciation_raw = clean_text(pronunciation_cell.get_text())
        
        # Process the texts
        english_processed, english_note = process_english_word(english_raw)
        arabic_processed = process_arabic_word(arabic_raw)
        pronunciation_processed = extract_pronunciation(pronunciation_raw)
        
        if not english_processed or not arabic_processed:
            continue
        
        # Create notes
        notes = []
        translation_notes = []
        
        if pronunciation_processed:
            pronunciation_note_id = create_note(pronunciation_processed, "pronunciation")
            if pronunciation_note_id:
                notes.append(pronunciation_note_id)
        
        if english_note:
            english_note_id = create_note(english_note, None, True)
            if english_note_id:
                translation_notes.append(english_note_id)
        
        # Create translation
        translation_id = create_translation(english_processed, translation_notes if translation_notes else None)
        
        # Create vocab entry
        create_vocab(
            language="apc",
            content=arabic_processed,
            considered_word=True,  # These are single words, so considered as words
            notes=notes if notes else None,
            translations=[translation_id] if translation_id else None,
            priority=priority
        )

def save_jsonl_files():
    """Save all collected data to JSONL files"""
    # Create directory structure
    output_dir = Path("sets/apc/1000-common-levantine")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save vocab.jsonl
    with open(output_dir / "vocab.jsonl", "w", encoding="utf-8") as f:
        for entry in vocab_data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    # Save translations.jsonl
    with open(output_dir / "translations.jsonl", "w", encoding="utf-8") as f:
        for entry in translation_data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    # Save notes.jsonl
    with open(output_dir / "notes.jsonl", "w", encoding="utf-8") as f:
        for entry in note_data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    print(f"Saved {len(vocab_data)} vocab entries")
    print(f"Saved {len(translation_data)} translation entries")
    print(f"Saved {len(note_data)} note entries")

def main():
    """Main function to parse HTML and create JSON output"""
    print("Parsing HTML table...")
    
    try:
        parse_html_table()
        
        # Save all data to JSONL files
        save_jsonl_files()
        
        print(f"Processing completed! Created vocab set with {len(vocab_data)} entries")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())