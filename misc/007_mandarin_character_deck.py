#!/usr/bin/env python3

import json
import os
import shutil
from typing import Dict, List, Any, Optional
from uuid import uuid4

def load_json(filepath: str) -> Any:
    """Load JSON data from file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_jsonl(data: List[Dict], filepath: str) -> None:
    """Save data as JSONL (JSON Lines) format."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

def copy_sound_file(word: str, sounds_dir: str, output_audio_dir: str) -> Optional[str]:
    """Copy sound file to output directory if it exists."""
    sound_file = f"{word}.mp3"
    source_path = os.path.join(sounds_dir, sound_file)
    
    if os.path.exists(source_path):
        # Create audio directory if it doesn't exist
        os.makedirs(output_audio_dir, exist_ok=True)
        
        # Copy the file
        dest_path = os.path.join(output_audio_dir, sound_file)
        shutil.copy2(source_path, dest_path)
        return sound_file
    
    return None

def parse_translation_content(content: str) -> tuple[str, Optional[str]]:
    """Parse translation content, extracting parenthetical notes."""
    if '(' in content and content.endswith(')'):
        # Find the last opening parenthesis
        paren_start = content.rfind('(')
        main_content = content[:paren_start].strip()
        note_content = content[paren_start+1:-1].strip()
        return main_content, note_content
    return content, None

