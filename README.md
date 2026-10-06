# 如意视频下载器（Ruyi Video Downloader）

这是一个面向 Windows 10 / Windows 11 的 PyQt6 桌面视频下载器项目。

## 当前阶段

项目已完成基础架构、视频 URL 信息解析、单个视频下载、下载进度显示和 FFmpeg 自动发现。

当前已具备：

- 模块化项目目录
- `main.py` 程序入口
- PyQt6 主窗口
- JSON 配置系统
- 统一日志系统
- 使用 yt-dlp 提取视频基本信息
- 使用 yt-dlp 下载单个视频
- 使用 yt-dlp progress hook 显示实时下载进度
- 自动发现 FFmpeg，并将路径传给 yt-dlp
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
- Cookie 设置页面
- 多任务下载
- 画质选择
- 暂停与取消
- PyInstaller 打包

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

## 使用方法

1. 启动如意视频下载器。
2. 在“视频 URL”中输入完整的视频链接。
3. 点击“解析视频”，或直接按 Enter。
4. 等待后台完成信息提取。
5. 在“视频信息”区域查看标题、作者、时长和可用格式。
6. 点击“开始下载”下载当前 URL 对应的单个视频。
7. 下载时在“下载任务”区域查看实时进度、速度、文件大小和剩余时间。

解析和下载均在后台线程执行，界面会保持响应。当前一次只处理一个解析或下载任务。解析过程本身不会下载视频文件。

下载目录优先读取 `config/settings.json` 中的 `download_path`；该配置为空时，使用当前用户的 `Downloads\Ruyi Video Downloader` 目录。

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

这样可以兼容 TikTok 等平台的完整 MP4，也可以兼容 Bilibili 等平台常见的视频流和音频流分离格式。对于分离格式，yt-dlp 会调用运行环境中可用的 FFmpeg 完成合并；本阶段不增加 FFmpeg 配置界面、独立合并功能或 Cookie 功能，也不实现画质选择。

## 代码分层

URL 解析调用流程：

```text
主窗口（UI）
    ↓
VideoInfoWorker（后台线程）
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

日志记录程序启动、配置加载、解析成功、下载开始、下载完成以及解析/下载失败等重要事件。日志中不记录 Cookie 内容、API Key、密码或 Token，下载 URL 的查询参数也不会写入日志。

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

测试中使用指定 Bilibili 视频完成了下载，输出文件同时包含 H.264 视频流和 AAC 音频流，并通过 FFmpeg 解码检查；同时使用 TikTok 视频验证原有下载流程仍然正常。

## 下一步计划

按照项目开发顺序，下一步将逐步实现：

1. 下载目录设置页面
2. FFmpeg 设置页面
3. Cookie 支持
4. 重复下载检测
5. 多任务管理
6. 设置页面
7. 错误处理完善
8. 自动化测试
9. PyInstaller 打包
