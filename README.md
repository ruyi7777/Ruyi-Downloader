# 如意视频下载器（Ruyi Video Downloader）

这是一个面向 Windows 10 / Windows 11 的 PyQt6 桌面视频下载器项目。

项目使用：

- Python 3
- PyQt6
- yt-dlp
- yt-dlp-ejs
- FFmpeg
- Node.js（由 yt-dlp 从 PATH 查找）

## 当前阶段

当前代码已完成：

- 项目基础架构；
- 视频信息解析；
- 单个视频下载；
- 下载进度显示；
- FFmpeg 自动发现；
- Cookie 文件路径和平台策略；
- 全局网络环境兼容；
- Node.js + yt-dlp-ejs；
- Stage 8.1 多 URL 提取、清洗、去重和批量顺序解析；
- Stage 8.1.1 解析超时、网络错误分类和协作取消；
- Stage 8.1.2 单个解析按钮二次点击取消和 Task ID 信号保护；
- Stage 8.1.3 yt-dlp 解析取消机制技术调查；
- Stage 8.2 批量下载任务队列和顺序执行。

下一代码阶段是 Stage 8.3：2 线程并发下载，尚未开始。

当前项目仍处于开发阶段，不等同于 V1.0 最终版本。准确 Git、环境和验证状态见 `PROJECT_STATUS.md`，阶段规划见 `ROADMAP.md`。

## 当前已具备的功能

- 模块化项目目录；
- `main.py` 程序入口；
- PyQt6 主窗口；
- JSON 配置系统；
- 统一日志系统；
- 使用 yt-dlp 提取视频基本信息；
- 从任意文字中自动提取、清洗并去重 HTTP/HTTPS URL；
- 按输入顺序逐个解析多个视频链接；
- 单个链接失败后继续解析后续链接；
- 解析专用 `socket_timeout = 12` 和 `extractor_retries = 1`；
- 网络超时、连接失败和平台错误的中文分类提示；
- 解析期间再次点击“解析视频”按钮请求取消；
- 取消后保留已成功和已失败结果，未完成行显示“已取消”；
- Task ID 防止旧 Worker 的延迟信号影响新一轮解析；
- 将本轮多个解析成功视频按表格顺序加入下载队列；
- 同一时间只运行一个下载任务，完成或失败后自动继续下一个；
- 队列任务具有等待、下载中、完成和失败状态；
- 单个任务失败不会中断后续任务，全部结束后显示成功/失败汇总；
- 没有解析结果时，单个 URL 仍可通过同一队列路径下载；
- 使用 yt-dlp progress hook 显示当前任务实时下载进度；
- 自动发现 FFmpeg 并将路径传给 yt-dlp；
- 选择、保存和清除 Netscape 格式的 Cookie 文件路径；
- 按平台策略决定是否把 Cookie 文件交给 yt-dlp；
- 网络出口由 Windows / v2rayN 外部环境决定，不内置代理管理；
- 后台线程解析与下载，避免阻塞 GUI 主线程；
- 友好中文错误提示与日志记录。

解析成功后显示：

- 视频 ID；
- 视频标题；
- 作者 / 频道名称；
- 视频时长；
- 网页 URL；
- 平台域名；
- 可用格式列表。

## 当前不包含的功能

- 并发下载；
- 下载任务取消、暂停和重试队列；
- 画质选择界面和 4K/AUTO 质量策略 UI；
- 文件命名模板、重复检测和下载历史；
- 完整设置页面；
- FFmpeg 设置界面；
- yt-dlp / FFmpeg 自动更新；
- 内置代理地址、端口、开关、代理池或平台代理切换；
- Cookie 浏览器自动导入；
- PyInstaller EXE 打包。

配置文件中的 `quality`、`concurrent_tasks`、`avoid_av1`、`output_format` 目前是预留配置，尚未全部接入完整业务链路，不能据此宣称对应功能已经完成。

## 安装与运行

建议使用 Python 3 虚拟环境。

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

启动程序：