def create_mandarin_character_deck():
    """Create a mandarin character deck from the input data."""
    
    # Get the script directory and project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    # File paths
    words_file = os.path.join(project_root, "public", "data_in", "chinese_words_tone_matches.json")
    translations_file = os.path.join(project_root, "public", "data_in", "chinese_translations.json")
    sounds_dir = os.path.join(project_root, "public", "data_in", "sounds")
    output_dir = os.path.join(project_root, "public", "sets", "cmn", "mandarin-character-deck")
    output_audio_dir = os.path.join(output_dir, "audio")
    
    # Load input data
    print("Loading input data...")
    words_data = load_json(words_file)
    translations_data = load_json(translations_file)
    
    # Storage for output data
    vocab_items = []
    translation_items = []
    note_items = []
    
    # ID mappings for relationships
    vocab_id_map = {}  # word -> vocab_id
    translation_id_map = {}  # content -> translation_id
    note_id_map = {}  # (content, noteType) -> note_id
    
    print(f"Processing {len(words_data)} word entries...")
    
    # Process each word entry
    for word_entry in words_data:
        main_word = word_entry["word"]
        main_pinyin = word_entry["pinyin"]
        closest_matches = word_entry.get("closest_matches", [])
        
        # Create main vocab item
        main_vocab_id = f"vocab_{len(vocab_items)}"
        vocab_id_map[main_word] = main_vocab_id
        
        # Get translation for main word
        translation_ids = []
        if main_word in translations_data:
            translation_content = translations_data[main_word]
            
            # First extract parenthetical content, then split by commas
            main_content, note_content = parse_translation_content(translation_content)
            
            # Split the main content by commas and create separate translations
            translation_parts = [part.strip() for part in main_content.split(',') if part.strip()]
            
            for part in translation_parts:
                
                # Create translation
                if part not in translation_id_map:
                    translation_id = f"translation_{len(translation_items)}"
                    translation_id_map[part] = translation_id
                    
                    translation_item = {
                        "id": translation_id,
                        "content": part,
                        "priority": 1
                    }
                    
                    # Add note if there was parenthetical content
                    if note_content:
                        note_key = (note_content, "translation_note")
                        if note_key not in note_id_map:
                            note_id = f"note_{len(note_items)}"
                            note_id_map[note_key] = note_id
                            
                            note_items.append({
                                "id": note_id,
                                "content": note_content,
                                "noteType": "translation_note",
                                "showBeforeExercice": False
                            })
                        
                        translation_item["notes"] = [note_id_map[note_key]]
                    
                    translation_items.append(translation_item)
                
                translation_ids.append(translation_id_map[part])
        
        # Create pinyin note for main word
        pinyin_note_key = (main_pinyin, "pinyin")
        if pinyin_note_key not in note_id_map:
            note_id = f"note_{len(note_items)}"
            note_id_map[pinyin_note_key] = note_id
            
            note_items.append({
                "id": note_id,
                "content": main_pinyin,
                "noteType": "pinyin",
                "showBeforeExercice": False
            })
        
        main_pinyin_note_id = note_id_map[pinyin_note_key]
        
        # Copy sound file to output directory
        sound_filename = copy_sound_file(main_word, sounds_dir, output_audio_dir)
        sounds_data = []
        if sound_filename:
            sounds_data.append({"filename": sound_filename})
        
        # Create main vocab entry
        main_vocab = {
            "id": main_vocab_id,
            "language": "cmn",
            "content": main_word,
            "consideredWord": True,
            "priority": 1,
            "notes": [main_pinyin_note_id],
            "translations": translation_ids,
            "similarSoundingButNotTheSame": [],  # Will be filled later
            "sounds": sounds_data if sounds_data else None
        }
        
        # Remove None values
        if main_vocab["sounds"] is None:
            del main_vocab["sounds"]
            
        vocab_items.append(main_vocab)
        
        # Process closest matches
        related_vocab_ids = []
        for match in closest_matches:
            match_word = match["word"]
            match_pinyin = match["pinyin"]
            
            # Create vocab for match if not exists
            if match_word not in vocab_id_map:
                match_vocab_id = f"vocab_{len(vocab_items)}"
                vocab_id_map[match_word] = match_vocab_id
                
                # Get translation for match
                match_translation_ids = []
                if match_word in translations_data:
                    translation_content = translations_data[match_word]
                    
                    # First extract parenthetical content, then split by commas
                    main_content, note_content = parse_translation_content(translation_content)
                    
                    # Split the main content by commas and create separate translations
                    translation_parts = [part.strip() for part in main_content.split(',') if part.strip()]
                    
                    for part in translation_parts:
                        
                        if part not in translation_id_map:
                            translation_id = f"translation_{len(translation_items)}"
                            translation_id_map[part] = translation_id
                            
                            translation_item = {
                                "id": translation_id,
                                "content": part,
                                "priority": 1
                            }
                            
                            if note_content:
                                note_key = (note_content, "translation_note")
                                if note_key not in note_id_map:
                                    note_id = f"note_{len(note_items)}"
                                    note_id_map[note_key] = note_id
                                    
                                    note_items.append({
                                        "id": note_id,
                                        "content": note_content,
                                        "noteType": "translation_note",
                                        "showBeforeExercice": False
                                    })
                                
                                translation_item["notes"] = [note_id_map[note_key]]
                            
                            translation_items.append(translation_item)
                        
                        match_translation_ids.append(translation_id_map[part])
                
                # Create pinyin note for match
                match_pinyin_note_key = (match_pinyin, "pinyin")
                if match_pinyin_note_key not in note_id_map:
                    note_id = f"note_{len(note_items)}"
                    note_id_map[match_pinyin_note_key] = note_id
                    
                    note_items.append({
                        "id": note_id,
                        "content": match_pinyin,
                        "noteType": "pinyin",
                        "showBeforeExercice": False
                    })
                
                match_pinyin_note_id = note_id_map[match_pinyin_note_key]
                
                # Copy sound file to output directory
                match_sound_filename = copy_sound_file(match_word, sounds_dir, output_audio_dir)
                match_sounds_data = []
                if match_sound_filename:
                    match_sounds_data.append({"filename": match_sound_filename})
                
                # Create match vocab entry
                match_vocab = {
                    "id": match_vocab_id,
                    "language": "cmn",
                    "content": match_word,
                    "consideredCharacter": True,
                    "consideredWord": True,
                    "priority": 1,
                    "notes": [match_pinyin_note_id],
                    "translations": match_translation_ids,
                    "relatedVocab": [],  # Not used for minimal pairs
            "similarSoundingButNotTheSame": [],  # Will be filled later
                    "sounds": match_sounds_data if match_sounds_data else None
                }
                
                # Remove None values
                if match_vocab["sounds"] is None:
                    del match_vocab["sounds"]
                
                vocab_items.append(match_vocab)
            
            related_vocab_ids.append(vocab_id_map[match_word])
        
        # Update main vocab with related vocab IDs
        if related_vocab_ids:
            # Find the main vocab item and update it
            for vocab_item in vocab_items:
                if vocab_item["id"] == main_vocab_id:
                    vocab_item["similarSoundingButNotTheSame"] = related_vocab_ids
                    break
    
    # Create metadata
    metadata = {
        "title": "Mandarin Character Deck",
        "description": "A comprehensive deck of Mandarin Chinese characters and words with pronunciation and related characters",
        "language": "cmn",
        "version": "1.0.0"
    }
    
    # Save output files
    print("Saving output files...")
    
    # Save vocabulary
    save_jsonl(vocab_items, f"{output_dir}/vocab.jsonl")
    print(f"Saved {len(vocab_items)} vocabulary items")
    
    # Save translations
    save_jsonl(translation_items, f"{output_dir}/translations.jsonl")
    print(f"Saved {len(translation_items)} translations")
    
    # Save notes
    save_jsonl(note_items, f"{output_dir}/notes.jsonl")
    print(f"Saved {len(note_items)} notes")
    
    # Save metadata
    with open(f"{output_dir}/metadata.json", 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print("Saved metadata")
    
    # Create index entry for language sets
    index_file = os.path.join(project_root, "public", "sets", "cmn", "index.json")
    if os.path.exists(index_file):
        with open(index_file, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
    else:
        index_data = []
    
    if "mandarin-character-deck" not in index_data:
        index_data.append("mandarin-character-deck")
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        print("Updated index.json")
    
    print(f"\nDeck creation complete!")
    print(f"Total vocabulary items: {len(vocab_items)}")
    print(f"Total translations: {len(translation_items)}")
    print(f"Total notes: {len(note_items)}")
    print(f"Output saved to: {output_dir}")

if __name__ == "__main__":
    create_mandarin_character_deck()