import os
import tempfile
import unittest

from src.core.generator import generate_dictionary_file, load_tasks_from_file


class TestGenerator(unittest.TestCase):
    def setUp(self):
        # Create a temporary file for the dictionary
        self.fd, self.temp_path = tempfile.mkstemp()
        os.close(self.fd)

    def tearDown(self):
        # Remove the temporary file
        if os.path.exists(self.temp_path):
            os.remove(self.temp_path)

    def test_generate_dictionary_M_day01_small_seq(self):
        """Test generating dictionary for Male, Day 01, small sequence"""
        # Gender M -> odd sequences (1, 3, 5...)
        # max_seq=4 -> sequences 0,1,2,3 -> only 1, 3 are odd.
        # 2 sequences * 10 check digits = 20 passwords.
        count = generate_dictionary_file(
            self.temp_path, gender="M", specific_day="01", max_seq=4
        )
        self.assertEqual(count, 20)

        with open(self.temp_path, "r") as f:
            lines = f.readlines()

        self.assertEqual(len(lines), 20)
        # Check first line: M_01,010010
        # seq=1 -> 001. check=0 -> 010010
        self.assertEqual(lines[0].strip(), "M_01,010010")
        # Check last line: M_01,010039
        # seq=3 -> 003. check=9 -> 010039
        self.assertEqual(lines[-1].strip(), "M_01,010039")

    def test_generate_dictionary_F_day02_small_seq(self):
        """Test generating dictionary for Female, Day 02"""
        # Gender F -> even sequences (0, 2, 4...)
        # max_seq=3 -> sequences 0,1,2 -> only 0, 2 are even.
        # 2 sequences * 10 check digits = 20 passwords.
        count = generate_dictionary_file(
            self.temp_path, gender="F", specific_day="02", max_seq=3
        )
        self.assertEqual(count, 20)

        with open(self.temp_path, "r") as f:
            lines = f.readlines()

        self.assertEqual(lines[0].strip(), "F_02,020000")  # seq 0, check 0

    def test_load_tasks_no_progress(self):
        """Test loading tasks without any progress map (start from scratch)"""
        generate_dictionary_file(
            self.temp_path, gender="M", specific_day="01", max_seq=2
        )
        # max_seq=2, M (odd) -> seq 1 only. 10 passwords.

        tasks = list(load_tasks_from_file(self.temp_path, progress_map={}))
        self.assertEqual(len(tasks), 10)
        self.assertEqual(tasks[0], ("010010", "M_01"))

    def test_load_tasks_with_progress(self):
        """Test loading tasks skipping already done ones"""
        generate_dictionary_file(
            self.temp_path, gender="M", specific_day="01", max_seq=4
        )
        # max_seq=4, M -> seq 1, 3.
        # seq 1 -> 01001[0-9]
        # seq 3 -> 01003[0-9]
        # Total 20 tasks.

        # Let's say we finished up to 010015
        progress = {"M_01": "010015"}

        tasks = list(load_tasks_from_file(self.temp_path, progress_map=progress))

        # Should skip 010010 ... 010015.
        # Should include 010016 ... 010019 (4 tasks)
        # Should include 010030 ... 010039 (10 tasks)
        # Total 14 tasks expected.
        self.assertEqual(len(tasks), 14)
        self.assertEqual(tasks[0][0], "010016")

    def test_load_tasks_progress_completed_day(self):
        """Test behavior when progress indicates day is done (or points to last item)"""
        generate_dictionary_file(
            self.temp_path, gender="M", specific_day="01", max_seq=2
        )
        # seq 1 only. 010010...010019

        # Progress at last item
        progress = {"M_01": "010019"}
        tasks = list(load_tasks_from_file(self.temp_path, progress_map=progress))
        self.assertEqual(len(tasks), 0)


if __name__ == "__main__":
    unittest.main()
