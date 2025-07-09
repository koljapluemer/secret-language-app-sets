import os
import json
import shutil
from pathlib import Path

def clear_public_folder():
    """Clear all folders and files in public/"""
    public_dir = Path("public")
    if public_dir.exists():
        shutil.rmtree(public_dir)
    public_dir.mkdir(exist_ok=True)
    print("Cleared public/ folder")

def copy_headers_file():
    """Copy _headers file to public/"""
    headers_src = Path("_headers")
    headers_dst = Path("public/_headers")
    if headers_src.exists():
        shutil.copy2(headers_src, headers_dst)
        print("Copied _headers file")
    else:
        print("Warning: _headers file not found")

def copy_data_files():
    """Copy all files from data/ to public/, preserving folder structure and compressing JSON"""
    data_dir = Path("data")
    public_dir = Path("public")
    
    if not data_dir.exists():
        print("Warning: data/ folder not found")
        return
    
    for file_path in data_dir.rglob("*"):
        if file_path.is_file():
            # Calculate relative path from data/ to preserve structure
            rel_path = file_path.relative_to(data_dir)
            dst_path = public_dir / rel_path
            
            # Create parent directories if they don't exist
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Handle JSON files specially - compress them
            if file_path.suffix.lower() == '.json':
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    with open(dst_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
                    print(f"Copied and compressed: {rel_path}")
                except Exception as e:
                    print(f"Error processing JSON file {file_path}: {e}")
            else:
                # Copy non-JSON files as-is
                shutil.copy2(file_path, dst_path)
                print(f"Copied: {rel_path}")

def generate_sets_json():
    """Generate public/sets.json with file paths and names"""
    public_dir = Path("public")
    sets_data = {}
    
    # Find all JSON files in public/ (excluding sets.json itself)
    for json_file in public_dir.rglob("*.json"):
        if json_file.name == "sets.json":
            continue
            
        # Calculate relative path from public/
        rel_path = json_file.relative_to(public_dir)
        file_path_str = str(rel_path).replace("\\", "/")  # Ensure forward slashes
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Get the "name" property from the JSON
            name = data.get("name", f"Set {file_path_str}")
            sets_data[file_path_str] = name
            
        except Exception as e:
            print(f"Error reading JSON file {json_file}: {e}")
            sets_data[file_path_str] = f"Set {file_path_str}"
    
    # Write sets.json
    sets_json_path = public_dir / "sets.json"
    with open(sets_json_path, 'w', encoding='utf-8') as f:
        json.dump(sets_data, f, ensure_ascii=False, separators=(',', ':'))
    
    print(f"Generated sets.json with {len(sets_data)} entries")

def main():
    """Main conversion process"""
    print("Starting conversion process...")
    
    # Step 1: Clear public/ folder
    clear_public_folder()
    
    # Step 2: Copy _headers file
    copy_headers_file()
    
    # Step 3: Copy data/ files with compressed JSON
    copy_data_files()
    
    # Step 4: Generate sets.json
    generate_sets_json()
    
    print("Conversion complete!")

if __name__ == "__main__":
    main()
