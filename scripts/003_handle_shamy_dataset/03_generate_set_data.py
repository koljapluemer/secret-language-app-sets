import pandas as pd
import json
import re
import os
from collections import Counter, defaultdict

# Create data directory if it doesn't exist
os.makedirs('data', exist_ok=True)

# Adjustable constants
MAX_WORDS_PER_SENTENCE = 7  # Maximum allowed words in Arabic sentence
MIN_SENTENCE_OCCURRENCES = 25  # Minimum number of different sentences a word must appear in
MAX_SENTENCE_OCCURRENCES = 50  # Maximum number of different sentences a word can appear in
FILE_CREATION_LIMIT = 2  # Set to an integer to limit number of files created, or None for no limit
OVERWRITE_EXISTING_FILES = True  # Set to False to skip existing files instead of overwriting
TASKS_PER_FILE = 5  # Number of word-based tasks to include in each file
CONSIDER_SENTENCE_PRIMARY_WHEN_HAS_LESS_THAN_N_WORDS = 4  # Sentences with fewer words go to primaryUnitsOfMeaning

# Load the filtered CSV
df = pd.read_csv('scripts/003_handle_shamy_dataset/levanti_filtered_3cols.csv')

# Filter out sentences with more than MAX_WORDS_PER_SENTENCE words in Arabic
filtered_indices = []
for idx, row in df.iterrows():
    if pd.notna(row['arabic']):
        arabic_text = str(row['arabic'])
        if len(arabic_text.split()) <= MAX_WORDS_PER_SENTENCE:
            filtered_indices.append(idx)
df = df.loc[filtered_indices].reset_index(drop=True)

# Count how many different sentences each word appears in
word_sentence_count = defaultdict(set)  # word -> set of sentence indices

for idx, row in df.iterrows():
    if pd.notna(row['arabic']):
        arabic_text = str(row['arabic'])
        raw_words = arabic_text.split()
        for word in raw_words:
            cleaned_word = re.sub(r'[^\w\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', '', word.strip())
            if cleaned_word and len(cleaned_word) > 3:
                word_sentence_count[cleaned_word].add(idx)

# Find words that appear in MIN_SENTENCE_OCCURRENCES to MAX_SENTENCE_OCCURRENCES different sentences
target_words = [word for word, sentence_indices in word_sentence_count.items() 
                if MIN_SENTENCE_OCCURRENCES <= len(sentence_indices) <= MAX_SENTENCE_OCCURRENCES]

print(f"Found {len(target_words)} words that appear in {MIN_SENTENCE_OCCURRENCES}-{MAX_SENTENCE_OCCURRENCES} different sentences")

# Process each target word
files_created = 0
current_file_tasks = []
current_file_index = 1

