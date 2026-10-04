"""Main window for Ruyi Video Downloader URL parsing."""
from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urlsplit

from PyQt6.QtCore import Qt, QThreadPool
from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.core.settings import SettingsManager
from app.core.video_info import VideoInfo
from app.core.video_info_parser import VideoInfoParser
from app.ui.video_info_worker import VideoInfoWorker
from app.utils.paths import get_config_path, get_log_file

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main window containing URL parsing without download functionality."""

    def __init__(
        self,
        settings: Optional[SettingsManager] = None,
        parent=None,
        parser: Optional[VideoInfoParser] = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings or SettingsManager()
        self.parser = parser or VideoInfoParser()
        self._is_parsing = False

        self.setWindowTitle("如意视频下载器")
        self.setMinimumSize(880, 700)
        self.setObjectName("mainWindow")

        self._build_ui()
        self._build_status_bar()

        logger.info("Main window created")

    def _build_ui(self) -> None:
        """Construct the URL parsing UI while keeping download disabled."""
        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(24, 20, 24, 20)
        root_layout.setSpacing(14)

        header_layout = QHBoxLayout()
        title_label = QLabel("如意视频下载器", self)
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        version_label = QLabel("Ruyi Video Downloader · URL 信息解析", self)
        version_label.setObjectName("versionLabel")
        header_layout.addWidget(version_label)
        root_layout.addLayout(header_layout)

        url_group = QGroupBox("视频 URL", self)
        url_group.setObjectName("urlGroup")
        url_layout = QFormLayout(url_group)
        url_layout.setContentsMargins(14, 12, 14, 12)
        url_layout.setSpacing(10)

        self.url_input = QLineEdit(url_group)
        self.url_input.setObjectName("urlInput")
        self.url_input.setPlaceholderText("https://...")
        self.url_input.setClearButtonEnabled(True)
        self.url_input.returnPressed.connect(self._start_parse)
        url_layout.addRow("视频链接：", self.url_input)

        self.parse_button = QPushButton("解析视频", url_group)
        self.parse_button.setObjectName("parseButton")
        self.parse_button.setToolTip("获取视频基本信息，不下载任何文件")
        self.parse_button.clicked.connect(self._start_parse)
        url_layout.addRow(self.parse_button)
        root_layout.addWidget(url_group)

        info_group = QGroupBox("视频信息", self)
        info_group.setObjectName("videoInfoGroup")
        info_layout = QFormLayout(info_group)
        info_layout.setContentsMargins(14, 12, 14, 12)
        info_layout.setSpacing(8)

        self.parse_status = QLabel("等待输入视频链接", info_group)
        self.parse_status.setObjectName("parseStatus")
        self.parse_status.setWordWrap(True)
        info_layout.addRow("解析状态：", self.parse_status)

        self.id_value = self._create_info_label(info_group, "videoIdValue")
        self.title_value = self._create_info_label(info_group, "videoTitleValue")
        self.uploader_value = self._create_info_label(info_group, "videoUploaderValue")
        self.duration_value = self._create_info_label(info_group, "videoDurationValue")
        self.webpage_value = self._create_info_label(info_group, "videoWebpageValue")
        self.platform_value = self._create_info_label(info_group, "videoPlatformValue")

        info_layout.addRow("视频 ID：", self.id_value)
        info_layout.addRow("标题：", self.title_value)
        info_layout.addRow("作者/频道：", self.uploader_value)
        info_layout.addRow("时长：", self.duration_value)
        info_layout.addRow("网页 URL：", self.webpage_value)
        info_layout.addRow("平台：", self.platform_value)

        self.formats_view = QPlainTextEdit(info_group)
        self.formats_view.setObjectName("videoFormatsView")
        self.formats_view.setReadOnly(True)
        self.formats_view.setPlaceholderText("解析成功后显示可用格式")
        self.formats_view.setMinimumHeight(130)
        self.formats_view.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        info_layout.addRow("可用格式：", self.formats_view)
        root_layout.addWidget(info_group)

        task_group = QGroupBox("下载任务", self)
        task_group.setObjectName("taskGroup")
        task_layout = QVBoxLayout(task_group)
        task_layout.setContentsMargins(14, 12, 14, 12)
        task_layout.setSpacing(8)

        task_hint = QLabel("当前仅支持信息解析，下载功能将在后续阶段启用", task_group)
        task_hint.setObjectName("taskHint")
        task_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        task_layout.addWidget(task_hint)

        self.download_button = QPushButton("开始下载", task_group)
        self.download_button.setObjectName("downloadButton")
        self.download_button.setEnabled(False)
        self.download_button.setToolTip("下载功能将在后续阶段实现")
        task_layout.addWidget(self.download_button)
        root_layout.addWidget(task_group)

        root_layout.addStretch()
        self.setCentralWidget(central_widget)

    @staticmethod
    def _create_info_label(parent: QWidget, object_name: str) -> QLabel:
        label = QLabel("—", parent)
        label.setObjectName(object_name)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return label

    def _build_status_bar(self) -> None:
        """Create the status bar and show current runtime paths."""
        status_bar = QStatusBar(self)
        status_bar.setObjectName("statusBar")
        self.setStatusBar(status_bar)
        status_message = (
            "基础架构已加载 | 配置："
            f"{get_config_path().name} | 日志：{get_log_file().name}"
        )
        status_bar.showMessage(status_message)

    def _start_parse(self) -> None:
        """Start one background parse request without blocking the GUI thread."""
        if self._is_parsing:
            return

        self._is_parsing = True
        self._set_parsing_state(True)
        self._reset_video_info()
        self._show_parse_status("正在解析视频信息，请稍候…", error=False)

        worker = VideoInfoWorker(self.url_input.text(), parser=self.parser)
        worker.signals.succeeded.connect(self._on_parse_succeeded)
        worker.signals.failed.connect(self._on_parse_failed)
        QThreadPool.globalInstance().start(worker)

    def _set_parsing_state(self, parsing: bool) -> None:
        self.parse_button.setEnabled(not parsing)
        self.url_input.setEnabled(not parsing)
        self.parse_button.setText("正在解析…" if parsing else "解析视频")

    def _reset_video_info(self) -> None:
        for label in (
            self.id_value,
            self.title_value,
            self.uploader_value,
            self.duration_value,
            self.webpage_value,
            self.platform_value,
        ):
            label.setText("—")
        self.formats_view.clear()

    def _on_parse_succeeded(self, video_info: VideoInfo) -> None:
        if not self._is_parsing:
            return

        self._is_parsing = False
        self._set_parsing_state(False)

        self.id_value.setText(video_info.video_id)
        self.title_value.setText(video_info.title)
        self.uploader_value.setText(video_info.uploader)
        self.duration_value.setText(video_info.duration_display)
        self.webpage_value.setText(video_info.webpage_url)
        self.platform_value.setText(self._platform_name(video_info.webpage_url))

        format_lines = [format_item.describe() for format_item in video_info.formats]
        self.formats_view.setPlainText(
            "\n".join(format_lines) if format_lines else "未检测到可用格式"
        )
        self._show_parse_status(
            f"解析成功，共发现 {len(video_info.formats)} 个可用格式",
            error=False,
        )

    def _on_parse_failed(self, user_message: str, _detail: str) -> None:
        if not self._is_parsing:
            return

        self._is_parsing = False
        self._set_parsing_state(False)
        self._show_parse_status(f"解析失败：{user_message}", error=True)

    def _show_parse_status(self, message: str, error: bool) -> None:
        self.parse_status.setText(message)
        self.statusBar().showMessage(message)
        color = "#b42318" if error else "#175cd3"
        self.parse_status.setStyleSheet(f"color: {color};")

    @staticmethod
    def _platform_name(webpage_url: str) -> str:
        try:
            return urlsplit(webpage_url).netloc or "未知"
        except ValueError:
            return "未知"

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt callback name
        """Log window closure without waiting for background parsing."""
        logger.info("Main window closed")
        super().closeEvent(event)