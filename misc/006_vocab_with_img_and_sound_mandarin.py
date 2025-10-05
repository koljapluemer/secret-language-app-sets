#!/usr/bin/env python3
"""
Script to generate Mandarin Chinese vocabulary with images and sound.
Creates JSONL files with vocab, translations, notes, and links for Linguanodon.
"""

import os
import json
import requests
import time
import logging
import random
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import deepl
from pexelsapi.pexels import Pexels
import re

# Load environment variables
load_dotenv()

# Configuration
DEBUG = False  # Set to True to process only first two words
TARGET_LANGUAGE = "cmn"  # Mandarin Chinese (ISO 639-3)
SOURCE_LANGUAGE = "eng"  # English (ISO 639-3)
OUTPUT_DIR = f"sets/{TARGET_LANGUAGE}/basic-vocab-with-images-and-sound"
MAX_RETRIES = 3
SLEEP_BETWEEN_REQUESTS = 1

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vocab_generation.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# API clients
deepL_client = None
pexels_api = None
speechgen_token = None
speechgen_email = None
available_voices = []

# Data storage
vocab_data = []
translation_data = []
note_data = []
link_data = []

# ID counters
vocab_id = 0
translation_id = 0
note_id = 0
link_id = 0

# Shared link ID - created once, used by all vocab entries
shared_pexels_link_id = None

WORDS = [
    "the apple", "the banana", "the orange", "the grape", "the watermelon", "the strawberry", "the lemon", "the peach", "the pear", "the pineapple",
    "the dog", "the cat", "the horse", "the cow", "the sheep", "the pig", "the chicken", "the duck", "the goose", "the rabbit",
    "the car", "the bus", "the bicycle", "the motorcycle", "the truck", "the train", "the boat", "the ship", "the airplane", "the helicopter",
    "the table", "the chair", "the bed", "the sofa", "the desk", "the lamp", "the door", "the window", "the cup", "the plate",
    "the house", "the apartment", "the school", "the hospital", "the store", "the restaurant", "the bridge", "the road", "the park", "the garden",
    "the tree", "the flower", "the grass", "the leaf", "the mountain", "the river", "the lake", "the sea", "the beach", "the island",
    "the sun", "the moon", "the star", "the cloud", "the rain", "the snow", "the wind", "the fire", "the ice", "the stone",
    "the man", "the woman", "the boy", "the girl", "the baby", "the teacher", "the doctor", "the farmer", "the police", "the chef",
    "the book", "the pen", "the pencil", "the paper", "the notebook", "the bag", "the phone", "the computer", "the clock", "the watch",
    "the shirt", "the pants", "the dress", "the skirt", "the shoes", "the hat", "the coat", "the socks", "the belt", "the gloves",
    "the bread", "the rice", "the egg", "the cheese", "the meat", "the fish", "the milk", "the butter", "the soup", "the cake",
    "the salt", "the sugar", "the pepper", "the oil", "the water", "the tea", "the coffee", "the juice", "the sandwich", "the pizza",
    "the ball", "the kite", "the doll", "the toy", "the bottle", "the box", "the bag", "the key", "the knife", "the fork",
    "the spoon", "the mirror", "the soap", "the brush", "the toothbrush", "the toothpaste", "the comb", "the towel", "the bucket", "the rope",
    "running", "walking", "jumping", "sitting", "standing", "sleeping", "eating", "drinking", "reading", "writing",
    "opening", "closing", "pushing", "pulling", "throwing", "catching", "climbing", "swimming", "driving", "riding",
    "singing", "dancing", "drawing", "painting", "cooking", "cleaning", "washing", "cutting", "building", "playing",
    "smiling", "crying", "laughing", "talking", "listening", "watching", "looking", "pointing", "waving", "carrying",
    "buying", "selling", "paying", "finding", "holding", "picking", "dropping", "helping", "sending", "calling",
    "digging", "planting", "watering", "feeding", "hunting", "fishing", "baking", "mixing", "fixing", "driving",
    "jumping", "kicking", "hitting", "throwing", "catching", "hugging", "kissing", "shaking", "turning", "stopping"
]