for word in target_words:
    if FILE_CREATION_LIMIT is not None and files_created >= FILE_CREATION_LIMIT:
        break
    
    # Check if word actually meets the criteria (double-check)
    if not (MIN_SENTENCE_OCCURRENCES <= len(word_sentence_count[word]) <= MAX_SENTENCE_OCCURRENCES):
        continue
    
    # Filter only relevant rows once for this word
    relevant_rows = df[df['arabic'].apply(lambda x: word in str(x).split())]
    matching_sentences = []
    for _, row in relevant_rows.iterrows():
        arabic_text = str(row['arabic'])
        english_text = str(row['english'])
        dialect = str(row['dialect'])
        # Create the sentence pair
        sentence_pair = {
            "arabic": {
                "language": "apc",
                "content": arabic_text,
                "notes": "",
                "credits": [{
                    "license": "CC-BY-NC-4.0",
                    "owner": "Guy Mor-Lan",
                    "ownerLink": "https://huggingface.co/guymorlan",
                    "source": "Levanti Dataset",
                    "sourceLink": "https://huggingface.co/datasets/guymorlan/levanti"
                }],
                "translations": [{"language": "en", "content": english_text}],
                "card": {"type": "sentence"}
            },
            "english": {
                "language": "en",
                "content": english_text,
                "notes": "",
                "credits": [{
                    "license": "CC-BY-NC-4.0",
                    "owner": "Guy Mor-Lan",
                    "ownerLink": "https://huggingface.co/guymorlan",
                    "source": "Levanti Dataset",
                    "sourceLink": "https://huggingface.co/datasets/guymorlan/levanti"
                }],
                "translations": [{"language": "apc", "content": arabic_text}],
                "card": {"type": "sentence"}
            }
        }
        matching_sentences.append(sentence_pair)
    
    # Create task for this word
    task = {
        "content": f"Use '{word}' in a sentence",
        "language": "apc",
        "unitsOfMeaning": [],
        "primaryUnitsOfMeaning": []
    }
    
    # Add all sentence pairs to unitsOfMeaning or primaryUnitsOfMeaning based on word count
    arabic_words = []
    english_words = []
    
    for pair in matching_sentences:
        arabic_word_count = len(pair["arabic"]["content"].split())
        if arabic_word_count < CONSIDER_SENTENCE_PRIMARY_WHEN_HAS_LESS_THAN_N_WORDS:
            task["primaryUnitsOfMeaning"].append(pair["arabic"])
            task["primaryUnitsOfMeaning"].append(pair["english"])
        else:
            task["unitsOfMeaning"].append(pair["arabic"])
            task["unitsOfMeaning"].append(pair["english"])
        
        # Extract words for frequency analysis
        arabic_text = pair["arabic"]["content"]
        english_text = pair["english"]["content"]
        
        # Extract Arabic words
        arabic_raw_words = arabic_text.split()
        for ar_word in arabic_raw_words:
            cleaned_word = re.sub(r'[^\w\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', '', ar_word.strip())
            if cleaned_word and len(cleaned_word) > 1:
                arabic_words.append(cleaned_word)
        
        # Extract English words
        english_raw_words = english_text.split()
        for en_word in english_raw_words:
            cleaned_word = re.sub(r'[^\w]', '', en_word.strip().lower())
            if cleaned_word and len(cleaned_word) > 1:
                english_words.append(cleaned_word)
    
    # Create word-to-sentence mappings for seeAlso
    word_to_sentences = defaultdict(set)
    sentence_to_words = defaultdict(set)
    
    # Process each sentence pair to build mappings
    for pair in matching_sentences:
        arabic_text = pair["arabic"]["content"]
        english_text = pair["english"]["content"]
        
        # Extract Arabic words from this sentence
        arabic_raw_words = arabic_text.split()
        sentence_ar_words = set()
        for ar_word in arabic_raw_words:
            cleaned_word = re.sub(r'[^\w\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', '', ar_word.strip())
            if cleaned_word and len(cleaned_word) > 1:
                sentence_ar_words.add(cleaned_word)
                word_to_sentences[("apc", cleaned_word)].add((arabic_text, "apc"))
        
        # Extract English words from this sentence
        english_raw_words = english_text.split()
        sentence_en_words = set()
        for en_word in english_raw_words:
            cleaned_word = re.sub(r'[^\w]', '', en_word.strip().lower())
            if cleaned_word and len(cleaned_word) > 1:
                sentence_en_words.add(cleaned_word)
                word_to_sentences[("en", cleaned_word)].add((english_text, "en"))
        
        # Add word references to sentence
        sentence_to_words[(arabic_text, "apc")] = sentence_ar_words
        sentence_to_words[(english_text, "en")] = sentence_en_words
    
    # Add seeAlso to sentences
    for pair in matching_sentences:
        arabic_text = pair["arabic"]["content"]
        english_text = pair["english"]["content"]
        
        # Add seeAlso to Arabic sentence
        ar_words = sentence_to_words.get((arabic_text, "apc"), set())
        pair["arabic"]["seeAlso"] = [{"language": "apc", "content": word} for word in sorted(ar_words)]
        
        # Add seeAlso to English sentence
        en_words = sentence_to_words.get((english_text, "en"), set())
        pair["english"]["seeAlso"] = [{"language": "en", "content": word} for word in sorted(en_words)]
    
    # Add all unique words as unitsOfMeaning (no linguType, credits, or translations), deduplicated by language+content
    for unique_ar_word in sorted(set(arabic_words)):
        word_unit = {
            "language": "apc",
            "content": unique_ar_word,
            "card": {"type": "word"}
        }
        # Add seeAlso to word unit
        word_sentences = word_to_sentences.get(("apc", unique_ar_word), set())
        word_unit["seeAlso"] = [{"language": lang, "content": content} for content, lang in sorted(word_sentences)]
        task["unitsOfMeaning"].append(word_unit)
        
    for unique_en_word in sorted(set(english_words)):
        word_unit = {
            "language": "en",
            "content": unique_en_word,
            "card": {"type": "word"}
        }
        # Add seeAlso to word unit
        word_sentences = word_to_sentences.get(("en", unique_en_word), set())
        word_unit["seeAlso"] = [{"language": lang, "content": content} for content, lang in sorted(word_sentences)]
        task["unitsOfMeaning"].append(word_unit)
    
    # Add the main word for the task (the same one used in the task content) to the very top of primaryUnitsOfMeaning
    # Create the main word unit with seeAlso
    main_word_unit = {
        "language": "apc",
        "content": word,
        "card": {"type": "word"}
    }
    # Add seeAlso to main word unit - it should reference all sentences where it occurs
    main_word_sentences = word_to_sentences.get(("apc", word), set())
    main_word_unit["seeAlso"] = [{"language": lang, "content": content} for content, lang in sorted(main_word_sentences)]
    task["primaryUnitsOfMeaning"] = [main_word_unit] + task["primaryUnitsOfMeaning"]
    
    # Deduplicate arrays at the end by converting to sets and back to lists
    # Convert to tuples for hashing, then back to dicts
    def deduplicate_units(units):
        seen = set()
        unique_units = []
        for unit in units:
            key = (unit["language"], unit["content"])
            if key not in seen:
                seen.add(key)
                unique_units.append(unit)
        return unique_units
    
    task["unitsOfMeaning"] = deduplicate_units(task["unitsOfMeaning"])
    task["primaryUnitsOfMeaning"] = deduplicate_units(task["primaryUnitsOfMeaning"])
    
    current_file_tasks.append(task)
    
    # If we've reached TASKS_PER_FILE or this is the last word, save the file
    if len(current_file_tasks) >= TASKS_PER_FILE or word == target_words[-1]:
        filename = f"data/natural_sentences_{current_file_index}.json"
        
        if not OVERWRITE_EXISTING_FILES and os.path.exists(filename):
            print(f"  Skipping {filename} (already exists)")
            current_file_tasks = []
            current_file_index += 1
            continue
        
        # Create the JSON structure
        json_data = {
            "name": f"Natural Sentences #{current_file_index}",
            "language": "apc",
            "tasks": current_file_tasks
        }
        
        # Save to JSON file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        print(f"  Created {filename} with {len(current_file_tasks)} tasks")
        files_created += 1
        
        # Reset for next file
        current_file_tasks = []
        current_file_index += 1

print("Done! All JSON files created in the data/ directory.")
