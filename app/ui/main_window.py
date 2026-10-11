"""Main window for Ruyi Video Downloader parsing and download queues."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

from PyQt6.QtCore import Qt, QThreadPool
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.download_models import (
    DownloadProgress,
    DownloadResult,
    DownloadStatus,
    DownloadTask,
    DownloadTaskStatus,
)
from app.core.downloader import VideoDownloader
from app.core.platform_policy import detect_platform
from app.core.settings import SettingsManager
from app.core.url_extractor import extract_http_urls
from app.core.video_info import VideoInfo
from app.core.video_info_parser import VideoInfoParser
from app.ui.download_queue_controller import DownloadQueueController
from app.ui.video_info_worker import VideoInfoBatchWorker
from app.utils.paths import get_config_path, get_log_file, get_project_root

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main window containing URL parsing and single-video download."""

    def __init__(
        self,
        settings: Optional[SettingsManager] = None,
        parent=None,
        parser: Optional[VideoInfoParser] = None,
        downloader: Optional[VideoDownloader] = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings or SettingsManager()
        self.parser = parser or VideoInfoParser(settings=self.settings)
        self.downloader = downloader or VideoDownloader(settings=self.settings)
        self._is_parsing = False
        self._is_downloading = False
        self._parse_urls: list[str] = []
        self._parse_results: dict[int, VideoInfo] = {}
        self._parse_failure_messages: dict[int, str] = {}
        self._parse_worker: VideoInfoBatchWorker | None = None
        self._parse_task_id = 0
        self._active_parse_task_id: int | None = None
        self._parse_cancel_requested = False
        self._download_queue_controller = DownloadQueueController(
            downloader=self.downloader,
        )
        self._download_queue_snapshots: dict[int, DownloadTask] = {}
        self._current_queue_task_label = ""
        self._download_queue_controller.queue_started.connect(
            self._on_queue_started
        )
        self._download_queue_controller.task_started.connect(
            self._on_queue_task_started
        )
        self._download_queue_controller.task_progress.connect(
            self._on_queue_task_progress
        )
        self._download_queue_controller.task_succeeded.connect(
            self._on_queue_task_succeeded
        )
        self._download_queue_controller.task_failed.connect(
            self._on_queue_task_failed
        )
        self._download_queue_controller.queue_finished.connect(
            self._on_queue_finished
        )

        self.setWindowTitle("如意视频下载器")
        self.setMinimumSize(880, 760)
        self.setObjectName("mainWindow")

        self._build_ui()
        self._build_status_bar()

        logger.info("Main window created")

    def _build_ui(self) -> None:
        """Construct the parsing and single-video download UI."""
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

        version_label = QLabel("Ruyi Video Downloader · URL 解析与顺序下载队列", self)
        version_label.setObjectName("versionLabel")
        header_layout.addWidget(version_label)
        root_layout.addLayout(header_layout)

        url_group = QGroupBox("视频 URL", self)
        url_group.setObjectName("urlGroup")
        url_layout = QFormLayout(url_group)
        url_layout.setContentsMargins(14, 12, 14, 12)
        url_layout.setSpacing(10)

        self.url_input = QPlainTextEdit(url_group)
        self.url_input.setObjectName("urlInput")
        self.url_input.setPlaceholderText(
            "可粘贴任意文字，并自动提取其中的一个或多个 HTTP/HTTPS 链接…"
        )
        self.url_input.setTabChangesFocus(True)
        self.url_input.setMinimumHeight(72)
        self.url_input.setMaximumHeight(120)
        url_layout.addRow("包含链接的文本：", self.url_input)

        parse_button_layout = QHBoxLayout()
        parse_button_layout.setSpacing(8)
        self.parse_button = QPushButton("解析视频", url_group)
        self.parse_button.setObjectName("parseButton")
        self.parse_button.setToolTip(
            "解析视频；解析期间再次点击可取消当前任务"
        )
        self.parse_button.clicked.connect(self._on_parse_button_clicked)
        parse_button_layout.addWidget(self.parse_button)
        parse_button_layout.addStretch()
        url_layout.addRow(parse_button_layout)
        root_layout.addWidget(url_group)

        cookie_group = QGroupBox("Cookie 文件", self)
        cookie_group.setObjectName("cookieGroup")
        cookie_layout = QFormLayout(cookie_group)
        cookie_layout.setContentsMargins(14, 12, 14, 12)
        cookie_layout.setSpacing(10)

        self.cookie_file_value = QLineEdit(cookie_group)
        self.cookie_file_value.setObjectName("cookieFileValue")
        self.cookie_file_value.setReadOnly(True)
        self.cookie_file_value.setPlaceholderText("未配置 Cookie 文件")
        cookie_layout.addRow("Cookie 文件：", self.cookie_file_value)

        cookie_button_layout = QHBoxLayout()
        cookie_button_layout.setSpacing(8)
        self.select_cookie_button = QPushButton("选择 Cookie", cookie_group)
        self.select_cookie_button.setObjectName("selectCookieButton")
        self.select_cookie_button.clicked.connect(self._select_cookie_file)
        self.clear_cookie_button = QPushButton("清除 Cookie", cookie_group)
        self.clear_cookie_button.setObjectName("clearCookieButton")
        self.clear_cookie_button.clicked.connect(self._clear_cookie_file)
        cookie_button_layout.addWidget(self.select_cookie_button)
        cookie_button_layout.addWidget(self.clear_cookie_button)
        cookie_button_layout.addStretch()
        cookie_layout.addRow(cookie_button_layout)
        self._refresh_cookie_display()
        root_layout.addWidget(cookie_group)

        info_group = QGroupBox("视频信息", self)
        info_group.setObjectName("videoInfoGroup")
        info_layout = QFormLayout(info_group)
        info_layout.setContentsMargins(14, 12, 14, 12)
        info_layout.setSpacing(8)

        self.parse_status = QLabel("等待输入包含链接的文本", info_group)
        self.parse_status.setObjectName("parseStatus")
        self.parse_status.setWordWrap(True)
        info_layout.addRow("解析状态：", self.parse_status)

        result_headers = ("序号", "状态", "平台", "标题", "作者/频道", "时长", "URL")
        self.parse_results_table = QTableWidget(0, len(result_headers), info_group)
        self.parse_results_table.setObjectName("parseResultsTable")
        self.parse_results_table.setHorizontalHeaderLabels(result_headers)
        self.parse_results_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.parse_results_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.parse_results_table.setAlternatingRowColors(True)
        self.parse_results_table.verticalHeader().setVisible(False)
        self.parse_results_table.setMinimumHeight(150)
        self.parse_results_table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        header = self.parse_results_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        self.parse_results_table.setColumnWidth(0, 52)
        self.parse_results_table.setColumnWidth(1, 170)
        self.parse_results_table.setColumnWidth(2, 95)
        self.parse_results_table.setColumnWidth(3, 240)
        self.parse_results_table.setColumnWidth(4, 140)
        self.parse_results_table.setColumnWidth(5, 85)
        info_layout.addRow("解析结果：", self.parse_results_table)

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

        path_layout = QHBoxLayout()
        path_layout.setSpacing(8)
        path_layout.addWidget(QLabel("下载目录：", task_group))
        self.download_path_value = QLabel(
            str(self.downloader.download_path),
            task_group,
        )
        self.download_path_value.setObjectName("downloadPathValue")
        self.download_path_value.setWordWrap(True)
        self.download_path_value.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        path_layout.addWidget(self.download_path_value, 1)
        task_layout.addLayout(path_layout)

        queue_label = QLabel("任务队列：", task_group)
        queue_label.setObjectName("downloadQueueLabel")
        task_layout.addWidget(queue_label)

        self.download_queue_table = QTableWidget(0, 4, task_group)
        self.download_queue_table.setObjectName("downloadQueueTable")
        self.download_queue_table.setHorizontalHeaderLabels(
            ("序号", "任务", "状态", "错误信息")
        )
        self.download_queue_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.download_queue_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.download_queue_table.setAlternatingRowColors(True)
        self.download_queue_table.verticalHeader().setVisible(False)
        self.download_queue_table.setMinimumHeight(90)
        queue_header = self.download_queue_table.horizontalHeader()
        queue_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        queue_header.setStretchLastSection(True)
        self.download_queue_table.setColumnWidth(0, 52)
        self.download_queue_table.setColumnWidth(1, 320)
        self.download_queue_table.setColumnWidth(2, 110)
        task_layout.addWidget(self.download_queue_table)

        self.download_status = QLabel("等待开始下载", task_group)
        self.download_status.setObjectName("downloadStatus")
        self.download_status.setWordWrap(True)
        self.download_status.setStyleSheet("color: #175cd3;")
        task_layout.addWidget(self.download_status)

        progress_layout = QFormLayout()
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(6)
        self.download_progress_bar = QProgressBar(task_group)
        self.download_progress_bar.setObjectName("downloadProgressBar")
        self.download_progress_bar.setRange(0, 100)
        self.download_progress_bar.setValue(0)
        self.download_progress_bar.setFormat("等待下载")
        self.download_progress_bar.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        progress_layout.addRow("下载进度：", self.download_progress_bar)
        task_layout.addLayout(progress_layout)

        progress_details_layout = QHBoxLayout()
        progress_details_layout.setSpacing(18)
        self.download_speed_value = QLabel("速度：—", task_group)
        self.download_speed_value.setObjectName("downloadSpeedValue")
        self.download_downloaded_value = QLabel("已下载：—", task_group)
        self.download_downloaded_value.setObjectName("downloadDownloadedValue")
        self.download_eta_value = QLabel("剩余时间：—", task_group)
        self.download_eta_value.setObjectName("downloadEtaValue")
        progress_details_layout.addWidget(self.download_speed_value)
        progress_details_layout.addWidget(self.download_downloaded_value)
        progress_details_layout.addWidget(self.download_eta_value)
        progress_details_layout.addStretch()
        task_layout.addLayout(progress_details_layout)

        self.download_button = QPushButton("开始下载", task_group)
        self.download_button.setObjectName("downloadButton")
        self.download_button.setEnabled(True)
        self.download_button.setToolTip(
            "按解析结果顺序下载任务；没有解析结果时支持单个 URL"
        )
        self.download_button.clicked.connect(self._start_download)
        task_layout.addWidget(self.download_button)
        root_layout.addWidget(task_group)

        root_layout.addStretch()

        # The full content has a larger minimum height than a normal window.
        # A scroll area keeps every group in layout order instead of allowing
        # the layout to compress child widgets until they overlap.
        scroll_area = QScrollArea(self)
        scroll_area.setObjectName("contentScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setWidget(central_widget)
        self.setCentralWidget(scroll_area)

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

    def _refresh_cookie_display(self) -> None:
        """Show only the configured path; never read Cookie contents."""
        configured = str(self.settings.get("cookie_file", "") or "").strip()
        self.clear_cookie_button.setEnabled(bool(configured))

        if not configured:
            self.cookie_file_value.setText("")
            self.cookie_file_value.setToolTip("")
            return

        cookie_path = Path(configured).expanduser()
        if not cookie_path.is_absolute():
            cookie_path = get_project_root() / cookie_path
        if cookie_path.is_file():
            display_path = str(cookie_path.resolve())
            self.cookie_file_value.setText(display_path)
            self.cookie_file_value.setToolTip(display_path)
            return

        self.cookie_file_value.setText(f"Cookie 文件不存在：{configured}")
        self.cookie_file_value.setToolTip(configured)
        logger.warning("Cookie file missing")

    def _select_cookie_file(self) -> None:
        """Choose a Netscape cookies file and save only its path."""
        if self._is_parsing or self._is_downloading:
            return

        start_directory = str(Path.home())
        configured = str(self.settings.get("cookie_file", "") or "").strip()
        if configured:
            current_path = Path(configured).expanduser()
            if current_path.is_dir():
                start_directory = str(current_path)
            elif current_path.parent.is_dir():
                start_directory = str(current_path.parent)

        selected, _filter = QFileDialog.getOpenFileName(
            self,
            "选择 Cookie 文件",
            start_directory,
            "Netscape Cookie 文件 (*.txt);;所有文件 (*)",
        )
        if not selected:
            return

        selected_path = Path(selected).expanduser()
        if not selected_path.is_file():
            QMessageBox.warning(
                self,
                "Cookie 文件错误",
                "Cookie 文件不存在，请重新选择 Cookie 文件。",
            )
            self._refresh_cookie_display()
            return

        self.settings.set(
            "cookie_file",
            str(selected_path.resolve()),
            save=True,
        )
        self._refresh_cookie_display()
        logger.info("Cookie file configured")
        self.statusBar().showMessage("Cookie 文件已配置")

    def _clear_cookie_file(self) -> None:
        """Clear only the application setting, never the user's file."""
        if self._is_parsing or self._is_downloading:
            return

        self.settings.set("cookie_file", "", save=True)
        self._refresh_cookie_display()
        logger.info("Cookie file cleared")
        self.statusBar().showMessage("Cookie 配置已清除，原文件未删除")

    def _on_parse_button_clicked(self) -> None:
        """Use one button to start parsing or request cancellation."""
        if self._parse_cancel_requested:
            return
        if self._is_parsing:
            self._cancel_parse()
            return
        self._start_parse()

    def _start_parse(self) -> None:
        """Extract URLs and start sequential background parsing."""
        if (
            self._is_parsing
            or self._is_downloading
            or self._parse_worker is not None
            or self._active_parse_task_id is not None
        ):
            return

        urls = extract_http_urls(self.url_input.toPlainText())
        if not urls:
            self._show_parse_status(
                "未找到有效的 HTTP/HTTPS 链接，请检查输入内容",
                error=True,
            )
            return

        # Keep the input as the normalized URL list so the next action sees
        # exactly the URLs that were extracted and de-duplicated.
        self.url_input.setPlainText("\n".join(urls))
        self._parse_urls = urls
        self._parse_task_id += 1
        task_id = self._parse_task_id
        self._active_parse_task_id = task_id
        self._parse_cancel_requested = False
        self._is_parsing = True
        self._set_interaction_state("parsing")
        self._reset_video_info()
        self._prepare_parse_results(urls)
        self._show_parse_status(
            f"共提取 {len(urls)} 个链接，开始逐个解析…",
            error=False,
        )

        worker = VideoInfoBatchWorker(urls, parser=self.parser)
        worker.signals.started.connect(
            lambda index, current_task_id=task_id: self._on_parse_started(
                current_task_id,
                index,
            )
        )
        worker.signals.succeeded.connect(
            lambda index, video_info, current_task_id=task_id: (
                self._on_parse_succeeded(current_task_id, index, video_info)
            )
        )
        worker.signals.failed.connect(
            lambda index, user_message, detail, current_task_id=task_id: (
                self._on_parse_failed(
                    current_task_id,
                    index,
                    user_message,
                    detail,
                )
            )
        )
        worker.signals.finished.connect(
            lambda success_count, failure_count, current_task_id=task_id: (
                self._on_parse_finished(
                    current_task_id,
                    success_count,
                    failure_count,
                )
            )
        )
        self._parse_worker = worker
        QThreadPool.globalInstance().start(worker)

    def _cancel_parse(self) -> None:
        """Request cooperative cancellation while keeping the GUI responsive."""
        if (
            not self._is_parsing
            or self._parse_worker is None
            or self._parse_cancel_requested
        ):
            return

        self._parse_cancel_requested = True
        self._parse_worker.cancel()
        self._set_interaction_state("cancelling")
        self._show_parse_status(
            "正在取消解析；当前请求将在超时上限内退出，尚未开始的链接不会继续",
            error=False,
        )

    def _start_download(self) -> None:
        """Start one sequential queue without blocking the GUI thread."""
        if (
            self._is_parsing
            or self._is_downloading
            or self._download_queue_controller.is_running
        ):
            return

        queue_items = self._collect_successful_download_items()
        if not queue_items:
            urls = extract_http_urls(self.url_input.toPlainText())
            if not urls:
                self._show_download_status(
                    "未找到有效的 HTTP/HTTPS 链接，请检查输入内容",
                    error=True,
                )
                return
            if len(urls) > 1:
                self._show_download_status(
                    "多个链接请先解析，再下载本轮解析成功的视频",
                    error=True,
                )
                return
            queue_items = [(urls[0], "")]

        self._is_downloading = True
        self._download_queue_snapshots = {}
        self._current_queue_task_label = ""
        self._set_interaction_state("downloading")
        self._reset_download_progress()
        self.download_queue_table.setRowCount(0)
        self._show_download_status(
            f"准备下载 {len(queue_items)} 个任务…",
            error=False,
        )

        if not self._download_queue_controller.start(queue_items):
            self._is_downloading = False
            self._set_interaction_state("idle")
            self._show_download_status("下载队列启动失败", error=True)

    def _collect_successful_download_items(self) -> list[tuple[str, str]]:
        """Return successful parsed rows in table order."""
        items: list[tuple[str, str]] = []
        for row in range(self.parse_results_table.rowCount()):
            status_item = self.parse_results_table.item(row, 1)
            if status_item is None or not status_item.text().startswith("成功"):
                continue
            video_info = self._parse_results.get(row)
            if video_info is None:
                continue
            url = video_info.webpage_url
            if not url:
                url_item = self.parse_results_table.item(row, 6)
                url = url_item.text() if url_item is not None else ""
            if url:
                items.append((url, video_info.title))
        return items

    @staticmethod
    def _download_task_status_text(status: DownloadTaskStatus) -> str:
        return {
            DownloadTaskStatus.QUEUED: "等待",
            DownloadTaskStatus.RUNNING: "下载中",
            DownloadTaskStatus.COMPLETED: "完成",
            DownloadTaskStatus.FAILED: "失败",
        }[status]

    def _prepare_download_queue(
        self,
        snapshots: tuple[DownloadTask, ...],
    ) -> None:
        self.download_queue_table.setRowCount(len(snapshots))
        for row, task in enumerate(snapshots):
            display_title = task.title or task.url
            values = (
                str(task.task_id),
                display_title,
                self._download_task_status_text(task.status),
                task.error_message,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 1:
                    item.setToolTip(task.url)
                self.download_queue_table.setItem(row, column, item)
            color = "#667085"
            if task.status is DownloadTaskStatus.RUNNING:
                color = "#175cd3"
            elif task.status is DownloadTaskStatus.COMPLETED:
                color = "#027a48"
            elif task.status is DownloadTaskStatus.FAILED:
                color = "#b42318"
            self.download_queue_table.item(row, 2).setForeground(QColor(color))
        self.download_queue_table.resizeRowsToContents()

    def _update_download_queue_task(
        self,
        task: DownloadTask,
        error_message: str = "",
    ) -> None:
        self._download_queue_snapshots[task.task_id] = task
        row = task.task_id - 1
        if row < 0 or row >= self.download_queue_table.rowCount():
            return
        status_item = self.download_queue_table.item(row, 2)
        if status_item is not None:
            status_item.setText(
                self._download_task_status_text(task.status)
            )
            color = "#667085"
            if task.status is DownloadTaskStatus.RUNNING:
                color = "#175cd3"
            elif task.status is DownloadTaskStatus.COMPLETED:
                color = "#027a48"
            elif task.status is DownloadTaskStatus.FAILED:
                color = "#b42318"
            status_item.setForeground(QColor(color))
        error_item = self.download_queue_table.item(row, 3)
        if error_item is not None:
            error_item.setText(
                error_message or task.error_message
            )

    def _on_queue_started(
        self,
        snapshots: tuple[DownloadTask, ...],
        counts,
    ) -> None:
        if not self._is_downloading:
            return
        self._download_queue_snapshots = {
            task.task_id: task for task in snapshots
        }
        self._prepare_download_queue(snapshots)
        self._show_download_status(
            f"下载队列已开始：共 {counts.total} 个任务",
            error=False,
        )

    def _on_queue_task_started(self, task: DownloadTask) -> None:
        if not self._is_downloading:
            return
        self._update_download_queue_task(task)
        total = self.download_queue_table.rowCount()
        title = task.title or task.url
        self._current_queue_task_label = (
            f"第 {task.task_id} / {total} 个：{title}"
        )
        self._reset_download_progress()
        self._show_download_status(
            f"正在下载第 {task.task_id} / {total} 个：{title}",
            error=False,
        )

    def _on_queue_task_progress(
        self,
        task: DownloadTask,
        progress: DownloadProgress,
    ) -> None:
        if not self._is_downloading:
            return
        self._update_download_queue_task(task)
        self._on_download_progress(progress)

    def _on_queue_task_succeeded(
        self,
        task: DownloadTask,
        _result: DownloadResult,
    ) -> None:
        if not self._is_downloading:
            return
        self._update_download_queue_task(task)
        self._show_download_status(
            f"任务 {task.task_id} 下载完成",
            error=False,
        )

    def _on_queue_task_failed(
        self,
        task: DownloadTask,
        user_message: str,
        _detail: str,
    ) -> None:
        if not self._is_downloading:
            return
        self._update_download_queue_task(task, error_message=user_message)
        self._show_download_status(
            f"任务 {task.task_id} 下载失败：{user_message}",
            error=True,
        )

    def _on_queue_finished(self, snapshots, counts) -> None:
        if not self._is_downloading:
            return

        self._is_downloading = False
        self._download_queue_snapshots = {
            task.task_id: task for task in snapshots
        }
        self._prepare_download_queue(snapshots)
        self._current_queue_task_label = ""
        self._set_interaction_state("idle")
        self.download_progress_bar.setRange(0, 100)
        self.download_progress_bar.setValue(0)
        self.download_progress_bar.setFormat("队列结束")
        self.download_speed_value.setText("速度：—")
        self.download_downloaded_value.setText("已下载：—")
        self.download_eta_value.setText("剩余时间：—")
        self._show_download_status(
            f"下载队列完成：成功 {counts.completed} 个，"
            f"失败 {counts.failed} 个",
            error=counts.failed > 0,
        )

    def _set_interaction_state(self, state: str) -> None:
        busy = state != "idle"
        self.parse_button.setEnabled(state in {"idle", "parsing"})
        self.download_button.setEnabled(not busy)
        self.url_input.setEnabled(not busy)

        if state == "parsing":
            self.parse_button.setText("取消解析")
            self.download_button.setText("开始下载")
        elif state == "cancelling":
            self.parse_button.setText("正在取消…")
            self.download_button.setText("开始下载")
        elif state == "downloading":
            self.parse_button.setText("解析视频")
            self.download_button.setText("正在下载…")
        else:
            self.parse_button.setText("解析视频")
            self.download_button.setText("开始下载")

    def _prepare_parse_results(self, urls: list[str]) -> None:
        """Create one waiting row for each extracted URL in input order."""
        self._parse_results = {}
        self._parse_failure_messages = {}
        table = self.parse_results_table
        table.setRowCount(0)

        for index, url in enumerate(urls):
            table.insertRow(index)
            values = (
                str(index + 1),
                "等待",
                self._platform_display(url),
                "—",
                "—",
                "—",
                url,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 6:
                    item.setToolTip(url)
                table.setItem(index, column, item)
            self._set_current_result_status(index, "等待", "#667085")

        table.resizeRowsToContents()

    def _set_current_result_status(self, index: int, status: str, color: str) -> None:
        item = self.parse_results_table.item(index, 1)
        if item is None:
            return
        item.setText(status)
        item.setForeground(QColor(color))

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

    def _is_current_parse_task(self, task_id: int) -> bool:
        return (
            self._active_parse_task_id == task_id
            and self._parse_worker is not None
        )

    def _on_parse_started(self, task_id: int, index: int) -> None:
        if not self._is_current_parse_task(task_id):
            return

        self._set_current_result_status(index, "解析中", "#175cd3")
        if len(self._parse_urls) == 1:
            message = "正在解析视频信息，请稍候…"
        else:
            message = (
                f"正在解析第 {index + 1} / {len(self._parse_urls)} 个链接…"
            )
        self._show_parse_status(message, error=False)

    def _on_parse_succeeded(
        self,
        task_id: int,
        index: int,
        video_info: VideoInfo,
    ) -> None:
        if not self._is_current_parse_task(task_id):
            return

        self._parse_results[index] = video_info
        self._set_current_result_status(index, "成功", "#027a48")
        self._set_result_cell(index, 2, self._platform_display(video_info.webpage_url))
        self._set_result_cell(index, 3, video_info.title)
        self._set_result_cell(index, 4, video_info.uploader)
        self._set_result_cell(index, 5, video_info.duration_display)
        self._set_result_cell(index, 6, video_info.webpage_url)
        self._show_video_info(video_info)

    def _on_parse_failed(
        self,
        task_id: int,
        index: int,
        user_message: str,
        _detail: str,
    ) -> None:
        if not self._is_current_parse_task(task_id):
            return

        self._parse_failure_messages[index] = user_message
        self._set_current_result_status(
            index,
            f"失败：{user_message}",
            "#b42318",
        )
        if len(self._parse_urls) == 1:
            self._show_parse_status(
                self._format_failure("解析失败", user_message),
                error=True,
            )
        else:
            self._show_parse_status(
                f"第 {index + 1} 个链接解析失败：{user_message}；继续解析后续链接…",
                error=True,
            )

    def _on_parse_finished(
        self,
        task_id: int,
        success_count: int,
        failure_count: int,
    ) -> None:
        if not self._is_current_parse_task(task_id):
            logger.debug(
                "Ignoring stale parse signal: task=%s, active=%s",
                task_id,
                self._active_parse_task_id,
            )
            return

        total_count = len(self._parse_urls)
        pending_count = max(0, total_count - success_count - failure_count)
        cancelled = self._parse_cancel_requested and pending_count > 0

        self._is_parsing = False
        self._parse_worker = None
        self._active_parse_task_id = None
        self._parse_cancel_requested = False
        self._set_interaction_state("idle")

        if cancelled:
            self._mark_unfinished_results_as_cancelled()
            message = (
                f"解析已取消：成功 {success_count} 个，"
                f"失败 {failure_count} 个，未完成 {pending_count} 个"
            )
            self._show_parse_status(message, error=False)
            logger.info(
                "Parsing cancelled from GUI: total=%s, success=%s, "
                "failure=%s, pending=%s",
                total_count,
                success_count,
                failure_count,
                pending_count,
            )
            return

        if failure_count == 0:
            message = f"解析完成：成功 {success_count} 个"
        elif success_count == 0 and len(self._parse_urls) == 1:
            message = self._format_failure(
                "解析失败",
                next(iter(self._parse_failure_messages.values()), "解析失败"),
            )
        else:
            message = (
                f"解析完成：成功 {success_count} 个，失败 {failure_count} 个"
            )
        self._show_parse_status(message, error=failure_count > 0)

    def _mark_unfinished_results_as_cancelled(self) -> None:
        """Preserve completed rows and mark only unfinished rows as cancelled."""
        for row in range(self.parse_results_table.rowCount()):
            item = self.parse_results_table.item(row, 1)
            if item is None:
                continue
            if item.text() in {"等待", "解析中"}:
                self._set_current_result_status(row, "已取消", "#667085")

    def _show_video_info(self, video_info: VideoInfo) -> None:
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

    def _set_result_cell(self, index: int, column: int, value: str) -> None:
        item = self.parse_results_table.item(index, column)
        if item is None:
            item = QTableWidgetItem(value)
            self.parse_results_table.setItem(index, column, item)
            return
        item.setText(value)
        if column == 6:
            item.setToolTip(value)

    def _reset_download_progress(self) -> None:
        self.download_progress_bar.setRange(0, 100)
        self.download_progress_bar.setValue(0)
        self.download_progress_bar.setFormat("等待下载")
        self.download_speed_value.setText("速度：—")
        self.download_downloaded_value.setText("已下载：—")
        self.download_eta_value.setText("剩余时间：—")

    def _on_download_progress(self, progress: DownloadProgress) -> None:
        """Update progress widgets in the GUI thread from worker signals."""
        if not self._is_downloading:
            return

        if progress.status is DownloadStatus.FAILED:
            self.download_progress_bar.setRange(0, 100)
            self.download_progress_bar.setValue(0)
            self.download_progress_bar.setFormat("下载失败")
            self.download_speed_value.setText("速度：—")
            self.download_eta_value.setText("剩余时间：—")
            self._set_download_progress_status("下载失败", error=True)
            return

        if progress.status is DownloadStatus.COMPLETED:
            self._complete_download_progress()
            return

        self._set_download_progress_status(
            "下载分段完成，继续处理…"
            if progress.status is DownloadStatus.PARTIAL_FINISHED
            else "下载中",
            error=False,
        )

        if progress.percent is None:
            self.download_progress_bar.setRange(0, 0)
            self.download_progress_bar.setFormat("下载中")
        else:
            self.download_progress_bar.setRange(0, 100)
            self.download_progress_bar.setValue(int(round(progress.percent)))
            self.download_progress_bar.setFormat("%p%")

        speed_text = (
            f"{self._format_bytes(progress.speed)}/s"
            if progress.speed is not None
            else "—"
        )
        self.download_speed_value.setText(f"速度：{speed_text}")
        self.download_downloaded_value.setText(
            self._format_downloaded_size(progress)
        )
        self.download_eta_value.setText(
            f"剩余时间：{self._format_eta(progress.eta)}"
        )

    def _complete_download_progress(self) -> None:
        self.download_progress_bar.setRange(0, 100)
        self.download_progress_bar.setValue(100)
        self.download_progress_bar.setFormat("100%")
        self.download_speed_value.setText("速度：—")
        self.download_eta_value.setText("剩余时间：—")

    def _set_download_progress_status(self, message: str, error: bool) -> None:
        if self._current_queue_task_label:
            message = f"{self._current_queue_task_label}｜{message}"
        self.download_status.setText(message)
        color = "#b42318" if error else "#175cd3"
        self.download_status.setStyleSheet(f"color: {color};")

    def _on_download_succeeded(self, result: DownloadResult) -> None:
        if not self._is_downloading:
            return

        self._is_downloading = False
        self._set_interaction_state("idle")
        self._complete_download_progress()
        self._show_download_status(
            f"下载完成：{result.file_name}",
            error=False,
        )

    def _on_download_failed(self, user_message: str, _detail: str) -> None:
        if not self._is_downloading:
            return

        self._is_downloading = False
        self._set_interaction_state("idle")
        self.download_progress_bar.setRange(0, 100)
        self.download_progress_bar.setValue(0)
        self.download_progress_bar.setFormat("下载失败")
        self.download_speed_value.setText("速度：—")
        self.download_downloaded_value.setText("已下载：—")
        self.download_eta_value.setText("剩余时间：—")
        self._show_download_status(
            self._format_failure("下载失败", user_message),
            error=True,
        )

    @staticmethod
    def _format_downloaded_size(progress: DownloadProgress) -> str:
        downloaded = (
            MainWindow._format_bytes(progress.downloaded_bytes)
            if progress.downloaded_bytes is not None
            else "未知"
        )
        if progress.total_bytes is None:
            return f"已下载：{downloaded} / 未知总大小"

        total_prefix = "约 " if progress.total_is_estimate else ""
        total = f"{total_prefix}{MainWindow._format_bytes(progress.total_bytes)}"
        return f"已下载：{downloaded} / {total}"

    @staticmethod
    def _format_bytes(value: Optional[float]) -> str:
        if value is None or value < 0:
            return "未知"

        units = ("B", "KB", "MB", "GB", "TB")
        size = float(value)
        unit_index = 0
        while size >= 1024.0 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1

        if unit_index == 0:
            return f"{int(round(size))} {units[unit_index]}"
        if size < 10:
            return f"{size:.1f} {units[unit_index]}"
        return f"{size:.0f} {units[unit_index]}"

    @staticmethod
    def _format_eta(seconds: Optional[int]) -> str:
        if seconds is None or seconds < 0:
            return "—"

        total_seconds = int(seconds)
        if total_seconds < 60:
            return f"{total_seconds} 秒"
        if total_seconds < 3600:
            minutes, remaining = divmod(total_seconds, 60)
            if remaining:
                return f"{minutes} 分 {remaining} 秒"
            return f"{minutes} 分"

        hours, remaining = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remaining, 60)
        if minutes and seconds:
            return f"{hours} 小时 {minutes} 分 {seconds} 秒"
        if minutes:
            return f"{hours} 小时 {minutes} 分"
        return f"{hours} 小时"

    @staticmethod
    def _format_failure(prefix: str, message: str) -> str:
        if message.startswith(prefix):
            return message
        return f"{prefix}：{message}"

    def _show_download_status(self, message: str, error: bool) -> None:
        self.download_status.setText(message)
        self.statusBar().showMessage(message)
        color = "#b42318" if error else "#175cd3"
        self.download_status.setStyleSheet(f"color: {color};")

    def _show_parse_status(self, message: str, error: bool) -> None:
        self.parse_status.setText(message)
        self.statusBar().showMessage(message)
        color = "#b42318" if error else "#175cd3"
        self.parse_status.setStyleSheet(f"color: {color};")

    @staticmethod
    def _platform_display(url: str) -> str:
        platform_names = {
            "youtube": "YouTube",
            "bilibili": "Bilibili",
            "tiktok": "TikTok",
            "x": "X",
            "douyin": "抖音",
        }
        platform = detect_platform(url)
        if platform != "unknown":
            return platform_names.get(platform, platform)
        try:
            return urlsplit(url).netloc or "未知"
        except ValueError:
            return "未知"

    @staticmethod
    def _platform_name(webpage_url: str) -> str:
        try:
            return urlsplit(webpage_url).netloc or "未知"
        except ValueError:
            return "未知"

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt callback name
        """Request cancellation on close without blocking the GUI thread."""
        if self._parse_worker is not None:
            self._parse_worker.cancel()
        logger.info("Main window closed")
        super().closeEvent(event)
