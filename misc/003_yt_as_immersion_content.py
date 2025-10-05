#!/usr/bin/env python3
"""
Script to download YouTube subtitles and extract vocabulary using OpenAI.
Creates RemoteResourceSet with isImmersionContent=true for language learning data.
"""

import os
import json
import sys
import uuid
from pathlib import Path
from typing import List, Dict, Any, Tuple
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
from dotenv import load_dotenv
from collections import Counter, defaultdict
import re

# Data storage
resource_data = []
vocab_data = []
translation_data = []
note_data = []

# ID counters
resource_id = 0
vocab_id = 0
translation_id = 0
note_id = 0

def get_next_resource_id():
    global resource_id
    resource_id += 1
    return str(resource_id)

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

def create_resource(language, title, content=None, priority=None, link=None, vocab=None, notes=None, fact_cards=None):
    """Create a resource entry with isImmersionContent=true and return its ID"""
    resource_entry = {
        "id": get_next_resource_id(),
        "isImmersionContent": True,
        "language": language,
        "title": title
    }
    if content:
        resource_entry["content"] = content
    if priority is not None:
        resource_entry["priority"] = priority
    if link:
        resource_entry["link"] = link
    if vocab:
        resource_entry["vocab"] = vocab
    if notes:
        resource_entry["notes"] = notes
    if fact_cards:
        resource_entry["factCards"] = fact_cards
    
    resource_data.append(resource_entry)
    return resource_entry["id"]

# Load environment variables from .env file
load_dotenv()

# Set the .txt file to use
VIDEO_LIST_TXT = "data_in/apc_ar.txt"  # Change as needed

# Debug option - set to True to process only first 2 videos for testing
RETURN_AFTER_TWO_VIDEOS = True

# Parse language codes from filename
filename = Path(VIDEO_LIST_TXT).stem  # e.g., 'apc_ar'
try:
    TARGET_LANG_CODE, VIDEO_SUBTITLE_LANGUAGE = filename.split("_")
except ValueError:
    print(f"Error: Could not parse language codes from filename '{VIDEO_LIST_TXT}'. Expected format '<target>_<subtitle>.txt'")
    sys.exit(1)

# Types
class VocabObject:
    def __init__(self, original: str, translation: str):
        self.original = original.strip()
        self.translation = translation.strip()
    def __hash__(self):
        return hash((self.original, self.translation))
    def __eq__(self, other):
        return (self.original, self.translation) == (other.original, other.translation)

# Download subtitles (returns list of lines)
def download_subtitles(video_id: str, lang_code: str) -> Tuple[List[str], str]:
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id, languages=[lang_code])
        lines = [entry.text.strip() for entry in transcript if entry.text.strip()]
        print(f"Downloaded {len(lines)} subtitle lines (language: {lang_code})")
        return lines, lang_code
    except Exception as e:
        print(f"Error downloading subtitles: {e}")
        raise

def get_openai_client() -> OpenAI:
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    return OpenAI(api_key=api_key)

