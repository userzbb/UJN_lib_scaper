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
    if len(sys.argv) < 3:
        print("用法: uv run python tools/full_api_test.py <学号> <密码>")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]

    print(f"UJN 图书馆 API 全自动测试 - {username}")
    print("=" * 60)

    sess = requests.Session()

    print("\n[1] 获取验证码...")
    resp = sess.get(CAPTCHA_API, timeout=10)
    data = resp.json()
    captcha_id = data.get("captchaId")
    img_b64 = data.get("captchaImage", "").split(",")[-1]
    print(f"    CaptchaId: {captcha_id}")

    code = solve_captcha(img_b64)
    print(f"    OCR识别: {code}")

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
    print(f"    Status: {resp.status_code}")
    print(f"    Response: {resp.text[:400]}")

    if result.get("status") != "success":
        print(f"    登录失败: {result.get('message')}")
        sys.exit(1)

    token = result.get("data", {}).get("token", "")
    print(f"    ✅ 登录成功! Token: {token[:30]}..." if token else "    ✅ 登录成功!")

    sess.headers.update({"token": token})

    print("\n[3] 测试各 API...")

    tests = [
        ("GET", "/rest/filters", None),
        ("GET", "/rest/user", None),
        ("GET", "/rest/reservations", None),
        ("GET", "/rest/rooms", None),
        ("GET", "/rest/dates", None),
    ]

    for method, path, data in tests:
        url = BASE_URL + path
        headers = generate_headers(method)
        if token:
            headers["token"] = token

        try:
            r = (
                sess.get(url, headers=headers, timeout=10)
                if method == "GET"
                else sess.post(url, headers=headers, json=data, timeout=10)
            )
            print(f"\n    {method} {path}")
            print(f"    Status: {r.status_code}")
            print(f"    Response: {r.text[:400]}")
        except Exception as e:
            print(f"    Error: {e}")


if __name__ == "__main__":
    main()
