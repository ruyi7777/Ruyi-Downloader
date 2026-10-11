# Ruyi Video Downloader 技术交接文档（HANDOFF）

> 文档用途：供下一位 AI 编程助手 / Codex 快速理解当前技术实现。
>
> 本文只维护架构、模块、调用链、实现约束、故障排查和技术交接信息。
>
> 当前状态、Git、环境和验证结果见 `PROJECT_STATUS.md`；阶段规划见 `ROADMAP.md`；工程规则见 `AGENTS.md`。
>
> 更新日期：2026-10-10。如果本文与实际代码冲突，以实际代码和命令输出为准。

---

## 0. 接手时先做什么

接手后不要直接改代码，按以下顺序执行：

1. 阅读 `AGENTS.md`，确认工程规则和修改边界。
2. 阅读 `PROJECT_STATUS.md`，确认当前分支、commit、环境和验证状态。
3. 阅读 `ROADMAP.md`，确认当前阶段、下一阶段和未开始阶段。
4. 阅读本文第 3 至 10 节，理解架构、解析、下载、Cookie、FFmpeg、代理和 Node.js。
5. 检查 `git status --short --branch`，保护工作区已有修改。
6. 修改后执行语法、导入、单元测试和 `git diff --check`。
7. 未经用户明确要求，不执行 commit、push、reset、restore 或 clean。

---

## 1. 文档职责与事实来源

本文的技术事实优先级为：

```text
实际代码 / Git 命令输出
    ↓
PROJECT_STATUS.md
    ↓
HANDOFF.md / README.md
    ↓
ROADMAP.md
    ↓
如意下载总设计文档.txt
```

本文重点保留：

- 项目架构和模块职责；
- UI → Worker → Core → Service → yt-dlp / FFmpeg 调用链；
- URL 解析和批量解析流程；
- 单视频下载和进度流程；
- Cookie、FFmpeg、Node.js 和网络代理约束；
- Stage 8.1.x 的实现细节；
- 常见故障排查和安全不变式。

当前分支、commit、Python/依赖版本、功能状态、已验证/未验证项目不在此处维护，统一见 `PROJECT_STATUS.md`。

---

## 2. 技术范围与依赖边界

本文记录当前技术实现，不承担 Git、环境版本或产品状态统计。

当前 Python 依赖以 `requirements.txt` 为准：

```text
PyQt6>=6.6,<7
yt-dlp>=2026.8.19,<2027
yt-dlp-ejs>=0.8.0,<0.9
```

Node.js 和 FFmpeg 是外部运行时，不写入 `requirements.txt`，也不应硬编码到业务代码。

解析专用参数：

```text
socket_timeout = 12
extractor_retries = 1
```

下载专用参数：

```text
socket_timeout = 15
retries = 2
fragment_retries = 2
```

当前实现边界、版本和 Git 状态分别见 `PROJECT_STATUS.md` 与 `ROADMAP.md`。

---

## 3. 实际项目目录结构

以下为排除 `__pycache__` 后的当前结构：

```text
D:\xiangmu\ruyi\video tiqu\
├── main.py
├── AGENTS.md
├── README.md
├── HANDOFF.md
├── PROJECT_STATUS.md
├── ROADMAP.md
├── requirements.txt
├── .gitignore
├── 如意下载总设计文档.txt
│
├── app/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── cookie_file.py
│   │   ├── download_models.py
│   │   ├── downloader.py
│   │   ├── platform_policy.py
│   │   ├── settings.py
│   │   ├── task_manager.py
│   │   ├── url_extractor.py
│   │   ├── video_info.py
│   │   └── video_info_parser.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ffmpeg_service.py
│   │   └── ytdlp_service.py
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── download_queue_controller.py
│   │   ├── download_worker.py
│   │   ├── main_window.py
│   │   ├── video_info_worker.py
│   │   └── widgets/
│   │       └── __init__.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py
│       └── paths.py
│
├── config/
│   └── settings.json
│
├── tests/
│   ├── test_download_queue_controller.py
│   ├── test_download_task_manager.py
│   ├── test_main_window_batch.py
│   ├── test_main_window_download_queue.py
│   ├── test_parse_cancellation.py
│   ├── test_parse_timeout.py
│   ├── test_stage81_fixes.py
│   ├── test_url_extractor.py
│   └── test_video_info_batch_worker.py
│
├── logs/
├── assets/
├── build/
└── .venv/
```

### 3.1 目录职责

#### `main.py`

只负责：

- 创建必要目录
- 初始化日志
- 加载配置
- 启动时尝试发现 FFmpeg
- 创建 `QApplication`
- 创建并显示 `MainWindow`
- 进入 Qt 事件循环

