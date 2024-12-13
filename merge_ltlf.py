#!/usr/bin/env python3
"""
LTLF File Merger

This script implements functionality to:
1. Relabel variables in .ltlf and .part files
2. Randomly select and merge multiple file pairs
3. Handle variable conflicts and minimize variable usage
"""

import os
import random
import re
from typing import Dict, List, Set, Tuple


class VariableManager:
    """Manages variable naming and conflict resolution."""

    def __init__(self):
        """Initialize variable manager with empty mapping."""
        self.var_mapping: Dict[str, str] = {}
        self.next_var_id: int = 1

    def get_new_var(self) -> str:
        """Generate a new unique variable name."""
        var = f"p{self.next_var_id}"
        self.next_var_id += 1
        return var

    def reset(self) -> None:
        """Reset the variable mapping and counter."""
        self.var_mapping.clear()
        self.next_var_id = 1


class LTLFPair:
    """Represents a pair of .ltlf and .part files."""

    def __init__(self, ltlf_path: str, part_path: str):
        """Initialize with paths to .ltlf and .part files."""
        self.ltlf_path: str = ltlf_path
        self.part_path: str = part_path
        self.formula: str = ""
        self.inputs: List[str] = []
        self.outputs: List[str] = []
        self.load_files()

    def load_files(self) -> None:
        """
        Load contents from .ltlf and .part files.

        The .part files contain input and output variable definitions.
        The .ltlf files contain temporal logic formulas.

        Raises:
            FileNotFoundError: If either file doesn't exist
            ValueError: If file format is invalid
        """
        # Load .part file
        try:
            with open(self.part_path, 'r') as f:
                lines = f.readlines()
                if len(lines) < 2:
                    raise ValueError(f"Invalid .part file format: {self.part_path}")

                # Parse inputs
                inputs_line = lines[0].strip()
                if not inputs_line.startswith('.inputs:'):
                    raise ValueError(f"Invalid .part file format - missing .inputs: {self.part_path}")
                self.inputs = inputs_line.split(':')[1].strip().split()

                # Parse outputs
                outputs_line = lines[1].strip()
                if not outputs_line.startswith('.outputs:'):
                    raise ValueError(f"Invalid .part file format - missing .outputs: {self.part_path}")
                self.outputs = outputs_line.split(':')[1].strip().split()
        except FileNotFoundError:
            raise FileNotFoundError(f"Part file not found: {self.part_path}")

        # Load .ltlf file
        try:
            with open(self.ltlf_path, 'r') as f:
                self.formula = f.read().strip()
                if not self.formula:
                    raise ValueError(f"Empty .ltlf file: {self.ltlf_path}")
        except FileNotFoundError:
            raise FileNotFoundError(f"LTLF file not found: {self.ltlf_path}")

    def relabel_variables(self, var_manager: VariableManager, mapping: Dict[str, str]) -> None:
        """
        Relabel variables using provided mapping.

        This method updates both the formula in the .ltlf file and the
        variables in the .part file according to the provided mapping.
        The mapping ensures no variable appears in both inputs and outputs.

        Args:
            var_manager: VariableManager instance for generating new variable names
            mapping: Dictionary mapping old variable names to new ones
        """
        # Update formula with new variable names
        formula = self.formula
        for old_var, new_var in mapping.items():
            # Use word boundaries to ensure we only replace complete variable names
            formula = re.sub(
                rf'\b{old_var}\b',
                new_var,
                formula
            )
        self.formula = formula

        # Update input variables
        self.inputs = [mapping.get(var, var) for var in self.inputs]

        # Update output variables
        self.outputs = [mapping.get(var, var) for var in self.outputs]


