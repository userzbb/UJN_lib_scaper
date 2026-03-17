# 🛠️ 技术演进与逆向工程实录 (Development Journey)

> 本文档详细记录了 **UJN Library Seat Scraper** 从一个简单的脚本演变为高性能安全测试工具的完整技术路径。
> 这个过程涵盖了 **Web 自动化**、**多进程并发**、**前端逆向分析**、**加密算法还原** 以及 **高并发架构设计**。

---

## 阶段一：初出茅庐 —— 浏览器模拟 (Browser Automation)

项目的起点非常简单：模拟人类操作。

### 1.1 技术选型
最初，我们选择了 **Playwright**（相比 Selenium 更快、更稳定）来驱动 Chromium 浏览器。

### 1.2 实现逻辑
1.  启动无头浏览器 (Headless Browser)。
2.  导航至图书馆登录页面。
3.  等待 DOM 加载，定位 `input` 标签输入账号密码。
4.  截图验证码区域，调用 OCR 库识别。
5.  点击“登录”按钮，判断 URL 跳转或错误提示。

### 1.3 遇到的瓶颈
虽然逻辑简单，但随着测试规模扩大，问题暴露无遗：
*   **资源消耗巨大**: 每个 Chrome 实例占用 100MB+ 内存，单机并发很难超过 10 个。
*   **速度极慢**: 完成一次完整的“打开->输入->识别->点击->等待”流程需要 2-3 秒。
*   **不可靠**: 页面加载超时、元素定位失败是常态。

**结论**: 这种方法适合“自动化预约”，但完全不适合“大规模测试”。

---

## 阶段二：暴力美学 —— 多进程调度 (Multi-Process Manager)

为了解决速度问题，我们尝试了简单粗暴的扩容方案。

### 2.1 架构调整
编写了一个 `crack_manager.py` 调度器：
*   利用 Python 的 `multiprocessing` 模块。
*   将任务按“出生日期”（01-31）切分。
*   同时启动 10-20 个 Python 进程，每个进程独立运行 Playwright。

### 2.2 效果与局限
*   **速度**: 提升到了约 **3-5 次/秒**。
*   **崩溃**: CPU 和内存迅速占满，系统变得极其卡顿。
*   **瓶颈**: 我们意识到，**渲染网页**（CSS/JS/DOM）是最大的性能浪费。对于“验证密码”这个目标来说，我们只需要 HTTP 响应，不需要渲染 UI。

---

## 阶段三：抽丝剥茧 —— 逆向工程 (Reverse Engineering)

为了突破性能瓶颈，我们决定抛弃浏览器，直接通过 HTTP 协议与服务器通信。但这面临着严峻的挑战：**加密与签名**。

### 3.1 抓包分析 (Traffic Analysis)
通过 F12 和 `mitmproxy`，我们捕获了登录接口 `/rest/auth` 的请求：

```http
GET /rest/auth?captchaId=...&answer=... HTTP/1.1
username: <Base64String_encrypt>
password: <Base64String_encrypt>
x-hmac-request-key: <64-char-hash>
x-request-id: <UUID>
x-request-date: <Timestamp>
```

**发现**:
1.  账号密码不是明文，甚至不是简单的 Base64，带有 `_encrypt` 后缀。
2.  Header 中包含了动态生成的签名 (`x-hmac-request-key`)，如果签名不对，服务器直接返回 403。

### 3.2 破解 AES 加密 (Cracking Encryption)
我们在前端源码（Webpack 打包后的 `app.js`）中搜索 `_encrypt` 关键字，定位到了加密函数。

*   **算法**: AES-128-CBC。
*   **Key**: 硬编码的字符串 `server_date_time`（或者从服务器时间获取，但在客户端逻辑中使用了固定值）。
*   **IV**: `client_date_time`。

我们编写了 Python 脚本复现了这一加密过程，成功生成了与浏览器一致的密文。

### 3.3 攻克 HMAC 签名 (The Hardest Part)
签名算法很容易识别（HMAC-SHA256），但密钥（Secret）在哪里？

在 JS 源码中，我们看到了类似 `hmac(msg, $NUMCODE)` 的调用。
然而，搜索整个代码库，都找不到 `$NUMCODE` 的定义。它很可能是在运行时动态生成，或者是混淆变量。

**突破口 —— 动态注入 (Runtime Extraction)**:
既然静态分析找不到，我们决定让浏览器“告诉”我们。
我们编写了一个特殊的 Playwright 脚本 (`tools/extract_runtime_secret.py`)：
1.  加载登录页面。
2.  注入一段 JS 代码，钩住 Vue 的原型链或全局变量。
3.  在控制台打印出运行时的 `$NUMCODE` 值。

**结果**:
我们成功提取到了密钥：**`ujnLIB2022tsg`**。
有了这个密钥，我们就可以在 Python 中伪造出合法的请求签名，彻底欺骗服务器。

---

## 阶段四：纯协议实现 —— 极速 HTTP (Pure HTTP)

拿着解密出的算法和密钥，我们重写了核心模块 (`src/core/worker.py`)。

### 4.1 核心流程
1.  **构造请求**:
    *   生成 UUID 和 时间戳。
    *   拼接签名字符串：`seat::<UUID>::<Timestamp>::GET`。
    *   使用 `ujnLIB2022tsg` 计算 HMAC-SHA256。
2.  **加密负载**:
    *   使用 AES 加密账号和密码。
3.  **发送请求**:
    *   使用 `requests` 库直接发送，无需加载任何页面资源。

### 4.2 性能飞跃
*   **内存**: 单线程仅需几 MB。
*   **并发**: 轻松支持 128+ 线程。
*   **速度**: 从 0.5 req/s 飙升至 **50-100 req/s**。

---

## 阶段五：工程化与稳定性 (Refactoring & Production)

速度快了，但稳定性成了新问题。网络波动、服务器限流、程序中断都会导致测试失败。

### 5.1 模块化重构
将单文件脚本拆分为 `src/` 目录结构：
*   `core/`: 核心逻辑。
*   `utils/`: 工具函数。
*   `database/`: 数据持久化。

### 5.2 智能断点续传 (State-Aware Resuming)
引入 **SQLite** 数据库：
*   **问题**: 跑了 50% 突然断网，重新跑很浪费时间。
*   **解决**: 实时记录每个账号、每个日期下的“最后尝试密码”。下次启动时，自动从数据库读取进度，并生成“过滤后”的任务队列。

### 5.3 自适应流控 (Adaptive Throttling)
*   **问题**: 128 线程全速运行时，服务器频繁返回 `429 Too Many Requests`。
*   **解决**:
    *   **指数退避**: 检测到 429 或网络错误，线程自动休眠 1s, 2s, 4s...
    *   **会话复用 (Performance Mode)**: 引入 `requests.Session()` 复用 TCP 连接，消除 SSL 握手开销，进一步提升 30% 性能。

---

## 总结 (Conclusion)

通过这一系列的演进，本项目从一个简单的“模拟点击器”进化为了一个“协议级安全测试工具”。这不仅验证了目标系统的安全性，也展示了从 **应用层**（浏览器）下沉到 **协议层**（HTTP/TCP）所带来的巨大性能红利。

> **Next Step**: 探索基于 `aiohttp` 的全异步实现，以进一步压榨单机性能极限。