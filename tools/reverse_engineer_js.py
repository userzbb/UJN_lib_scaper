# -*- coding: utf-8 -*-
import re
import time

from playwright.sync_api import sync_playwright


def reverse_engineer_js():
    print("启动浏览器进行 JS 逆向分析...")
    print("目标: 寻找 '_encrypt' 和 'x-hmac-request-key' 的生成逻辑")

    # 关键搜索词
    KEYWORDS = [
        r"_encrypt",
        r"x-hmac-request-key",
        r"rest/auth",
        r"password:",  # 查找构建 payload 的地方
        r"AES",
        r"RSA",
        r"encrypt",
        r"HMAC",
    ]

    captured_js_urls = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 监听请求，捕获 JS 文件
        def on_request(req):
            if req.resource_type == "script" or req.url.endswith(".js"):
                captured_js_urls.add(req.url)

        page.on("request", on_request)

        print("正在打开页面: https://seat.ujn.edu.cn/libseat/#/login")
        try:
            page.goto("https://seat.ujn.edu.cn/libseat/#/login", timeout=60000)
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception as e:
            print(f"页面加载可能超时，但继续分析已捕获的资源: {e}")

        # 给一点时间让动态 JS 加载
        time.sleep(3)

        print(f"共捕获 {len(captured_js_urls)} 个 JS 文件。开始分析...")
        print("=" * 50)

        for url in captured_js_urls:
            try:
                # 获取 JS 内容
                # 使用 page.request.get(url) 获取内容，这样利用了浏览器的上下文（Cookie等虽然这里可能不需要）
                resp = page.request.get(url)
                if resp.status != 200:
                    continue

                content = resp.text()

                # 检查每个关键词
                found_in_file = False
                for kw in KEYWORDS:
                    # 使用正则查找，并获取上下文
                    matches = list(re.finditer(kw, content, re.IGNORECASE))
                    if matches:
                        if not found_in_file:
                            print(f"\n📄 分析文件: {url}")
                            found_in_file = True

                        print(f"  --> 发现关键词: '{kw}' ({len(matches)} 次)")

                        # 打印第一个匹配的上下文（前后 100 字符）
                        m = matches[0]
                        start = max(0, m.start() - 100)
                        end = min(len(content), m.end() + 100)
                        snippet = (
                            content[start:end].replace("\n", " ").replace("\r", "")
                        )
                        print(f"      上下文: ...{snippet}...\n")

            except Exception as e:
                print(f"无法分析 {url}: {e}")

        print("=" * 50)
        print("分析完成。")
        browser.close()


if __name__ == "__main__":
    reverse_engineer_js()
