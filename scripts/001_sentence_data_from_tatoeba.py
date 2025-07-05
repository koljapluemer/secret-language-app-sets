#!/usr/bin/env python3
"""
Script to fetch English sentences with South Levantine Arabic (ajp) translations
from the Tatoeba API and generate a JSON file in the specified format.
"""

import requests
import json
import time
import logging
import urllib.parse
import re
from typing import Dict, List, Any

# Constants
SOURCE_LANGUAGE = 'eng'  # English
TARGET_LANGUAGE = 'ajp'  # South Levantine Arabic

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api_responses.log', encoding='utf-8'),
        logging.StreamHandler()  # Also log to console
    ]
)
logger = logging.getLogger(__name__)

def fetch_sentences_with_ajp_translations() -> List[Dict[str, Any]]:
    """
    Fetch {SOURCE_LANGUAGE} sentences that have {TARGET_LANGUAGE} translations.
    
    Returns:
        List of sentence pairs with {SOURCE_LANGUAGE} and {TARGET_LANGUAGE} translations
    """
    base_url = "https://api.tatoeba.org/unstable/sentences"
    all_sentences = []
    page_count = 0
    current_url = base_url
    params = {
        'lang': SOURCE_LANGUAGE,
        'trans:lang': TARGET_LANGUAGE,
        'sort': 'words',
        'limit': 20
    }
    after_value = None
    logger.info("=== Starting Tatoeba API requests ===")
    while True:
        page_count += 1
        logger.info(f"Fetching page {page_count}...")
        if page_count == 1:
            logger.debug(f"Request URL: {current_url}")
            logger.debug(f"Request params: {params}")
            response = requests.get(current_url, params=params)
        else:
            # Manually construct the URL to avoid encoding 'trans:lang'
            query = f"lang={SOURCE_LANGUAGE}&trans:lang={TARGET_LANGUAGE}&sort=words&limit=20&after={after_value}"
            full_url = f"{base_url}?{query}"
            logger.debug(f"Request URL: {full_url}")
            logger.debug(f"Request params: None (manual URL)")
            response = requests.get(full_url)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Response data: {json.dumps(data, indent=2, ensure_ascii=False)}")
        sentences = data.get('data', [])
        logger.info(f"Page {page_count}: fetched {len(sentences)} sentences")
        all_sentences.extend(sentences)
        paging = data.get('paging', {})
        next_url = paging.get('next')
        logger.info(f"Next URL: {next_url}")
        if not next_url or len(sentences) == 0:
            logger.info(f"No more pages available. Total sentences fetched: {len(all_sentences)}")
            break
        # Extract 'after' value from next_url
        match = re.search(r'after=([^&]+)', next_url)
        if match:
            after_value = urllib.parse.unquote(match.group(1))
            logger.info(f"Next page will use after={after_value}")
        else:
            logger.error("Could not extract 'after' value from next_url. Stopping pagination.")
            break
        logger.info("Sleeping 1 second before next page...")
        time.sleep(1)
        current_url = base_url
    logger.info(f"Successfully fetched {len(all_sentences)} sentence pairs total")
    return all_sentences

def clean_dict(d: dict) -> dict:
    """Return a copy of the dict with all None or empty values removed."""
    return {k: v for k, v in d.items() if v is not None and v != ''}

