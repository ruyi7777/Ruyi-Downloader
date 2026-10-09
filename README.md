# 如意视频下载器（Ruyi Video Downloader）

这是一个面向 Windows 10 / Windows 11 的 PyQt6 桌面视频下载器项目。

## 当前阶段

项目已完成基础架构、视频 URL 信息解析、单个视频下载、下载进度显示、FFmpeg 自动发现、Cookie 文件支持、Cookie 智能使用策略、Stage 7.1 网络环境兼容验证、Node.js + yt-dlp-ejs 支持、Stage 8.1 多链接解析和 URL 自动提取与清洗，Stage 8.1.1 视频解析超时与可取消机制，以及 Stage 8.1.2 将取消操作合并到主解析按钮。

当前已具备：

- 模块化项目目录
- `main.py` 程序入口
- PyQt6 主窗口
- JSON 配置系统
- 统一日志系统
- 使用 yt-dlp 提取视频基本信息
- 从任意文字中自动提取、清洗并去重 HTTP/HTTPS URL
- 按输入顺序逐个解析多个视频链接，单个失败不会中断后续解析
- 视频信息解析集中限制网络超时和提取器重试次数
- 批量解析期间可协作取消，已成功结果保留且未完成状态显示“已取消”
- 使用 yt-dlp 下载单个视频
- 使用 yt-dlp progress hook 显示实时下载进度
- 自动发现 FFmpeg，并将路径传给 yt-dlp
- 支持选择、保存和清除 Netscape 格式的 Cookie 文件路径
- 根据平台策略决定是否把已配置的 Cookie 文件交给 yt-dlp
- 网络出口由 v2rayN / Windows 全局网络环境决定，程序不内置代理管理
- 使用 Node.js + yt-dlp-ejs 处理 YouTube 当前 JS Challenge
- 后台线程解析与下载，避免阻塞 GUI 主线程
- 友好中文错误提示与日志记录

当前解析成功后可以显示：

- 视频 ID
- 视频标题
- 作者 / 频道名称
- 视频时长
- 网页 URL
- 平台域名
- 可用格式列表

当前**不包含**以下功能：

- FFmpeg 设置界面
- 多链接下载与任务队列
- 并发解析
- 画质选择
- 下载任务的暂停与取消（视频解析取消已支持）
- PyInstaller 打包
- 内置代理地址、端口、开关、代理池或平台代理切换

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

- PyQt6：图形界面
- yt-dlp：视频信息解析与下载引擎
- yt-dlp-ejs：yt-dlp 的 JavaScript Challenge 求解组件
- Node.js：YouTube JS Challenge 的系统运行时，由 yt-dlp 从 PATH 查找

## 使用方法

1. 启动如意视频下载器。
2. 在“包含链接的文本”区域粘贴一段包含一个或多个链接的文字；普通文字、标点和多个 URL 都可以保留。
3. 点击“解析视频”，程序会自动提取其中的 HTTP/HTTPS URL，清洗首尾包装符号并去重。
4. 等待后台按输入顺序逐个完成解析；解析期间同一个“解析视频”按钮会变为“取消解析”，再次点击即可停止尚未开始的链接。
5. 在“解析结果”表格中查看每个链接的等待、解析中、成功或失败状态；成功后可在“视频信息”区域查看标题、作者、时长和可用格式。
6. 如当前平台需要认证，先点击“选择 Cookie”选择 Netscape 格式的 cookies.txt；不需要时可点击“清除 Cookie”。
7. 点击“开始下载”下载一个视频；下载仍然一次只支持一个 URL。
8. 下载时在“下载任务”区域查看实时进度、速度、文件大小和剩余时间。

解析和下载均在后台线程执行，界面会保持响应。当前多链接只进行后台顺序解析，不进行并发解析；单个链接解析失败会显示中文错误并继续处理后续链接。解析过程本身不会下载视频文件。

下载目录优先读取 `config/settings.json` 中的 `download_path`；该配置为空时，使用当前用户的 `Downloads\Ruyi Video Downloader` 目录。

## 多链接解析与 URL 清洗