def setup_apis():
    """Initialize API clients with environment variables"""
    global deepl_client, pexels_api, speechgen_token, speechgen_email, available_voices
    
    # DeepL
    deepl_key = os.getenv('DEEPL_API_KEY')
    if not deepl_key:
        raise ValueError("DEEPL_API_KEY not found in environment variables")
    deepl_client = deepl.Translator(deepl_key)
    
    # Pexels
    pexels_key = os.getenv('PEXELS_API_KEY')
    if not pexels_key:
        raise ValueError("PEXELS_API_KEY not found in environment variables")
    pexels_api = Pexels(pexels_key)
    
    # SpeechGen
    speechgen_token = os.getenv('SPEECHGEN_API_KEY')
    speechgen_email = os.getenv('SPEECHGEN_EMAIL')
    if not speechgen_token:
        raise ValueError("SPEECHGEN_API_KEY not found in environment variables")
    if not speechgen_email:
        raise ValueError("SPEECHGEN_EMAIL not found in environment variables")
    
    # Fetch available voices
    available_voices = fetch_speechgen_voices()
    if not available_voices:
        raise ValueError("Failed to fetch SpeechGen voices")
    
    logger.info(f"API clients initialized successfully with {len(available_voices)} voices")

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

def get_next_link_id():
    global link_id
    link_id += 1
    return str(link_id)

def create_link(label: str, url: str, owner: Optional[str] = None, owner_link: Optional[str] = None, license: Optional[str] = None) -> str:
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

def create_note(content: str, note_type: Optional[str] = None, show_before_exercise: Optional[bool] = None) -> str:
    """Create a note entry and return its ID"""
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

def create_translation(content: str, notes: Optional[List[str]] = None) -> str:
    """Create a translation entry and return its ID"""
    translation_entry = {
        "id": get_next_translation_id(),
        "content": content
    }
    if notes:
        translation_entry["notes"] = notes
    
    translation_data.append(translation_entry)
    return translation_entry["id"]

def create_vocab(language: str, content: str, considered_character: Optional[bool] = None, 
                considered_sentence: Optional[bool] = None, considered_word: Optional[bool] = None,
                notes: Optional[List[str]] = None, translations: Optional[List[str]] = None, 
                links: Optional[List[str]] = None, images: Optional[List[Dict]] = None, 
                sounds: Optional[List[Dict]] = None, is_picturable: Optional[bool] = None) -> str:
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
    if notes:
        vocab_entry["notes"] = notes
    if translations:
        vocab_entry["translations"] = translations
    if links:
        vocab_entry["links"] = links
    if images:
        vocab_entry["images"] = images
    if sounds:
        vocab_entry["sounds"] = sounds
    if is_picturable is not None:
        vocab_entry["isPicturable"] = is_picturable
    
    vocab_data.append(vocab_entry)
    return vocab_entry["id"]

def clean_word_for_search(word: str) -> str:
    """Remove 'the ' article and clean word for image search"""
    cleaned = word.lower()
    if cleaned.startswith("the "):
        cleaned = cleaned[4:]
    return cleaned

def translate_with_deepl(text: str, timeout: int = 30) -> Optional[Dict[str, str]]:
    """Translate text to Mandarin using DeepL"""
    try:
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"DeepL translation timed out after {timeout} seconds")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        
        try:
            result = deepl_client.translate_text(text, target_lang="ZH-HANS")  # Chinese Simplified
            signal.alarm(0)  # Cancel alarm
            return {
                "text": result.text,
                "detected_source_lang": result.detected_source_lang
            }
        finally:
            signal.alarm(0)  # Ensure alarm is cancelled
            
    except Exception as e:
        logger.warning(f"DeepL translation failed for '{text}': {e}")
        return None