不得把 URL 解析、Cookie 判断、yt-dlp 参数、下载、任务队列等业务逻辑写回 `main.py`。

#### `app/ui/`

负责：

- PyQt6 控件
- 用户输入
- 按钮、表格、进度条、状态显示
- 文件选择对话框
- Qt Worker 和 Qt Signal 的连接
- 只在 GUI 线程更新界面

`MainWindow` 可以协调 UI 状态，但不能直接包含完整 yt-dlp 或 FFmpeg 业务逻辑。

#### `app/core/`

负责：

- 配置管理
- URL 提取与清洗
- 平台识别
- Cookie 策略
- 视频信息模型
- 解析流程协调
- 单视频下载流程协调
- 下载状态和进度模型
- 下载任务状态机和 FIFO 队列快照

#### `app/services/`

负责与外部工具/第三方库交互：

- `ytdlp_service.py`：yt-dlp Python API
- `ffmpeg_service.py`：FFmpeg 可执行文件发现

#### `app/utils/`

负责通用工具：

- `paths.py`：项目根目录、配置、日志、目录创建
- `logger.py`：统一控制台和轮转文件日志

#### `config/`

保存应用配置。当前只有：

```text
config/settings.json
```

#### `tests/`

保存 `unittest` 单元和离屏 GUI 测试。当前没有引入 pytest。

---

## 4. 架构规则与核心调用链

### 4.1 总体分层

```text
GUI（app/ui）
    ↓
Worker（QRunnable + Qt Signal）
    ↓
Core（app/core）
    ↓
Service（app/services）
    ↓
yt-dlp / FFmpeg
```

### 4.2 视频信息解析链路

Stage 8.1 当前解析链路：

```text
MainWindow._start_parse
    ↓
app.core.url_extractor.extract_http_urls
    ↓
清洗、基础校验、顺序去重
    ↓
VideoInfoBatchWorker（QRunnable，后台线程）
    ↓ 逐个 URL、单个失败隔离
VideoInfoParser.parse
    ↓
platform_policy.resolve_cookie_for_url
    ↓
YtDlpService.extract_video_info
    ↓
yt-dlp extract_info(download=False)
    ↓
VideoInfo
    ↓ Qt Signal
MainWindow 更新解析表格和视频信息区域
```

关键点：

- URL 提取唯一入口是 `app/core/url_extractor.py::extract_http_urls`
- 不要在 MainWindow 或测试中复制另一套 URL 正则
- 一个 Worker 只做后台计算，不直接操作 GUI 控件
- `VideoInfoBatchWorker` 在同一个后台任务中**顺序**解析，不并发
- 单个 URL 失败会发 `failed(index, user_message, detail)`，随后继续下一个 URL
- 最终发 `finished(success_count, failure_count)`

### 4.3 顺序下载队列链路

```text
MainWindow._start_download
    ↓ 收集解析结果表中的成功行，或单 URL 直接入队
DownloadQueueController.start
    ↓
TaskManager.enqueue_many（FIFO，QUEUED）
    ↓
TaskManager.get_next_queued → RUNNING
    ↓
每次只创建一个 DownloadWorker（QRunnable，后台线程）
    ↓
VideoDownloader.download
    ↓
平台 Cookie 策略 / FFmpegService.discover
    ↓
YtDlpService.download_video
    ↓
yt-dlp progress hook
    ↓ DownloadWorker.throttled progress Signal
DownloadQueueController 按 generation + task_id 过滤旧信号
    ↓
TaskManager 更新 COMPLETED / FAILED
    ↓
自动启动下一个 QUEUED 任务
    ↓
队列结束时发送 snapshots + counts
    ↓
MainWindow 更新任务表、当前进度和成功/失败汇总
```

Stage 8.2 下载规则：

- 同一时间最多一个 `RUNNING` 任务；
- 按解析结果表顺序执行；
- 解析失败或取消行不入队；
- 单个 URL 无解析结果时也走同一队列；
- 多个原始 URL 无解析结果时提示先解析；
- 一个任务失败后继续下一个；
- 不读取 `concurrent_tasks`；
- 不实现下载取消、暂停、继续或重试。

### 4.4 GUI 线程规则

禁止在 GUI 主线程执行：

- yt-dlp 网络请求
- FFmpeg 进程
- 长时间文件操作
- 批量循环网络解析
- 下载

当前使用：

- `QThreadPool.globalInstance()`
- `QRunnable`
- `pyqtSignal` / `pyqtSlot`
- Worker 只发数据，GUI 只接收 Signal 后更新控件