Stage 8.1 支持直接粘贴任意文字，不要求用户整理成固定格式：

```text
视频地址：[https://youtu.be/abc123]，快去看看！
B站：https://www.bilibili.com/video/BV123【推荐】
```

处理流程为：

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

清洗只处理 URL 外部包装，保留内部的 `?`、`&`、`=`、`/`、`-`、`_`、`.`、`:`、`%` 和 `#` 等字符。未知平台的合法 HTTP/HTTPS URL 不会被提前丢弃，仍会交给现有 yt-dlp 解析流程。

单个 URL 解析失败时，界面显示简短中文原因并继续解析下一个 URL，最终分别显示成功和失败数量。当前只扩展解析能力，下载仍保持一次一个视频，不包含多链接下载、并发解析或任务队列。

## 解析超时与取消

视频信息解析只使用解析专用网络限制，不改变下载任务参数：

```text
socket_timeout = 12 秒
extractor_retries = 1 次
```

`socket_timeout` 约束单次网络操作等待时间，`extractor_retries` 约束 yt-dlp 已知提取器错误的重试次数；下载继续使用原有 `socket_timeout=15`、`retries=2` 和 `fragment_retries=2`。

网络超时、连接失败和其他平台错误分别显示不同的中文提示，不会统一误报为“视频不存在”。

批量解析期间再次点击主按钮“解析视频”（按钮文字变为“取消解析”）会设置线程安全的取消事件：

```text
同一主按钮二次点击
    ↓ 立即更新按钮和状态
threading.Event
    ↓
Worker 在每个新 URL 开始前检查
    ↓
Parser / yt-dlp logger 检查点协作退出
    ↓
已成功结果保留，未完成行显示“已取消”
```

当前正在阻塞的网络操作不会被强制杀死；最迟会在单次 `socket_timeout` 超时或下一次 yt-dlp 日志检查点退出。一个 URL 可能包含多个顺序网络请求，因此没有设置整个 URL 的绝对总时长上限。

## 下载进度

下载进度来自 yt-dlp 的原生 progress hook，不通过轮询文件大小获取。进度链路为：

```text
yt-dlp progress hook
    ↓
DownloadWorker（后台线程，progress Qt Signal）
    ↓ Qt Signal
主窗口（GUI 线程）
```

界面会尽量显示：

- 下载百分比
- 当前下载速度
- 已下载大小 / 总大小
- 剩余时间
- 等待下载、下载中、下载完成和下载失败状态

当 yt-dlp 没有提供总大小时，进度条使用不确定进度并显示“下载中”，不会生成错误的百分比。速度或剩余时间缺失时显示“—”。

对于视频流和音频流分离的平台（例如 Bilibili），yt-dlp 会分别报告每个流的进度，因此进度条可能在一个分段完成后进入下一个分段；全部流程完成后最终显示 100%。高频进度事件在 Worker 中限制为约每 200 毫秒更新一次，避免给 GUI 线程造成压力，也不会逐次写入日志。

## FFmpeg 自动发现

程序启动和下载前会自动寻找 FFmpeg，不会修改 Windows 系统 PATH，也不需要用户在终端手动执行 PATH 命令。

如果 config/settings.json 中的 ffmpeg_path 非空，该路径作为显式配置优先使用；为空时按以下顺序自动搜索：

1. 当前系统 PATH 中的 ffmpeg.exe
2. 项目根目录及上级目录附近的 tools 目录
3. 用户目录下常见的 FFmpeg 工具目录（例如 Scoop、WinGet 常见位置）
4. 未来 PyInstaller 可执行文件附近的工具目录

搜索使用 pathlib，不会把当前机器的专属路径写死在多个文件中。找到的路径会传给 yt-dlp 的 ffmpeg_location，用于 Bilibili 等分离格式的音视频合并。

如果没有找到 FFmpeg，程序不会崩溃；需要合并的下载会显示：

```text
未找到 FFmpeg，请安装 FFmpeg 或在设置中配置 FFmpeg 路径。
```

当前阶段没有 FFmpeg 设置界面，ffmpeg_path 仍可通过 config/settings.json 配置。