def download_image_from_pexels(search_term: str, filename: str) -> bool:
    """Download image from Pexels and save to images directory"""
    # Check if file already exists
    images_dir = Path(OUTPUT_DIR) / "images"
    image_path = images_dir / filename
    if image_path.exists():
        logger.info(f"Image already exists for '{search_term}': {filename}")
        return True
    
    try:
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Pexels search timed out after 30 seconds")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)
        
        try:
            # Search for photos
            photos = pexels_api.search_photos(query=search_term, page=1, per_page=1)
            signal.alarm(0)  # Cancel alarm
        finally:
            signal.alarm(0)  # Ensure alarm is cancelled
        
        if not photos or 'photos' not in photos or len(photos['photos']) == 0:
            logger.warning(f"No images found on Pexels for '{search_term}'")
            return False
        
        # Get first photo
        photo = photos['photos'][0]
        image_url = photo['src']['medium']  # Use medium size
        photographer = photo['photographer']
        photo_url = photo['url']
        
        # Download image with timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)
        
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            signal.alarm(0)  # Cancel alarm
        finally:
            signal.alarm(0)  # Ensure alarm is cancelled
        
        # Save image
        images_dir.mkdir(parents=True, exist_ok=True)
        
        with open(image_path, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"Downloaded image for '{search_term}' from {photographer}")
        return True
        
    except Exception as e:
        logger.warning(f"Failed to download image for '{search_term}': {e}")
        return False

def fetch_speechgen_voices() -> List[Dict]:
    """Fetch available voices from SpeechGen API"""
    try:
        response = requests.get(
            "https://speechgen.io/index.php?r=api/voices",
            timeout=30
        )
        response.raise_for_status()
        
        voices_data = response.json()
        if 'Chinese' in voices_data:
            chinese_voices = voices_data['Chinese']
            logger.info(f"Found {len(chinese_voices)} Chinese voices")
            return chinese_voices
        else:
            logger.warning("No 'Chinese' key found in voices data")
            return []
    except Exception as e:
        logger.warning(f"Failed to fetch voices: {e}")
        return []

def generate_audio_with_speechgen(text: str, filename: str) -> bool:
    """Generate audio using SpeechGen TTS"""
    # Check if file already exists
    audio_dir = Path(OUTPUT_DIR) / "audio"
    audio_path = audio_dir / filename
    if audio_path.exists():
        logger.info(f"Audio already exists for '{text}': {filename}")
        return True
    
    try:
        # Select random voice
        voice = random.choice(available_voices)
        voice_name = voice.get('voice', voice.get('name', 'default'))
        
        # Prepare API request
        params = {
            'token': speechgen_token,
            'email': speechgen_email,
            'voice': voice_name,
            'text': text,
            'format': 'mp3',
            'speed': 1.0
        }
        
        logger.info(f"Generating audio for '{text}' using voice '{voice_name}'")
        
        # Make API request
        response = requests.post(
            "https://speechgen.io/index.php?r=api/text",
            data=params,
            timeout=60
        )
        response.raise_for_status()
        
        result = response.json()
        
        if result.get('status') == 1 and 'file' in result:
            # Download the audio file
            audio_url = result['file']
            audio_response = requests.get(audio_url, timeout=30)
            audio_response.raise_for_status()
            
            # Save audio
            audio_dir.mkdir(parents=True, exist_ok=True)
            
            # Change extension to mp3 since SpeechGen returns mp3
            audio_path = audio_path.with_suffix('.mp3')
            
            with open(audio_path, 'wb') as f:
                f.write(audio_response.content)
            
            logger.info(f"Generated audio for '{text}' using voice '{voice_name}'")
            return True
        else:
            logger.warning(f"SpeechGen API failed: {result}")
            return False
        
    except Exception as e:
        logger.warning(f"Failed to generate audio for '{text}': {e}")
        return False

