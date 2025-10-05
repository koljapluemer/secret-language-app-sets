#!/usr/bin/env python3

import json
import os
from pathlib import Path

# Data storage
immersion_content_data = []
vocab_data = []
translation_data = []
note_data = []

# ID counters
immersion_content_id = 0
vocab_id = 0
translation_id = 0
note_id = 0

def get_next_immersion_content_id():
    global immersion_content_id
    immersion_content_id += 1
    return str(immersion_content_id)

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

def create_immersion_content(language, title, content=None, priority=None, link_id=None, needed_vocab=None, notes=None):
    """Create an immersion content entry and return its ID"""
    content_entry = {
        "id": get_next_immersion_content_id(),
        "language": language,
        "title": title
    }
    if content:
        content_entry["content"] = content
    if priority is not None:
        content_entry["priority"] = priority
    if link_id:
        content_entry["link"] = link_id
    if needed_vocab:
        content_entry["neededVocab"] = needed_vocab
    if notes:
        content_entry["notes"] = notes
    
    immersion_content_data.append(content_entry)
    return content_entry["id"]

def load_sentences_data():
    """Load the usable sentences data from JSON file"""
    input_file = "data_in/usable_sentences_with_vocab.json"
    
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def process_vocab_item(vocab_item):
    """Process vocab item and return vocab ID"""
    apc_content = vocab_item["apc"]
    eng_content = vocab_item["eng"]
    
    # Create translation for English content
    translation_id = create_translation(eng_content)
    
    # Create vocab entry
    vocab_id = create_vocab(
        language="apc",
        content=apc_content,
        considered_word=True,  # These are single words, so considered as words
        translations=[translation_id] if translation_id else None,
        priority=1
    )
    
    return vocab_id

def process_sentence(sentence_data, index):
    """Process sentence data and create immersion content"""
    apc_sentence = sentence_data["apc"]
    eng_sentence = sentence_data["eng"]
    vocab_items = sentence_data.get("vocab", [])
    
    # Process vocabulary items and get their IDs
    needed_vocab_ids = []
    for vocab_item in vocab_items:
        vocab_id = process_vocab_item(vocab_item)
        if vocab_id:
            needed_vocab_ids.append(vocab_id)
    
    # Create translation note for the sentence
    translation_note_id = create_note(f"Translation: {eng_sentence}")
    
    # Create immersion content entry
    content_id = create_immersion_content(
        language="apc",
        title=f"Levanti Sentence {index + 1}",
        content=apc_sentence,
        priority=index + 1,
        needed_vocab=needed_vocab_ids if needed_vocab_ids else None,
        notes=[translation_note_id] if translation_note_id else None
    )
    
    return content_id

def process_sentences(sentences_data):
    """Process all sentences and create entities"""
    for i, sentence_data in enumerate(sentences_data):
        process_sentence(sentence_data, i)

def save_jsonl_files():
    """Save all collected data to JSONL files"""
    # Create directory structure
    output_dir = Path("sets/apc/levanti-sentences")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save immersion_content.jsonl
    with open(output_dir / "immersion_content.jsonl", "w", encoding="utf-8") as f:
        for entry in immersion_content_data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
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
    
    print(f"Saved {len(immersion_content_data)} immersion content entries")
    print(f"Saved {len(vocab_data)} vocab entries")
    print(f"Saved {len(translation_data)} translation entries")
    print(f"Saved {len(note_data)} note entries")

def main():
    """Main function to convert Levanti dataset to JSONL format"""
    print("Converting Levanti dataset to JSONL format...")
    
    try:
        # Load input data
        sentences_data = load_sentences_data()
        print(f"Loaded {len(sentences_data)} sentences from dataset")
        
        # Process all sentences
        process_sentences(sentences_data)
        
        # Save all data to JSONL files
        save_jsonl_files()
        
        print(f"Processing completed! Created immersion content set with {len(immersion_content_data)} entries")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())