#!/usr/bin/env python3
"""
Data conversion script for linguanodon-data.

Converts data/*.json files to the format required by linguanodon-nuxt,
outputting to public/learning_goals and public/units_of_meaning directories.
"""

import json
import logging
import os
import re
import sys
import shutil
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional


class DataConverter:
    """Main class for converting data files."""
    
    def __init__(self, data_dir: str = "data", public_dir: str = "public", log_level: str = "INFO"):
        """Initialize the converter with directories and logging."""
        self.data_dir = Path(data_dir)
        self.public_dir = Path(public_dir)
        self.learning_goals_dir = self.public_dir / "learning_goals"
        self.units_of_meaning_dir = self.public_dir / "units_of_meaning"
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Track generated UIDs to detect duplicates
        self.generated_uoms: Set[str] = set()
        self.generated_lgs: Set[str] = set()
    
    def url_safe_uid(self, language: str, content: str, lingu_type: str = "") -> str:
        """
        Generate a UID from language, content, and optionally lingu_type.
        Replace slashes with the Unicode solidus character, and truncate to stay within filesystem limits.
        """
        if lingu_type:
            uid_parts = [language, content, lingu_type]
        else:
            uid_parts = [language, content]
        
        # Join with underscore
        uid = "_".join(uid_parts)
        # Replace problematic characters with Unicode alternatives
        uid = uid.replace("/", "⧸")
        uid = uid.replace("#", "ⵌ")
        uid = uid.replace("?", "﹖")
        
        # Truncate to stay under filesystem limits (255 chars for filename)
        # Leave some room for .json extension and path
        max_length = 200
        if len(uid) > max_length:
            uid = uid[:max_length]
        
        return uid
    
    def process_data_files(self) -> None:
        """Process all JSON files in the data directory."""
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Data directory {self.data_dir} does not exist")
        
        # Delete and recreate public directory
        if self.public_dir.exists():
            shutil.rmtree(self.public_dir)
            self.logger.info(f"Deleted existing {self.public_dir}")
        
        self.public_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Created {self.public_dir}")
        
        # Create Netlify _headers file
        self._create_netlify_headers()
        
        json_files = list(self.data_dir.glob("*.json"))
        if not json_files:
            self.logger.warning(f"No JSON files found in {self.data_dir}")
            return
        
        self.logger.info(f"Found {len(json_files)} JSON files to process")
        
        # Create output directories
        self._create_output_directories()
        
        # Process each file
        for json_file in json_files:
            self.logger.info(f"Processing {json_file}")
            try:
                self._process_single_file(json_file)
            except Exception as e:
                self.logger.error(f"Failed to process {json_file}: {e}")
                raise
    
    def _create_output_directories(self) -> None:
        """Create the necessary output directory structure."""
        self.learning_goals_dir.mkdir(parents=True, exist_ok=True)
        self.units_of_meaning_dir.mkdir(parents=True, exist_ok=True)
    
    def _create_netlify_headers(self) -> None:
        """Create Netlify _headers file for CORS support."""
        headers_file = self.public_dir / "_headers"
        headers_content = """/*.json
  Access-Control-Allow-Origin: *
"""
        with open(headers_file, 'w', encoding='utf-8') as f:
            f.write(headers_content)
        self.logger.info(f"Created Netlify _headers file: {headers_file}")
    
    def _process_single_file(self, file_path: Path) -> None:
        """Process a single JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract units of meaning and learning goals
        units_of_meaning = data.get("unitsOfMeaning", {})
        learning_goals = data.get("learningGoals", {})
        
        # Process units of meaning first (learning goals depend on them)
        uom_mapping = self._process_units_of_meaning(units_of_meaning)
        
        # Process learning goals
        self._process_learning_goals(learning_goals, uom_mapping)
    
    def _process_units_of_meaning(self, units_of_meaning: Dict) -> Dict[str, str]:
        """
        Process units of meaning and return mapping from old keys to new UIDs.
        
        Returns:
            Dict mapping original dictionary keys to generated UIDs
        """
        uom_mapping = {}
        
        # First pass: generate UIDs and create mapping
        for key, uom_data in units_of_meaning.items():
            uid = self.url_safe_uid(
                uom_data["language"], 
                uom_data["content"], 
                uom_data["linguType"]
            )
            
            if uid in self.generated_uoms:
                self.logger.warning(f"Duplicate UOM UID generated: {uid}")
            
            self.generated_uoms.add(uid)
            uom_mapping[key] = uid
        
        # Second pass: create the actual objects with resolved relationships
        for key, uom_data in units_of_meaning.items():
            uid = uom_mapping[key]
            
            # Resolve translations and related relationships
            translations = []
            if "translations" in uom_data:
                for trans_key in uom_data["translations"]:
                    if trans_key in uom_mapping:
                        translations.append(uom_mapping[trans_key])
            
            related = []
            if "related" in uom_data:
                for rel_key in uom_data["related"]:
                    if rel_key in uom_mapping:
                        related.append(uom_mapping[rel_key])
            
            # Create the unit of meaning object
            uom_obj = {
                "uid": uid,
                "language": uom_data["language"],
                "content": uom_data["content"],
                "linguType": uom_data["linguType"],
                "context": "unknown",
                "translations": translations if translations else None,
                "related": related if related else None
            }
            
            # Add optional fields if present
            for field in ["pronunciation", "notes", "license", "owner", "ownerLink", "source", "sourceLink"]:
                if field in uom_data:
                    uom_obj[field] = uom_data[field]
            
            # Remove None values
            uom_obj = {k: v for k, v in uom_obj.items() if v is not None}
            
            # Save to file
            self._save_unit_of_meaning(uom_obj)
        
        # Third pass: ensure mutual relationships
        self._ensure_mutual_relationships(units_of_meaning, uom_mapping)
        
        return uom_mapping
    
    def _ensure_mutual_relationships(self, units_of_meaning: Dict, uom_mapping: Dict[str, str]) -> None:
        """Ensure that translations and related relationships are mutual."""
        for key, uom_data in units_of_meaning.items():
            uid = uom_mapping[key]
            
            # Handle translations
            if "translations" in uom_data:
                for trans_key in uom_data["translations"]:
                    if trans_key in uom_mapping:
                        trans_uid = uom_mapping[trans_key]
                        self._add_mutual_translation(uid, trans_uid)
            
            # Handle related
            if "related" in uom_data:
                for rel_key in uom_data["related"]:
                    if rel_key in uom_mapping:
                        rel_uid = uom_mapping[rel_key]
                        self._add_mutual_related(uid, rel_uid)
    
    def _add_mutual_translation(self, uid1: str, uid2: str) -> None:
        """Add mutual translation relationship between two UIDs."""
        for uid in [uid1, uid2]:
            file_path = self._get_uom_file_path(uid)
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    uom_data = json.load(f)
                
                translations = uom_data.get("translations", [])
                other_uid = uid2 if uid == uid1 else uid1
                
                if other_uid not in translations:
                    translations.append(other_uid)
                    uom_data["translations"] = translations
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(uom_data, f, ensure_ascii=False, separators=(',', ':'))
    
    def _add_mutual_related(self, uid1: str, uid2: str) -> None:
        """Add mutual related relationship between two UIDs."""
        for uid in [uid1, uid2]:
            file_path = self._get_uom_file_path(uid)
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    uom_data = json.load(f)
                
                related = uom_data.get("related", [])
                other_uid = uid2 if uid == uid1 else uid1
                
                if other_uid not in related:
                    related.append(other_uid)
                    uom_data["related"] = related
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(uom_data, f, ensure_ascii=False, separators=(',', ':'))
    
    def _process_learning_goals(self, learning_goals: Dict, uom_mapping: Dict[str, str]) -> None:
        """Process learning goals."""
        lg_mapping = {}
        
        # First pass: generate UIDs and create mapping
        for key, lg_data in learning_goals.items():
            uid = self.url_safe_uid(lg_data["language"], lg_data["name"])
            
            if uid in self.generated_lgs:
                self.logger.warning(f"Duplicate LG UID generated: {uid}")
            
            self.generated_lgs.add(uid)
            lg_mapping[key] = uid
        
        # Second pass: create the actual objects
        for key, lg_data in learning_goals.items():
            uid = lg_mapping[key]
            
            # Resolve units of meaning
            units_of_meaning = []
            if "unitsOfMeaning" in lg_data:
                for uom_key in lg_data["unitsOfMeaning"]:
                    if uom_key in uom_mapping:
                        units_of_meaning.append(uom_mapping[uom_key])
            
            # Resolve parents
            parents = []
            if "parents" in lg_data:
                for parent_key in lg_data["parents"]:
                    if parent_key in lg_mapping:
                        parents.append(lg_mapping[parent_key])
            
            # Create the learning goal object
            lg_obj = {
                "uid": uid,
                "name": lg_data["name"],
                "language": lg_data["language"],
                "unitsOfMeaning": units_of_meaning,
                "parents": parents,
                "blockedBy": [],  # Default empty array
                "userCreated": False  # Default value
            }
            
            # Save to file
            self._save_learning_goal(lg_obj)
    
    def _save_unit_of_meaning(self, uom_obj: Dict) -> None:
        """Save a unit of meaning to the appropriate directory."""
        language = uom_obj["language"]
        uid = uom_obj["uid"]
        
        # Create language directory
        lang_dir = self.units_of_meaning_dir / language
        lang_dir.mkdir(parents=True, exist_ok=True)
        
        # Save individual file
        file_path = lang_dir / f"{uid}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(uom_obj, f, ensure_ascii=False, separators=(',', ':'))
        
        # Update index
        self._update_uom_index(language, uid, uom_obj["content"])
    
    def _save_learning_goal(self, lg_obj: Dict) -> None:
        """Save a learning goal to the appropriate directory."""
        language = lg_obj["language"]
        uid = lg_obj["uid"]
        
        # Create language directory
        lang_dir = self.learning_goals_dir / language
        lang_dir.mkdir(parents=True, exist_ok=True)
        
        # Save individual file
        file_path = lang_dir / f"{uid}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(lg_obj, f, ensure_ascii=False, separators=(',', ':'))
        
        # Update index
        self._update_lg_index(language, uid, lg_obj["name"])
    
    def _update_uom_index(self, language: str, uid: str, content: str) -> None:
        """Update the index.json file for units of meaning in a language."""
        lang_dir = self.units_of_meaning_dir / language
        index_path = lang_dir / "index.json"
        
        if index_path.exists():
            with open(index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
        else:
            index_data = []
        
        # Add or update entry
        entry = {"uid": uid, "content": content}
        existing_index = next((i for i, item in enumerate(index_data) if item["uid"] == uid), None)
        
        if existing_index is not None:
            index_data[existing_index] = entry
        else:
            index_data.append(entry)
        
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, separators=(',', ':'))
    
    def _update_lg_index(self, language: str, uid: str, name: str) -> None:
        """Update the index.json file for learning goals in a language."""
        lang_dir = self.learning_goals_dir / language
        index_path = lang_dir / "index.json"
        
        if index_path.exists():
            with open(index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
        else:
            index_data = []
        
        # Add or update entry
        entry = {"uid": uid, "name": name}
        existing_index = next((i for i, item in enumerate(index_data) if item["uid"] == uid), None)
        
        if existing_index is not None:
            index_data[existing_index] = entry
        else:
            index_data.append(entry)
        
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, separators=(',', ':'))
    
    def _get_uom_file_path(self, uid: str) -> Path:
        """Get the file path for a unit of meaning by UID."""
        # This is a helper method that would need to be enhanced to find the correct language directory
        # For now, we'll search through all language directories
        for lang_dir in self.units_of_meaning_dir.iterdir():
            if lang_dir.is_dir():
                file_path = lang_dir / f"{uid}.json"
                if file_path.exists():
                    return file_path
        raise FileNotFoundError(f"Unit of meaning file not found for UID: {uid}")


def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert data files for linguanodon-nuxt")
    parser.add_argument("--data-dir", default="data", help="Input data directory")
    parser.add_argument("--public-dir", default="public", help="Output public directory")
    parser.add_argument("--log-level", default="INFO", 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Logging level")
    
    args = parser.parse_args()
    
    try:
        converter = DataConverter(
            data_dir=args.data_dir,
            public_dir=args.public_dir,
            log_level=args.log_level
        )
        converter.process_data_files()
        # Copy everything from other_data/ to public/
        other_data_dir = Path("other_data")
        public_dir = Path(args.public_dir)
        if other_data_dir.exists() and other_data_dir.is_dir():
            for item in other_data_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, public_dir / item.name)
        print("Data conversion completed successfully!")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