```powershell
python main.py
```

主要依赖：

- PyQt6：图形界面；
- yt-dlp：视频信息解析与下载引擎；
- yt-dlp-ejs：yt-dlp 的 JavaScript Challenge 求解组件；
- Node.js：YouTube JS Challenge 的系统运行时，由 yt-dlp 从 PATH 查找。

## 使用方法

1. 启动如意视频下载器。
2. 在“包含链接的文本”区域粘贴一个或多个链接，也可以保留普通文字和标点。
3. 点击“解析视频”，程序自动提取 HTTP/HTTPS URL，清洗首尾包装符号并去重。
4. 等待后台按输入顺序逐个解析；解析期间同一个按钮变为“取消解析”，再次点击可请求取消。
5. 在“解析结果”表格中查看等待、解析中、成功、失败或已取消状态。
6. 如当前平台需要认证，点击“选择 Cookie”选择 Netscape 格式的 `cookies.txt`；不需要时点击“清除 Cookie”。
7. 点击“开始下载”，本轮解析成功的视频会按解析结果表顺序进入下载队列。
8. 在“任务队列”查看每个任务的等待、下载中、完成和失败状态。
9. 在进度区域查看当前任务的百分比、速度、文件大小和剩余时间；队列结束后显示成功、失败汇总。

解析和下载均在后台线程执行，界面保持响应。下载队列同一时间只运行一个任务，单个任务失败后继续下一个；不使用 `concurrent_tasks`，不进行并发下载。没有解析结果时，多个原始链接会提示先解析，单个 URL 仍可直接进入同一队列路径。

下载目录优先读取 `config/settings.json` 中的 `download_path`；该配置为空时，使用当前用户的 `Downloads\Ruyi Video Downloader` 目录。

## 多链接解析与 URL 清洗

Stage 8.1 支持直接粘贴任意文字：

```text
视频地址：[https://youtu.be/abc123]，快去看看！
B站：https://www.bilibili.com/video/BV123【推荐】
```

处理流程：

```text
用户粘贴原始文本
    ↓
自动提取 HTTP/HTTPS URL
    ↓
清洗 URL 首尾包装文字与标点
    ↓
基础 URL 校验
    ↓
去重并保留第一次出现的顺序
    ↓
后台按顺序逐个解析
    ↓
表格显示每个链接的解析结果
```

清洗只处理 URL 外部包装，保留内部的 `?`、`&`、`=`、`/`、`-`、`_`、`.`、`:`、`%` 和 `#` 等字符。未知平台的合法 HTTP/HTTPS URL 不会提前丢弃，仍交给 yt-dlp 解析。

## 解析超时与取消

视频信息解析只使用解析专用网络限制：

```text
socket_timeout = 12 秒
extractor_retries = 1 次
```

下载继续使用原有参数：

```text
socket_timeout = 15
retries = 2
fragment_retries = 2
```

取消采用 `threading.Event` 协作机制：

```text
同一主按钮二次点击
    ↓
threading.Event
    ↓
Worker 在每个新 URL 前检查
    ↓
Parser / YtDlpService / yt-dlp logger 检查点
    ↓
已成功结果保留，未完成行显示“已取消”
```

当前正在阻塞的网络操作不会被强制杀死。单次网络操作主要受 12 秒 timeout 约束；一个 URL 可能包含多个顺序请求，因此没有整个 URL 的绝对总时长硬上限。

## 下载进度

下载进度来自 yt-dlp 原生 progress hook：

```text
yt-dlp progress hook
    ↓
DownloadWorker（后台线程，progress Qt Signal）
    ↓ Qt Signal
主窗口（GUI 线程）
```

界面显示：

- 下载百分比；
- 当前下载速度；
- 已下载大小 / 总大小；
- 剩余时间；
- 等待、下载中、分段完成、完成或失败状态。

## FFmpeg 自动发现

启动和每次下载前通过 `FFmpegService` 自动发现 FFmpeg，搜索顺序为：

