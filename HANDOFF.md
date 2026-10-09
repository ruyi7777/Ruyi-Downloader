# Ruyi Video Downloader 技术交接文档（HANDOFF）

> 文档用途：供下一位 AI 编程助手 / Codex 直接接手开发使用。<br>
> 本文不是面向普通用户的项目介绍，而是记录**当前真实代码状态、架构约束、已验证事实、已知故障、测试方式和下一步边界**。<br>
> 生成日期：2026-10-07。<br>
> 如果本文与实际文件、Git 状态或运行环境冲突，**以实际代码和实际命令输出为准**，并更新本文。

---

## 0. 接手时先做什么

接手后不要直接改代码，按以下顺序执行：

1. 阅读 `AGENTS.md`，这是项目最高优先级开发规则。
2. 阅读 `README.md`，确认对外功能描述。
3. 执行本文第 13 节的基础验收命令。
4. 阅读本文第 4、5、8、9、10 节，理解架构、Cookie、代理、Node.js 和 Stage 8.1。
5. 在确认工作区状态后，再进行最小范围修改。
6. 修改后必须重新执行语法、导入、单元测试和相关真实回归测试。
7. 未经用户明确要求，不执行 `git commit`、`git push`、`git reset`、`git clean`、`git checkout -- .` 等操作。

---

## 1. 项目基本信息

### 1.1 项目标识

| 项目 | 实际值 |
|---|---|
| 项目名称 | Ruyi Video Downloader（如意视频下载器） |
| 项目路径 | `C:\xiangmu\video tiqu` |
| 项目用途 | Windows 桌面视频信息解析和视频下载工具 |
| 主要 GUI | PyQt6 |
| 下载/解析引擎 | yt-dlp |
| 音视频合并 | FFmpeg |
| 计划打包工具 | PyInstaller（当前尚未安装，也尚未打包） |
| Git 仓库 | `https://github.com/ruyi7777/Ruyi-Downloader.git` |
| 当前分支 | `main` |

### 1.2 当前实际环境版本

以下版本来自当前 `.venv` 和本机实际命令，不是根据 README 猜测：

| 组件 | 实际状态 |
|---|---|
| Windows | Windows 11，`Windows-11-10.0.26200-SP0` |
| Python | `3.13.16` |
| 虚拟环境 | `C:\xiangmu\video tiqu\.venv` |
| PyQt6 distribution | `6.11.0` |
| Qt runtime | `6.11.0` |
| yt-dlp | `2026.08.19` |
| yt-dlp-ejs | `0.8.0` |
| 用户机器 Node.js | `C:\软件\node.js\node.exe`，`v24.21.0` |
| 当前 Codex shell PATH 中的 Node.js | `C:\Users\ruyi\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe`，`v24.19.0` |
| FFmpeg | `C:\xiangmu\tools\ffmpeg-9.0.2-essentials_build\bin\ffmpeg.exe` |
| FFmpeg 版本 | `ffmpeg version 9.0.2-essentials_build-www.gyan.dev` |
| PyInstaller | 当前 `.venv` **未安装**，`requirements.txt` 也未包含 |
| Git remote | `origin` → `https://github.com/ruyi7777/Ruyi-Downloader.git` |

### 1.3 `requirements.txt` 当前完整内容

```text
PyQt6>=6.6,<7
yt-dlp>=2026.8.19,<2027
yt-dlp-ejs>=0.8.0,<0.9
```

当前环境 `pip check` 结果：

```text
No broken requirements found.
```

不要为了本机 Node.js 或 FFmpeg 的绝对路径添加依赖。Node.js 和 FFmpeg 都是外部运行时。

---

## 2. 当前 Git 状态

### 2.1 生成本文时的实际状态

生成 `HANDOFF.md` 之前实际检查结果：

- 当前分支：`main`
- HEAD：`5a5ab0a303ec905078015f76a773442bcaa946b0`
- HEAD 摘要：`5a5ab0a 实现多链接解析与URL自动清洗`
- HEAD 时间：`2026-10-07 16:26:11 +08:00`
- 工作区：clean
- upstream：`origin/main`
- 相对 upstream：ahead 1、behind 0
- remote HEAD：`2f19e3c 完善全局代理环境兼容与YouTube运行时支持`
- 当前是否 push：**Stage 8.1 尚未 push**
- 最近完成 Stage：**Stage 8.1 多链接解析 + URL 自动提取与清洗**

