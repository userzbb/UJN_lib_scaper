# 项目进度报告 (Project Progress)

**最后更新时间**: 2024-03-18

## 🟢 已完成功能 (Completed)

### 4. 极速 HTTP 爆破系统 (High Performance)
- **`crack_login_http.py`**: 纯协议层爆破工具，彻底摆脱浏览器依赖。
  - **性能**: 支持 64-128+ 线程并发，速度是浏览器版的 50-100 倍。
  - **核心突破**: 成功逆向 HMAC-SHA256 签名算法与 AES 加密参数。
  - **功能**:
    - 自动解决验证码 (ddddocr)。
    - 自动生成 `x-hmac-request-key` 签名。
    - 数据库状态持久化 (兼容 `crack.db`)。
    - 智能重试与错误处理。

### 1. 自动化预约核心
- **`auto_book.py`**: 基于 Playwright 的全自动座位预约脚本。
  - 集成 `ddddocr` 自动识别验证码。
  - 支持自定义阅览室和座位号。
  - 包含失败重试与错误检测机制。

### 2. 弱密码破解系统 (Playwright 版)
- **`crack_login.py`**: 单进程密码测试工具。
  - **策略**: 基于身份证后六位规则 (日+顺序码+校验位)。
  - **精细控制**: 支持指定性别 (`-g M/F`) 和特定日期 (`-d 08`)。
  - **持久化**: 使用 SQLite (`crack.db`) 记录进度，支持断点续传（精确到天）。
  - **容错**: 自动处理验证码错误（重试当前密码）与密码错误（跳过）。

### 3. 多进程并发管理器
- **`crack_manager.py`**: 针对浏览器模拟速度慢的解决方案。
  - **并发调度**: 自动启动多个 `crack_login.py` 子进程（默认使用 CPU 核心数）。
  - **任务分配**: 按“日期” (01-31) 分配任务，极大提升爆破效率 (4-8倍)。
  - **状态同步**: 实时监控子进程状态，一旦发现密码立即终止所有任务。

## 🟡 逆向工程成果 (Reverse Engineering - Solved)

**状态**: ✅ 已完全攻克

### 技术细节 (Technical Details)
通过动态调试与逆向分析，我们完全掌握了登录接口 (`/rest/auth`) 的安全机制：

1.  **参数加密 (AES)**:
    -   算法: AES-128-CBC (Pkcs7 Padding)
    -   Key: `"server_date_time"`
    -   IV: `"client_date_time"`
    -   字段: `username`, `password` (加密后追加 `_encrypt`)

2.  **请求签名 (HMAC-SHA256)**:
    -   Header: `x-hmac-request-key`
    -   Message: `seat::<UUID>::<Timestamp>::GET`
    -   **Secret Key**: `"ujnLIB2022tsg"`
        - *获取方式*: 通过 Playwright 注入 JS 读取运行时 `Vue.prototype.$NUMCODE` 得到密文 (`UmrX+lxhFE5neclEsBPing==`)，再使用 AES Key 解密获得明文。

### 🔴 当前阻塞点 (Blocker)

-   **无** (None)。所有技术障碍已清除。

## 🚀 下一步计划 (Next Steps)

1.  **开始爆破**:
    -   直接运行 **`python3 crack_login_http.py <学号> -g <M/F> -t 64`**。
    -   这是目前最快、最高效的方案。

2.  **监控**:
    -   注意观察日志中的网络错误，虽然脚本会自动重试，但如果出现大量连续错误，需考虑降低线程数。