1. `config/settings.json` 中的 `ffmpeg_path`；
2. 当前进程 PATH；
3. 项目 `tools/`、用户目录、Scoop、Python 目录和 WinGet Links 等公共目录。

发现过程不修改 Windows PATH。Bilibili 等分离音视频格式依赖 FFmpeg 合并；FFmpeg 缺失时显示中文错误，不让程序崩溃。

## 格式策略

当前下载格式策略优先选择：

1. 完整 MP4；
2. H.264/AVC MP4；
3. 分离视频和音频后由 FFmpeg 合并；
4. yt-dlp 可用的最佳格式。

默认尽量避免 AV1，优先 H.264 / VP9。具体格式选择仍由 yt-dlp 完成；画质选择界面和质量 fallback UI 尚未实现。

## Cookie 文件支持与使用策略

Cookie 只保存文件路径，不读取或显示 Cookie 内容。

当前平台策略：

```text
YouTube   NEVER
Bilibili  NEVER
TikTok    NEVER
X         NEVER
Douyin    AUTO
unknown   NEVER
```

Cookie 文件必须是 Netscape 格式的 `cookies.txt`。清除 Cookie 只清空配置路径，不删除用户原文件。

Cookie 内容不写入配置、日志、普通 UI 或 Git。Cookie 和代理保持解耦。

## Node.js + yt-dlp-ejs

解析和下载 options 都启用：

```python
options["js_runtimes"] = {"node": {}}
```

yt-dlp 从 PATH 查找 Node.js，`yt-dlp-ejs` 提供 JavaScript Challenge 求解脚本。项目不硬编码 Node.js 绝对路径。

YouTube 默认 Cookie 策略为 `NEVER`，某些出口 IP 可能触发机器人校验；这不能通过擅自修改 Cookie 策略掩盖。

## 网络与代理策略

项目不实现软件内置代理系统，不保存代理地址，不调用 v2rayN API，不修改 Windows 系统代理。

网络路径为：

```text
Windows / v2rayN 外部网络环境
    ↓
yt-dlp
    ↓
各视频平台
```

## 代码分层

```text
主窗口（UI）
    ↓
Worker + Qt Signal
    ↓
Core（URL、Parser、Downloader、TaskManager、配置、Cookie 策略）
    ↓
Service（yt-dlp / FFmpeg）
    ↓
外部工具
```

详细调用链和实现约束见 `HANDOFF.md`。

## 目录说明

- `main.py`：程序入口与全局初始化；
- `app/ui/`：主窗口、控件、后台 Worker 和下载队列控制器；
- `app/core/`：配置、URL、解析/下载协调、任务状态机、Cookie 策略和模型；
- `app/services/`：yt-dlp、FFmpeg 适配；
- `app/utils/`：路径和日志；
- `config/`：运行时配置；
- `tests/`：自动测试；
- `logs/`：运行日志；
- `assets/`、`build/`：资源和构建输出。

## 配置与日志

配置文件：

```text
config/settings.json
```

配置文件缺失或损坏时自动恢复默认值，不会导致程序崩溃。

日志文件：

```text
logs/ruyi.log
```

日志记录启动、配置加载、解析、下载、Cookie 配置和失败事件，不记录 Cookie 内容、API Key、密码或 Token。

## 测试

当前自动测试使用 `unittest`，包括 URL 提取、批量解析 Worker、解析超时、解析取消、Core 任务状态机、下载队列控制器和离屏 GUI 队列测试。

基础检查：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

当前测试数量和历史真实网络回归结果以 `PROJECT_STATUS.md` 为准；不要把历史回归记录当作本轮重新验证。

## 项目文档

- `AGENTS.md`：Codex / AI 工程师工作规则；
- `README.md`：项目介绍、当前功能和运行方式；
- `PROJECT_STATUS.md`：当前真实状态；
- `HANDOFF.md`：技术实现和交接细节；
- `ROADMAP.md`：阶段规划；
- `如意下载总设计文档.txt`：长期产品和技术设计。
