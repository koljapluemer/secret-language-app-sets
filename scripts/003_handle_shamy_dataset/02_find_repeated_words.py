import pandas as pd
from collections import Counter
import re

# Load the filtered CSV
df = pd.read_csv('levanti_filtered_3cols.csv')

# Extract all words from the arabic column
all_words = []
for text in df['arabic']:
    if pd.notna(text):  # Check for NaN values
        # Split by whitespace and clean each word
        raw_words = str(text).split()
        for word in raw_words:
            # Clean the word: remove punctuation and trim
            cleaned_word = re.sub(r'[^\w\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', '', word.strip())
            # Only include if it's not empty and has more than 3 characters
            if cleaned_word and len(cleaned_word) > 3:
                all_words.append(cleaned_word)

# Count word frequencies
word_counts = Counter(all_words)

# Get the 50 most common words
most_common = word_counts.most_common(50)

print("50 most common words in the Arabic column (excluding words with 3 characters or less):")
print("=" * 80)
for i, (word, count) in enumerate(most_common, 1):
    print(f"{i:2d}. '{word}': {count}")

print(f"\nTotal unique words found: {len(word_counts)}")
print(f"Total word occurrences: {sum(word_counts.values())}")

# Find words with 25-50 occurrences
words_25_to_50 = [(word, count) for word, count in word_counts.items() if 25 <= count <= 50]
words_25_to_50.sort(key=lambda x: x[1], reverse=True)  # Sort by count descending

print(f"\nWords with 25-50 occurrences ({len(words_25_to_50)} words):")
print("=" * 50)
for i, (word, count) in enumerate(words_25_to_50, 1):
    print(f"{i:2d}. '{word}': {count}")
