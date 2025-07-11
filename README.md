# Linguanodon Data

## Goal

- Provide pure JSON data for the *linguanodon* frontend

## Functionality

- Editors administrate data in `data/` `JSON` files
- `convert_data.py` creates `public/`, which contains compressed `JSON` files, optimized for API-like access
- `public/` directory is deployed as a "static site" on Netlify

## Integrated Sources

- A manually (=ChatGPT) written example: [this JSON file](data/italian_expressions.json)
- Some sentence and word extraction (feeding into cloze), handled in [this script](scripts/003_handle_shamy_dataset/03_generate_set_data.py)
    - To update this data, first run `python scripts/003_handle_shamy_dataset/03_generate_set_data.py`, then `python convert.py`, then push