## 格式策略

当前单个下载按以下顺序选择 yt-dlp 格式：

```text
优先完整 H.264 MP4
    ↓
其他完整 MP4
    ↓
H.264 视频流 + M4A 音频流
    ↓
其他视频流 + 音频流
    ↓
yt-dlp best
```

这样可以兼容 TikTok 等平台的完整 MP4，也可以兼容 Bilibili 等平台常见的视频流和音频流分离格式。对于分离格式，yt-dlp 会调用运行环境中可用的 FFmpeg 完成合并；本阶段不增加 FFmpeg 配置界面、独立合并功能，也不实现画质选择。

## Cookie 文件支持与使用策略

程序支持通过主窗口选择一个 Netscape HTTP Cookie File（常见文件名 cookies.txt）。配置只保存文件路径到 config/settings.json，不保存 Cookie 内容。

- “选择 Cookie”使用 Windows 文件对话框选择 `.txt` 文件，也可选择所有文件。
- “清除 Cookie”只清空程序配置，不会删除用户电脑上的 Cookie 文件。
- 配置的文件不存在时会显示明确的中文提示，程序不会崩溃。
- Cookie 文件不会复制到项目目录，不会写入 Git、日志、GUI 内容或 README。
- 当前只支持外部 cookies.txt 文件，不读取 Chrome、Edge、Firefox 的浏览器 Cookie 数据库。

已配置 Cookie 不会自动应用到所有平台。解析或下载前会先根据 URL 识别平台，再由内部 Cookie 策略决定是否使用该文件：

| 平台 | 默认 Cookie 策略 |
| --- | --- |
| Douyin | 配置了有效 Cookie 文件时使用 |
| YouTube | 默认不使用 |
| Bilibili | 默认不使用 |
| TikTok | 默认不使用 |
| X | 默认不使用 |
| 未知平台 | 默认不使用 |

这样可以避免全局 Cookie 配置影响原本不需要 Cookie 的平台，同时保留后续扩展“自动 / 始终使用 / 从不使用”策略的空间。当前策略仅作为内部规则实现，本阶段不提供策略设置界面。

Cookie 调用链保持现有分层：

```text
URL
    ↓
平台识别与 Cookie Policy
    ↓
settings
    ↓
VideoInfoParser / VideoDownloader
    ↓
YtDlpService
    ↓
yt-dlp
```

## Node.js + yt-dlp-ejs 支持

项目已在 `YtDlpService` 的统一 yt-dlp options 构造位置启用 Node.js 运行时：

```text
YtDlpService
    ↓
js_runtimes = {"node": {}}
    ↓
yt-dlp 从当前系统 PATH 查找 Node.js
    ↓
yt-dlp-ejs 提供 JavaScript Challenge 求解脚本
    ↓
YouTube 解析或下载
```

解析和下载共用同一个内部辅助函数，不在 UI、Downloader 或多个文件中重复配置。代码不写死 `C:\软件\node.js\node.exe` 或其他 Node.js 绝对路径，因此开发环境和以后 PyInstaller 环境都应通过系统 PATH 提供 Node.js。`requirements.txt` 已包含 `yt-dlp-ejs`。

当前验证环境中 yt-dlp 能识别 Node.js 运行时，并使用 yt-dlp-ejs 0.8.0 求解 YouTube JS Challenge。服务层传入有效 YouTube Cookie 文件时，`https://youtu.be/eDrH-noimf8` 的解析和实际下载均成功。现有 Stage 6.1 平台策略仍保持 YouTube 为 `NEVER`，因此普通项目解析不会自动使用配置的 Cookie 文件；如当前代理出口触发 YouTube 机器人校验，会继续显示现有中文登录/Cookie 提示。

## Stage 7.1：网络环境与代理策略

本阶段不实现软件内置代理系统。项目不保存代理地址，不提供代理地址、端口、开关、代理池或平台代理切换，也不修改 Windows 系统代理、不调用 v2rayN API、不检测 v2rayN 是否安装。

网络路径由外部环境决定：

