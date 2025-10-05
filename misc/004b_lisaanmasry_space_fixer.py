"""
Loads public/sets/arz/lisaanmasry-examples/vocab.jsonl.
Gets every line
Uses OpenAI API to fix formatting within the Arabic words saved in content.
Sometimes, there is an extra space after an Arabic diacritic.
More often the diacritics (fatḥas) are visually separated by tatweel-like connectors (ـ) around them instead of being *on*
the given letter, e.g. "عـَمـَل" instead of "عَمَل". That should be fixed.
The goal for the script is to save the same format to the same file, just with the fixed Arabic words.
"""

import json
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_openai_client():
    """Initialize OpenAI client with API key from environment"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    return OpenAI(api_key=api_key)

def fix_arabic_formatting(client, arabic_text):
    """
    Use OpenAI API to fix Arabic text formatting issues:
    - Remove extra spaces after diacritics
    - Remove tatweel characters (ـ) that separate diacritics from letters
    - Properly attach diacritics to their base letters
    """
    prompt = f"""Fix the Arabic text formatting by:
1. Removing any tatweel characters (ـ) that separate diacritics from their base letters
2. Removing extra spaces after Arabic diacritics
3. Ensuring diacritics are properly attached to their letters

Original text: {arabic_text}

Return ONLY the corrected Arabic text, nothing else."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert in Arabic typography and text formatting. Fix the Egyptian Arabic text's formatting issues while preserving the meaning and pronunciation. Do not invent diacritics that weren't there before. Do not remove a prefixed connector if it indicates that the word is used as a suffix."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.1
        )
        
        fixed_text = response.choices[0].message.content.strip()
        return fixed_text
    except Exception as e:
        print(f"Error fixing text '{arabic_text}': {e}")
        return arabic_text  # Return original if fixing fails

def save_entries_to_file(entries, file_path):
    """Save all entries to the file"""
    with open(file_path, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

def process_vocab_file():
    """Process the vocab.jsonl file and fix Arabic formatting in all entries"""
    file_path = Path("sets/arz/lisaanmasry-examples/vocab.jsonl")
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    client = setup_openai_client()
    
    # Read all entries
    entries = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    
    print(f"Processing {len(entries)} vocab entries...")
    
    # Process each entry
    fixed_count = 0
    save_interval = 100
    
    for i, entry in enumerate(entries):
        if 'content' in entry and entry.get('language') in ['arz', 'arb']:  # Only process Arabic entries
            original_content = entry['content']
            
            print(f"Fixing entry {i+1}/{len(entries)}: {original_content}")
            fixed_content = fix_arabic_formatting(client, original_content)
            
            if fixed_content != original_content:
                entry['content'] = fixed_content
                fixed_count += 1
                print(f"  → {fixed_content}")
            else:
                print(f"  → No changes needed")
        
        # Save progress every 100 entries
        if (i + 1) % save_interval == 0:
            print(f"\nSaving progress... (processed {i + 1}/{len(entries)} entries)")
            save_entries_to_file(entries, file_path)
            print(f"Progress saved. Fixed {fixed_count} entries so far.\n")
    
    print(f"\nFixed {fixed_count} entries total")
    
    # Final save
    save_entries_to_file(entries, file_path)
    print(f"Final save completed to {file_path}")

if __name__ == "__main__":
    try:
        process_vocab_file()
        print("Arabic formatting fix completed successfully!")
    except Exception as e:
        print(f"Error: {e}")