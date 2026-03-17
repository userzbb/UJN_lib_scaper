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

*或者如果已安装 Python，也可以通过 pip 安装：*
```bash
pip install uv
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
| `--threads` | `-t` | 线程数，建议 64-128 | `64` | `-t 128` |
| `--day` | `-d` | 指定只跑某一天 (01-31) | 全量 | `-d 08` |
| `--max-seq` | `-s` | 每日最大出生序列号限制 | `500` | `-s 200` |

**特性说明**:
- **进度保存**: 进度会自动保存为 `性别_日期` (如 `M_30`) 的格式，支持断点续传。
- **默认行为**: 若不指定 `-g`，脚本会同时爆破男女两个队列。

**使用示例**:

```bash
# 场景1: 默认模式 (爆破全部性别，全天日期)
uv run crack_login_http.py 202331223001

# 场景2: 只爆破男生账号，全速模式 (128线程)
uv run crack_login_http.py 202331223001 -g M -t 128

# 场景3: 只爆破女生账号，仅测试 '15' 号出生的密码
uv run crack_login_http.py 202331223002 -g F -d 15
```

---

### 2. 浏览器模拟爆破 (crack_login.py) [可视/调试]

旧版脚本，使用 Playwright 启动真实浏览器。适合调试或当 HTTP 脚本失效时作为备用。

**基本语法**:
```bash
uv run crack_login.py [学号] [选项]
```

**参数详解**:
| 参数 | 简写 | 说明 |
| :--- | :--- | :--- |
| `username` | - | **(必选)** 目标学号 |
| `--gender` | `-g` | 性别 (M/F)，默认 M |
| `--day` | `-d` | 指定日期 (01-31) |
| `--show` | - | 显示浏览器窗口 (默认无头模式) |

**使用示例**:
```bash
# 可视化运行 (能看到浏览器自动输入)
uv run crack_login.py 202331223001 -g M --show
```

---

### 3. 自动化预约 (auto_book.py)

登录成功后，使用此脚本进行自动选座。

**配置说明**:
此脚本目前暂不支持命令行参数，**需要手动修改脚本顶部的配置**：

1. 打开 `auto_book.py`
2. 修改 `USERNAME` 和 `PASSWORD` 变量：
   ```python
   # ================= 配置区域 =================
   USERNAME = "202331223065"  # 替换为你的学号
   PASSWORD = "080518"        # 替换为你的密码
   # ===========================================
   ```
3. (可选) 修改底部的阅览室名称 (`target_room`) 和座位号 (`seat_num`)。

**运行命令**:
```bash
uv run auto_book.py
```

---

### 4. 辅助分析工具

- **`analyze_login.py`**:
  - 用途: 启动浏览器并监听网络请求，分析登录接口的 Header 和加密参数。
  - 命令: `uv run analyze_login.py`
- **`extract_runtime_secret.py`**:
  - 用途: 通过 Playwright 注入 JS，从内存中提取 HMAC 密钥。
  - 命令: `uv run extract_runtime_secret.py`

---

## 📂 项目结构 (Project Structure)

```text
UJN_lib_scaper/
├── 🚀 核心工具 (Core Tools)
│   ├── crack_login_http.py       # [推荐] 极速 HTTP 爆破脚本 (128+ 线程, 纯协议实现)
│   ├── auto_book.py              # [推荐] 自动化座位预约脚本 (Playwright)
│   └── crack_login.py            # [旧版] 基于浏览器的爆破脚本 (单线程)
│
├── 🛠️ 逆向工程与辅助 (Reverse Engineering)
│   ├── analyze_login.py          # 登录接口抓包分析工具
│   ├── extract_runtime_secret.py # 运行时 HMAC 密钥提取工具 (Playwright 注入)
│   ├── decrypt_numcode.py        # AES 解密测试工具 (验证密钥有效性)
│   ├── verify_hmac.py            # HMAC 签名验证工具 (验证签名算法)
│   ├── find_captcha_endpoint.py  # 验证码 API 探测工具
│   └── reverse_engineer_js.py    # JS 静态分析扫描工具
│
├── 📦 数据与配置 (Data & Config)
│   ├── crack.db                  # SQLite 数据库 (存储爆破进度与结果)
│   ├── found_passwords.csv       # 成功破解的密码导出文件 (部分旧脚本生成)
│   ├── pyproject.toml            # uv 项目依赖配置
│   └── uv.lock                   # 依赖锁定文件
│
└── 🗑️ 其他/废弃 (Legacy/Misc)
    ├── crack_manager.py          # [废弃] 多进程浏览器调度器
    ├── app.js / vendor.js        # [临时] 抓取的网站前端源码
    └── PROGRESS.md               # 开发进度记录
```

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