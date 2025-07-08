import pandas as pd

# Read the CSV in chunks to handle large files efficiently
input_file = 'levanti.csv'
output_file = 'levanti_filtered_3cols.csv'

chunk_size = 100000  # Adjust as needed for memory
first_chunk = True

for chunk in pd.read_csv(input_file, chunksize=chunk_size):
    # Filter rows where synthesized is False (case-insensitive, handles bool and str)
    filtered = chunk[chunk['synthesized'].astype(str).str.lower() == 'false']
    # Keep only the specified columns
    filtered = filtered[['dialect', 'arabic', 'english']]
    # Write header only for the first chunk
    filtered.to_csv(output_file, mode='w' if first_chunk else 'a', index=False, header=first_chunk)
    first_chunk = False