下载进度发送节流间隔：

```python
_PROGRESS_UPDATE_INTERVAL_SECONDS = 0.2
```

### 4.5 稳定模块保护

不要未经用户明确要求重构：

- `main_window.py`
- `ytdlp_service.py`
- `downloader.py`
- `platform_policy.py`
- `ffmpeg_service.py`
- 现有 Worker

这些模块已经经过多阶段真实回归。优先做局部修改、补测试，不要为了新功能整体重写。

---

## 5. 配置与日志

### 5.1 当前 `config/settings.json`

生成本文时实际内容：

```json
{
    "download_path": "",
    "quality": "1080p",
    "concurrent_tasks": 2,
    "avoid_av1": true,
    "output_format": "mp4",
    "ffmpeg_path": "",
    "cookie_file": ""
}
```

当前配置值以实际文件和 `PROJECT_STATUS.md` 为准，不把本机运行时状态写死到本文。

### 5.2 配置兼容逻辑

`SettingsManager`：

- 默认值和旧配置合并：`{**DEFAULT_SETTINGS, **loaded}`
- 缺失配置会补默认值
- JSON 损坏时恢复默认值并写日志
- UTF-8 写入，缩进 4
- 不允许配置损坏导致程序崩溃

新增配置必须先加入 `DEFAULT_SETTINGS`，保证旧版本配置兼容。

### 5.3 下载目录

`VideoDownloader.download_path`：

