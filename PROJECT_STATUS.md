# PROJECT_STATUS.md

> 本文件记录项目当前真实状态。它不是路线图，也不是长期设计文档。
>
> 检查日期：2026-10-10。状态以实际代码和 Git 命令输出为准；本文件更新后应重新执行一致性检查。

## 1. 当前结论

| 项目 | 当前值 |
|---|---|
| 当前代码阶段 | Stage 8.1.3 技术调查已完成；Stage 8.1.x 代码已提交 |
| 当前工作性质 | 项目文档体系治理，未开始 Stage 8.2 |
| 下一代码阶段 | Stage 8.2：多任务下载队列 / 顺序下载 |
| 产品版本状态 | 开发阶段，尚未达到 V1.0 最终目标 |
| Git 分支 | `main` |
| 当前 commit | `dc14afc385b8834f34b2ab26df2731fcdbb891c2` |
| commit 摘要 | `完成8.1.2解析取消机制` |
| commit 时间 | 2026-10-09 22:02:33 +08:00 |
| upstream | `origin/main`，与 HEAD 同步（ahead 0 / behind 0） |
| 业务代码工作区 | 文档治理前 clean；当前仅应出现文档治理相关修改 |
| Git tag / EXE | 未发现 Git tag；未打包 EXE |

本次文档治理不提交 Git。文档修改完成后，工作区预期会显示文档变更和两个新文件，这是待用户审查状态，不是业务代码回归。

## 2. 实际环境

| 组件 | 当前值 |
|---|---|
| 操作系统 | Windows 11，`Windows-11-10.0.26200-SP0` |
| Python | 3.13.16 |
| 虚拟环境 | `D:\xiangmu\ruyi\video tiqu\.venv` |
| PyQt6 | 6.11.0 |
| yt-dlp | 2026.08.19 |
| yt-dlp-ejs | 0.8.0 |
| Node.js | `D:\游戏\codex\node\node.exe`，v24.21.0 |
| FFmpeg source | `common` |
| FFmpeg 路径 | `D:\xiangmu\ruyi\tools\ffmpeg-2026-10-08-git-ec420ba161-essentials_build\bin\ffmpeg.exe` |
| `pip check` | PASS |
| requirements | `PyQt6>=6.6,<7`、`yt-dlp>=2026.8.19,<2027`、`yt-dlp-ejs>=0.8.0,<0.9` |

Node.js 和 FFmpeg 是外部运行时，不写入 `requirements.txt`。FFmpeg 通过自动发现机制查找，不依赖修改 Windows PATH。

## 3. 当前项目结构

```text
D:\xiangmu\ruyi\video tiqu\
├── main.py
├── AGENTS.md
├── README.md
├── HANDOFF.md
├── ROADMAP.md
├── PROJECT_STATUS.md
├── 如意下载总设计文档.txt
├── requirements.txt
├── app/
│   ├── core/
│   ├── services/
│   ├── ui/
│   └── utils/
├── config/settings.json
├── tests/
├── logs/
├── assets/
├── build/
└── .venv/
```

核心模块：

- `app/core/`：配置、URL 提取、解析/下载协调、Cookie 策略、数据模型、任务占位；
- `app/services/`：yt-dlp 和 FFmpeg 适配；
- `app/ui/`：主窗口、解析/下载 Worker 和 Qt Signal；
- `app/utils/`：路径和日志；
- `tests/`：单元、批量 Worker、超时、取消和离屏 GUI 测试。

## 4. 已完成功能

### 基础能力

- PyQt6 主窗口；
- JSON 配置和损坏恢复；
- 统一日志；
- yt-dlp 视频信息解析；
- 单个视频下载；
- yt-dlp progress hook 下载进度；
- FFmpeg 自动发现；
- Cookie 文件路径选择、保存和清除；
- 平台 Cookie 策略；
- Node.js + yt-dlp-ejs；
- 不内置代理、继承外部 Windows 网络环境。

### Stage 8.1.x