class LTLFMerger:
    """Handles merging of multiple LTLF pairs."""

    def __init__(self, filtered_dir: str):
        """Initialize merger with directory containing filtered files."""
        self.filtered_dir: str = filtered_dir
        self.var_manager: VariableManager = VariableManager()

    def get_file_pairs(self) -> List[LTLFPair]:
        """Get list of all .ltlf/.part file pairs in directory."""
        pairs = []
        for filename in os.listdir(self.filtered_dir):
            if filename.endswith('.ltlf'):
                base = filename[:-5]  # Remove .ltlf extension
                ltlf_path = os.path.join(self.filtered_dir, f"{base}.ltlf")
                part_path = os.path.join(self.filtered_dir, f"{base}.part")
                if os.path.exists(part_path):
                    pairs.append(LTLFPair(ltlf_path, part_path))
        return pairs

    def merge_pairs(self, pairs: List[LTLFPair]) -> Tuple[str, List[str], List[str]]:
        """
        Merge multiple LTLF pairs into a single pair.

        This method handles:
        1. Variable conflict resolution between inputs and outputs
        2. Minimal variable name usage
        3. Formula combination with proper bracketing

        Args:
            pairs: List of LTLFPair objects to merge

        Returns:
            Tuple containing:
            - Merged formula string
            - List of merged input variables
            - List of merged output variables
        """
        self.var_manager.reset()
        mapping: Dict[str, str] = {}

        # Collect all variables
        all_inputs: Set[str] = set()
        all_outputs: Set[str] = set()
        for pair in pairs:
            all_inputs.update(pair.inputs)
            all_outputs.update(pair.outputs)

        # Handle conflicts and create mapping
        used_vars: Set[str] = set()

        # First, handle variables that appear in both inputs and outputs
        conflicts = all_inputs.intersection(all_outputs)
        for var in conflicts:
            new_var = self.var_manager.get_new_var()
            mapping[var] = new_var
            used_vars.add(new_var)

        # Then try to reuse existing variable names when possible
        for var in all_inputs.union(all_outputs):
            if var not in mapping:
                if var not in used_vars:
                    # Can reuse the original name
                    mapping[var] = var
                    used_vars.add(var)
                else:
                    # Need a new name
                    new_var = self.var_manager.get_new_var()
                    mapping[var] = new_var
                    used_vars.add(new_var)

        # Apply relabeling to all pairs
        merged_pairs = []
        for pair in pairs:
            new_pair = LTLFPair(pair.ltlf_path, pair.part_path)
            new_pair.relabel_variables(self.var_manager, mapping)
            merged_pairs.append(new_pair)

        # Create merged formula with proper bracketing
        merged_formula = "(" + " && ".join(p.formula for p in merged_pairs) + ")"

        # Create merged inputs and outputs lists
        merged_inputs = sorted(set(v for p in merged_pairs for v in p.inputs))
        merged_outputs = sorted(set(v for p in merged_pairs for v in p.outputs))

        return merged_formula, merged_inputs, merged_outputs

    def random_merge(self, n: int) -> Tuple[str, List[str], List[str]]:
        """Randomly select and merge n pairs of files."""
        all_pairs = self.get_file_pairs()
        if n > len(all_pairs):
            raise ValueError(f"Requested {n} pairs but only {len(all_pairs)} available")
        selected_pairs = random.sample(all_pairs, n)
        return self.merge_pairs(selected_pairs)


def main():
    """Main entry point for the script."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description='Merge LTLF file pairs.')
    parser.add_argument('--n', type=int, default=2,
                       help='Number of file pairs to merge (default: 2)')
    parser.add_argument('--output-prefix', type=str, default='merged',
                       help='Prefix for output files (default: merged)')
    parser.add_argument('--filtered-dir', type=str, default='syft_1_filtered',
                       help='Directory containing filtered files (default: syft_1_filtered)')

    args = parser.parse_args()

    try:
        merger = LTLFMerger(args.filtered_dir)
        merged_formula, inputs, outputs = merger.random_merge(args.n)

        # Write output files
        ltlf_file = f"{args.output_prefix}.ltlf"
        part_file = f"{args.output_prefix}.part"

        with open(ltlf_file, 'w') as f:
            f.write(merged_formula)

        with open(part_file, 'w') as f:
            f.write(f".inputs: {' '.join(inputs)}\n")
            f.write(f".outputs: {' '.join(outputs)}\n")

        print(f"Successfully merged {args.n} file pairs:")
        print(f"- LTLF file: {ltlf_file}")
        print(f"- Part file: {part_file}")
        print(f"\nInput variables: {len(inputs)}")
        print(f"Output variables: {len(outputs)}")

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
