import os
import queue
import sqlite3
import tempfile
import unittest
from unittest.mock import mock_open, patch

# We import the functions to test
from src.core.database import (
    db_updater_loop,
    get_progress_map,
    init_db,
    save_success,
)


class TestDatabase(unittest.TestCase):
    def setUp(self):
        # Create a temp file for DB
        self.db_fd, self.db_path = tempfile.mkstemp()
        os.close(self.db_fd)

        # Patch the DB_FILE variable inside src.core.database
        self.config_patcher = patch("src.core.database.DB_FILE", self.db_path)
        self.mock_db_file = self.config_patcher.start()

    def tearDown(self):
        self.config_patcher.stop()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_init_db(self):
        """Test that init_db creates the correct tables."""
        conn = init_db()
        cursor = conn.cursor()

        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cursor.fetchall()}
        self.assertIn("found_passwords", tables)
        self.assertIn("crack_progress_detail", tables)
        conn.close()

    def test_save_success_db(self):
        """Test that save_success writes to the database."""
        init_db()  # Create tables first

        # Mock file operations to prevent writing real CSV
        with patch("builtins.open", mock_open()) as mocked_file:
            save_success("user123", "pass123")

        # Verify DB insertion
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password FROM found_passwords WHERE username=?", ("user123",)
        )
        result = cursor.fetchone()
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "pass123")
        conn.close()

    def test_progress_tracking(self):
        """Test retrieving progress map from DB."""
        conn = init_db()
        cursor = conn.cursor()

        # Insert some fake progress
        cursor.execute(
            "INSERT INTO crack_progress_detail (username, day_prefix, last_tried_password, updated_at) VALUES (?, ?, ?, ?)",
            ("user1", "M_01", "010010", "2023-01-01"),
        )
        conn.commit()

        progress = get_progress_map(conn, "user1")
        self.assertEqual(progress.get("M_01"), "010010")

        # Check different user
        progress2 = get_progress_map(conn, "user2")
        self.assertEqual(progress2, {})
        conn.close()

    def test_db_updater_loop(self):
        """Test the background updater thread logic."""
        init_db()

        q = queue.Queue()
        # Add tasks
        q.put(("user1", "M_01", "010010"))
        q.put(("user1", "M_01", "010020"))  # Should overwrite previous for M_01
        q.put(("user1", "F_02", "020005"))
        q.put(None)  # Sentinel to stop the loop

        # Run updater (it should exit after sentinel)
        db_updater_loop(q)

        # Verify DB state
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT last_tried_password FROM crack_progress_detail WHERE username=? AND day_prefix=?",
            ("user1", "M_01"),
        )
        res_m = cursor.fetchone()
        self.assertEqual(
            res_m[0], "010020"
        )  # Should be the latest one (lexically larger)

        cursor.execute(
            "SELECT last_tried_password FROM crack_progress_detail WHERE username=? AND day_prefix=?",
            ("user1", "F_02"),
        )
        res_f = cursor.fetchone()
        self.assertEqual(res_f[0], "020005")

        conn.close()


if __name__ == "__main__":
    unittest.main()
