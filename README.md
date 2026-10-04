# 如意视频下载器（Ruyi Video Downloader）

这是一个面向 Windows 10 / Windows 11 的 PyQt6 桌面视频下载器项目。

## 当前阶段

项目已完成基础架构，并实现第一个核心功能：视频 URL 信息解析。

当前已具备：

- 模块化项目目录
- `main.py` 程序入口
- PyQt6 主窗口
- JSON 配置系统
- 统一日志系统
- 使用 yt-dlp 提取视频基本信息
- 后台线程解析，避免阻塞 GUI 主线程
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

- 视频下载
- 下载进度
- FFmpeg 音视频合并
- 多任务下载
- Cookie 设置页面
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
- yt-dlp：视频信息解析与后续下载引擎

## 使用方法

1. 启动如意视频下载器。
2. 在“视频 URL”中输入完整的视频链接。
3. 点击“解析视频”，或直接按 Enter。
4. 等待后台完成信息提取。
5. 在“视频信息”区域查看标题、作者、时长和可用格式。

解析过程不会下载视频文件，也不会调用 FFmpeg。

## 代码分层

当前 URL 解析调用流程：

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

界面不直接调用 yt-dlp，也不在按钮事件中编写复杂解析逻辑。

## 目录说明

- `main.py`：程序入口与全局初始化
- `app/ui/`：主窗口、界面组件和后台解析任务
- `app/core/`：配置、视频信息模型和解析协调
- `app/services/`：yt-dlp 等外部服务适配层
- `app/utils/`：路径、日志等通用工具
- `assets/`：后续界面资源
- `config/`：运行时配置
- `logs/`：运行日志
- `tests/`：测试文件
- `build/`：后续构建输出

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

日志记录程序启动、配置加载、解析成功和解析失败等重要事件。日志中不记录 Cookie 内容、API Key、密码或 Token。

## 当前测试状态

当前版本已经完成以下验证：

- Python 语法检查
- 核心模块导入检查
- 完整程序启动
- 主窗口创建
- 有效视频 URL 解析
- 无效 URL 错误处理
- GUI 解析期间事件循环非阻塞测试
- 成功与失败日志检查
- 敏感信息日志扫描

测试中使用 Bilibili 视频成功获取了视频 ID、标题、作者、时长、网页 URL 和 8 个可用格式。

## 下一步计划

按照项目开发顺序，下一步将逐步实现：

1. 自动化测试
2. 单任务视频下载
3. 下载进度
4. 下载目录
5. FFmpeg 合并
6. Cookie 支持
7. 多任务管理
8. 设置页面
9. 错误处理完善
10. PyInstaller 打包