- Stage 8.1：多 URL 提取、清洗、去重、批量顺序解析、单个失败隔离；
- Stage 8.1.1：解析专用 `socket_timeout=12`、`extractor_retries=1`、超时/连接错误分类、`threading.Event` 协作取消；
- Stage 8.1.2：解析按钮二次点击取消、取消中按钮状态、Task ID 过滤旧 Worker 信号；
- Stage 8.1.3：只读调查 yt-dlp `extract_info()` 的可中断能力，没有修改业务代码。

## 5. 当前未完成功能

- 多链接下载；
- 下载任务队列；
- 并发下载；
- 下载任务取消、暂停和重试；
- 画质选择 UI 和 4K/AUTO 完整质量链路；
- 文件命名模板和重复检测；
- 下载目录设置页面和打开下载目录；
- 完整设置页面；
- FFmpeg 设置界面；
- Cookie 浏览器自动导入；
- yt-dlp / FFmpeg 更新；
- PyInstaller / EXE；
- 内置代理管理。

配置中的 `quality`、`concurrent_tasks`、`avoid_av1`、`output_format` 是预留或部分接入配置，不能当作完整功能完成证明。

## 6. 验证状态

### 当前执行并通过

| 检查 | 结果 |
|---|---|
| `unittest discover -s tests -v` | PASS，23 项 |
| Python 语法检查 | PASS（29 个 Python 文件） |
| 核心模块导入检查 | PASS |
| `pip check` | PASS |
| FFmpeg 自动发现 | PASS |
| Node.js PATH 检测 | PASS |
| `git diff --check` | PASS（文档治理前后均执行） |

### 历史记录、本轮未重新验证

以下结果来自此前阶段记录，本轮文档治理没有重新连接真实平台：

- Bilibili、TikTok、X、Douyin 历史解析/下载回归；
- YouTube Node.js + yt-dlp-ejs 显式 Cookie 历史成功记录；
- YouTube 默认 `NEVER` Cookie 路径的历史机器人校验失败；
- v2rayN 开启/关闭网络环境回归；
- FFmpeg 分离格式真实合并。

因此本轮真实网络状态应写为：

```text
NOT RETESTED
```

不要把历史 PASS 当作 2026-10-10 的新验证。

## 7. 已知问题与限制

1. 无网络或不可达网络时，当前阻塞的 HTTP 请求可能等待到解析专用 `socket_timeout=12`；整个 URL 可能包含多个顺序请求，没有绝对总时长硬上限。
2. yt-dlp 当前没有 `extract_info()` 的官方即时取消 callback；logger 只能在主动调用点协作退出。
3. YouTube 默认 Cookie 策略为 `NEVER`，某些出口 IP 可能触发机器人校验。
4. Bilibili 等分离格式依赖 FFmpeg；FFmpeg 缺失必须显示友好错误。
5. 下载仍一次一个 URL；`task_manager.py` 只是占位模块。
6. `quality`、`concurrent_tasks`、`avoid_av1`、`output_format` 配置尚未全部接入业务链路。
7. 真实网络回归和人工鼠标点击验证没有在本轮重新执行。

## 8. 下一步建议

进入 Stage 8.2 前：

1. 由 Director 确认阶段目标和验收条件；
2. 阅读 `ROADMAP.md` 的 Stage 8.2 设计问题；
3. 先设计任务状态机和 Core 层队列；
4. 复用现有 `DownloadWorker` 和 Qt Signal；
5. 不在 `MainWindow` 中堆叠队列逻辑；
6. 保持下载参数、Cookie、FFmpeg 和代理约束；
7. 完成后更新本文件的 Git、验证和功能状态。

## 9. 更新规则

以下情况必须更新本文件：

- Git branch、commit 或工作区状态变化；
- Python、PyQt6、yt-dlp、yt-dlp-ejs、Node.js、FFmpeg 环境变化；
- 新阶段完成；
- 自动测试数量或结果变化；
- 真实网络回归结果变化；
- 已知问题或限制变化。

更新时不要猜测 commit、测试结果或真实网络状态；没有验证就写 `NOT TESTED`。