```text
v2rayN / Windows 全局网络环境
    ↓
如意视频下载器
    ↓
yt-dlp
    ↓
各平台
```

yt-dlp 直接继承程序启动时的 Windows 网络环境，因此 v2rayN 关闭时使用当前直连网络，开启全局代理时由 v2rayN 提供网络出口。Cookie 文件仍由现有 cookiefile 配置独立传递，网络层与 Cookie 层保持解耦。未来多链接解析也应统一复用当前 Windows 网络环境，不引入全局、当前或按平台变化的软件代理状态。

本阶段已完成以下记录：

- Windows 系统代理开启（`127.0.0.1:10808`）环境下的代码检查、GUI 启动和平台回归：PASS
- Bilibili、TikTok、X、Douyin 的实际解析、下载、进度和输出文件检查：PASS
- YouTube Node.js + yt-dlp-ejs 服务层解析、实际下载和输出文件检查：PASS
- YouTube 按 Stage 6.1 `NEVER` 策略的普通项目解析：FAIL（当前代理出口返回机器人校验提示）
- v2rayN 关闭环境：NOT TESTED（未切换用户的系统代理设置）
- v2rayN 具体节点名称：NOT TESTED（终端无法读取 v2rayN 内部节点选择）
- 未新增代理代码；`yt-dlp-ejs` 是本次唯一新增依赖；未修改 Cookie、FFmpeg、下载进度或平台识别策略

## 代码分层

URL 解析调用流程：

```text
主窗口（UI）
    ↓
extract_http_urls（URL 提取、清洗、校验与顺序去重）
    ↓
VideoInfoBatchWorker（单个后台线程，顺序解析）
    ↓
VideoInfoParser（URL 校验与业务协调）
    ↓
YtDlpService（外部服务适配）
    ↓
yt-dlp Python API
```

单个视频下载调用流程：

```text
主窗口（UI）
    ↓
DownloadWorker（后台线程）
    ↓
VideoDownloader（下载目录、URL 校验与任务协调）
    ↓
YtDlpService（外部服务适配）
    ↓
yt-dlp Python API
```

界面不直接调用 yt-dlp，也不在按钮事件中编写复杂解析或下载逻辑。

## 目录说明

- `main.py`：程序入口与全局初始化
- `app/ui/`：主窗口、界面组件和后台解析/下载任务
- `app/core/`：配置、视频信息模型、下载模型和任务协调
- `app/services/`：yt-dlp 等外部服务适配层
- `app/utils/`：路径、日志等通用工具
- `assets/`：后续界面资源
- `config/`：运行时配置
- `logs/`：运行日志
- `tests/`：测试文件
- `build/`：后续构建输出和测试文件

## 配置与日志

配置文件为：

```text
config/settings.json
```

配置文件缺失或损坏时会自动恢复默认值，不会导致程序崩溃。

日志文件为：

```text
logs/ruyi.log
```

日志记录程序启动、配置加载、解析成功、下载开始、下载完成、Cookie 文件配置/清除以及解析/下载失败等重要事件。日志中不记录 Cookie 内容、API Key、密码或 Token，下载 URL 的查询参数也不会写入日志。

## 当前测试状态

当前版本已经完成以下验证：