def process_word(english_word: str) -> bool:
    """Process a single word: translate, get image, generate audio, create data entries"""
    logger.info(f"Processing word: '{english_word}'")
    
    # Clean word for image search
    search_term = clean_word_for_search(english_word)
    
    # Translate to Mandarin
    translation_result = translate_with_deepl(english_word)
    if not translation_result:
        logger.warning(f"Skipping '{english_word}' - translation failed")
        return False
    
    mandarin_word = translation_result["text"]
    logger.info(f"Translated '{english_word}' to '{mandarin_word}'")
    
    # Generate filenames
    image_filename = f"{search_term}.jpg"
    audio_filename = f"{mandarin_word}.mp3"
    
    # Download image
    image_success = download_image_from_pexels(search_term, image_filename)
    
    # Generate audio
    audio_success = generate_audio_with_speechgen(mandarin_word, audio_filename)
    
    # If both media failed, skip this word
    if not image_success and not audio_success:
        logger.warning(f"Skipping '{english_word}' - both image and audio failed")
        return False
    
    # Use shared Pexels link (created once in main)
    global shared_pexels_link_id
    
    # Create English translation
    english_translation_id = create_translation(english_word)
    
    # Prepare vocab entry data
    notes = []
    images_list = []
    sounds_list = []
    links = [shared_pexels_link_id]
    
    # Add image if successful
    if image_success:
        images_list.append({
            "filename": image_filename,
            "alt": f"Image of {search_term}"
        })
    
    # Add audio if successful  
    if audio_success:
        sounds_list.append({
            "filename": audio_filename
        })
    
    # Create vocab entry
    vocab_id = create_vocab(
        language=TARGET_LANGUAGE,
        content=mandarin_word,
        considered_word=True,  # These are individual words/phrases
        notes=notes if notes else None,
        translations=[english_translation_id],
        links=links,
        images=images_list if images_list else None,
        sounds=sounds_list if sounds_list else None,
        is_picturable=image_success
    )
    
    logger.info(f"Successfully processed '{english_word}' -> '{mandarin_word}'")
    return True

def save_jsonl_files():
    """Save all collected data to JSONL files"""
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save vocab.jsonl
    if vocab_data:
        with open(output_dir / "vocab.jsonl", "w", encoding="utf-8") as f:
            for entry in vocab_data:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    # Save translations.jsonl
    if translation_data:
        with open(output_dir / "translations.jsonl", "w", encoding="utf-8") as f:
            for entry in translation_data:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    # Save notes.jsonl
    if note_data:
        with open(output_dir / "notes.jsonl", "w", encoding="utf-8") as f:
            for entry in note_data:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    # Save links.jsonl
    if link_data:
        with open(output_dir / "links.jsonl", "w", encoding="utf-8") as f:
            for entry in link_data:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    logger.info(f"Saved {len(vocab_data)} vocab entries")
    logger.info(f"Saved {len(translation_data)} translation entries") 
    logger.info(f"Saved {len(note_data)} note entries")
    logger.info(f"Saved {len(link_data)} link entries")
    logger.info(f"Files saved to: {output_dir}")

def main():
    """Main function to process all words and generate files"""
    try:
        logger.info("Starting Mandarin vocabulary generation with images and sound")
        
        # Setup API clients
        setup_apis()
        
        # Create shared Pexels link ONCE
        global shared_pexels_link_id
        shared_pexels_link_id = create_link(
            "Pexels",
            "https://pexels.com",
            None,
            None,
            "Pexels License"
        )
        logger.info("Created shared Pexels attribution link")
        
        # Process words
        words_to_process = WORDS[:2] if DEBUG else WORDS
        successful_words = 0
        
        for i, word in enumerate(words_to_process):
            logger.info(f"Processing word {i+1}/{len(words_to_process)}: {word}")
            
            if process_word(word):
                successful_words += 1
            
            # Sleep between requests to be respectful to APIs
            if i < len(words_to_process) - 1:
                time.sleep(SLEEP_BETWEEN_REQUESTS)
        
        # Save all data to files
        save_jsonl_files()
        
        logger.info(f"Completed! Successfully processed {successful_words}/{len(words_to_process)} words")
        if DEBUG:
            logger.info("DEBUG mode was enabled - only processed first 2 words")
            
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise

if __name__ == "__main__":
    main()