def extract_vocab_from_line(line: str, source_language_code: str, client: OpenAI) -> List[VocabObject]:
    prompt = f"""You are an expert in language teaching.\n\nExtract language learning vocabulary from the following subtitle snippet in {source_language_code} language.\n\nGuidelines:\n- Extract meaningful words and phrases that would be useful for language learners\n- Ignore music indicators like [موسيقى] or [music]\n- Extract even single words if they are meaningful vocabulary\n- Ignore proper nouns (names, places, brands), exclamations (oh, wow), and non-translatable words\n- For each extracted word/phrase, provide an English translation suitable for learning\n- Retain correct capitalization and spelling\n- Focus on common, everyday vocabulary that learners would encounter\n- Even if snippets are short, extract any meaningful vocabulary\n- Avoid!! comma-separated synonyms. Simply give the most fitting translation!\n- Only add the pure words/expressions themselves. Do not add notes or extra infos.\n\nReturn your answer as a JSON array with objects containing 'original' and 'translation' fields.\n\nSubtitle snippet to analyze:\n{line}\n"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant specialized in language learning and vocabulary extraction. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        print(f"OpenAI Response for line: {line}\n{content}\n")
        parsed = json.loads(content)
        # Accept both array and object with 'vocabulary' or 'words' keys
        if isinstance(parsed, list):
            return [VocabObject(obj.get('original') or obj.get('word'), obj.get('translation')) for obj in parsed if obj.get('original') or obj.get('word')]
        elif 'vocabulary' in parsed:
            return [VocabObject(obj.get('original') or obj.get('word'), obj.get('translation')) for obj in parsed['vocabulary'] if obj.get('original') or obj.get('word')]
        elif 'words' in parsed:
            return [VocabObject(obj.get('original') or obj.get('word'), obj.get('translation')) for obj in parsed['words'] if obj.get('original') or obj.get('word')]
        else:
            return []
    except Exception as e:
        print(f"Error extracting vocabulary: {e}")
        print(f"Response content: {content if 'content' in locals() else 'No content'}")
        return []

def convert_to_vocab_entry(vocab_obj: VocabObject, target_lang_code: str) -> str:
    """Convert VocabObject to vocab entry and return vocab ID"""
    # Create translation
    translation_id = create_translation(vocab_obj.translation)
    
    # Create vocab entry
    vocab_id = create_vocab(
        language=target_lang_code,
        content=vocab_obj.original,
        considered_word=True,  # These are individual vocabulary words
        translations=[translation_id] if translation_id else None,
        priority=1
    )
    
    return vocab_id

def process_video(video_id: str, target_lang_code: str, subtitle_lang_code: str, client: OpenAI) -> str:
    print(f"Processing YouTube video: {video_id}")
    
    # Download subtitles
    print("Downloading subtitles...")
    lines, subtitle_lang_code_actual = download_subtitles(video_id, subtitle_lang_code)
    print("\n--- SUBTITLE DEBUG (first 3 lines) ---")
    for i, line in enumerate(lines[:3]):
        print(f"Line {i+1}: {line}")
    print("--- END SUBTITLE DEBUG ---\n")
    
    # Extract vocab for each line
    all_vocab = []
    for idx, line in enumerate(lines):
        print(f"\nProcessing line {idx+1}/{len(lines)}: {line}")
        vocab_objs = extract_vocab_from_line(line, subtitle_lang_code_actual, client)
        all_vocab.extend(vocab_objs)
    
    print(f"\nExtracted {len(all_vocab)} vocab objects from all lines.")
    
    # Aggregate vocabulary to avoid duplicates
    unique_vocab = {}
    for vocab_obj in all_vocab:
        key = (vocab_obj.original, vocab_obj.translation)
        if key not in unique_vocab:
            unique_vocab[key] = vocab_obj
    
    # Convert to vocab entries and get IDs
    needed_vocab_ids = [convert_to_vocab_entry(vocab_obj, target_lang_code) 
                       for vocab_obj in unique_vocab.values()]
    
    # Create note for video info
    note_id = create_note(f"YouTube Video ID: {video_id}\nSubtitle language: {subtitle_lang_code_actual}")
    
    # Create resource entry (immersion content)
    resource_id = create_resource(
        language=target_lang_code,
        title=f"YouTube Video - {video_id}",
        content=f"Watch this video: https://www.youtube.com/watch?v={video_id}",
        priority=1,
        vocab=needed_vocab_ids if needed_vocab_ids else None,
        notes=[note_id] if note_id else None
    )
    
    return resource_id

def save_jsonl_files(target_lang_code: str, subtitle_lang_code: str):
    """Save all collected data to JSONL files"""
    # Create directory structure
    output_dir = Path(f"sets/{target_lang_code}/youtube-{target_lang_code}-{subtitle_lang_code}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save resources.jsonl (immersion content as resources)
    with open(output_dir / "resources.jsonl", "w", encoding="utf-8") as f:
        for entry in resource_data:
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
    
    print(f"Saved {len(resource_data)} resource entries (immersion content)")
    print(f"Saved {len(vocab_data)} vocab entries")
    print(f"Saved {len(translation_data)} translation entries")
    print(f"Saved {len(note_data)} note entries")

def main():
    print("Converting YouTube videos to JSONL format...")
    
    try:
        # Read video codes from file
        with open(VIDEO_LIST_TXT, "r", encoding="utf-8") as f:
            video_ids = [line.strip() for line in f if line.strip()]
        
        print(f"Loaded {len(video_ids)} video IDs from {VIDEO_LIST_TXT}")
        
        # Get OpenAI client
        client = get_openai_client()
        
        # Process each video
        for idx, video_id in enumerate(video_ids):
            print(f"\n[{idx+1}/{len(video_ids)}] Processing video: {video_id}")
            try:
                process_video(
                    video_id, TARGET_LANG_CODE, VIDEO_SUBTITLE_LANGUAGE, client
                )
                
            except Exception as e:
                print(f"Error processing video {video_id}: {e}\nSKIPPING this video.")
                continue
            
            # Debug: return after processing 2 videos
            if RETURN_AFTER_TWO_VIDEOS and idx >= 1:
                print(f"\nDEBUG: Returning after processing 2 videos as requested.")
                break
        
        # Save all data to JSONL files
        save_jsonl_files(TARGET_LANG_CODE, VIDEO_SUBTITLE_LANGUAGE)
        
        print(f"Processing completed! Created resource set with {len(resource_data)} immersion content entries")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
