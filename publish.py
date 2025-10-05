import os
import json
import shutil
from pathlib import Path

def main():
    sets_dir = Path("sets")
    public_dir = Path("public")

    # Step 0: Clear out the public folder
    if public_dir.exists():
        shutil.rmtree(public_dir)
    public_dir.mkdir()

    # Copy _headers file to public/
    headers_file = Path("_headers")
    if headers_file.exists():
        shutil.copy2(headers_file, public_dir / "_headers")
        print("Copied _headers to public/")

    # Get all language code folders from sets/
    lang_folders = [f.name for f in sets_dir.iterdir() if f.is_dir()]

    # Generate public/index.json with available languages
    with open(public_dir / "index.json", "w") as f:
        json.dump(lang_folders, f, indent=2)

    print(f"Created public/index.json with {len(lang_folders)} languages: {lang_folders}")

    # Process each language folder
    for lang_code in lang_folders:
        lang_src = sets_dir / lang_code
        lang_dest = public_dir / lang_code
        lang_dest.mkdir()

        # Get all set folders in this language
        set_folders = [f.name for f in lang_src.iterdir() if f.is_dir()]

        # Collect metadata for all sets in this language
        lang_metadata = {}

        for set_name in set_folders:
            set_src = lang_src / set_name
            set_dest = lang_dest / set_name
            set_dest.mkdir()

            # Read metadata.json from the set folder
            metadata_file = set_src / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                    lang_metadata[set_name] = metadata

            # Copy contents from out/ subfolder to public set folder
            out_dir = set_src / "out"
            if out_dir.exists():
                for item in out_dir.iterdir():
                    if item.is_dir():
                        shutil.copytree(item, set_dest / item.name)
                    else:
                        shutil.copy2(item, set_dest / item.name)

            print(f"Published {lang_code}/{set_name}")

        # Write index.json for this language with all set metadata
        with open(lang_dest / "index.json", "w") as f:
            json.dump(lang_metadata, f, indent=2)

        print(f"Created {lang_code}/index.json with {len(lang_metadata)} sets")

if __name__ == "__main__":
    main()
