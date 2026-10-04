# 如意视频下载器（Ruyi Video Downloader）

这是一个面向 Windows 的 PyQt6 桌面视频下载器项目。

## 当前阶段

第一阶段仅建立项目基础架构：

- 模块化目录结构
- `main.py` 程序入口
- PyQt6 基础主窗口
- JSON 配置系统
- 统一日志系统
- 基础依赖与 Git 忽略规则

当前**不包含**视频解析、yt-dlp 下载或 FFmpeg 处理功能。

## 运行

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

启动程序：

```powershell
python main.py
```

## 目录说明

- `app/ui/`：界面与主窗口
- `app/core/`：配置和后续业务逻辑
- `app/services/`：后续外部服务适配层
- `app/utils/`：路径、日志等通用工具
- `config/`：运行时配置
- `logs/`：运行日志
- `tests/`：测试文件
- `build/`：后续构建输出

## 配置与日志

配置文件为 `config/settings.json`，文件缺失或损坏时会自动恢复默认值。日志写入 `logs/ruyi.log`。
