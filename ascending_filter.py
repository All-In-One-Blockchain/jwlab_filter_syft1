#!/usr/bin/env python3

import csv
from pathlib import Path
import shutil
import sys

# Function to read and filter entries from ascending_filtered.csv
def read_filtered_entries(csv_path: str) -> set[str]:
    realizable_files = set()
    try:
        with open(csv_path, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if len(row) < 3:
                    continue
                _, f_num, status = [x.strip() for x in row]
                if status == "Realizable":
                    num = f_num[1:] if f_num.startswith('f') else f_num
                    realizable_files.add(num)
    except FileNotFoundError:
        print(f"Error: {csv_path} not found", file=sys.stderr)
        sys.exit(1)
    return realizable_files

# Function to copy .ltlf and .part file pairs
def copy_file_pairs(src_dir: Path, dest_dir: Path, file_num: str) -> bool:
    padded_num = f"{int(file_num):d}"
    ltlf_file = src_dir / f"f{padded_num}.ltlf"
    part_file = src_dir / f"f{padded_num}.part"

    if ltlf_file.exists() and part_file.exists():
        out_dir = dest_dir / src_dir.name
        out_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy2(ltlf_file, out_dir)
        shutil.copy2(part_file, out_dir)
        return True
    return False

# Main function to coordinate the filtering process
def main():
    # Create output directory
    output_dir = Path('ascending_filtered')
    output_dir.mkdir(exist_ok=True)

    # Read realizable entries
    realizable_files = read_filtered_entries('ascending_filtered.csv')

    # Process each tree_size directory
    ascending_dir = Path('Ascending')
    processed = 0
    for tree_dir in ascending_dir.glob('tree_size_*'):
        for file_num in realizable_files:
            if copy_file_pairs(tree_dir, output_dir, file_num):
                processed += 1
                print(f"Copied files for f{file_num} from {tree_dir.name}")

    print(f"\nTotal file pairs copied: {processed}")

if __name__ == '__main__':
    main()
