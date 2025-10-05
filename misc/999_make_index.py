import os
import json
from pathlib import Path

def main():
    sets_dir = Path("sets")
    
    if not sets_dir.exists():
        print("sets/ directory does not exist")
        return
    
    # Get all top-level folder names in sets/
    top_level_folders = [f.name for f in sets_dir.iterdir() if f.is_dir()]
    
    # Write sets/index.json with array of folder names
    index_data = top_level_folders
    with open(sets_dir / "index.json", "w") as f:
        json.dump(index_data, f, indent=2)
    
    print(f"Created sets/index.json with {len(top_level_folders)} folders: {top_level_folders}")
    
    # Go into each top-level folder and create index files for subfolders
    for folder_name in top_level_folders:
        folder_path = sets_dir / folder_name
        
        # Get all subfolder names in this folder
        subfolders = [f.name for f in folder_path.iterdir() if f.is_dir()]
        
        # Write index.json in this folder with array of subfolder names
        subfolder_index_data = subfolders
        with open(folder_path / "index.json", "w") as f:
            json.dump(subfolder_index_data, f, indent=2)
        
        print(f"Created {folder_path}/index.json with {len(subfolders)} subfolders: {subfolders}")

if __name__ == "__main__":
    main()