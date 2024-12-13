#!/usr/bin/env python3

import csv
from pathlib import Path
import shutil
import sys

def main():
    # Create output directory if it doesn't exist
    output_dir = Path('syft_1_filtered')
    output_dir.mkdir(exist_ok=True)

    # Read and process syft_1_ok.csv
    try:
        with open('syft_1_ok.csv', 'r') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if len(row) < 2:
                    continue

                # Extract and clean number from row
                number = row[1].strip()
                if not number:
                    continue

                try:
                    # Pad number with zeros to 3 digits
                    padded_num = f"{int(number):03d}"

                    # Define source file paths
                    ltlf_file = Path('syft_1') / f"{padded_num}.ltlf"
                    part_file = Path('syft_1') / f"{padded_num}.part"

                    # Check if both files exist and copy them
                    if ltlf_file.exists() and part_file.exists():
                        shutil.copy2(ltlf_file, output_dir)
                        shutil.copy2(part_file, output_dir)
                        print(f"Copied files for number {padded_num}")
                    else:
                        print(f"Warning: Files for number {padded_num} not found")
                except ValueError:
                    print(f"Warning: Invalid number format: {number}")
    except FileNotFoundError:
        print("Error: syft_1_ok.csv not found", file=sys.stderr)
        sys.exit(1)
    except csv.Error as e:
        print(f"Error reading CSV file: {e}", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print("Error: Permission denied accessing files", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
