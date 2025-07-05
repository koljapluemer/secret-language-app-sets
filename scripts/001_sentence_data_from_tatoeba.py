#!/usr/bin/env python3
"""
Script to fetch English sentences with South Levantine Arabic (ajp) translations
from the Tatoeba API and generate a JSON file in the specified format.
"""

import requests
import json
from typing import Dict, List, Any

# Constants
FETCH_LIMIT = 20
SOURCE_LANGUAGE = 'eng'  # English
TARGET_LANGUAGE = 'ajp'  # South Levantine Arabic

def fetch_sentences_with_ajp_translations() -> List[Dict[str, Any]]:
    """
    Fetch {SOURCE_LANGUAGE} sentences that have {TARGET_LANGUAGE} translations.
    
    Args:
        limit: Number of sentence pairs to fetch
        
    Returns:
        List of sentence pairs with {SOURCE_LANGUAGE} and {TARGET_LANGUAGE} translations
    """
    # Tatoeba API endpoint for sentences
    base_url = "https://api.tatoeba.org/unstable/sentences"
    
    # Parameters to get {SOURCE_LANGUAGE} sentences with {TARGET_LANGUAGE} translations
    params = {
        'lang': SOURCE_LANGUAGE,  # {SOURCE_LANGUAGE} sentences
        'trans:lang': TARGET_LANGUAGE,  # {TARGET_LANGUAGE} translations
        'limit': FETCH_LIMIT,
        'sort': 'random'  # Get random sentences
    }
    
    try:
        print(f"Fetching {FETCH_LIMIT} {SOURCE_LANGUAGE} sentences with {TARGET_LANGUAGE} translations...")
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        
        data = response.json()
        print(f"API Response structure: {type(data)}")
        print(f"API Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
        
        sentences = data.get('data', [])
        print(f"Number of sentences fetched: {len(sentences)}")
        
        if sentences:
            print(f"First sentence structure: {type(sentences[0])}")
            print(f"First sentence keys: {list(sentences[0].keys()) if isinstance(sentences[0], dict) else 'Not a dict'}")
            print(f"First sentence content: {sentences[0]}")
        
        print(f"Successfully fetched {len(sentences)} sentence pairs")
        return sentences
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching sentences: {e}")
        return []

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
            "language": SOURCE_LANGUAGE,
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
        
        # Create a goal for each sentence pair
        goals[goal_id] = {
            "name": f"Learn sentence {i+1}",
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
        print("No sentences fetched. Exiting.")
        return
    
    # Generate the JSON structure
    json_data = generate_tatoeba_json(sentences)
    
    # Save to file
    output_filename = "data/001_ajp_sentences_from_tatoeba.json"
    
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)
        
        print(f"Successfully generated {output_filename}")
        print(f"Created {len(json_data['unitsOfMeaning'])} units of meaning")
        print(f"Created {len(json_data['learningGoals'])} learning goals")
        
    except Exception as e:
        print(f"Error saving file: {e}")

if __name__ == "__main__":
    main()
