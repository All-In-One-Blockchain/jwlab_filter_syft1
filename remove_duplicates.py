#!/usr/bin/env python3

import os
from pathlib import Path
import shutil

def normalize_formula(content):
    return content
    """Normalize formula by removing whitespace and newlines"""
    return ''.join(content.split())

def find_duplicates(directory):
    """Find duplicate .ltlf files based on formula content"""
    formulas = {}  # formula -> list of file paths
    dir_path = Path(directory)

    # First pass: collect all formulas
    for ltlf_file in dir_path.glob('*.ltlf'):
        with open(ltlf_file, 'r') as f:
            content = f.read()
            normalized = normalize_formula(content)
            if normalized not in formulas:
                formulas[normalized] = []
            formulas[normalized].append(ltlf_file)

    return {formula: paths for formula, paths in formulas.items() if len(paths) > 1}

def main():
    duplicates = find_duplicates('/home/lic/dev/create_new_benchmark/jwlab_filter_syft2/drafts/conjunct_2/ratio_5')

    # Create backup directory
    backup_dir = Path('syft_1_filtered_backup')
    if not backup_dir.exists():
        shutil.copytree('syft_1_filtered', backup_dir)
        print(f"Created backup in {backup_dir}")

    # Remove duplicates, keeping the lowest numbered file
    for formula, paths in duplicates.items():
        # Sort by numeric value of filename
        paths.sort(key=lambda x: int(x.stem))
        keep_file = paths[0]

        print(f"\nDuplicate group:")
        print(f"Keeping: {keep_file}")

        # Remove all but the first file
        for path in paths[1:]:
            part_file = path.with_suffix('.part')
            print(f"Removing: {path} and {part_file}")
            path.unlink()
            if part_file.exists():
                part_file.unlink()

if __name__ == '__main__':
    main()
