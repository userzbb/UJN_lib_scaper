import base64
import threading

import ddddocr

from src.config import CAPTCHA_API

# Thread-local storage for OCR engines
thread_local = threading.local()


def get_ocr_engine():
    """Get or create a thread-local OCR engine"""
    if not hasattr(thread_local, "engine"):
        # Initialize one engine per thread
        thread_local.engine = ddddocr.DdddOcr(show_ad=False, old=True)
    return thread_local.engine


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

    except Exception:
        return None, None
