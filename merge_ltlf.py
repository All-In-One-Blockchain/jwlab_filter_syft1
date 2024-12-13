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
        output_mapping: Dict[str, str] = {}  # Special mapping for output occurrences
        used_vars: Set[str] = set()

        # First pass: collect all input and output variables
        all_inputs: Set[str] = set()
        all_outputs: Set[str] = set()
        for pair in pairs:
            all_inputs.update(pair.inputs)
            all_outputs.update(pair.outputs)

        # Find conflicts (variables that appear in both inputs and outputs)
        conflicts = all_inputs.intersection(all_outputs)

        # Create new mapping for all variables to ensure minimal usage
        next_input_var = 1
        next_output_var = max(len(all_inputs), len(all_outputs)) + 1

        # First, map all input variables
        for var in sorted(all_inputs):
            new_var = f"p{next_input_var}"
            mapping[var] = new_var
            used_vars.add(new_var)
            next_input_var += 1

        # Then, map output variables
        for var in sorted(all_outputs):
            if var in conflicts:
                # For conflicts, create a new output variable
                new_var = f"p{next_output_var}"
                output_mapping[var] = new_var
                used_vars.add(new_var)
                next_output_var += 1
            elif var not in mapping:
                new_var = f"p{next_input_var}"
                mapping[var] = new_var
                used_vars.add(new_var)
                next_input_var += 1

        # Apply relabeling to all pairs
        merged_pairs = []
        for pair in pairs:
            new_pair = LTLFPair(pair.ltlf_path, pair.part_path)

            # Handle inputs using regular mapping
            new_pair.inputs = [mapping[var] for var in pair.inputs]

            # Handle outputs using output_mapping for conflicts
            new_pair.outputs = []
            for var in pair.outputs:
                if var in conflicts:
                    new_pair.outputs.append(output_mapping[var])
                else:
                    new_pair.outputs.append(mapping[var])

            # Update formula
            formula = new_pair.formula

            # For each variable in the formula, determine if it's used in an output context
            # by checking if it appears in the outputs of this pair
            formula_mapping = mapping.copy()
            for var in pair.outputs:
                if var in output_mapping:
                    formula_mapping[var] = output_mapping[var]

            # Apply mappings to formula, longest variable names first to avoid partial matches
            for var in sorted(formula_mapping.keys(), key=len, reverse=True):
                formula = re.sub(
                    rf'\b{var}\b',
                    formula_mapping[var],
                    formula
                )
            new_pair.formula = formula

            merged_pairs.append(new_pair)

        # Create merged formula with proper bracketing
        merged_formula = "(" + " && ".join(p.formula for p in merged_pairs) + ")"

        # Create merged inputs and outputs lists
        merged_inputs = sorted(set(v for p in merged_pairs for v in p.inputs))
        merged_outputs = sorted(set(v for p in merged_pairs for v in p.outputs))

        # Verify no variable appears in both inputs and outputs
        assert len(set(merged_inputs) & set(merged_outputs)) == 0, \
            "Bug: Variable appears in both inputs and outputs after merging"

        return merged_formula, merged_inputs, merged_outputs

    def random_merge(self, n: int) -> Tuple[str, List[str], List[str]]:
        """Randomly select and merge n pairs of files."""
        all_pairs = self.get_file_pairs()
        if n > len(all_pairs):
            raise ValueError(f"Requested {n} pairs but only {len(all_pairs)} available")
        selected_pairs = random.sample(all_pairs, n)
        return self.merge_pairs(selected_pairs)


def main():
    """Main function to handle command line arguments and execute merging"""
    import argparse

    parser = argparse.ArgumentParser(description='Merge LTLF files')
    parser.add_argument('--n', type=int, default=2,
                       help='Number of file pairs to merge')
    parser.add_argument('--output-prefix', type=str, default='merged',
                       help='Prefix for output files')
    parser.add_argument('--filtered-dir', type=str, default='syft_1_filtered',
                       help='Directory containing filtered LTLF files')
    parser.add_argument('--test', action='store_true',
                       help='Run test suite')

    args = parser.parse_args()

    if args.test:
        import unittest
        import sys
        # Add the tests directory to Python path
        sys.path.append('tests')
        # Load and run tests
        from test_merge_ltlf import TestLTLFMerger
        suite = unittest.TestLoader().loadTestsFromTestCase(TestLTLFMerger)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        sys.exit(not result.wasSuccessful())

    merger = LTLFMerger()
    pairs = merger.get_file_pairs(args.filtered_dir)

    if len(pairs) < args.n:
        print(f"Error: Not enough file pairs in {args.filtered_dir}. "
              f"Found {len(pairs)}, requested {args.n}")
        return 1

    # Randomly select n pairs
    import random
    selected_pairs = random.sample(pairs, args.n)

    # Merge the selected pairs
    formula, inputs, outputs = merger.random_merge(selected_pairs)

    # Write output files
    with open(f"{args.output_prefix}.ltlf", "w") as f:
        f.write(formula)

    with open(f"{args.output_prefix}.part", "w") as f:
        f.write(f".inputs: {' '.join(inputs)}\n")
        f.write(f".outputs: {' '.join(outputs)}\n")

    return 0


if __name__ == "__main__":
    main()