- Python 语法检查
- 核心模块导入检查
- 完整程序启动
- 主窗口创建
- 有效视频 URL 解析
- 无效 URL 错误处理
- 单个视频实际下载
- 空 URL 与无效 URL 错误处理
- 下载失败错误处理
- 实时下载进度变化与完成后 100% 状态
- GUI 解析和下载期间事件循环非阻塞测试
- 现有 Bilibili 解析功能回归
- Bilibili 分离格式下载与可播放性检查
- TikTok 单个视频下载回归
- 成功与失败日志检查
- 敏感信息日志扫描
- 未修改 PATH 时的 FFmpeg 启动自动发现
- Bilibili 分离格式在自动发现 FFmpeg 后下载与合并
- TikTok 自动发现 FFmpeg 后回归下载
- X 视频下载回归
- YouTube 视频解析回归
- FFmpeg 缺失模拟与中文错误提示
- Cookie 路径未配置、文件不存在和目录路径错误处理
- Cookie 文件选择、路径保存、界面显示与清除配置
- 清除 Cookie 配置后用户原文件仍然保留
- 无 Cookie 时 Bilibili、TikTok、X、YouTube 解析回归
- 无 Cookie 时 Bilibili、TikTok、X 实际下载回归
- 无效 Cookie 文件的中文错误提示与敏感信息扫描
- Cookie 已配置时 YouTube、Bilibili、TikTok、X 解析回归
- Cookie 已配置时 Bilibili、TikTok、X 实际下载回归
- YouTube 无 Cookie 与已配置 Cookie 两种状态解析对比
- Cookie 平台策略诊断日志与敏感信息扫描
- Cookie 策略下 FFmpeg 自动发现、下载进度与 GUI 响应回归
- 硬编码代理扫描与全局代理状态扫描
- compileall 和核心模块导入检查
- 完整程序与 Cookie UI 启动检查
- v2rayN 全局代理开启时的 Bilibili、TikTok、X、Douyin 解析与实际下载
- v2rayN 全局代理开启时使用服务层显式 YouTube Cookie 的 YouTube 解析与实际下载
- v2rayN 全局代理开启时的下载进度与 GUI 响应检查
- `yt-dlp-ejs` Python 模块导入、yt-dlp 依赖识别和 Node.js PATH 检测
- yt-dlp `js_runtimes` 解析与 YouTube JavaScript Challenge 求解
- requirements 依赖一致性与 `pip check`
- 硬编码代理参数、代理 URL 和软件代理状态扫描
- Cookie 平台策略回归与敏感信息日志扫描
- 任意中文文字、中文标点和 ASCII 符号包围的 URL 提取与清洗
- 单行与多行多 URL 提取，以及查询参数和 Fragment 保留
- HTTP/HTTPS、未知平台 URL 校验和顺序去重
- 多链接后台顺序解析、单个失败隔离与混合成功/失败结果
- 离屏 GUI 多链接解析、事件循环响应和按钮状态回归
- 真实 Bilibili URL 与无效网页混合解析回归

Stage 8.1 已完成 URL 自动提取、清洗、去重和多链接顺序解析。离屏 GUI 测试确认成功、失败、成功混合场景按输入顺序显示，解析期间事件循环持续响应，单个失败不会中断后续链接；真实网络回归中 Bilibili 解析成功、无效网页解析失败，任务仍完成并正确统计。下载功能仍限制为一次一个视频。

Stage 7.1 在当前 Windows 系统代理开启环境完成了收尾回归。Bilibili、TikTok、X、Douyin 均完成实际解析和下载，下载进度正常；Bilibili 分离格式由自动发现的 FFmpeg 完成合并，输出文件包含 H.264 视频流和 AAC 音频流并可解码播放。Douyin 使用当前已配置 Cookie 文件和当前系统代理环境成功解析、下载并合并，但终端无法读取 v2rayN 内部节点名称，因此只记录系统代理地址，不猜测节点。

YouTube 服务层在显式传入有效 YouTube Cookie 文件时，Node.js + yt-dlp-ejs 成功解决 JS Challenge，`https://youtu.be/eDrH-noimf8` 解析和实际下载均成功。按照 Stage 6.1 的 YouTube `NEVER` 策略，普通项目解析仍不自动使用配置 Cookie；本次该路径返回“需要登录或 Cookie”的机器人校验提示，因此 README 如实标记为 FAIL，没有通过修改 Cookie 策略掩盖该结果。v2rayN 关闭环境没有切换用户系统代理，状态为 NOT TESTED。项目代码和配置中没有代理参数、代理 URL 或软件代理状态，yt-dlp 会继承当前 Windows 网络环境。

## 下一步计划

按照项目开发顺序，下一步将逐步实现：

1. 下载目录设置页面
2. FFmpeg 设置页面
3. 重复下载检测
4. 多任务管理
5. 设置页面
6. 错误处理完善
7. 自动化测试
8. PyInstaller 打包
