"""
- the goal of this script is to generate a set, similar to what is generated in @public/010_hsk1_vocab.py or @public/009_mulan_vocab.py
- first, get the 5000 most common Chinese words by using the python library wordfreq
- split all into characters, make one big list with used characters (do NOT deduplicate)
- then, loop this list
- for each, check the character against @public/data_in/cmn_characters.jsonl
- we are interested in the composition of the characters, so check if that line exists and has a valid decomposition prop
- add the components from the decomposition prop (ignore "？" and IDS position identifiers such as "⿱") to a data structure that for each component tracks:
  - component "look" (the symbol itself)
  - array with all the characters it is part of
  - array with all the words from the frequency list it is part of
- then, take the 250 most "important" components (as measured by nr of words they are part of)
- loop them and match them against @/home/b/GITHUB/linguanodon/public/data_in/Unihan_Readings.txt
  - tab separated file, sorted by unicode (not rendered character)
  - simply ignore components not in Unihan readings
  - make each component a Vocab object
  - use rows of type "kMandarin" as an attached note to the vocab, of noteType pinyin
  - use rows of type "kDefinition" for translations.
     - split string by both semicolon and comma (dataset is inconsistent) and make each a translation
     - do not split text with parenthesis, if that exist, extract that to a note attached to the translation
     - e.g.: `U+6C3D	kDefinition	to float; to deep fry; (Cant.) to turn inside-out` yields 3 translations, the last one with a note "Cant."
- make this license once and attach to all vocab


https://hexdocs.pm/unicode_unihan/license.html

Copyright 2023 Kip Cole (@kipcole9) & Jon Chui (@jkwchui)

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

The Unihan Database data files in this repository are governed by the terms of the Unicode, Inc. License Agreement.
"""

import json
import re
from pathlib import Path
from wordfreq import top_n_list
from collections import defaultdict

# Paths
DATA_IN = Path(__file__).parent / "data_in"
CMN_CHARACTERS = DATA_IN / "cmn_characters.jsonl"
UNIHAN_READINGS = DATA_IN / "Unihan_Readings.txt"
OUTPUT_DIR = Path(__file__).parent / "sets" / "cmn" / "character-components"

# IDS (Ideographic Description Sequence) characters to ignore
IDS_CHARS = set([
    "⿰", "⿱", "⿲", "⿳", "⿴", "⿵", "⿶", "⿷", "⿸", "⿹", "⿺", "⿻", "？"
])

# License link
LICENSE_LINK = {
    "label": "Unihan Database License",
    "url": "https://hexdocs.pm/unicode_unihan/license.html",
    "owner": "Unicode, Inc.",
    "ownerLink": "https://unicode.org/",
    "license": "Unicode, Inc. License Agreement"
}

def load_character_decompositions():
    """Load character decomposition data from cmn_characters.jsonl"""
    decompositions = {}
    with open(CMN_CHARACTERS, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line.strip())
            if 'decomposition' in data and data['decomposition']:
                decompositions[data['character']] = data['decomposition']
    return decompositions

def extract_components(decomposition):
    """Extract components from decomposition string, ignoring IDS chars and ？"""
    components = []
    for char in decomposition:
        if char not in IDS_CHARS:
            components.append(char)
    return components

def get_top_words(n=5000):
    """Get top N most common Chinese words"""
    return top_n_list('zh', n)

def build_component_data(words, decompositions):
    """Build component tracking data structure"""
    component_data = defaultdict(lambda: {
        'component': '',
        'characters': set(),
        'words': set()
    })

    # Split words into characters (not deduplicated)
    all_characters = []
    for word in words:
        chars = list(word)
        all_characters.extend(chars)

        # Track which words each character appears in
        for char in chars:
            if char in decompositions:
                components = extract_components(decompositions[char])
                for comp in components:
                    component_data[comp]['component'] = comp
                    component_data[comp]['characters'].add(char)
                    component_data[comp]['words'].add(word)

    return component_data