生成本文件后，若尚未提交，`git status` 应出现：

```text
?? HANDOFF.md
```

这是预期状态。不要因为出现该文件就执行破坏性 Git 操作。

### 2.2 最近重要提交

```text
5a5ab0a 实现多链接解析与URL自动清洗
2f19e3c 完善全局代理环境兼容与YouTube运行时支持
05bad5e 实现Cookie支持与智能平台策略
ccd85bd 实现FFmpeg自动发现与配置
71940ad 实现下载进度显示
3afa61e 实现单个视频下载
fe7d775 实现 yt-dlp 视频信息解析
0fae96b 完成项目基础骨架
```

### 2.3 Stage 8.1 提交内容

```text
README.md
app/core/url_extractor.py
app/ui/main_window.py
app/ui/video_info_worker.py
tests/test_main_window_batch.py
tests/test_stage81_fixes.py
tests/test_url_extractor.py
tests/test_video_info_batch_worker.py
```

Stage 8.1 不是 Git 历史重写，也不是 Cookie、代理或 FFmpeg 功能重构。

### 2.4 Git 安全要求

默认禁止执行：

```powershell
git commit
git push
git reset --hard
git clean
git checkout -- .
git restore .
```

只有用户明确要求时才可以执行相应操作。尤其禁止为了“清理工作区”直接覆盖用户本地配置或未提交修改。

---

## 3. 实际项目目录结构

以下为排除 `__pycache__` 后的当前结构：

```text
C:\xiangmu\video tiqu\
├── main.py
├── AGENTS.md
├── README.md
├── HANDOFF.md
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
│   ├── test_main_window_batch.py
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
- 未来任务管理

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

### 4.3 单视频下载链路

```text
MainWindow._start_download
    ↓
DownloadWorker（QRunnable，后台线程）
    ↓
VideoDownloader.download
    ↓
平台 Cookie 策略
    ↓
FFmpegService.discover
    ↓
YtDlpService.download_video
    ↓
yt-dlp progress hook
    ↓ DownloadWorker.throttled progress Signal
MainWindow 更新百分比、速度、大小、ETA
    ↓
DownloadResult / DownloadError
    ↓ Qt Signal
MainWindow 显示成功或失败
```

当前下载仍严格限制为**一次一个 URL**：

- 无 URL：中文错误
- 多于一个 URL：提示“当前下载功能一次只支持一个视频”
- 不要把它误认为已经完成 Stage 8.2 多链接下载

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

该文件当前与 Git HEAD 一致。

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

曾经 `config/settings.json` 中出现：

```json
"cookie_file": "C:\\Users\\ruyi\\Downloads\\www.douyin.com_cookies.txt"
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
当前文件已恢复为 Git HEAD 的：

```json
"cookie_file": ""
```

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

当前用户机器 FFmpeg 实际位于：

```text
C:\xiangmu\tools\ffmpeg-9.0.2-essentials_build\bin\ffmpeg.exe
```

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

生成本文前执行过针对以下关键字的代码检查：

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

以下都不是 Stage 8.1：

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

---

## 11. 已完成功能与未完成功能

### 11.1 已完成

- 项目基础骨架
- PyQt6 主窗口
- 配置系统
- 日志系统
- yt-dlp 视频信息解析
- 单个视频下载
- yt-dlp 原生下载进度
- FFmpeg 自动发现
- Cookie 文件路径选择/保存/清除
- 平台 Cookie 智能策略
- Node.js + yt-dlp-ejs
- 全局代理环境兼容验证
- Stage 8.1 多链接解析和 URL 自动清洗
- Stage 8.1.1 视频解析超时与可取消机制
- Stage 8.1.2 单按钮解析/取消交互

### 11.2 当前明确未完成

- 多链接下载
- 任务队列
- 并发解析/下载
- 下载任务的暂停、取消、重试（视频解析取消已支持）
- 画质选择 UI
- 重复下载检测
- 下载目录设置页面
- FFmpeg 设置页面
- 完整设置页面
- Cookie 浏览器自动读取
- Cookie 自动刷新
- 内部代理
- 自动更新 yt-dlp/FFmpeg
- 播放器
- PyInstaller 打包

