# ROADMAP.md

> 本文件负责项目开发路线和阶段规划。
> 当前真实状态以 `PROJECT_STATUS.md` 为准，长期产品目标以 `如意下载总设计文档.txt` 为准。

## 状态定义

```text
已完成：代码和相应验证已经存在
当前阶段：正在收尾或等待人工确认
下一阶段：已经明确但尚未开始
计划阶段：方向已确定，尚未排定具体实现
长期目标：V1.x / V2.0 目标，不表示当前完成
```

计划阶段只表示开发方向，不表示功能已经存在。

## 一、已完成阶段

| 阶段 | 内容 | 事实依据 |
|---|---|---|
| 基础骨架 | `main.py`、PyQt6 主窗口、配置、日志、项目目录 | 提交 `0fae96b` 及当前代码 |
| 视频信息解析 | yt-dlp `extract_info`、VideoInfo 模型、错误处理 | 提交 `fe7d775` 及当前代码 |
| 单视频下载 | VideoDownloader、DownloadWorker、单 URL 下载 | 提交 `3afa61e` 及当前代码 |
| 下载进度 | yt-dlp progress hook、速度/大小/ETA | 提交 `71940ad` 及当前代码 |
| FFmpeg 自动发现 | 配置路径、PATH、公共目录搜索 | 提交 `ccd85bd` 及当前代码 |
| Cookie 文件与平台策略 | 路径保存/清除、平台 NEVER/AUTO 策略 | 提交 `05bad5e` 及当前代码 |
| 全局网络与 Node.js | 不内置代理、`js_runtimes={"node":{}}`、yt-dlp-ejs | 提交 `2f19e3c` 及当前代码 |
| Stage 8.1 | 多 URL 提取、清洗、去重、批量顺序解析、失败隔离 | 提交 `5a5ab0a` 及当前代码 |
| Stage 8.1.1 | 解析专用 12 秒 timeout、1 次 extractor retry、错误分类、协作取消 | 提交 `dc14afc` 中的代码和测试 |
| Stage 8.1.2 | 单按钮二次点击取消、取消中状态、Task ID 防旧 Worker 信号 | 提交 `dc14afc` 及当前代码 |
| Stage 8.1.3 | 调查 yt-dlp `extract_info` 的可中断能力 | 只读调查完成，无业务代码变更 |

### Stage 8.1.3 调查结论

- yt-dlp 2026.08.19 没有 `extract_info()` 的官方外部取消 callback；
- `progress_hooks` 只用于下载，`download=False` 时不形成可靠解析检查点；
- logger 只能在 yt-dlp 主动调用它的位置协作退出；
- Requests / urllib 请求是同步的，socket 阻塞期间 logger 没有机会运行；
- 当前阻塞单次网络操作主要受 `socket_timeout=12` 约束；
- 整个 URL 可能包含多个顺序请求，因此没有绝对总时长硬上限；
- `match_filter` / `DownloadCancelled` 只能在信息提取到相应阶段后中断后续处理，不能中断正在阻塞的 socket。

## 二、当前阶段

当前状态：

```text
代码阶段：Stage 8.1.3 技术调查已完成
代码工作区：以 PROJECT_STATUS.md 实际 Git 状态为准
文档治理：六文档体系整理
下一代码阶段：Stage 8.2
```

Stage 8.2 尚未开始，不得把规划内容写成当前功能。

## 三、下一阶段

### Stage 8.2：多任务下载队列 / 顺序下载

目标：

- 建立任务模型和状态机；
- 支持多个下载任务顺序入队；
- 复用现有单任务 DownloadWorker；
- 明确任务失败对后续队列的影响；
- 保持当前下载参数、Cookie、FFmpeg 和代理约束；
- 不在 `MainWindow` 中堆积复杂队列逻辑。

开始前需要确认：

- 一次最多加入多少任务；
- 是否继续单线程顺序下载；
- 任务状态如何复用 `DownloadStatus`；
- `concurrent_tasks` 是否从预留配置变为真实并发；
- 是否先实现重复检测；
- 输出目录冲突如何处理；
- 队列取消和单任务取消如何区分。

## 四、计划阶段

以下阶段均未开始，具体顺序可由用户调整。

### Stage 8.3：2 线程并发下载

- 将预留 `concurrent_tasks` 接入真实并发控制；
- 限制最大并发数；
- 验证 Cookie、日志、进度和输出目录在多任务间的隔离；
- 避免创建无限线程。

### Stage 8.4：下载取消 / 重试 / 队列控制

- 下载任务取消；
- 失败重试；
- 队列暂停、继续和清空；
- 与解析取消机制区分；
- 不强制终止 Python 线程。

### Stage 8.5：画质选择 / 4K / AUTO

- 把 `quality` 预留配置接入真实格式选择；
- 支持 2160p、1440p、1080p、720p、360p、最佳；
- 缺失画质向下兼容；
- 默认尽量避免 AV1；
- 验证 MP4 和分离格式回退。

### Stage 8.6：文件命名 / 重复检测 / 输出目录管理

- 下载目录设置页面；
- 打开下载目录；
- 安全文件名模板；
- 文件已存在处理；
- 基于视频 ID 的重复任务检测；
- Windows 中文路径和权限测试。

### Stage 8.7：Cookie GUI / 平台 Cookie 策略完善

基础 Cookie 选择、保存、清除已经存在。本阶段只规划完善项：

- 平台策略可视化；
- Cookie 文件状态诊断；
- 更清晰的错误提示；
- 不自动读取浏览器 Cookie，除非用户明确要求；
- 不把 Cookie 与代理耦合。

### Stage 8.8：yt-dlp / FFmpeg 更新

- 版本检测；
- 用户确认后更新；
- 更新失败回滚和日志；
- 不在未确认时自动修改系统环境。

### Stage 8.9：UI 整体整理

- 设置页面；
- 任务列表和状态布局；
- 解析结果与下载任务视觉分层；
- 不进行无关的大规模重写。

### Stage 9：完整回归测试

- URL、解析、下载、进度、FFmpeg、Cookie、代理、Node.js；
- 错误和边界条件；
- Windows 中文路径、空格路径、权限；
- 真实平台回归与 mock 自动测试结合；
- 对 PASS / FAIL / NOT TESTED 分开记录。

### Stage 10：PyInstaller / EXE

- PyInstaller 配置；
- FFmpeg 和 Node.js 外部运行时策略；
- 无 Python 环境 Windows 测试；
- 中文路径和中文用户名测试；
- 敏感文件和配置排除检查。

## 五、长期版本目标

长期版本目标由 `如意下载总设计文档.txt` 维护：

- V1.0：稳定、可用的 Windows 桌面下载器；
- V1.1：批量导入、下载历史、缩略图、暗色模式等；
- V1.2：播放列表、字幕、音频模式、命名模板等；
- V2.0：更完善任务队列、暂停/继续、历史数据库、自动更新和平台兼容。

这些是目标，不表示当前已经实现。

## 六、阶段推进规则

1. 先读取 `PROJECT_STATUS.md`。
2. 由 Director 确认阶段目标和验收条件。
3. Engineer 阅读 `HANDOFF.md` 和相关源码。
4. 以最小范围实施。
5. 执行测试和 diff 检查。
6. 更新 `PROJECT_STATUS.md`，必要时更新 README / HANDOFF。
7. 等待用户确认后再进入下一阶段。
