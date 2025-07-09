#!/usr/bin/env python3
"""
Script to download YouTube subtitles and extract vocabulary using OpenAI.
Creates unitsOfMeaning structure for language learning data.
"""

import os
import json
import sys
from typing import List, Dict, Any
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
YOUTUBE_VIDEO_ID = "r4psGFKZQqQ"  # Replace with your video ID
OUTPUT_FILE = "data/002_youtube_vocabulary.json"

class WordEntry(BaseModel):
    word: str
    translation: str

class WordEntryResponse(BaseModel):
    words: List[WordEntry]

def get_openai_client() -> OpenAI:
    """Initialize OpenAI client with API key from environment"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    return OpenAI(api_key=api_key)

def download_subtitles(video_id: str) -> str:
    """Download subtitles from YouTube video"""
    try:
        # Get transcript list to find available languages
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Try to get transcript in the video's original language first
        # If that fails, fall back to any available transcript
        try:
            # Get the first available transcript (usually in the video's original language)
            transcript = next(iter(transcript_list))
            print(f"Found transcript in language: {transcript.language} ({transcript.language_code})")
        except StopIteration:
            # If no transcripts available, try to find any transcript
            available_transcripts = list(transcript_list)
            if not available_transcripts:
                raise Exception("No transcripts available for this video")
            transcript = available_transcripts[0]
            print(f"Using available transcript in: {transcript.language} ({transcript.language_code})")
        
        # Fetch the transcript
        fetched_transcript = transcript.fetch()
        
        # Combine all text snippets
        full_text = " ".join([snippet.text for snippet in fetched_transcript])
        
        print(f"Downloaded transcript with {len(fetched_transcript)} snippets")
        print(f"Language: {transcript.language} ({transcript.language_code})")
        
        return full_text, transcript.language_code
        
    except Exception as e:
        print(f"Error downloading subtitles: {e}")
        sys.exit(1)

def extract_vocabulary(text: str, source_language_code: str, client: OpenAI) -> List[WordEntry]:
    """Extract vocabulary from text using OpenAI"""
    
    # Generic prompt that works for any language
    prompt = f"""You are an expert in language learning and vocabulary extraction.

Extract language learning vocabulary from the following text in {source_language_code} language. 

Guidelines:
- Extract meaningful words and phrases that would be useful for language learners
- Ignore proper nouns (names, places, brands), exclamations (oh, wow), and non-translatable words
- For each extracted word/phrase, provide an English translation suitable for learning
- Retain correct capitalization and spelling
- If a word appears in declined, conjugated, or plural form, include both the occurring form and base form as separate entries
- Focus on common, everyday vocabulary that learners would encounter

Return your answer as a structured list of vocabulary entries with word and translation.

Text to analyze:
{text}

Output JSON:"""

    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant specialized in language learning and vocabulary extraction."},
                {"role": "user", "content": prompt}
            ],
            response_format=WordEntryResponse,
        )
        return response.choices[0].message.parsed.words
    except Exception as e:
        print(f"Error extracting vocabulary: {e}")
        sys.exit(1)

def create_units_of_meaning(vocabulary: List[WordEntry], source_language_code: str) -> Dict[str, Any]:
    """Create unitsOfMeaning structure from vocabulary"""
    
    units = {}
    counter = 0
    
    for entry in vocabulary:
        # Create unit for the source language word
        source_id = chr(ord('a') + counter)
        units[source_id] = {
            "language": source_language_code,
            "content": entry.word,
            "linguType": "word",  # Could be enhanced to detect word type
            "translations": [chr(ord('a') + counter + 1)]
        }
        
        # Create unit for the English translation
        translation_id = chr(ord('a') + counter + 1)
        units[translation_id] = {
            "language": "en",
            "content": entry.translation,
            "linguType": "word",
            "related": [source_id]
        }
        
        counter += 2
    
    return {"unitsOfMeaning": units}

def save_to_file(data: Dict[str, Any], filename: str):
    """Save data to JSON file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Vocabulary data saved to {filename}")
    except Exception as e:
        print(f"Error saving file: {e}")
        sys.exit(1)

def main():
    """Main function"""
    print(f"Processing YouTube video: {YOUTUBE_VIDEO_ID}")
    
    # Initialize OpenAI client
    client = get_openai_client()
    
    # Download subtitles
    print("Downloading subtitles...")
    text, language_code = download_subtitles(YOUTUBE_VIDEO_ID)
    
    # Extract vocabulary
    print("Extracting vocabulary...")
    vocabulary = extract_vocabulary(text, language_code, client)
    
    print(f"Extracted {len(vocabulary)} vocabulary entries")
    
    # Create unitsOfMeaning structure
    print("Creating unitsOfMeaning structure...")
    data = create_units_of_meaning(vocabulary, language_code)
    
    # Save to file
    save_to_file(data, OUTPUT_FILE)
    
    print("Script completed successfully!")

if __name__ == "__main__":
    main()
