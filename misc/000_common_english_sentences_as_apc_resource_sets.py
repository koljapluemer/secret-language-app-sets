#!/usr/bin/env python3
import json
import os
from pathlib import Path

# Data storage
resource_data = []
link_data = []

# ID counters
resource_id = 0
link_id = 0

def get_next_resource_id():
    global resource_id
    resource_id += 1
    return str(resource_id)

def get_next_link_id():
    global link_id
    link_id += 1
    return str(link_id)

def create_link(label, url, owner=None, owner_link=None, license=None):
    """Create a link entry and return its ID"""
    link_entry = {
        "id": get_next_link_id(),
        "label": label,
        "url": url
    }
    if owner:
        link_entry["owner"] = owner
    if owner_link:
        link_entry["ownerLink"] = owner_link
    if license:
        link_entry["license"] = license
    
    link_data.append(link_entry)
    return link_entry["id"]

def create_resource(language, title, priority=None, content=None, link_id=None, notes=None):
    """Create a resource entry and return its ID"""
    resource_entry = {
        "id": get_next_resource_id(),
        "language": language,
        "title": title
    }
    if priority is not None:
        resource_entry["priority"] = priority
    if content:
        resource_entry["content"] = content
    if link_id:
        resource_entry["link"] = link_id
    if notes:
        resource_entry["notes"] = notes
    
    resource_data.append(resource_entry)
    return resource_entry["id"]

def save_jsonl_files():
    """Save all collected data to JSONL files"""
    # Create directory structure
    output_dir = Path("sets/apc/common-english-sentences")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save resources.jsonl
    with open(output_dir / "resources.jsonl", "w", encoding="utf-8") as f:
        for entry in resource_data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    # Save links.jsonl
    with open(output_dir / "links.jsonl", "w", encoding="utf-8") as f:
        for entry in link_data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    print(f"Saved {len(resource_data)} resource entries")
    print(f"Saved {len(link_data)} link entries")

def create_common_english_resource_set():
    # Read the input file from data_in/links.json
    with open("data_in/links.json", "r") as f:
        data = json.load(f)
    
    # Process each entry
    for i, entry in enumerate(data, 1):
        # Create link entry
        link_id = create_link(
            label=entry["title"],
            url=entry["url"]
        )
        
        # Create resource entry
        create_resource(
            language="apc",
            title=entry["title"],
            priority=i,
            link_id=link_id
        )
    
    # Save all data to JSONL files
    save_jsonl_files()
    
    print(f"Created resource set with {len(resource_data)} resources")

if __name__ == "__main__":
    create_common_english_resource_set()