1. `download_path` 非空：使用配置路径
2. 空：`Path.home() / "Downloads" / "Ruyi Video Downloader"`
3. 相对路径：基于项目根目录解析
4. 不硬编码 `D:\`、`C:\xiangmu\...` 等下载路径

### 5.4 `cookie_file` 曾被修改的原因

必须保留以下交接事实：

曾经 `config/settings.json` 中出现过类似的本机 Cookie 文件绝对路径，例如：

```text
C:\Users\<user>\Downloads\<site>_cookies.txt
```

这不是 Stage 8.1 的代码修改，也不是把 Cookie 内容提交到 Git。原因是用户在 GUI 中点击“选择 Cookie”后，`app/ui/main_window.py` 执行：

```python
self.settings.set(
    "cookie_file",
    str(selected_path.resolve()),
    save=True,
)
```

它只保存**本机文件路径**，属于正常的本地运行时配置。<br>
当前默认配置应保持 `cookie_file` 为空；实际值以配置文件和 Git 状态为准。

下一位助手：

- 不要为测试擅自写入用户本机 Cookie 路径
- 不要把用户 Cookie 文件复制进项目
- 不要把 Cookie 内容写入 `settings.json`
- 如果运行后该字段再次变化，先判断是否为 GUI 正常保存，不要直接认定代码错误
- 提交前应确认不把无关本地运行时配置混入代码提交

### 5.5 日志系统

日志位置：

```text
logs/ruyi.log
```

特性：

- 控制台 + `RotatingFileHandler`
- 单文件最大 1,000,000 bytes
- 保留 3 个备份
- 编码 UTF-8
- 级别可由 `log_level` 设置，当前默认 INFO

必须记录：

- 程序启动
- 配置加载
- FFmpeg 发现结果
- URL 解析成功/失败
- 下载开始/完成/失败
- Cookie 文件配置/清除
- 平台 Cookie policy 的 enabled 状态

禁止记录：

- Cookie 文件内容
- Cookie header/value
- Authorization
- Token
- API Key
- 密码
- 下载 URL 的敏感 query/fragment

`YtDlpService._sanitize_detail()` 会移除 URL query，但不能依赖它掩盖所有错误；调用日志时仍不能主动打印敏感对象。

### 5.6 `.gitignore` 的 Cookie 规则

当前已有：

```gitignore
cookies.txt
cookies*.txt
*.cookies.txt
```

还忽略：

- `.venv/`
- `__pycache__/`
- `build/`
- `dist/`
- `*.spec`
- `logs/`
- `config/*.local.json`

注意：`config/settings.json` **被 Git 跟踪**，不是被忽略文件。

---

## 6. Cookie 机制

### 6.1 平台策略

策略唯一实现位置：

```text
app/core/platform_policy.py
```

当前策略：

```text
YouTube   NEVER
Bilibili  NEVER
TikTok    NEVER
X         NEVER
Douyin    AUTO
unknown   NEVER
```

平台识别通过 hostname 后缀实现，支持短链和子域名：

```text
youtube.com / youtu.be / youtube-nocookie.com
bilibili.com / b23.tv
tiktok.com
twitter.com / x.com
douyin.com / iesdouyin.com
```

### 6.2 Cookie 文件流

```text
GUI 选择文件
    ↓ 只保存路径
config/settings.json.cookie_file
    ↓
VideoInfoParser / VideoDownloader
    ↓
resolve_cookie_for_url
    ↓ 平台策略允许时才校验
resolve_cookie_file
    ↓ 只返回 Path
YtDlpService
    ↓
options["cookiefile"] = str(path)
    ↓
yt-dlp 自己读取文件
```

重要：

- 项目不读取 Cookie 文件内容
- GUI 不显示 Cookie 内容
- 日志不显示 Cookie 内容
- settings 只保存路径
- 无效路径只在实际需要 Cookie 的平台校验，避免影响 NEVER 平台

### 6.3 Cookie 文件错误提示

未配置：

- 空字符串是合法状态
- 普通平台继续工作

文件不存在：

```text
Cookie 文件不存在，请重新选择 Cookie 文件。
```

配置为目录：

```text
Cookie 路径不是有效的文件。
```

“清除 Cookie”只清空配置，不删除用户文件。

### 6.4 Cookie 与代理解耦

Cookie 是认证层，代理是网络出口层。<br>
不要创建：

```text
Cookie + proxy
平台代理自动切换
根据 Cookie 自动换节点
```

这种耦合逻辑。

---

## 7. FFmpeg 自动发现

### 7.1 当前实际搜索顺序

`FFmpegService.discover()` 当前顺序：

1. `config/settings.json` 中的 `ffmpeg_path`
   - 非空且有效：source=`config`
   - 配置无效时警告并继续自动发现
2. 当前进程 `PATH` 中的 `ffmpeg`
   - source=`path`
3. 扩展公共目录
   - source=`common`

公共目录由 `pathlib` 构造，主要包括：

- 项目根 `tools/`
- 项目父目录 `tools/`
- 用户目录 `tools/`
- Scoop ffmpeg/shims
- 当前 Python 可执行文件目录及 `tools/`、`bin/`
- `%LOCALAPPDATA%\Microsoft\WinGet\Links`

搜索目录结构支持：

- 根目录直接放 `ffmpeg.exe`
- 根目录下 `bin/ffmpeg.exe`
- 根目录下一层子目录或子目录 `bin/`

### 7.2 设计约束

- 使用 `pathlib`
- 不修改 Windows PATH
- 不修改系统环境变量
- 不要求用户每次开终端执行 `$env:Path += ...`
- 不把 `C:\xiangmu\...` 写死到多个文件
- FFmpeg 缺失时程序不能崩溃，应转换为中文错误

当前检查环境中自动发现到的 FFmpeg 位于：

```text
D:\xiangmu\ruyi\tools\ffmpeg-2026-10-08-git-ec420ba161-essentials_build\bin\ffmpeg.exe
```

这是当前机器的环境事实，不是应硬编码进项目的唯一方案。

该路径是测试环境事实，不是应硬编码进项目的唯一方案。

### 7.3 FFmpeg 缺失时的错误

期望用户提示：

```text
未找到 FFmpeg，请安装 FFmpeg 或在设置中配置 FFmpeg 路径。
```

Bilibili DASH 视频/音频分离格式必须依赖 FFmpeg 合并。没有 FFmpeg 时允许下载失败，但不能显示底层难懂错误或导致 GUI 崩溃。

---

## 8. 网络 / 代理架构

### 8.1 当前决定

项目**不实现内部代理系统**。

实际网络路径：

```text
如意视频下载器
    ↓
yt-dlp
    ↓
Windows 当前网络环境
    ↓（若开启）
v2rayN
    ↓
代理出口
```

程序只调用 yt-dlp，继承当前系统网络环境。

### 8.2 明确禁止新增

除非未来用户明确另开阶段并修改规则，否则不要新增：

- HTTP/HTTPS/SOCKS5 代理设置
- 代理地址输入框
- 代理端口
- 代理开关
- 平台代理规则
- 代理池
- 自动切换代理
- 代理测试按钮
- v2rayN API
- 修改 Windows 系统代理
- 保存代理地址配置
- `global_proxy`
- `current_proxy`
- `platform_proxy`

### 8.3 当前硬编码代理检查

可执行针对以下关键字的代码检查：

```text
proxy
socks5
127.0.0.1
7890
10809
10808
global_proxy
current_proxy
platform_proxy
```

排除文档和日志后，没有发现实际代理参数逻辑。

### 8.4 未来多链接下载的网络原则

未来多链接任务中的：

```text
URL 1 → yt-dlp
URL 2 → yt-dlp
URL 3 → yt-dlp
```

全部自然继承同一个 Windows 网络环境，不引入每个任务独立的软件代理状态。

---

## 9. Node.js 与 yt-dlp-ejs（YouTube JS Challenge）

### 9.1 当前实现

`app/services/ytdlp_service.py` 中统一函数：

```python
def _apply_js_runtime(options: Dict[str, Any]) -> None:
    """Enable Node.js through yt-dlp's normal PATH-based runtime lookup."""
    options["js_runtimes"] = {"node": {}}
```

当前同时应用于：

1. 视频信息解析 options
2. 视频下载 options

对应测试 `tests/test_stage81_fixes.py` 会断言两者都为：

```python
{"node": {}}
```

### 9.2 依赖关系

当前正式依赖：

```text
yt-dlp
yt-dlp-ejs
```

Node.js 是外部运行时，通过 PATH 被 yt-dlp 查找，不写入 `requirements.txt`。

当前项目 Python 环境能够导入：

```text
yt_dlp
yt_dlp_ejs
```

### 9.3 不要硬编码 Node.js 路径

用户机器实际 Node.js 为：

```text
C:\软件\node.js\node.exe
```

但项目代码不得写死该路径。当前 Codex shell 的 `node` 还可能解析到 Codex 自带 runtime：

```text
C:\Users\ruyi\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe
```

因此测试报告必须记录实际 PATH，不要假定两个 shell 环境完全相同。

### 9.4 YouTube 已确认问题

YouTube 曾出现：

```text
LOGIN_REQUIRED
Sign in to confirm you're not a bot
```

真实结论：

- 不是 Stage 8.1 URL 提取代码导致
- 不是项目内部代理代码导致
- 项目没有内部代理可切换
- 同一 YouTube 视频在不同 v2rayN 出口 IP 下结果不同
- 某些节点正常，某些节点触发 YouTube 风控
- Node.js + yt-dlp-ejs 正常工作后，正常出口 IP 下可以解析和下载

已成功测试的视频：

```text
https://www.youtube.com/watch?v=eDrH-noimf8
```

成功命令形态：

```powershell
yt-dlp --verbose --simulate --js-runtimes node: "https://www.youtube.com/watch?v=eDrH-noimf8"
```

成功日志包含：

```text
[debug] JS runtimes: node-24.21.0
[download] 100%
```

并曾成功选择格式：

```text
137+251-20
```

遇到 YouTube `LOGIN_REQUIRED` 时的判断顺序：

```text
1. 当前 v2rayN 出口 IP 是否被 YouTube 风控
2. 当前 Node.js / yt-dlp-ejs 是否可用
3. YouTube 当前反爬和版本变化
```

不要仅因为某个节点返回 `LOGIN_REQUIRED` 就：

- 修改平台 Cookie 策略
- 新增内部代理
- 把所有平台改成强制 Cookie
- 伪造测试通过

---

## 10. Stage 8.1 已完成内容

### 10.1 功能范围

Stage 8.1 = **多链接解析 + URL 自动提取与清洗**。

已完成：

- 从任意文字提取 HTTP/HTTPS URL
- 支持一行多个 URL
- 支持多行多个 URL
- 支持 URL 前后存在中文文字
- 支持中文标点：`， 。 ！ 【 】` 等
- 支持 ASCII 包装：`[] () <> "" ''`
- 清除 URL 外部包装符号
- 保留 URL 内部字符：`? & = / - _ . : % #`
- HTTP 和 HTTPS 都支持
- 未知平台 URL 不提前丢弃
- 清洗后顺序去重
- 保留第一次出现顺序
- 后台按顺序逐个解析
- 单个 URL 失败不阻止其他 URL
- 失败显示友好中文原因
- 解析输入框成功后自动替换为每行一个清洗 URL
- 无 URL 时保留原文并显示“未找到…”提示
- 结果表格显示序号、状态、平台、标题、作者、时长、URL
- 普通、最大化、恢复窗口状态避免控件重叠
- GUI 解析期间保持响应

### 10.2 关键实现文件

```text
app/core/url_extractor.py
app/ui/video_info_worker.py
app/ui/main_window.py
README.md
tests/test_url_extractor.py
tests/test_video_info_batch_worker.py
tests/test_main_window_batch.py
tests/test_stage81_fixes.py
```

### 10.3 `url_extractor.py` 规则

唯一公共入口：

```python
extract_http_urls(text: str) -> List[str]
```

辅助校验：

```python
is_valid_http_url(url: str) -> bool
```

实现要点：

- 正则匹配 `http://` 或 `https://`
- 使用 `urlsplit` 检查 scheme、netloc、hostname
- 左侧只去明确包装字符
- 右侧逐个移除包装标点
- 使用 `seen` 保持顺序去重，不依赖无序集合的输出顺序
- 不做平台白名单过滤

不要在 MainWindow 重新实现 URL 正则。

### 10.4 多链接 Worker 信号

```python
class VideoInfoBatchWorkerSignals(QObject):
    started = pyqtSignal(int)
    succeeded = pyqtSignal(int, object)
    failed = pyqtSignal(int, str, str)
    finished = pyqtSignal(int, int)
```

调用顺序：

```text
started(index)
  ├─ succeeded(index, VideoInfo)
  └─ failed(index, user_message, detail)
...
finished(success_count, failure_count)
```

### 10.5 Stage 8.1 未包含

以下都不是 Stage 8.1（该阶段当时下载仍为单 URL）：

- 多链接下载
- 任务队列
- 并发解析
- 并发下载
- 暂停/取消
- 画质选择
- 重复下载检测
- 代理系统
- Cookie 浏览器自动导入
- PyInstaller

### 10.6 Stage 8.1.1 视频解析超时与可取消机制

Stage 8.1.1 只修改视频信息解析链路：

- 解析专用 `socket_timeout=12`
- 解析专用 `extractor_retries=1`
- 下载 options 继续保持 `socket_timeout=15`、`retries=2`、`fragment_retries=2`
- 超时、连接失败和其他错误使用不同中文提示
- `VideoInfoBatchWorker` 使用 `threading.Event` 协作取消
- Worker 在每个新 URL 前检查取消状态
- `VideoInfoParser` 把事件传给 `YtDlpService`
- yt-dlp logger 检查点发现事件后抛出 `VideoParseCancelled`
- GUI 立即显示“正在取消”，完成后恢复按钮
- 成功和失败结果保留，未完成行显示“已取消”

限制：当前阻塞网络操作不会被强制终止。单次网络操作等待上限为 12 秒；一个 URL 可能包含多个顺序请求，因此没有整个 URL 的绝对总时长硬上限。

### 10.7 Stage 8.1.2 单按钮取消交互

Stage 8.1.2 只调整 GUI 交互，不重新实现取消机制：

- 空闲状态主按钮显示“解析视频”
- 解析进行中同一按钮显示“取消解析”
- 二次点击调用已有 `VideoInfoBatchWorker.cancel()`
- 取消请求发出后显示“正在取消…”并禁用按钮
- 不再创建独立取消按钮
- 每轮解析使用任务 ID 连接信号
- 旧 Worker 的延迟 started/succeeded/failed/finished 信号会被忽略
- 正常完成和取消完成都恢复主按钮
- Stage 8.1.1 的超时、错误分类、结果保留和协作取消保持不变

### 10.8 Stage 8.1.3：解析取消机制技术调查

本阶段是只读调查，没有修改业务代码。

针对当前安装的 yt-dlp 2026.08.19 和 Python 3.13：

- `YoutubeDL.extract_info()` 没有官方 cancellation/abort callback；
- `progress_hooks` 是下载进度 hook，`extract_info(download=False)` 不会形成可靠解析检查点；
- 项目的 `_CancellableYtDlpLogger` 只能在 yt-dlp 主动调用 logger 时执行；
- Requests / urllib 请求同步执行，socket 阻塞期间 logger 没有机会运行；
- `RequestDirector.send()` 和 `RequestHandler.send()` 没有取消事件检查；
- 当前单次网络操作主要由解析专用 `socket_timeout=12` 约束；
- `match_filter` / `DownloadCancelled` 只能在信息提取到相应阶段后中断后续处理；
- `YoutubeDL.close()` 不是安全的并发取消 API；
- Python 线程不能通过 `threading.Event` 强制中断已经阻塞的 socket。

结论：当前协作取消机制有效，但无网络时当前请求仍可能等待到 timeout；不存在可以在同一线程内保证“点击后立即中断当前 HTTP socket”的官方机制。

---

## 11. 当前实现边界（技术）

以下边界是当前代码实现事实，不是长期产品目标：

- 视频信息解析支持多 URL 顺序执行，但不并发；
- 单个 URL 失败不会阻断后续 URL；
- 下载按队列顺序执行，同一时间最多一个 RUNNING 任务；
- `app/core/task_manager.py` 已实现纯 FIFO 状态机；
- 下载通过 `DownloadQueueController` 顺序执行，但没有下载取消、暂停或重试队列；
- 队列任务状态为 QUEUED / RUNNING / COMPLETED / FAILED；
- `DownloadProgress.PARTIAL_FINISHED` 只属于进度，不是任务终态；
- 解析专用参数是 `socket_timeout=12`、`extractor_retries=1`；
- 下载参数保持 `socket_timeout=15`、`retries=2`、`fragment_retries=2`；
- `quality`、`concurrent_tasks`、`avoid_av1`、`output_format` 配置存在，但尚未全部接入完整业务链路；
- 项目不内置代理，不修改 Windows 系统代理；
- Cookie 平台策略和代理策略保持解耦；
- 旧 Worker 的延迟信号通过 Task ID 过滤，不进入新一轮任务。

长期任务队列、并发下载、画质选择、重复检测、设置页面和打包目标属于 `ROADMAP.md` / 总设计文档，不属于当前已实现能力。

---

## 12. 测试与验证入口

### 12.1 当前自动测试

当前测试套件包含：

- `tests/test_url_extractor.py`
- `tests/test_video_info_batch_worker.py`
- `tests/test_main_window_batch.py`
- `tests/test_stage81_fixes.py`
- `tests/test_parse_timeout.py`
- `tests/test_parse_cancellation.py`
- `tests/test_download_task_manager.py`
- `tests/test_download_queue_controller.py`
- `tests/test_main_window_download_queue.py`

基础命令：

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m pip check
git diff --check
```

2026-10-11 Stage 8.2 实际执行结果：

| 检查 | 结果 |
|---|---|
| unittest | PASS，37 项 |
| 新增测试 | 14 项 |
| 已有测试回归 | 23 项 PASS |
| `pip check` | PASS |
| Python 语法 / 核心导入 | PASS |
| `git diff --check` | PASS |

### 12.2 测试覆盖边界

现有自动测试重点覆盖：

- URL 提取、清洗和顺序去重；
- 批量 Worker 顺序执行和失败隔离；
- 解析 timeout、连接失败和错误分类；
- 协作取消、结果保留和取消状态；
- 单按钮交互、Task ID 和旧信号保护；
- 离屏 GUI 事件循环响应；
- Node.js runtime options；
- 下载参数不因解析参数改变；
- Core FIFO、合法状态转换、失败继续和队列统计；
- 控制器单任务执行、旧信号过滤、当前进度归属和单次结束；
- GUI 成功行入队、失败行排除、失败继续、单 URL 直连和控件恢复。

### 12.3 真实网络回归

历史文档记录过 Bilibili、TikTok、X、Douyin 和 YouTube 的真实解析/下载回归，但本轮文档治理没有重新连接真实平台。

因此：

```text
真实网络回归：NOT RETESTED（本轮）
历史记录：见 README 旧记录和相关阶段报告
```

YouTube 默认 `NEVER` Cookie 策略下的机器人校验是已知历史问题，不应通过修改策略掩盖。

---

## 13. 常见故障排查

### 13.1 YouTube `LOGIN_REQUIRED`

优先检查：

1. 当前 v2rayN/系统出口 IP 是否被风控
2. `node --version` 是否可用
3. `yt-dlp-ejs` 是否安装
4. yt-dlp 是否输出 `JS runtimes: node-*`
5. 当前 YouTube 是否发生站点变更

不要自动修改 Cookie NEVER 策略，也不要新增代理系统。

### 13.2 Bilibili DASH 合并失败

检查：

1. `FFmpegService.discover()` 日志中的 `source` 和 `path`
2. `ffmpeg_path` 配置是否有效
3. PATH 是否能执行 FFmpeg
4. 下载目录是否可写
5. 是否选择需要 FFmpeg 的分离格式

默认格式策略已经允许普通 Bilibili 格式回退到：

```text
bestvideo + bestaudio
```

不要强制要求非会员 4K/1080P 高码率格式。

### 13.3 Cookie 配置后平台失败

先确认：

1. 平台 Cookie 策略是否为 AUTO
2. NEVER 平台是否实际未启用 `cookiefile`
3. Cookie 文件是否存在、是否为文件
4. 是否只保存了路径而没有读取内容
5. 出口 IP 是否与 Cookie 使用环境一致

不要把配置路径存在误判为敏感信息泄漏。

### 13.4 URL 提取错误

唯一修改点应是：

```text
app/core/url_extractor.py
```

并优先补：

```text
tests/test_url_extractor.py
```

不要在 MainWindow 添加补充正则。

特别注意不能损坏：

```text
? & = / - _ . : % #
```

### 13.5 配置文件被运行测试修改

离屏 GUI 或启动测试可能触发：

- Cookie 路径保存
- 配置默认值写入
- 日志目录创建

如果 `config/settings.json` 出现本机运行时差异：

1. 检查实际值
2. 判断是否为正常 GUI 保存
3. 只恢复不该提交的本机字段
4. 不要覆盖用户原 Cookie 文件
5. 不要执行破坏性 Git 恢复命令

---

## 14. 安全和提交前检查

### 14.1 敏感信息

提交和日志中禁止出现：

```text
cookie_value
cookie_header
authorization
token
api_key
password
Cookie 文件实际内容
```

建议扫描：

```powershell
rg -n -i "cookie_value|cookie_header|authorization|token|api_key|password" logs README.md app config
```

注意：代码中出现变量名 `cookie_file` 或路径 `cookiefile` 是正常的，不能据此误报为泄漏。

### 14.2 代理扫描

```powershell
rg -n -i "proxy|socks5|127\.0\.0\.1|7890|10809|10808|global_proxy|current_proxy|platform_proxy" app main.py
```

搜索到普通字符串时必须人工判断是否真的是代理逻辑。不要因为命中 `README` 中“无代理”说明就新增或删除代码。

### 14.3 提交前检查清单

```powershell
.venv\Scripts\python.exe -m compileall -q main.py app
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m pip check
git diff --check
git status
git diff --stat
```

额外确认：

- `requirements.txt` 未误删 `yt-dlp`
- `config/settings.json` 只包含允许提交的默认值
- `cookie_file` 不包含用户本机路径
- `options["js_runtimes"] = {"node": {}}` 仍同时存在于解析和下载 options
- 未新增内部代理
- 未改变 Cookie 平台策略
- 未混入 Stage 8.3 并发、下载取消、重试或其他未批准功能

用户明确要求前不执行 commit。

---

## 15. 下一阶段技术入口

Stage 8.2 顺序下载队列已实现。下一代码阶段由 `ROADMAP.md` 管理，方向是 Stage 8.3：2 线程并发下载，尚未开始。

进入 Stage 8.3 前应先设计：

1. `concurrent_tasks` 如何从预留配置接入真实并发；
2. 最大并发数和线程池上限；
3. 多任务进度如何按 task_id 隔离；
4. Cookie、FFmpeg 和网络环境如何在任务间共享；
5. 输出目录和日志并发安全；
6. GUI 如何同时显示多个任务状态；
7. 失败、暂停和取消是否仍推迟；
8. 并发上限测试和真实网络回归范围。

不要在 Stage 8.3 中顺便实现代理系统、浏览器 Cookie 自动导入、自动更新、PyInstaller 或大规模 UI 重写。

---

## 16. 本项目最重要的不变式

接手期间始终满足以下不变式：

1. `AGENTS.md` 是规则来源。
2. `main.py` 只启动程序。
3. UI 不直接调用 yt-dlp 下载细节。
4. 长任务不运行在 GUI 主线程。
5. URL 提取只维护一套逻辑。
6. Cookie 内容永不进入配置、日志、GUI 或 Git。
7. Cookie 平台策略保持：
   - YouTube/Bilibili/TikTok/X：NEVER
   - Douyin：AUTO
   - unknown：NEVER
8. 项目不内置代理系统。
9. Node.js 通过 PATH 查找，不硬编码。
10. FFmpeg 自动发现不依赖修改系统 PATH。
11. Stage 8.2 下载队列严格顺序执行，同一时间最多一个 RUNNING 任务。
12. 不为了测试通过而修改无关架构或伪造结果。
13. 未经用户明确要求，不执行破坏性 Git 操作。
14. 所有报告明确 PASS / FAIL / NOT TESTED。

---

## 17. 最终接手摘要

当前项目的核心技术事实是：

```text
基础架构
→ 视频信息解析
→ 单视频下载
→ 下载进度
→ FFmpeg 自动发现
→ Cookie 文件和平台策略
→ 全局网络环境兼容
→ Node.js + yt-dlp-ejs
→ Stage 8.1 多链接解析
→ Stage 8.1.1 超时与取消
→ Stage 8.1.2 单按钮取消与 Task ID
→ Stage 8.1.3 可中断机制调查
→ Stage 8.2 批量下载任务队列 / 顺序执行
```

当前实现仍然保持：

- 解析顺序执行；
- 下载队列顺序执行，同一时间一个 RUNNING 任务；
- 不内置代理；
- 不强制终止线程；
- Cookie 内容不进入配置、日志或普通 UI；
- 下载参数、Node.js runtime 和 FFmpeg 发现逻辑不因解析调查而改变。

当前状态、Git 和验证结果请看 `PROJECT_STATUS.md`，下一阶段请看 `ROADMAP.md`。下一位 Engineer 应先理解、小修改、测试、报告，再等待 Director 确认是否进入 Stage 8.3。
