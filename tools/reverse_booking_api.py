#!/usr/bin/env python3
import re
import time
from playwright.sync_api import sync_playwright


def analyze_booking_js():
    print("JS逆向分析 - 寻找预约/签到API")
    print("=" * 60)

    API_PATTERNS = [
        r'["\']/(?:rest|api)/[a-zA-Z/]+(?:book|reserve|sign|check|cancel)',  # 包含关键词的API
        r'endpoint["\']\s*:\s*["\'][^"\']+["\']',
        r'url["\']\s*:\s*["\'][^"\']+["\']',
        r'path["\']\s*:\s*["\'][^"\']+["\']',
        r'\.(?:post|get)\(["\'][^"\']+["\']',
        r"axios\.(?:post|get)\([^)]+\)",
        r"fetch\([^)]+\)",
    ]

    KEYWORDS = [
        "freeBook",
        "book",
        "reserve",
        "signIn",
        "checkIn",
        "cancel",
        "reservation",
        "seat",
        "room",
        "layout",
        "startTime",
        "endTime",
        "/rest/",
        "/api/",
        "baseURL",
        "BASE_URL",
        "createSeat",
        "selectSeat",
        "confirmBook",
        "doBook",
    ]

    captured_js = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        js_urls = set()

        def on_request(req):
            if req.resource_type == "script" or req.url.endswith(".js"):
                js_urls.add(req.url)

        page.on("request", on_request)

        print("🌐 打开预约页面...")
        page.goto("https://seat.ujn.edu.cn/libseat/#/login", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=10000)
        time.sleep(3)

        # 尝试导航到预约相关页面
        try:
            page.goto("https://seat.ujn.edu.cn/libseat/#/self", timeout=10000)
            time.sleep(2)
        except:
            pass

        print(f"📦 捕获 {len(js_urls)} 个 JS 文件\n")

        for url in js_urls:
            try:
                resp = page.request.get(url)
                if resp.status != 200:
                    continue

                content = resp.text()

                for kw in KEYWORDS:
                    if kw.lower() in content.lower():
                        if url not in captured_js:
                            captured_js[url] = []
                        captured_js[url].append(kw)
            except:
                continue

        browser.close()

    print("发现包含关键词的JS文件:")
    print("=" * 60)

    for url, keywords in captured_js.items():
        print(f"\n📄 {url}")
        print(f"   关键词: {', '.join(set(keywords))}")

    if captured_js:
        target_url = list(captured_js.keys())[0]
        print(f"\n正在分析第一个文件: {target_url}")

        try:
            import urllib.request

            resp = urllib.request.urlopen(target_url, timeout=10)
            content = resp.read().decode("utf-8", errors="ignore")

            print("\n--- 搜索 API 路径 ---")
            for pattern in API_PATTERNS[:3]:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    print(f"  模式 {pattern[:30]}...: {len(matches)} 处匹配")
                    for m in matches[:5]:
                        print(f"    {m[:100]}")

            print("\n--- 搜索完整URL ---")
            url_pattern = r'["\']https?://[^"\']+(?:rest|api)[^"\']*["\']'
            urls = re.findall(url_pattern, content, re.IGNORECASE)
            for u in urls[:10]:
                print(f"  {u}")

            print("\n--- 搜索相对路径 ---")
            path_pattern = r'["\'](/[a-zA-Z0-9/_-]+){2,6}["\']'
            paths = re.findall(path_pattern, content)
            for p in paths[:20]:
                print(f"  {p}")

        except Exception as e:
            print(f"  获取失败: {e}")


if __name__ == "__main__":
    analyze_booking_js()