README 不得提前把这些写成已实现。

---

## 12. 测试与当前验证状态

### 12.1 Stage 8.1 自动测试

已执行：

```powershell
.venv\Scripts\python.exe -m compileall -q main.py app
.venv\Scripts\python.exe -m unittest discover -s tests -v
git diff --check
git status --short --branch
```

生成本文前结果：

| 测试 | 状态 |
|---|---|
| `compileall` | PASS |
| unittest 自动测试 | PASS |
| `git diff --check` | PASS |
| 工作区 | clean（生成 HANDOFF 前） |
| Git 分支状态 | `main`，ahead 1 |

Stage 8.1.1/8.1.2 当前验证结果：

| 测试 | 状态 |
|---|---|
| unittest 自动测试（23 项） | PASS |
| Python 语法与核心导入（29 个文件） | PASS |
| `pip check` | PASS |
| `git diff --check` | PASS |
| 离屏完整程序启动到主窗口创建 | PASS |
| 真实鼠标交互取消 | NOT TESTED |
| 真实国外网络超时回归 | NOT TESTED |

### 12.2 Stage 8.1 测试文件

#### `tests/test_url_extractor.py`

覆盖：

- 中文文字包围 URL
- ASCII 和中文包装符号
- 单行多 URL
- 多行多 URL
- query/fragment 保留
- HTTP 和未知平台
- 顺序去重
- 空输入和非法候选

#### `tests/test_video_info_batch_worker.py`

覆盖：

- 顺序解析
- 中间 URL 失败
- 后续 URL 继续
- started/succeeded/failed/finished 信号

#### `tests/test_main_window_batch.py`

覆盖：

- 离屏 GUI 多链接解析
- 混合成功/失败
- 事件循环持续响应
- 按钮状态

#### `tests/test_stage81_fixes.py`

覆盖：

- 解析成功后输入框替换成清洗 URL 列表
- 无 URL 保留原文
- 普通、最大化、恢复布局不重叠
- 解析和下载 options 都启用 `js_runtimes={"node": {}}`

#### `tests/test_parse_timeout.py`

覆盖：

- 正常解析成功
- 网络超时与连接失败的中文错误区分
- 其他错误不误报为视频不存在
- 解析专用超时和提取器重试参数
- 下载超时、重试和进度参数不回归
- 取消事件的请求前检查和 yt-dlp logger 检查点

#### `tests/test_parse_cancellation.py`

覆盖：

- 空闲、解析中、取消中和完成后的单按钮状态
- 二次点击同一按钮启动取消而不是重新解析
- 重复取消不会异常
- 旧任务延迟信号不会影响新任务
- 取消后不启动后续 URL
- 已成功结果保留
- 取消不计入普通失败
- Parser 接收线程安全取消事件
- 离屏 GUI 点击取消后的状态、按钮恢复和再次解析
- 解析期间事件循环持续响应

### 12.3 真实网络回归

README 记录的真实回归状态：

| 平台 | 状态 | 说明 |
|---|---|---|
| Bilibili Stage 8.1 解析 | PASS | 真实 URL 与无效网页混合解析，单个失败不中断 |
| Bilibili 下载/FFmpeg | PASS | 之前真实下载约 106,980,236 bytes，H.264+AAC |
| TikTok 下载 | PASS | 之前真实下载约 39,155,061 bytes，H.264+AAC |
| X 下载 | PASS（历史回归） | Stage 7.1 收尾回归曾通过；若下一轮无测试 URL，应写 NOT TESTED，不要伪造 |
| Douyin | PASS（特定 Cookie + 当前出口环境） | 某些出口 IP 返回 HTTP 403/Fresh cookies；更换节点或出口后曾成功 |
| YouTube Node/EJS + 显式服务层 Cookie | PASS | `eDrH-noimf8` 曾解析并下载成功 |
| YouTube 默认 NEVER Cookie 项目路径 | FAIL（已知） | 可能触发机器人校验，不能通过改 Cookie 策略掩盖 |
| v2rayN 关闭环境 | NOT TESTED | 没有擅自切换用户系统代理 |

