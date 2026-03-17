import logging
import queue
import sqlite3
import time
from datetime import datetime

from src.config import DB_FILE

logger = logging.getLogger("HTTP_Cracker")


def init_db():
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS found_passwords (
        username TEXT PRIMARY KEY,
        password TEXT,
        found_at TIMESTAMP
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS crack_progress_detail (
        username TEXT,
        day_prefix TEXT,
        last_tried_password TEXT,
        updated_at TIMESTAMP,
        PRIMARY KEY (username, day_prefix)
    )
    """)
    conn.commit()
    return conn


def get_progress_map(conn, username):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT day_prefix, last_tried_password FROM crack_progress_detail WHERE username = ?",
        (username,),
    )
    return {row[0]: row[1] for row in cursor.fetchall()}


def save_success(username, password):
    # Save to CSV
    try:
        # Check if already exists in CSV to avoid duplicates
        csv_path = "found_passwords.csv"
        already_exists = False
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith(f"{username},"):
                        already_exists = True
                        break
        except FileNotFoundError:
            pass

        if not already_exists:
            with open(csv_path, "a", encoding="utf-8") as f:
                f.write(f"{username},{password}\n")
    except Exception as e:
        logger.error(f"CSV Error saving success: {e}")

    # Save to DB
    try:
        with sqlite3.connect(DB_FILE, timeout=10.0) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
            INSERT OR REPLACE INTO found_passwords (username, password, found_at)
            VALUES (?, ?, ?)
            """,
                (username, password, datetime.now().isoformat()),
            )
            conn.commit()
    except Exception as e:
        logger.error(f"DB Error saving success: {e}")


def db_updater_loop(progress_queue):
    """Background thread to batch update progress"""
    logger.info("DB Updater thread started.")
    # Use a separate connection for this thread
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    cursor = conn.cursor()

    pending_updates = {}  # (username, day) -> password
    last_commit = time.time()

    while True:
        try:
            try:
                # Wait for items
                item = progress_queue.get(timeout=0.5)

                # Sentinel check
                if item is None:
                    logger.info("DB Updater received sentinel. Flushing and exiting.")
                    break

                username, day, password = item

                # High-water mark logic: only update if password is lexically larger
                # This prevents regression in progress if threads finish out of order
                key = (username, day)
                if key not in pending_updates or password > pending_updates[key]:
                    pending_updates[key] = password

            except queue.Empty:
                # If stop_event is set AND we haven't received sentinel yet,
                # we just wait. Main is responsible for sending sentinel.
                pass

            # Commit if batch is large enough or time has passed
            current_time = time.time()
            if len(pending_updates) > 0 and (
                len(pending_updates) > 50 or (current_time - last_commit > 2.0)
            ):
                try:
                    data = [
                        (u, d, p, datetime.now().isoformat())
                        for (u, d), p in pending_updates.items()
                    ]
                    cursor.executemany(
                        """
                        INSERT OR REPLACE INTO crack_progress_detail
                        (username, day_prefix, last_tried_password, updated_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        data,
                    )
                    conn.commit()
                    logger.info(
                        f"Saved progress for {len(pending_updates)} items to DB."
                    )
                    pending_updates.clear()
                    last_commit = current_time
                except Exception as e:
                    logger.error(f"DB Batch Update Error: {e}")

        except Exception as e:
            logger.error(f"DB Updater Loop Error: {e}")
            time.sleep(1)

    # Final commit on exit
    if pending_updates:
        try:
            data = [
                (u, d, p, datetime.now().isoformat())
                for (u, d), p in pending_updates.items()
            ]
            cursor.executemany(
                """
                INSERT OR REPLACE INTO crack_progress_detail
                (username, day_prefix, last_tried_password, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                data,
            )
            conn.commit()
            logger.info(
                f"Final progress save completed. ({len(pending_updates)} items)"
            )
        except Exception as e:
            logger.error(f"Final DB Save Error: {e}")
    conn.close()
    logger.info("DB Updater thread exited.")
