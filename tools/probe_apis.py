#!/usr/bin/env python3
import sys
import base64
import ddddocr

sys.path.insert(0, ".")
from src.utils.crypto import generate_headers, encrypt_aes
import requests

BASE_URL = "https://seat.ujn.edu.cn"
CAPTCHA_API = f"{BASE_URL}/auth/createCaptcha"
LOGIN_API = f"{BASE_URL}/rest/auth"

ocr = ddddocr.DdddOcr(show_ad=False, old=True)


def solve_captcha(img_b64):
    img_data = base64.b64decode(img_b64)
    code = ocr.classification(img_data)
    return code if isinstance(code, str) else code.get("text", "")


def main():
    username = "202331223125"
    password = "080518"

    print(f"UJN 图书馆 API 探测 - {username}")
    print("=" * 60)

    sess = requests.Session()

    print("\n[1] 获取验证码...")
    resp = sess.get(CAPTCHA_API, timeout=10)
    data = resp.json()
    captcha_id = data.get("captchaId")
    img_b64 = data.get("captchaImage", "").split(",")[-1]

    code = solve_captcha(img_b64)
    print(f"    OCR: {code}")

    print("\n[2] 登录...")
    headers = generate_headers("GET")
    headers["username"] = encrypt_aes(username)
    headers["password"] = encrypt_aes(password)

    resp = sess.get(
        LOGIN_API,
        headers=headers,
        params={"captchaId": captcha_id, "answer": code},
        timeout=10,
    )
    result = resp.json()

    token = result.get("data", {}).get("token", "")
    print(f"    ✅ Token: {token[:30]}...")

    print("\n[3] 探测 API 路径...")

    # 可能的 API 路径
    paths = [
        "/rest/v2/free/filters",
        "/rest/v2/filters",
        "/rest/v2/user",
        "/rest/v2/checkIn",
        "/rest/v2/user/reservations",
        "/rest/v2/freeBook",
        "/rest/v2/room/stats2/2",
        "/rest/v2/room/layoutByDate/19/2024-03-25/",
        "/rest/v2/startTimesForSeat/1234/2024-03-25",
        "/rest/v2/history/1/10",
        "/rest/v2/cancel/123456",
        "/rest/v2/dates",
        "/rest/v2/rooms",
        "/libseat/rest/filters",
        "/libseat/rest/user",
        "/api/filters",
        "/api/user",
        "/api/reservations",
    ]

    working_apis = []

    for path in paths:
        url = BASE_URL + path
        headers = generate_headers("GET")
        if token:
            headers["token"] = token

        try:
            r = sess.get(url, headers=headers, timeout=5)
            resp_text = r.text[:200]

            if r.status_code == 200 and "fail" not in resp_text.lower()[:50]:
                print(f"    ✅ {path} -> {r.status_code}")
                working_apis.append((path, resp_text))
            elif r.status_code != 404:
                print(f"    ⚠️  {path} -> {r.status_code} (可能是登录相关)")
                working_apis.append((path, resp_text))
            else:
                print(f"    ❌ {path} -> 404")
        except Exception as e:
            print(f"    ❌ {path} -> Error: {e}")

    print("\n" + "=" * 60)
    print(f"发现 {len(working_apis)} 个可能工作的 API:")
    for path, resp in working_apis:
        print(f"\n--- {path} ---")
        print(resp[:400])


if __name__ == "__main__":
    main()
