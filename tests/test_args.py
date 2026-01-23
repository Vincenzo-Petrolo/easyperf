import unittest
import subprocess
import os

class TestEasyperfArgs(unittest.TestCase):
    def test_version(self):
        result = subprocess.run(["./easyperf", "--version"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("easyperf version 0.1.0", result.stdout)

    def test_process_parsing(self):
        # Validate that arguments are validated
        # -p with non-existent file
        result = subprocess.run(["./easyperf", "-p", "/does/not/exist"], capture_output=True, text=True)
        # Should fail validation
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid argument", result.stderr)

    def test_time_validation(self):
        result = subprocess.run(["./easyperf", "-t", "-1"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid argument", result.stderr)

if __name__ == '__main__':
    unittest.main()
