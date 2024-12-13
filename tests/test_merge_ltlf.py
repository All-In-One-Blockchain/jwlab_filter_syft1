import unittest
import os
import shutil
from merge_ltlf import LTLFMerger, LTLFPair

class TestLTLFMerger(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test"""
        self.test_dir = "test_files"
        os.makedirs(self.test_dir, exist_ok=True)
        self.merger = LTLFMerger(self.test_dir)

    def tearDown(self):
        """Clean up test environment after each test"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def create_test_files(self, base_name: str, inputs: list[str],
                         outputs: list[str], formula: str) -> tuple[str, str]:
        """Helper method to create test .ltlf and .part files"""
        ltlf_path = os.path.join(self.test_dir, f"{base_name}.ltlf")
        part_path = os.path.join(self.test_dir, f"{base_name}.part")

        with open(ltlf_path, "w") as f:
            f.write(formula)

        with open(part_path, "w") as f:
            f.write(f".inputs: {' '.join(inputs)}\n")
            f.write(f".outputs: {' '.join(outputs)}\n")

        return ltlf_path, part_path

    def test_basic_merge_no_conflicts(self):
        """Test basic merge with no variable conflicts"""
        # Create first pair with p1-p4 as inputs, p10-p13 as outputs
        ltlf1, part1 = self.create_test_files(
            "test1",
            ["p1", "p2", "p3", "p4"],
            ["p10", "p11", "p12", "p13"],
            "G(p1 -> X[!](p10))"
        )

        # Create second pair with p5-p8 as inputs, p14-p17 as outputs
        ltlf2, part2 = self.create_test_files(
            "test2",
            ["p5", "p6", "p7", "p8"],
            ["p14", "p15", "p16", "p17"],
            "G(p5 -> X[!](p14))"
        )

        pairs = [
            LTLFPair(ltlf1, part1),
            LTLFPair(ltlf2, part2)
        ]

        formula, inputs, outputs = self.merger.merge_pairs(pairs)

        # Verify no variable appears in both inputs and outputs
        self.assertEqual(len(set(inputs) & set(outputs)), 0)
        # Verify all variables are preserved
        self.assertEqual(len(inputs), 8)  # p1-p8
        self.assertEqual(len(outputs), 8)  # p10-p17
        # Verify formula is properly merged with brackets
        self.assertTrue(formula.startswith("(") and formula.endswith(")"))
        self.assertIn("&&", formula)

    def test_input_output_conflict(self):
        """Test merging when variable appears in inputs of one file and outputs of another"""
        # Create first pair with p1 in inputs
        ltlf1, part1 = self.create_test_files(
            "test1",
            ["p1", "p2"],
            ["p10", "p11"],
            "G(p1 -> X[!](p10))"
        )

        # Create second pair with p1 in outputs
        ltlf2, part2 = self.create_test_files(
            "test2",
            ["p3", "p4"],
            ["p1", "p12"],  # p1 appears in outputs
            "G(p3 -> X[!](p1))"
        )

        pairs = [
            LTLFPair(ltlf1, part1),
            LTLFPair(ltlf2, part2)
        ]

        formula, inputs, outputs = self.merger.merge_pairs(pairs)

        # Verify no variable appears in both inputs and outputs
        self.assertEqual(len(set(inputs) & set(outputs)), 0)
        # Verify p1 is properly handled (should be renamed in one location)
        self.assertTrue(
            ("p1" in inputs and "p1" not in outputs) or
            ("p1" in outputs and "p1" not in inputs)
        )

    def test_minimal_variable_usage(self):
        """Test that merged result uses minimal variable names"""
        # Create first pair with gaps in variable numbering
        ltlf1, part1 = self.create_test_files(
            "test1",
            ["p1", "p5"],
            ["p10", "p15"],
            "G(p1 -> X[!](p10))"
        )

        # Create second pair with different gaps
        ltlf2, part2 = self.create_test_files(
            "test2",
            ["p3", "p7"],
            ["p12", "p17"],
            "G(p3 -> X[!](p12))"
        )

        pairs = [
            LTLFPair(ltlf1, part1),
            LTLFPair(ltlf2, part2)
        ]

        formula, inputs, outputs = self.merger.merge_pairs(pairs)

        # Get all variable numbers
        all_vars = set()
        for var in inputs + outputs:
            num = int(var[1:])  # Extract number from pX
            all_vars.add(num)

        # Verify variables are numbered consecutively from 1
        expected_vars = set(range(1, len(all_vars) + 1))
        self.assertEqual(all_vars, expected_vars)

    def test_empty_sets(self):
        """Test merging with empty input/output sets"""
        # Create pair with empty inputs
        ltlf1, part1 = self.create_test_files(
            "test1",
            [],
            ["p10", "p11"],
            "G(true)"
        )

        # Create pair with empty outputs
        ltlf2, part2 = self.create_test_files(
            "test2",
            ["p1", "p2"],
            [],
            "G(p1)"
        )

        pairs = [
            LTLFPair(ltlf1, part1),
            LTLFPair(ltlf2, part2)
        ]

        formula, inputs, outputs = self.merger.merge_pairs(pairs)

        # Verify handling of empty sets
        self.assertEqual(len(set(inputs) & set(outputs)), 0)
        self.assertEqual(len(inputs), 2)
        self.assertEqual(len(outputs), 2)

    def test_formula_merge(self):
        """Test that formulas are merged with proper bracketing"""
        ltlf1, part1 = self.create_test_files(
            "test1",
            ["p1"],
            ["p10"],
            "G(p1)"
        )

        ltlf2, part2 = self.create_test_files(
            "test2",
            ["p2"],
            ["p11"],
            "F(p2)"
        )

        pairs = [
            LTLFPair(ltlf1, part1),
            LTLFPair(ltlf2, part2)
        ]

        formula, inputs, outputs = self.merger.merge_pairs(pairs)

        # Verify proper bracketing
        self.assertEqual(formula.count("("), formula.count(")"))
        self.assertTrue(formula.startswith("("))
        self.assertTrue(formula.endswith(")"))
        self.assertIn("&&", formula)
        # Verify original formulas are preserved
        self.assertIn("G(p1)", formula)
        self.assertIn("F(p2)", formula)

if __name__ == "__main__":
    unittest.main()
