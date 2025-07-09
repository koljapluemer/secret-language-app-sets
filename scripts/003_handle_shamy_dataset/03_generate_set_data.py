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
TASKS_PER_FILE = 2  # Number of word-based tasks to include in each file

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
    
    # Find all sentences containing this word (exact match)
    matching_sentences = []
    seen_uids = set()  # For deduplication
    
    for _, row in df.iterrows():
        arabic_text = str(row['arabic'])
        english_text = str(row['english'])
        dialect = str(row['dialect'])
        
        # Check if the word appears in the Arabic text (exact match)
        if word in arabic_text.split():
            # Create UIDs
            arabic_uid = f"apc_{arabic_text}_sentence"
            english_uid = f"en_{english_text}_sentence"
            
            # Skip if we've already seen this sentence
            if arabic_uid in seen_uids:
                continue
            seen_uids.add(arabic_uid)
            
            # Create the sentence pair
            sentence_pair = {
                "arabic": {
                    "uid": arabic_uid,
                    "language": "apc",
                    "content": arabic_text,
                    "linguType": "sentence",
                    "credits": [{
                        "license": "CC-BY-NC-4.0",
                        "owner": "Guy Mor-Lan",
                        "ownerLink": "https://huggingface.co/guymorlan",
                        "source": "Levanti Dataset",
                        "sourceLink": "https://huggingface.co/datasets/guymorlan/levanti"
                    }],
                    "translations": [english_uid]
                },
                "english": {
                    "uid": english_uid,
                    "language": "en",
                    "content": english_text,
                    "linguType": "sentence",
                    "credits": [{
                        "license": "CC-BY-NC-4.0",
                        "owner": "Guy Mor-Lan",
                        "ownerLink": "https://huggingface.co/guymorlan",
                        "source": "Levanti Dataset",
                        "sourceLink": "https://huggingface.co/datasets/guymorlan/levanti"
                    }],
                    "translations": [arabic_uid]
                }
            }
            matching_sentences.append(sentence_pair)
    
    # Create task for this word
    task = {
        "content": f"Use '{word}' in a sentence",
        "language": "apc",
        "unitsOfMeaning": []
    }
    
    # Add all sentence pairs to unitsOfMeaning
    for pair in matching_sentences:
        task["unitsOfMeaning"].append(pair["arabic"])
        task["unitsOfMeaning"].append(pair["english"])
    
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
