#!/usr/bin/env python3
"""
LTLF File Merger

This script implements functionality to:
1. Relabel variables in .ltlf and .part files
2. Randomly select and merge multiple file pairs
3. Handle variable conflicts and minimize variable usage
"""

import os
import glob
import random
import sys
import argparse
import re
from typing import List, Tuple, Set, Dict


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

    def relabel_variables(self, mapping: Dict[str, str]) -> str:
        """
        Relabel variables using provided mapping.

        This method updates the formula in the .ltlf file using the provided mapping.
        The mapping ensures no variable appears in both inputs and outputs.

        Args:
            mapping: Dictionary mapping old variable names to new ones

        Returns:
            The relabeled formula
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
        return formula

    def write_files(self, prefix: str, formula: str, inputs: List[str], outputs: List[str]) -> None:
        """
        Write merged formula and parameters to output files.

        Args:
            prefix: Base name for output files
            formula: The merged formula to write
            inputs: List of input variables
            outputs: List of output variables
        """
        # Write merged formula to output file
        with open(f"{prefix}.ltlf", "w") as f:
            f.write(formula)

        # Write merged parameters to output file with colons
        with open(f"{prefix}.part", "w") as f:
            f.write(".inputs: " + " ".join(sorted(inputs)) + "\n")
            f.write(".outputs: " + " ".join(sorted(outputs)) + "\n")


class LTLFMerger:
    """Handles merging of multiple LTLF pairs."""

    def __init__(self):
        """Initialize merger with directory containing filtered files."""
        self.var_manager: VariableManager = VariableManager()

    def get_file_pairs(self, filtered_dir: str) -> List[LTLFPair]:
        """Get list of all .ltlf/.part file pairs in directory."""
        pairs = []
        for filename in os.listdir(filtered_dir):
            if filename.endswith('.ltlf'):
                base = filename[:-5]  # Remove .ltlf extension
                ltlf_path = os.path.join(filtered_dir, f"{base}.ltlf")
                part_path = os.path.join(filtered_dir, f"{base}.part")
                if os.path.exists(part_path):
                    pairs.append(LTLFPair(ltlf_path, part_path))
        return pairs

    def merge_pairs(self, pairs: List[LTLFPair], filtered_dir: str) -> Tuple[str, List[str], List[str]]:
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
        input_vars: Dict[str, Set[str]] = {}
        output_vars: Dict[str, Set[str]] = {}

        # Debug print for input analysis
        print("=== Debug: Variable Usage Analysis ===")

        # Load all pairs and collect variable usage
        for pair in pairs:
            pair.load_files()
            print(f"\nFile: {pair.ltlf_path}")
            print(f"Inputs: {pair.inputs}")
            print(f"Outputs: {pair.outputs}")

            for var in pair.inputs:
                if var not in input_vars:
                    input_vars[var] = set()
                input_vars[var].add(pair.ltlf_path)
            for var in pair.outputs:
                if var not in output_vars:
                    output_vars[var] = set()
                output_vars[var].add(pair.ltlf_path)

        print("\nInput variables usage:")
        for var, files in input_vars.items():
            print(f"{var}: appears in {len(files)} files")

        print("\nOutput variables usage:")
        for var, files in output_vars.items():
            print(f"{var}: appears in {len(files)} files")

        # Find variables that can be merged (appear in same role but different files)
        input_groups: List[Set[str]] = []
        output_groups: List[Set[str]] = []
        used_vars = set()  # Track all used variable names

        # Group input variables that can be merged
        sorted_inputs = sorted(input_vars.keys())
        for var1 in sorted_inputs:
            files1 = input_vars[var1]
            merged = False
            # Try to add to existing group first
            for group in input_groups:
                can_merge = True
                for var2 in group:
                    # Check if variables appear in same file
                    if files1.intersection(input_vars[var2]):
                        can_merge = False
                        break
                if can_merge:
                    group.add(var1)
                    merged = True
                    break
            # Create new group if couldn't merge with existing
            if not merged:
                input_groups.append({var1})

        print("\nInput groups for merging:")
        for i, group in enumerate(input_groups):
            print(f"Group {i + 1}: {sorted(group)}")

        # Group output variables that can be merged
        sorted_outputs = sorted(output_vars.keys())
        for var1 in sorted_outputs:
            files1 = output_vars[var1]
            merged = False
            # Try to add to existing group first
            for group in output_groups:
                can_merge = True
                for var2 in group:
                    # Check if variables appear in same file
                    if files1.intersection(output_vars[var2]):
                        can_merge = False
                        break
                if can_merge:
                    group.add(var1)
                    merged = True
                    break
            # Create new group if couldn't merge with existing
            if not merged:
                output_groups.append({var1})

        print("\nOutput groups for merging:")
        for i, group in enumerate(output_groups):
            print(f"Group {i + 1}: {sorted(group)}")

        # Create optimized mappings
        input_mapping: Dict[str, str] = {}
        output_mapping: Dict[str, str] = {}
        var_counter = 1

        # First pass: Map input groups, preserving variables that shouldn't be merged
        for group in input_groups:
            # Check if variables in this group share common variables in their files
            common_vars = set()
            for var1 in group:
                for var2 in group:
                    if var1 < var2:  # Only check each pair once
                        files1 = input_vars[var1]
                        files2 = input_vars[var2]
                        # Find variables that appear with both var1 and var2
                        for var in input_vars:
                            if var != var1 and var != var2:
                                if any(input_vars[var].intersection(files1)) and any(input_vars[var].intersection(files2)):
                                    common_vars.add(var)

            # Merge variables if they share common variables and don't appear in same files
            should_merge = len(common_vars) > 0 and all(
                not input_vars[var1].intersection(input_vars[var2])
                for var1 in group
                for var2 in group
                if var1 < var2
            )

            if should_merge:
                # Merge all variables in group to same new variable
                new_var = f"p{var_counter}"
                var_counter += 1
                for var in sorted(group):
                    input_mapping[var] = new_var
            else:
                # Keep variables distinct
                for var in sorted(group):
                    new_var = f"p{var_counter}"
                    var_counter += 1
                    input_mapping[var] = new_var

        # Second pass: Map output groups to completely new variables
        # Keep output variables distinct to preserve the correct number
        for group in output_groups:
            for var in sorted(group):
                new_var = f"p{var_counter}"
                var_counter += 1
                output_mapping[var] = new_var
        print("\nFinal mappings:")
        print("Inputs:", input_mapping)
        print("Outputs:", output_mapping)

        # Merge formulas and apply mappings
        merged_formula = ""
        all_inputs = set()
        all_outputs = set()

        for i, pair in enumerate(pairs):
            # Create separate mappings for formula to preserve variable relationships
            formula_mapping = {**input_mapping}  # Only use input mapping for formula
            relabeled_formula = pair.relabel_variables(formula_mapping)

            if i == 0:
                merged_formula = relabeled_formula
            else:
                merged_formula = f"({merged_formula} && {relabeled_formula})"

            # Collect all unique mapped variables
            for var in pair.inputs:
                all_inputs.add(input_mapping[var])
            for var in pair.outputs:
                all_outputs.add(output_mapping[var])

        return merged_formula, sorted(all_inputs), sorted(all_outputs)

    def random_merge(self, n: int, filtered_dir: str) -> Tuple[str, List[str], List[str]]:
        """Randomly select and merge n pairs of files."""
        all_pairs = self.get_file_pairs(filtered_dir)
        if n > len(all_pairs):
            raise ValueError(f"Requested {n} pairs but only {len(all_pairs)} available")
        selected_pairs = random.sample(all_pairs, n)
        return self.merge_pairs(selected_pairs, filtered_dir)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Merge LTLF files.")
    parser.add_argument(
        "--n",
        type=int,
        default=2,
        help="Number of file pairs to merge (default: 2)",
    )
    parser.add_argument(
        "--output-prefix",
        type=str,
        default="merged",
        help="Prefix for output files (default: merged)",
    )
    parser.add_argument(
        "--filtered-dir",
        type=str,
        default="syft_1_filtered",
        help="Directory containing filtered LTLF files (default: syft_1_filtered)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run test suite",
    )
    args = parser.parse_args()

    if args.test:
        import unittest
        from tests.test_merge_ltlf import TestLTLFMerger
        suite = unittest.TestLoader().loadTestsFromTestCase(TestLTLFMerger)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        sys.exit(not result.wasSuccessful())

    merger = LTLFMerger()
    try:
        formula, inputs, outputs = merger.random_merge(args.n, args.filtered_dir)
        pair = LTLFPair("", "")  # Dummy pair for writing files
        pair.write_files(args.output_prefix, formula, inputs, outputs)
        print(f"Successfully merged {args.n} file pairs.")
        print(f"Output files: {args.output_prefix}.ltlf and {args.output_prefix}.part")
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
