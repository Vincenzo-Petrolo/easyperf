import unittest
import subprocess
import os
import csv

class TestEasyperfBasic(unittest.TestCase):
    def test_help(self):
        result = subprocess.run(["./easyperf", "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Example usage:", result.stdout)

    def test_list(self):
        result = subprocess.run(["./easyperf", "--list"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Available Events:", result.stdout)

    def test_simple_run(self):
        if os.path.exists("easyperf.csv"):
            os.remove("easyperf.csv")

        # Run for 2 seconds
        result = subprocess.run(["./easyperf", "--time", "2", "--sleep", "1"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(os.path.exists("easyperf.csv"))

        with open("easyperf.csv", "r") as f:
            reader = csv.reader(f)
            header = next(reader)
            self.assertTrue(len(header) > 0)
            rows = list(reader)
            # Should have at least 1 or 2 rows
            self.assertTrue(len(rows) >= 1)

    def test_process_run(self):
        if os.path.exists("process_out.csv"):
            os.remove("process_out.csv")

        # Run ls
        result = subprocess.run(["./easyperf", "--process", "/bin/ls", "--output", "process_out.csv", "--time", "2"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(os.path.exists("process_out.csv"))

if __name__ == '__main__':
    unittest.main()
