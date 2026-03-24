#!/usr/bin/env python3
import json
import time
from playwright.sync_api import sync_playwright

BASE_URL = "https://seat.ujn.edu.cn"


def capture_all_apis():
    print("UJN Library API 捕货 - 网络请求监听版")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        captured = []

        def handle_request(request):
            if BASE_URL not in request.url:
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

        def handle_response(response):
            if BASE_URL not in response.url:
                return
            try:
                body = response.text()
            except:
                body = ""
            for item in captured:
                if item["url"] == response.url:
                    item["status"] = response.status
                    item["response_body"] = body[:500] if body else ""
                    break

        page.on("request", handle_request)
        page.on("response", handle_response)

        print(f"打开: {BASE_URL}/libseat/#/login")
        page.goto(f"{BASE_URL}/libseat/#/login")
        page.wait_for_load_state("networkidle", timeout=10000)

        print("等待30秒，请手动操作页面执行预约/签到...")
        print("(这期间请: 登录 -> 选择座位 -> 点击预约)")
        time.sleep(30)

        print(f"\n共捕获 {len(captured)} 个请求")

        apis = [c for c in captured if "/rest/" in c["url"]]
        print(f"其中 {len(apis)} 个 /rest/ API 请求\n")

        for i, api in enumerate(apis, 1):
            print(f"--- API #{i} ---")
            print(f"URL: {api['url']}")
            print(f"Method: {api['method']}")
            print(f"Status: {api.get('status', 'N/A')}")
            print(
                "Headers:",
                json.dumps(api["headers"], indent=2, ensure_ascii=False)[:300],
            )
            if api.get("post_data"):
                print(f"POST Data: {api['post_data']}")
            if api.get("response_body"):
                print(f"Response: {api['response_body'][:200]}")
            print()

        with open("captured_apis.json", "w", encoding="utf-8") as f:
            json.dump(apis, f, indent=2, ensure_ascii=False)
        print("已保存到 captured_apis.json")

        input("按回车退出...")
        browser.close()


if __name__ == "__main__":
    capture_all_apis()
