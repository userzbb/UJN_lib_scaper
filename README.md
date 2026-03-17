# UJN Library Seat Reservation Cracker & Auto-Booker

[![Project Status: Active](https://img.shields.io/badge/Status-Active-brightgreen)](https://github.com/zizimiku/UJN_lib_scaper)
[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

这是一个针对 **济南大学图书馆座位预约系统 (UJN Library Seat System)** 的综合性安全测试与自动化工具集。

本项目经历了从 **Web 自动化 (Selenium/Playwright)** 到 **逆向工程 (Reverse Engineering)** 再到 **纯协议层高并发爆破 (HTTP Protocol)** 的完整演进过程。

---

## 🚀 核心功能 (Features)

### 1. 极速密码爆破 (High-Performance Cracker)
- **纯 HTTP 协议实现**: 摆脱浏览器资源限制，单机轻松支持 **128+ 线程**。
- **速度**: 约 **50-100 次尝试/秒** (取决于 OCR 速度，是浏览器版的 100 倍)。
- **智能策略**:
  - 自动识别验证码 (`ddddocr`)。
  - 自动处理 AES 加密与 HMAC-SHA256 签名。
  - 错误自动重试与账号锁定保护。
  - 支持 **断点续传** (基于 SQLite 数据库)。

### 2. 自动化预约 (Auto Booker)
- 基于 `Playwright` 的全自动座位预约。
- 支持自定义阅览室、座位号、时间段。
- 自动处理登录验证码。

---

## 🛠️ 技术演进与逆向过程 (Reverse Engineering Journey)

本项目的开发过程是一次典型的从“模拟”到“对抗”的技术升级。

### 第一阶段：浏览器模拟 (Browser Automation)
最初，我们使用 `Playwright` 模拟用户行为。
- **方案**: 启动 Chromium -> 输入账号密码 -> 截图验证码 -> OCR 识别 -> 点击登录。
- **局限**: 内存占用极大，启动慢，并发无法超过 10 个进程，爆破效率极低 (约 0.5 次/秒)。

### 第二阶段：多进程并发 (Multi-Process Manager)
为了解决速度问题，我们开发了 `crack_manager.py`。
- **方案**: 编写调度器，按“日期” (01-31) 将任务分发给多个 `crack_login.py` 进程。
- **提升**: 速度提升至 3-5 次/秒，但受限于 CPU 和内存，无法进一步扩展。

### 第三阶段：逆向工程与协议破解 (The Breakthrough)
为了实现极致速度，我们决定抛弃浏览器，直接构造 HTTP 请求。这需要破解其加密与签名机制。

#### 1. 抓包分析
通过 `analyze_login.py` 监听网络请求，发现登录接口 `/rest/auth` 包含特殊的 Header：
- `username`/`password`: 密文 (Base64 + `_encrypt` 后缀)。
- `x-hmac-request-key`: 64位哈希签名。
- `x-request-id` / `x-request-date`: UUID 与时间戳。

#### 2. AES 加密破解
- **分析**: 在 `app.js` (Webpack bundle) 中定位到加密函数。
- **发现**: 使用 AES-128-CBC 算法。
- **验证**: 编写 `decrypt_numcode.py` 成功解密了抓包到的密码密文。

#### 3. HMAC 签名破解 (核心难点)
- **分析**: 发现 Header 中的签名由 `hmac-sha256` 生成。
- **消息格式**: `seat::<UUID>::<Timestamp>::GET`。
- **密钥难题**: 密钥变量名为 `$NUMCODE`，但在静态代码中找不到真实值。
- **动态提取**: 编写 `extract_runtime_secret.py`，使用 Playwright 注入 JS 代码，在页面加载完成后直接从 `Vue.prototype` 读取运行时变量。
  - **提取结果**: `UmrX+lxhFE5neclEsBPing==` (加密的 Base64)。
- **最终解密**: 使用之前的 AES Key 对其解密，得到真实 HMAC Secret。

### 🔓 核心密钥一览 (Discovered Secrets)

| 密钥类型 | 变量名/用途 | 值 (Value) | 备注 |
| :--- | :--- | :--- | :--- |
| **HMAC Secret** | `$NUMCODE` | **`ujnLIB2022tsg`** | 用于请求签名 (核心) |
| **AES Key** | `server_date_time` | `server_date_time` | 密码加密 Key |
| **AES IV** | `client_date_time` | `client_date_time` | 密码加密 IV |

### 第四阶段：纯 HTTP 爆破 (Pure HTTP)
基于以上成果，开发了 **`crack_login_http.py`**，实现了无需浏览器的毫秒级请求，彻底解决了性能瓶颈。

---

## 📦 安装与配置 (Installation)

本项目推荐使用 [uv](https://github.com/astral-sh/uv) 进行依赖管理，它比 pip 更快且兼容性更好。

### 1. 环境准备
确保已安装 Python 3.12+。

```bash
# 安装 uv (如果未安装)
pip install uv
```

### 2. 安装依赖
```bash
# 使用 uv 同步依赖
uv sync
```

或者使用传统的 pip:
```bash
pip install -r requirements.txt
# 核心依赖: playwright, ddddocr, pycryptodome, requests
```

---

## 💻 使用指南 (Usage)

### 1. 极速爆破 (推荐)

使用 `crack_login_http.py` 进行身份证后六位爆破。

**命令格式**:
```bash
uv run crack_login_http.py <学号> -g <M/F> -t <线程数>
```

**参数说明**:
- `<学号>`: 目标用户的学号。
- `-g`: 性别 (Gender)。`M`=男 (最后一位奇数), `F`=女 (最后一位偶数)。**必选**，这能减少一半的尝试量。
- `-t`: 线程数。推荐 `64` 或 `128`。
- `-d`: (可选) 指定只跑某一天的日期 (如 `08`)，用于分布式或测试。

**示例**:
```bash
# 爆破学号 20230001，男生，使用 64 线程
uv run crack_login_http.py 20230001 -g M -t 64

# 爆破学号 20230002，女生，只跑 15 号的数据
uv run crack_login_http.py 20230002 -g F -d 15
```

### 2. 自动化预约 (Auto Booking)

使用 `auto_book.py` 进行座位预约。

```bash
uv run auto_book.py
```
*注意: 需先在代码中配置好账号密码和目标座位。*

### 3. 辅助工具

- **`crack_manager.py`**: 旧版的多进程浏览器调度器 (已废弃，仅供参考)。
- **`analyze_login.py`**: 用于抓包分析登录接口的工具。
- **`extract_runtime_secret.py`**: 用于提取 HMAC 密钥的工具。

---

## 📊 数据库结构 (Database)

程序会自动在当前目录创建 `crack.db` (SQLite)，包含两张表：

1.  **`crack_progress_detail`**: 记录进度。
    -   `username`, `day_prefix`: 联合主键。
    -   `last_tried_password`: 该日期下最后一次尝试失败的密码。
    -   *作用*: 程序中断后，下次运行会自动读取此表，跳过已尝试的密码。

2.  **`found_passwords`**: 记录结果。
    -   `username`: 学号。
    -   `password`: 破解成功的密码。
    -   `found_at`: 破解时间。

---

## ⚠️ 免责声明 (Disclaimer)

1.  **仅供学习研究**: 本项目旨在研究网络安全、逆向工程与自动化技术。请勿用于非法用途。
2.  **遵守规定**: 请遵守济南大学网络使用规范，不要对服务器造成过大压力。
3.  **账号安全**: 爆破测试仅限用户授权的账号，或用于找回自己遗忘的密码。

---

## 📝 作者 (Author)

**Zizimiku**