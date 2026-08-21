"""Test to ensure the baseline reference file remains intact."""

import os
import json
import unittest
from pathlib import Path

class TestBaselineReference(unittest.TestCase):
    def test_reference_file_integrity(self):
        """Verify the reference results file exists, is valid JSON, and has 5 complete entries."""
        reference_path = Path(__file__).resolve().parent.parent / "app" / "baseline" / "reference_results.json"
        
        # 1. File exists
        self.assertTrue(reference_path.exists(), f"Reference file missing at {reference_path}")
        
        # 2. Valid JSON
        with open(reference_path, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                self.fail(f"Reference file is not valid JSON: {e}")
                
        # 3. Exactly 5 entries
        self.assertEqual(len(data), 5, "Reference file must contain exactly 5 entries.")
        
        # 4. Correct schema per entry
        for i, entry in enumerate(data):
            self.assertIn("question", entry, f"Entry {i} missing 'question'")
            self.assertIn("answer", entry, f"Entry {i} missing 'answer'")
            self.assertIn("chunks_used", entry, f"Entry {i} missing 'chunks_used'")
            self.assertIn("human_judgment", entry, f"Entry {i} missing 'human_judgment'")
            
            # Ensure chunks_used is a list
            self.assertIsInstance(entry["chunks_used"], list, f"Entry {i} 'chunks_used' must be a list")

if __name__ == '__main__':
    unittest.main()
