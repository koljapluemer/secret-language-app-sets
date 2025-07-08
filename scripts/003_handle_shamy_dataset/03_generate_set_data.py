import pandas as pd
import json
import re
import os
from collections import Counter, defaultdict

# Create data directory if it doesn't exist
os.makedirs('data', exist_ok=True)

# Load the filtered CSV
df = pd.read_csv('levanti_filtered_3cols.csv')

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

# Find words that appear in 25-50 different sentences
target_words = [word for word, sentence_indices in word_sentence_count.items() 
                if 25 <= len(sentence_indices) <= 50]

print(f"Found {len(target_words)} words that appear in 25-50 different sentences")

# Process each target word
for word in target_words:
    print(f"Processing word: {word} (appears in {len(word_sentence_count[word])} sentences)")
    
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
                    "license": "CC-BY-NC-4.0",
                    "owner": "Guy Mor-Lan",
                    "ownerLink": "https://huggingface.co/guymorlan",
                    "source": "Levanti Dataset",
                    "sourceLink": "https://huggingface.co/datasets/guymorlan/levanti",
                    "translations": [english_uid]
                },
                "english": {
                    "uid": english_uid,
                    "language": "en",
                    "content": english_text,
                    "linguType": "sentence",
                    "license": "CC-BY-NC-4.0",
                    "owner": "Guy Mor-Lan",
                    "ownerLink": "https://huggingface.co/guymorlan",
                    "source": "Levanti Dataset",
                    "sourceLink": "https://huggingface.co/datasets/guymorlan/levanti",
                    "translations": [arabic_uid]
                }
            }
            matching_sentences.append(sentence_pair)
    
    # Create the JSON structure
    json_data = {
        "language": "ar",
        "tasks": [
            f"Make a sentence with '{word}'."
        ],
        "unitsOfMeaning": []
    }
    
    # Add all sentence pairs to unitsOfMeaning
    for pair in matching_sentences:
        json_data["unitsOfMeaning"].append(pair["arabic"])
        json_data["unitsOfMeaning"].append(pair["english"])
    
    # Save to JSON file
    filename = f"data/{word}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    print(f"  Created {filename} with {len(matching_sentences)} sentence pairs")

print("Done! All JSON files created in the data/ directory.")