任何新报告必须明确使用：

- PASS
- FAIL
- NOT TESTED

不得把“没测”写成“通过”。

### 12.4 建议的基础验收命令

```powershell
.venv\Scripts\python.exe -m compileall -q main.py app
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m pip check
git diff --check
git status --short --branch
```

核心导入检查至少包含：

```python
from app.core.settings import SettingsManager
from app.core.cookie_file import CookieFileError, resolve_cookie_file
from app.core.platform_policy import (
    detect_platform,
    cookie_mode_for_platform,
    resolve_cookie_for_url,
)
from app.services.ffmpeg_service import FFmpegService
from app.services.ytdlp_service import YtDlpService
from app.ui.main_window import MainWindow
```

GUI 测试：

```powershell
.venv\Scripts\python.exe main.py
```

### 12.5 真实下载回归建议

当前已知测试 URL：

```text
Bilibili:
https://www.bilibili.com/video/BV1Ebho6BE2J?t=7.9

TikTok:
https://www.tiktok.com/@prosperx18/video/7685578173676817694

YouTube:
https://youtu.be/B91bZL8wcAI
https://www.youtube.com/watch?v=eDrH-noimf8
```

真实下载必须记录：

- 平台
- URL
- v2rayN/系统代理状态
- 是否使用 Cookie 策略
- 是否找到 FFmpeg
- 是否达到 100%
- 输出文件大小
- 视频/音频编码
- 是否能解码播放

Douyin 当前已知测试 URL 曾为：

```text
https://www.douyin.com/video/7692287637746437439
```

该 URL 的结果受 Cookie 和出口 IP 影响，必须如实记录 HTTP 403 或成功结果，不要通过改代码掩盖。

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
- 未把 Stage 8.2 内容混入本阶段

用户明确要求前不执行 commit。

---

## 15. 下一阶段建议

### 15.1 当前合理下一步

Stage 8.1 已完成，下一阶段自然方向是：

```text
Stage 8.2：多链接下载 / 下载任务管理准备
```

但在开发前应先设计，不要直接往 `MainWindow` 堆逻辑。

建议先明确：

1. 一次最多加入多少下载任务
2. 是继续单任务下载，还是引入任务队列
3. 任务状态模型如何复用 `DownloadStatus`
4. `concurrent_tasks` 是否从“预留配置”变成真实并发
5. 是否实现暂停/取消
6. 多任务如何共用 `QThreadPool`
7. 一个平台失败如何影响队列
8. 如何避免 Cookie 和网络环境在多任务间被错误耦合
9. 输出目录冲突如何处理
10. 是否先实现重复检测

### 15.2 不要在下一阶段顺便做

除非用户明确要求：

- 内部代理系统
- Cookie 浏览器自动导入
- FFmpeg 自动更新
- PyInstaller
- 大规模 UI 重写
- 修改 AGENTS.md
- 未经测试宣称功能完成

### 15.3 推荐实施顺序

1. 设计任务模型和状态机
2. 抽离 Core 层任务队列
3. 复用现有 `DownloadWorker` / Qt Signal
4. 用测试验证并发上限
5. 再扩展 UI
6. 最后做真实多平台回归

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
11. 当前下载仍是一次一个视频，除非下一阶段明确实现。
12. 不为了测试通过而修改无关架构或伪造结果。
13. 未经用户明确要求，不执行破坏性 Git 操作。
14. 所有报告明确 PASS / FAIL / NOT TESTED。

---

## 17. 最终接手摘要

当前项目已经稳定完成：

```text
基础架构
→ 视频信息解析
→ 单视频下载
→ 下载进度
→ FFmpeg 自动发现
→ Cookie 文件支持
→ Cookie 智能策略
→ 全局代理环境兼容
→ Node.js + yt-dlp-ejs
→ Stage 8.1 多链接解析与 URL 清洗
```

当前 Git 最新本地提交为：

```text
5a5ab0a 实现多链接解析与URL自动清洗
```

该提交尚未 push。<br>
`config/settings.json` 当前恢复为默认 Cookie 空路径。<br>
工作区在生成本文件前 clean。

下一位助手应优先维护稳定性，先理解、小修改、测试、报告，再根据用户明确指令进入 Stage 8.2。
