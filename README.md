# UJN Library Seat Reservation Cracker & Auto-Booker

[![Project Status: Active](https://img.shields.io/badge/Status-Active-brightgreen)](https://github.com/zizimiku/UJN_lib_scaper)
[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

这是一个针对 **济南大学图书馆座位预约系统 (UJN Library Seat System)** 的综合性安全测试与自动化工具集。

本项目经历了从 **Web 自动化 (Selenium/Playwright)** 到 **逆向工程 (Reverse Engineering)** 再到 **纯协议层高并发爆破 (HTTP Protocol)** 的完整演进过程。

📖 **深度阅读**:
- [API 文档 (API.md)](docs/API.md) —— 完整的 API 端点说明、验证结果、密钥和时间格式
- [预约使用指南 (BOOKING.md)](docs/BOOKING.md) —— booking 模块使用说明、功能状态、已知问题
- [项目进度 (PROGRESS.md)](docs/PROGRESS.md) —— 开发进度记录、阻塞点分析
- [技术演进与逆向工程实录 (DEV_JOURNEY.md)](docs/DEV_JOURNEY.md) —— 了解本项目如何一步步突破反爬限制
- [爆破逻辑与进度管理机制 (CRACKING_LOGIC.md)](docs/CRACKING_LOGIC.md) —— 了解断点续传与任务调度的实现细节

> **⚠️ 最新更新 (v2.0 Refactored)**:
> 项目已完成重构，引入了 **智能断点续传**、**自适应流控** 和 **模块化架构**，大幅提升了稳定性和易用性。

---

## 🚀 核心功能 (Features)

### 1. ⚡ 极速 HTTP 爆破 (High-Performance Cracker)
- **纯 HTTP 协议实现**: 摆脱浏览器资源限制，单机轻松支持 **64+ 线程**。
- **速度**: 约 **50-100 次尝试/秒** (取决于 OCR 速度，是浏览器版的 100 倍)。
- **智能策略**:
  - **自动识别验证码**: 集成 `ddddocr` 离线识别模型。
  - **全自动加密签名**: 自动处理 AES 加密与 HMAC-SHA256 请求签名。

### 2. 🔄 智能断点续传 (State-Aware Resuming)
- **数据库驱动**: 所有进度实时保存至 `crack.db` (SQLite)。
- **自动恢复**: 程序意外中断（如 Ctrl+C、网络断开）后，下次运行会自动读取数据库，**跳过已测试的密码**，从断点处继续执行。
- **状态感知**: 能够区分 "验证码错误"（重试）与 "密码错误"（推进进度），确保不漏测。

### 3. 🛡️ 自适应流控与稳定性 (Adaptive Throttling)
- **智能避让**: 自动检测服务器 `429 Too Many Requests` 或 "操作频繁" 提示，并触发指数退避 (Exponential Backoff)。
- **错误容忍**: 网络波动或代理失败时会自动重试，超过阈值（默认 15 次）才放弃该密码，防止线程卡死。

### 4. 🤖 自动化预约辅助 (Auto Booker)
- 基于 `Playwright` 的**半自动**座位预约辅助。
- 自动化登录（可绕过登录验证码），辅助选座，但**预约提交仍需人工操作**。
- ⚠️ **未破解**: 预约时的中文点选验证码无法绕过，需手动完成。

### 5. 📱 预约签到模块 (Booking Module) [新增]
- 纯 Python 实现的预约辅助工具 (`booking/`)
- **可用功能**: 查看阅览室、查看预约列表、取消预约
- **⚠️ 受限功能**: 签到(API不可用)、新预约(需中文点选验证码，无法破解)

---

## 🛠️ 技术架构 (Architecture)

本项目采用模块化设计，核心逻辑位于 `src/` 目录下：

```text
UJN_lib_scaper/
├── 🚀 入口脚本
│   ├── crack_login_http.py       # [主程序] 极速 HTTP 爆破入口
│   ├── auto_book.py              # [辅助] Playwright 自动化预约脚本
│
├── 📦 核心源码 (src/)
│   ├── main.py                   # 调度主逻辑 (生成字典 -> 过滤任务 -> 线程池)
│   ├── config.py                 # 全局配置 (API 地址, 密钥)
│   ├── core/
│   │   ├── generator.py          # 字典生成器 (支持按性别/日期生成)
│   │   ├── worker.py             # 工作线程 (登录逻辑, 重试策略)
│   │   └── database.py           # 数据库操作 (SQLite 读写)
│   └── utils/
│       ├── crypto.py             # 加密算法 (AES, HMAC)
│       └── captcha.py            # 验证码识别 (ddddocr)
│
├── 📱 预约签到模块 (booking/)      # [新增] 纯 Python 预约辅助
│   ├── main.py                   # CLI 入口
│   ├── client.py                 # API 客户端
│   ├── crypto.py                 # HMAC/AES 加密
│   ├── api.py                    # 端点常量
│   └── config.json               # 默认配置
│
├── 📄 文档 (Docs)
│   └── docs/
│       ├── API.md                # [新增] API 文档
│       ├── BOOKING.md            # [新增] 预约使用指南
│       ├── PROGRESS.md           # [新增] 项目进度
│       ├── DEV_JOURNEY.md        # 技术演进与逆向工程记录
│       └── CRACKING_LOGIC.md     # 爆破逻辑与进度管理说明
│
├── 📊 数据文件
│   ├── data/                     # [新增] 逆向 JS 文件
│   │   ├── app.js               # 应用主逻辑
│   │   └── vendor.js            # 第三方库
│   ├── crack.db                  # 进度数据库
│   └── found_passwords.csv       # 成功结果导出
```

---

## 📦 安装与配置 (Installation)

本项目推荐使用 [uv](https://github.com/astral-sh/uv) 进行依赖管理，它比 pip 更快且兼容性更好。

### 1. 安装 uv
推荐使用官方脚本安装（无需依赖 Python）：

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. 初始化项目环境
`uv` 会自动创建虚拟环境并安装所有依赖，无需手动激活环境。

```bash
# 1. 克隆项目
git clone https://github.com/zizimiku/UJN_lib_scaper.git
cd UJN_lib_scaper

# 2. 同步依赖 (自动创建 .venv)
uv sync

# 3. 安装 Playwright 浏览器内核 (首次运行必须)
uv run playwright install chromium
```

---

## 💻 使用指南 (Usage)

### 1. 极速 HTTP 爆破 (crack_login_http.py) [推荐]

这是本项目的核心工具，通过纯 HTTP 协议进行高并发密码测试。

**基本语法**:
```bash
uv run crack_login_http.py [学号] [选项]
```

**参数详解**:

| 参数 | 简写 | 说明 | 默认值 | 示例 |
| :--- | :--- | :--- | :--- | :--- |
| `username` | - | **(必选)** 目标学号 | - | `2023001` |
| `--gender` | `-g` | 性别，`M`=男, `F`=女, `ALL`=全部 | `ALL` | `-g F` |
| `--day` | `-d` | 指定只跑某一天 (01-31) | 全量 | `-d 08` |
| `--max-seq` | `-s` | **[新]** 每日最大出生序列号限制 | `500` | `-s 200` |
| `--threads` | `-t` | 线程数，建议 16-64 | `64` | `-t 32` |
| `--performance`| `-p` | **[新]** 启用长连接模式 (速度更快) | 关 | `-p` |

**使用示例**:

```bash
# 场景1: 默认模式 (爆破全部性别，全天日期，默认序列 0-500)
uv run crack_login_http.py 202331223001

# 场景2: 针对性爆破 (已知是男生，猜测出生在 15 号，缩小范围)
uv run crack_login_http.py 202331223001 -g M -d 15 -s 300

# 场景3: 稳定模式 (适合网络较差环境，降低线程数)
uv run crack_login_http.py 202331223001 -t 16

# 场景4: 🚀 高性能模式 (启用 Session 复用，追求极致速度)
uv run crack_login_http.py 202331223001 -g M -d 08 -p
```

### 💡 关于断点续传的说明

当你中断程序后再次运行，可能会看到类似如下的日志：

```text
[*] Resuming: Found progress for 5 days.
    (Skipping already tested passwords...)
Generating full candidate list: passwords_xxxx.txt ...
```

**解释**:
1. 程序首先生成完整的候选密码列表（这很快）。
2. 然后读取数据库中的进度记录。
3. 在分发任务时，**自动跳过**所有已经测试过的密码。
4. 进度条的 `Processed` 计数只包含**本次运行**实际测试的数量。

### ⚡ 关于高性能模式 (Performance Mode)

使用 `-p` 或 `--performance` 参数启用。

- **原理**: 线程会复用底层的 TCP/SSL 连接 (Keep-Alive)，避免了每次请求都进行昂贵的 SSL 握手。
- **优势**: 理论速度可提升 50%-100% (消除握手延迟)。
- **风险**: 可能会更容易触发服务器的频率限制 (Rate Limit)。如果遇到大量连接错误，请关闭此模式。

---

### 2. 自动化预约辅助 (auto_book.py)

登录成功后，使用此脚本进行半自动选座辅助。

**⚠️ 重要说明**: 此脚本**不能**全自动预约！它只能：
- ✅ 自动化完成登录（绕过登录验证码）
- ✅ 自动打开自选座位页面并选择阅览室和座位号
- ❌ 预约提交需人工点击确认（因为预约时的中文点选验证码无法破解）

**使用方法**:

1. **指定学号运行** (推荐):
   ```bash
   uv run auto_book.py 202331223125
   ```

2. **使用默认配置**:
   如果不带参数运行，脚本将使用代码中配置的默认学号 (默认为 `202331223111`)。
   ```bash
   uv run auto_book.py
   ```

脚本运行到座位选择后会暂停并提示 `脚本已暂停，请手动完成剩余步骤`，此时你需要人工完成验证码和确认操作。

**配置说明**:
如果需要修改默认阅览室 (`target_room`) 或座位号 (`seat_num`)，请直接编辑 `auto_book.py` 底部相关变量。

### 3. 预约签到工具 (booking/main.py) [新增]

纯 Python 实现的预约辅助模块，基于逆向的 API 调用，不依赖浏览器。

**⚠️ API 实际可用性**:

| 功能 | 命令 | API 端点 | 状态 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| 查看阅览室 | `--rooms` | `GET /rest/v2/free/filters` | ✅ 可用 | 列出所有阅览室 |
| 查看预约列表 | `--list` | `GET /rest/v2/user/reservations` | ✅ 可用 | 查看当前账号的预约 |
| 取消预约 | `--cancel <ID>` | `GET /rest/v2/cancel/{id}` | ✅ 可用 | 取消指定预约 |
| 签到 | `--checkin <ID>` | `GET /rest/v2/checkIn/{id}` | ❌ 不可用 | API 返回"请扫码"，服务器不支持 |
| 预约座位 | `--room --seat` | `POST /rest/v2/freeBook` | ❌ 不可用 | 需点击式中文验证码，无法绕过 |
| 查看座位布局 | (内部) | `GET /rest/v2/room/layoutByDate/{id}/{date}` | ✅ 可用 | 用于查找座位状态 |

**使用示例**:

```bash
# ✅ 场景1: 查看阅览室
uv run python booking/main.py 202331223125 --rooms

# ✅ 场景2: 查看我的预约
uv run python booking/main.py 202331223125 --list

# ✅ 场景3: 取消预约
uv run python booking/main.py 202331223125 --cancel 19971660

# ❌ 场景4: 签到 (不可用 - 服务器不支持)
uv run python booking/main.py 202331223125 --checkin 19971660

# ❌ 场景5: 预约座位 (不可用 - 需验证码)
uv run python booking/main.py 202331223125 --room 17 --seat 001
```

**⚠️ 为什么签到和预约功能实现不了？**

**1. 签到功能 - 服务器不支持 API 操作**
```
API响应: "请扫描小程序签到二维码或在触屏机上操作"
```
签到 API 的后端逻辑被**完全禁用**，服务器明确返回错误提示要求扫码。这是**后端架构设计**，不是验证码问题，无法绕过。

**2. 预约功能 - 需要点击式汉字验证码**

调用 `POST /rest/v2/freeBook` 时，服务器会返回：
```
{"status":"captcha","message":"需进行验证码操作","captchaType":"clickWords",...}
```

这是**点击式汉字验证码**（如：点击图片中所有"块"字），流程是：
1. 服务器下发一张包含多个汉字的图片
2. 附带文字提示（如"块"）
3. 用户需点击图片中所有匹配的汉字
4. 返回点击坐标后服务器验证

**为什么无法自动化？**
- ddddocr 只能识别字符，**无法理解语义**判断应该点击哪个字
- 每次验证码图片不同，汉字位置随机
- 即使识别出所有汉字，**坐标点击的精确度**也无法保证
- 这是专门设计来对抗自动化的，类似于 12306 的点选验证码

**结论**：签到是服务器禁用，预约是验证码对抗。目前唯一解法是**人工在浏览器中完成验证**。

如需半自动辅助预约，请使用上面的 **auto_book.py**，它可以帮你自动化登录和选座位。

---

## 🔍 进阶分析 (Advanced)

本项目包含一套用于逆向分析的工具集，位于 `tools/` 目录：

- **`tools/analyze_login.py`**:
  - 用途: 启动浏览器并监听网络请求，分析登录接口的 Header 和加密参数。
- **`tools/extract_runtime_secret.py`**:
  - 用途: 通过 Playwright 注入 JS，从内存中提取 HMAC 密钥 (`$NUMCODE`)。

### 核心密钥一览 (Discovered Secrets)

详见 [API 文档 - 密钥](docs/API.md#密钥)

| 密钥类型 | 值 | 备注 |
| :--- | :--- | :--- |
| **HMAC Secret** | `ujnLIB2022tsg` | 用于请求签名 |
| **AES Key** | `server_date_time` | 密码加密 |
| **AES IV** | `client_date_time` | 密码加密 |

---

## ⚠️ 免责声明 (Disclaimer)

1.  **仅供学习研究**: 本项目旨在研究网络安全、逆向工程与自动化技术。请勿用于非法用途。
2.  **遵守规定**: 请遵守济南大学网络使用规范，不要对服务器造成过大压力。
3.  **账号安全**: 爆破测试仅限用户授权的账号，或用于找回自己遗忘的密码。
4.  **预约限制**: 图书馆系统有签到和预约验证码机制，请遵守相关规定。

---

## 📝 作者 (Author)

**Zizimiku**