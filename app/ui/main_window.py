"""Main window for the Ruyi Video Downloader phase-one skeleton."""
from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.core.settings import SettingsManager
from app.utils.paths import get_config_path, get_log_file

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """A minimal, stable main window without download functionality."""

    def __init__(self, settings: Optional[SettingsManager] = None, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings or SettingsManager()

        self.setWindowTitle("如意视频下载器")
        self.setMinimumSize(760, 520)
        self.setObjectName("mainWindow")

        self._build_ui()
        self._build_status_bar()

        logger.info("Main window created")

    def _build_ui(self) -> None:
        """Construct the phase-one UI skeleton."""
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

        version_label = QLabel("Ruyi Video Downloader · 第一阶段", self)
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
        url_layout.addRow("视频链接：", self.url_input)

        self.parse_button = QPushButton("解析视频", url_group)
        self.parse_button.setObjectName("parseButton")
        self.parse_button.setEnabled(False)
        self.parse_button.setToolTip("视频解析将在后续阶段实现")
        url_layout.addRow(self.parse_button)
        root_layout.addWidget(url_group)

        info_group = QGroupBox("视频信息", self)
        info_group.setObjectName("videoInfoGroup")
        info_layout = QFormLayout(info_group)
        info_layout.setContentsMargins(14, 12, 14, 12)
        info_layout.setSpacing(8)

        self.title_value = QLabel("—", info_group)
        self.title_value.setObjectName("videoTitleValue")
        self.duration_value = QLabel("—", info_group)
        self.duration_value.setObjectName("videoDurationValue")
        self.platform_value = QLabel("—", info_group)
        self.platform_value.setObjectName("videoPlatformValue")
        info_layout.addRow("标题：", self.title_value)
        info_layout.addRow("时长：", self.duration_value)
        info_layout.addRow("平台：", self.platform_value)
        root_layout.addWidget(info_group)

        task_group = QGroupBox("下载任务", self)
        task_group.setObjectName("taskGroup")
        task_layout = QVBoxLayout(task_group)
        task_layout.setContentsMargins(14, 12, 14, 12)
        task_layout.setSpacing(8)

        task_hint = QLabel("任务列表将在后续阶段启用", task_group)
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

    def _build_status_bar(self) -> None:
        """Create the status bar and show phase-one runtime paths."""
        status_bar = QStatusBar(self)
        status_bar.setObjectName("statusBar")
        self.setStatusBar(status_bar)
        status_message = (
            "基础架构已加载 | 配置："
            f"{get_config_path().name} | 日志：{get_log_file().name}"
        )
        status_bar.showMessage(status_message)

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt callback name
        """Log window closure without performing any download cleanup."""
        logger.info("Main window closed")
        super().closeEvent(event)
