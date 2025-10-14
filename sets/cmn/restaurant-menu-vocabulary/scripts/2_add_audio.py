#!/usr/bin/env python3
"""
Generate pronunciation audio for the restaurant menu vocabulary set using SpeechGen.

This script:
  * loads vocab entries from out/vocab.jsonl
  * generates (or reuses) mp3 files in out/audio for each vocab item's Chinese content
  * adds/updates the vocab.sounds array so each entry references its audio file

Environment variables required:
  SPEECHGEN_API_KEY  - SpeechGen API token
  SPEECHGEN_EMAIL    - Email address associated with the SpeechGen account
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
import random
from typing import Dict, Iterable, List, Optional, Tuple

import requests
from dotenv import load_dotenv

SET_DIR = Path(__file__).parent.parent
OUT_DIR = SET_DIR / "out"
VOCAB_PATH = OUT_DIR / "vocab.jsonl"
NOTES_PATH = OUT_DIR / "notes.jsonl"
AUDIO_DIR = OUT_DIR / "audio"

SPEECHGEN_TOKEN_ENV = "SPEECHGEN_API_KEY"
SPEECHGEN_EMAIL_ENV = "SPEECHGEN_EMAIL"

REQUEST_TIMEOUT = 60
DOWNLOAD_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_SLEEP = 2.0
REQUEST_SLEEP = 1.0


def load_jsonl(path: Path) -> List[Dict]:
    """Read a JSONL file into a list of dictionaries."""
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")

    entries: List[Dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            entries.append(json.loads(line))
    return entries


def write_jsonl(entries: Iterable[Dict], path: Path) -> None:
    """Write iterable of dicts back to JSONL."""
    with path.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def dedupe_preserve_order(items: Iterable[str]) -> List[str]:
    """Deduplicate an iterable while preserving order."""
    seen = set()
    result: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def fetch_chinese_voices() -> List[str]:
    """Fetch SpeechGen Chinese voice identifiers."""
    try:
        response = requests.get(
            "https://speechgen.io/index.php?r=api/voices",
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        voices_data = response.json()
        chinese_entries = voices_data.get("Chinese", [])
        voices: List[str] = []
        for entry in chinese_entries:
            voice_id = entry.get("voice") or entry.get("name")
            if voice_id:
                voices.append(voice_id)
        return voices
    except Exception as exc:
        raise RuntimeError(f"Unable to fetch SpeechGen voices: {exc}") from exc


def load_voice_pool() -> List[str]:
    """Fetch the list of SpeechGen voices to use for generation."""
    voices = fetch_chinese_voices()
    if not voices:
        raise RuntimeError(
            "SpeechGen returned no Chinese voices. "
        )
    print(f"Using {len(voices)} SpeechGen voices (random selection per vocab)")
    return voices


def request_speechgen_audio(
    token: str, email: str, voice: str, text: str
) -> Optional[str]:
    """Request TTS generation and return temporary file URL if successful."""
    params = {
        "token": token,
        "email": email,
        "voice": voice,
        "text": text,
        "format": "mp3",
        "speed": 1.0,
    }
    response = requests.post(
        "https://speechgen.io/index.php?r=api/text",
        data=params,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()

    if payload.get("status") == 1 and "file" in payload:
        return payload["file"]

    print(f"SpeechGen request failed for '{text}': {payload}")
    return None


def download_file(url: str, destination: Path) -> None:
    """Download file at url to destination path."""
    response = requests.get(url, timeout=DOWNLOAD_TIMEOUT)
    response.raise_for_status()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as handle:
        handle.write(response.content)


def ensure_audio_file(
    token: str,
    email: str,
    voices: List[str],
    vocab_entry: Dict,
) -> Tuple[Optional[str], bool]:
    """
    Ensure an mp3 file exists for the vocab entry.

    Returns (filename, created_new_file)
    """
    vocab_id = vocab_entry["id"]
    text = vocab_entry.get("content", "").strip()
    if not text:
        return None, False

    filename = f"{vocab_id}.mp3"
    audio_path = AUDIO_DIR / filename
    if audio_path.exists():
        return filename, False

    selected_voice = random.choice(voices)
    print(f"Generating audio for {vocab_id}: '{text}' (voice: {selected_voice})")
    retries = 0
    while retries < MAX_RETRIES:
        try:
            file_url = request_speechgen_audio(token, email, selected_voice, text)
            if not file_url:
                retries += 1
                time.sleep(RETRY_SLEEP)
                continue

            download_file(file_url, audio_path)
            return filename, True
        except Exception as exc:
            retries += 1
            print(f"Attempt {retries} failed for {vocab_id}: {exc}")
            time.sleep(RETRY_SLEEP)

    print(f"Failed to generate audio for {vocab_id} after {MAX_RETRIES} attempts")
    return None, False


def update_vocab_sounds(vocab_entries: List[Dict], audio_filenames: Dict[str, str]) -> int:
    """Attach audio filenames to vocab entries."""
    updated_count = 0
    for vocab in vocab_entries:
        vocab_id = vocab["id"]
        filename = audio_filenames.get(vocab_id)
        if not filename:
            continue

        existing_sounds = vocab.get("sounds", [])
        sound_entry = {"filename": filename}
        if sound_entry in existing_sounds:
            continue

        updated_sounds = existing_sounds + [sound_entry]
        vocab["sounds"] = updated_sounds
        updated_count += 1
    return updated_count


def main() -> None:
    load_dotenv()

    token = os.getenv(SPEECHGEN_TOKEN_ENV)
    email = os.getenv(SPEECHGEN_EMAIL_ENV)
    if not token or not email:
        raise RuntimeError(
            "SPEECHGEN_API_KEY and SPEECHGEN_EMAIL must be set in the environment."
        )

    voice_pool = load_voice_pool()

    print("Loading vocab and notes JSONL files...")
    vocab_entries = load_jsonl(VOCAB_PATH)
    _ = load_jsonl(NOTES_PATH)  # Ensure notes exist; not used directly here.
    print(f"Loaded {len(vocab_entries)} vocab entries")

    audio_filenames: Dict[str, str] = {}
    created_files = 0
    for index, vocab in enumerate(vocab_entries, start=1):
        filename, created = ensure_audio_file(token, email, voice_pool, vocab)
        if filename:
            audio_filenames[vocab["id"]] = filename
        if created:
            created_files += 1
        time.sleep(REQUEST_SLEEP)

    attached_count = update_vocab_sounds(vocab_entries, audio_filenames)

    print(f"Generated {created_files} new audio files")
    print(f"Attached audio to {attached_count} vocab entries")

    print("Writing updated vocab.jsonl...")
    write_jsonl(vocab_entries, VOCAB_PATH)
    print("Done.")


if __name__ == "__main__":
    main()