def load_unihan_readings():
    """Load Unihan readings data"""
    unihan_data = defaultdict(dict)

    with open(UNIHAN_READINGS, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split('\t')
            if len(parts) < 3:
                continue

            unicode_point = parts[0]
            reading_type = parts[1]
            value = parts[2]

            # Extract character from unicode point (e.g., U+4E00 -> 一)
            char_code = unicode_point.replace('U+', '')
            char = chr(int(char_code, 16))

            unihan_data[char][reading_type] = value

    return unihan_data

def parse_definition(definition):
    """Parse definition string into translations with notes"""
    translations = []

    # Split by semicolon first, then by comma
    parts = re.split(r'[;,]', definition)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Check for parenthetical notes at the beginning of the part
        # Match pattern like "(Cant.) something" or "(archaic) something"
        note_match = re.match(r'^\(([^)]+)\)\s*(.+)$', part)
        if note_match:
            note = note_match.group(1)
            translation = note_match.group(2).strip()
            translations.append({
                'content': translation,
                'note': note
            })
        else:
            # No leading parenthetical, use the whole part as translation
            translations.append({
                'content': part,
                'note': None
            })

    return translations

def generate_vocab_objects(top_components, unihan_data):
    """Generate vocab objects for components"""
    vocab_list = []
    translation_list = []
    note_list = []
    link_list = [LICENSE_LINK]

    link_id = "link_unihan_license"

    for comp_data in top_components:
        component = comp_data['component']

        # Skip if not in Unihan
        if component not in unihan_data:
            continue

        vocab_id = f"comp_{ord(component):04X}"
        vocab_obj = {
            'id': vocab_id,
            'language': 'cmn',
            'content': component,
            'consideredCharacter': True,
            'notes': [],
            'translations': [],
            'links': [link_id],
            'contains': []
        }

        # Add pinyin as note
        if 'kMandarin' in unihan_data[component]:
            pinyin = unihan_data[component]['kMandarin']
            note_id = f"note_{vocab_id}_pinyin"
            note_obj = {
                'id': note_id,
                'content': pinyin,
                'noteType': 'pinyin'
            }
            note_list.append(note_obj)
            vocab_obj['notes'].append(note_id)

        # Add translations
        if 'kDefinition' in unihan_data[component]:
            definition = unihan_data[component]['kDefinition']
            parsed_translations = parse_definition(definition)

            trans_idx = 0
            for idx, trans in enumerate(parsed_translations):
                content = trans['content']

                # Check if this is a "radical" entry (case-insensitive)
                # Matches: "radical 123", "radical number 123", "radical no. 123", "KangXi radical 123", etc.
                is_radical = re.search(r'radical\s+(?:number|no\.?)?\s*\d+', content, re.IGNORECASE)

                if is_radical:
                    # Debug: print when we catch a radical
                    print(f"  Found radical entry: '{content}' for component {component}")
                    # Add as note to vocab instead of translation
                    radical_note_id = f"note_{vocab_id}_radical_{idx}"
                    radical_note_obj = {
                        'id': radical_note_id,
                        'content': content,
                        'noteType': 'radical'
                    }
                    note_list.append(radical_note_obj)
                    vocab_obj['notes'].append(radical_note_id)
                    continue

                trans_id = f"trans_{vocab_id}_{trans_idx}"
                trans_idx += 1
                trans_obj = {
                    'id': trans_id,
                    'content': content,
                    'notes': []
                }

                # Add note if present
                if trans['note']:
                    trans_note_id = f"note_{trans_id}"
                    trans_note_obj = {
                        'id': trans_note_id,
                        'content': trans['note'],
                        'noteType': 'context'
                    }
                    note_list.append(trans_note_obj)
                    trans_obj['notes'].append(trans_note_id)

                translation_list.append(trans_obj)
                vocab_obj['translations'].append(trans_id)

        vocab_list.append(vocab_obj)

    return vocab_list, translation_list, note_list, link_list

def write_jsonl(data, filepath):
    """Write data to JSONL file"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

def write_metadata(output_dir, title):
    """Write metadata.json"""
    metadata = {
        'title': title
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / 'metadata.json', 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

def write_set(vocab_list, translation_list, note_list, link_list, output_dir, title):
    """Write a complete set to output directory"""
    print(f"  Writing {len(vocab_list)} vocab items to {output_dir.name}...")
    write_jsonl(vocab_list, output_dir / 'vocab.jsonl')
    write_jsonl(translation_list, output_dir / 'translations.jsonl')
    write_jsonl(note_list, output_dir / 'notes.jsonl')
    write_jsonl(link_list, output_dir / 'links.jsonl')
    write_metadata(output_dir, title)
    print(f"  Done!")

def main():
    print("Loading character decompositions...")
    decompositions = load_character_decompositions()

    print("Getting top 5000 words...")
    words = get_top_words(5000)

    print("Building component data...")
    component_data = build_component_data(words, decompositions)

    print(f"Found {len(component_data)} unique components")

    # Sort by number of words they appear in
    sorted_components = sorted(
        component_data.values(),
        key=lambda x: len(x['words']),
        reverse=True
    )

    print("Loading Unihan readings...")
    unihan_data = load_unihan_readings()

    # Generate full set (250 components)
    print("\n=== Generating full set (250 components) ===")
    top_250 = sorted_components[:250]
    vocab_list_250, translation_list_250, note_list_250, link_list_250 = generate_vocab_objects(
        top_250, unihan_data
    )
    print(f"Generated {len(vocab_list_250)} vocab items, {len(translation_list_250)} translations, {len(note_list_250)} notes")

    full_output_dir = Path(__file__).parent / "sets" / "cmn" / "character-components"
    write_set(vocab_list_250, translation_list_250, note_list_250, link_list_250,
              full_output_dir, "Mandarin Character Components")

    # Generate mini set (20 components)
    print("\n=== Generating mini set (20 components) ===")
    top_20 = sorted_components[:20]
    vocab_list_20, translation_list_20, note_list_20, link_list_20 = generate_vocab_objects(
        top_20, unihan_data
    )
    print(f"Generated {len(vocab_list_20)} vocab items, {len(translation_list_20)} translations, {len(note_list_20)} notes")

    mini_output_dir = Path(__file__).parent / "sets" / "cmn" / "character-components-mini"
    write_set(vocab_list_20, translation_list_20, note_list_20, link_list_20,
              mini_output_dir, "Mandarin Character Components (Mini)")

    print(f"\n✓ All done!")

if __name__ == '__main__':
    main()