def create_units_of_meaning(sentences: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Create units of meaning from sentence pairs.
    
    Args:
        sentences: List of sentence pairs from Tatoeba API
        
    Returns:
        Dictionary of units of meaning
    """
    units = {}
    
    for i, sentence_pair in enumerate(sentences):
        # Generate unique IDs for each unit
        eng_id = f"eng_{i+1}"
        ajp_id = f"ajp_{i+1}"
        
        # {SOURCE_LANGUAGE} sentence metadata
        eng_license = sentence_pair.get('license')
        eng_owner = sentence_pair.get('owner')
        eng_owner_link = f"https://tatoeba.org/en/user/profile/{eng_owner}" if eng_owner else None
        eng_sentence_id = sentence_pair.get('id')
        eng_sentence_link = f"https://tatoeba.org/en/sentences/show/{eng_sentence_id}" if eng_sentence_id else None
        
        eng_unit = {
            "language": SOURCE_LANGUAGE.replace("eng", "en"),
            "content": sentence_pair.get('text', ''),
            "linguType": "sentence",
            "translations": [ajp_id],
            "context": "Tatoeba API",
            "license": eng_license,
            "owner": eng_owner,
            "ownerLink": eng_owner_link,
            "source": "Tatoeba",
            "sourceLink": "https://tatoeba.org/",
            "sentenceLink": eng_sentence_link
        }
        units[eng_id] = clean_dict(eng_unit)
        
        # Find the {TARGET_LANGUAGE} translation and its metadata
        ajp_translation = ""
        ajp_license = None
        ajp_owner = None
        ajp_owner_link = None
        ajp_sentence_id = None
        ajp_sentence_link = None
        translations = sentence_pair.get('translations', [])
        
        for translation_group in translations:
            for translation in translation_group:
                if translation.get('lang') == TARGET_LANGUAGE:
                    ajp_translation = translation.get('text', '')
                    ajp_license = translation.get('license')
                    ajp_owner = translation.get('owner')
                    ajp_owner_link = f"https://tatoeba.org/en/user/profile/{ajp_owner}" if ajp_owner else None
                    ajp_sentence_id = translation.get('id')
                    ajp_sentence_link = f"https://tatoeba.org/en/sentences/show/{ajp_sentence_id}" if ajp_sentence_id else None
                    break
            if ajp_translation:
                break
        
        ajp_unit = {
            "language": TARGET_LANGUAGE,
            "content": ajp_translation,
            "linguType": "sentence",
            "context": "Tatoeba API",
            "license": ajp_license,
            "owner": ajp_owner,
            "ownerLink": ajp_owner_link,
            "source": "Tatoeba",
            "sourceLink": "https://tatoeba.org/",
            "sentenceLink": ajp_sentence_link
        }
        units[ajp_id] = clean_dict(ajp_unit)
    
    return units

def create_learning_goals(sentences: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Create learning goals for each sentence pair.
    
    Args:
        sentences: List of sentence pairs from Tatoeba API
        
    Returns:
        Dictionary of learning goals
    """
    goals = {}
    
    # Meta goal that all other goals are parented to
    goals["meta"] = {
        "name": "Learn Basic South Levantine Sentences From Tatoeba",
        "language": "ajp",
        "unitsOfMeaning": []
    }
    
    for i, sentence_pair in enumerate(sentences):
        goal_id = f"goal_{i+1}"
        eng_id = f"eng_{i+1}"
        ajp_id = f"ajp_{i+1}"
        
        # Get the Arabic translation for the goal name
        ajp_translation = ""
        translations = sentence_pair.get('translations', [])
        
        for translation_group in translations:
            for translation in translation_group:
                if translation.get('lang') == TARGET_LANGUAGE:
                    ajp_translation = translation.get('text', '')
                    break
            if ajp_translation:
                break
        
        # Create a goal with the actual sentence content
        if ajp_translation:
            goal_name = f"Learn '{ajp_translation}'"
        else:
            goal_name = f"Learn sentence {i+1}"
        
        goals[goal_id] = {
            "name": goal_name,
            "language": "ajp",
            "unitsOfMeaning": [eng_id, ajp_id],
            "parents": ["meta"]
        }
        
        # Add units to meta goal
        goals["meta"]["unitsOfMeaning"].extend([eng_id, ajp_id])
    
    return goals

def generate_tatoeba_json(sentences: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate the complete JSON structure in the required format.
    
    Args:
        sentences: List of sentence pairs from Tatoeba API
        
    Returns:
        Complete JSON structure
    """
    units = create_units_of_meaning(sentences)
    goals = create_learning_goals(sentences)
    
    return {
        "unitsOfMeaning": units,
        "learningGoals": goals
    }

def main():
    """Main function to fetch data and generate JSON file."""
    
    # Fetch sentences from Tatoeba API
    sentences = fetch_sentences_with_ajp_translations()
    
    if not sentences:
        logger.error("No sentences fetched. Exiting.")
        return
    
    # Generate the JSON structure
    json_data = generate_tatoeba_json(sentences)
    
    # Save to file
    output_filename = "data/001_ajp_sentences_from_tatoeba.json"
    
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)
        
        logger.info(f"Successfully generated {output_filename}")
        logger.info(f"Created {len(json_data['unitsOfMeaning'])} units of meaning")
        logger.info(f"Created {len(json_data['learningGoals'])} learning goals")
        
    except Exception as e:
        logger.error(f"Error saving file: {e}")

if __name__ == "__main__":
    main()
