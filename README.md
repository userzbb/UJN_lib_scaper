# UJN Library Scraper & Automation Tools

这是一个针对济南大学（UJN）图书馆座位预约系统的自动化工具集，主要功能包括自动登录、座位预约以及基于身份证后六位规则的弱密码测试工具。

本项目使用 [uv](https://github.com/astral-sh/uv) 进行依赖管理和环境配置，确保环境一致性与极速安装体验。

## ⚠️ 免责声明 (Disclaimer)

**本项目仅供学习交流和安全测试使用。**
请勿将本项目用于任何非法用途，包括但不限于未经授权的渗透测试、暴力破解他人账号、恶意抢占公共资源等。使用本工具产生的任何后果由使用者自行承担。

## 功能特性

1.  **自动座位预约 (`auto_book.py`)**
    *   使用 Playwright 模拟浏览器操作。
    *   集成 `ddddocr` 自动识别验证码。
    *   支持自定义选座（阅览室、座位号）。
    *   具备失败重试机制。

2.  **弱密码测试/找回 (`crack_login.py`)**
    *   针对默认密码规则（身份证后六位）进行字典枚举。
    *   **精准策略**：支持指定**性别**（男/女）和**出生日期**（01-31日）生成特定的身份证后六位字典。
    *   **精细化断点续传**：使用 SQLite 数据库按"学号+日期"维度记录破解进度。中断后可自动恢复，且不同日期的进度互不干扰。
    *   **验证码容错**：自动处理验证码识别错误，仅在密码错误时切换下一个尝试。
    *   **多用户支持**：支持通过命令行参数指定不同学号，进度独立保存。

## 环境依赖

*   [uv](https://docs.astral.sh/uv/) (极速 Python 包管理器)
*   Playwright (浏览器自动化)

## 安装与配置

本项目使用 `uv` 管理依赖，请确保本地已安装 `uv`。

1.  **安装 uv** (如果尚未安装)
    ```bash
    # MacOS / Linux
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Windows
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

2.  **克隆项目**
    ```bash
    git clone https://github.com/your-repo/UJN_lib_scaper.git
    cd UJN_lib_scaper
    ```

3.  **同步依赖环境**
    `uv` 会根据 `uv.lock` 自动创建虚拟环境并安装所有依赖。
    ```bash
    uv sync
    ```

4.  **安装 Playwright 浏览器**
    由于 Playwright 需要下载浏览器二进制文件，需在虚拟环境中执行安装命令：
    ```bash
    uv run playwright install
    ```

## 使用说明

所有脚本均需通过 `uv run` 命令执行，以确保使用项目隔离的虚拟环境。

### 1. 弱密码测试 (`crack_login.py`)

该脚本用于测试账号是否使用了基于身份证后六位的弱密码。默认逻辑为**男生**身份证规则：`日(01-31) + 顺序码(奇数) + 校验位(0-9)`。

**基本用法：**

```bash
# 默认跑全量（男生，01-31日）
uv run crack_login.py 202331223125
```

**高级用法：**

*   **指定性别** (`-g` / `--gender`)：
    ```bash
    # 跑女生的身份证规则（偶数顺序码）
    uv run crack_login.py 202331223125 --gender F
    ```

*   **指定日期** (`-d` / `--day`)：
    ```bash
    # 只跑“8号”出生的男生
    uv run crack_login.py 202331223125 --day 08
    ```

*   **组合使用**：
    ```bash
    # 只跑“15号”出生的女生
    uv run crack_login.py 202331223125 --gender F --day 15
    ```

*   **显示浏览器** (`--show`)：
    ```bash
    # 默认无头模式运行，添加此参数可显示浏览器窗口
    uv run crack_login.py 202331223125 --show
    ```

**运行逻辑：**
*   脚本会自动打开浏览器尝试登录。
*   **进度保存**：每次尝试失败（密码错误）后，会将进度保存到 `crack.db` 数据库。进度是按 `(学号, 日期)` 维度分开记录的，您可以随意切换日期或性别跑，进度不会丢失。
*   **结果保存**：破解成功的密码会自动写入 `found_passwords.csv` 和数据库。

### 2. 自动预约 (`auto_book.py`)

用于登录成功后自动抢座。

**配置：**
打开 `auto_book.py`，修改顶部的配置区域：
```python
USERNAME = "2023xxxxxx"  # 你的学号
PASSWORD = "xxxxxx"      # 你的密码
```
以及底部的阅览室和座位号逻辑（需根据实际网页结构调整 `target_room` 和 `seat_num`）。

**运行：**
```bash
uv run auto_book.py
```

## 目录结构

*   `crack.db`: SQLite 数据库，存储破解进度和结果（已忽略，不提交）。
*   `found_passwords.csv`: 存储破解成功的账号密码文本文件（已忽略，不提交）。
*   `pyproject.toml` / `uv.lock`: uv 项目依赖定义文件。
*   `.venv/`: uv 自动创建的虚拟环境目录。