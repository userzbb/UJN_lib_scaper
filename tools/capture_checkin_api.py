#!/usr/bin/env python3
"""
UJN 图书馆 - 签到 API 抓包脚本
专门用于捕获签到 (checkIn) API

uv run python tools/capture_checkin_api.py
"""

import json
import time
from playwright.sync_api import sync_playwright

BASE_URL = "https://seat.ujn.edu.cn"


def capture_checkin_api():
    print("UJN 图书馆签到 API 抓包")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        captured = []

        def on_request(request):
            if BASE_URL not in request.url:
                return
            if request.resource_type in ["image", "stylesheet", "font", "media"]:
                return
            captured.append(
                {
                    "url": request.url,
                    "method": request.method,
                    "headers": dict(request.headers),
                    "post_data": request.post_data,
                    "resource_type": request.resource_type,
                }
            )

        def on_response(response):
            if BASE_URL not in response.url:
                return
            try:
                body = response.text()
            except:
                body = ""
            for item in captured:
                if item["url"] == response.url:
                    item["status"] = response.status
                    item["response_body"] = body[:1000] if body else ""
                    break

        page.on("request", on_request)
        page.on("response", on_response)

        print(f"打开登录页: {BASE_URL}/libseat/#/login")
        page.goto(f"{BASE_URL}/libseat/#/login")
        page.wait_for_load_state("networkidle", timeout=10000)

        print("\n请手动操作:")
        print("1. 登录账号")
        print("2. 进入'我的预约'页面")
        print("3. 点击'签到'按钮")
        print("\n60秒后自动分析...")

        time.sleep(60)

        print(f"\n共捕获 {len(captured)} 个请求")

        rest_apis = [c for c in captured if "/rest/" in c["url"]]
        print(f"其中 {len(rest_apis)} 个 /rest/ API\n")

        for i, api in enumerate(rest_apis, 1):
            print(f"--- API #{i} ---")
            print(f"URL: {api['url']}")
            print(f"Method: {api['method']}")
            print(f"Status: {api.get('status', 'N/A')}")

            if "check" in api["url"].lower() or "sign" in api["url"].lower():
                print("*** 可能是签到相关 ***")

            if api.get("post_data"):
                print(f"POST Data: {api['post_data']}")

            if api.get("response_body"):
                print(f"Response: {api['response_body'][:300]}")
            print()

        with open("captured_checkin_apis.json", "w", encoding="utf-8") as f:
            json.dump(rest_apis, f, indent=2, ensure_ascii=False)
        print("已保存到 captured_checkin_apis.json")

        input("按回车退出...")
        browser.close()


if __name__ == "__main__":
    capture_checkin_api()
