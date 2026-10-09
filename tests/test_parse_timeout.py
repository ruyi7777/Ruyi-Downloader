"""Tests for metadata-only timeout, retry, and cancellation limits."""
from __future__ import annotations

import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.core.video_info import VideoParseCancelled, VideoParseError
from app.services.ytdlp_service import (
    _build_download_options,
    _build_info_options,
    _INFO_EXTRACTOR_RETRIES,
    _INFO_SOCKET_TIMEOUT_SECONDS,
    YtDlpService,
)


def _make_ydl(extract_info):
    ydl = MagicMock()
    ydl.__enter__.return_value = ydl
    ydl.__exit__.return_value = False
    if isinstance(extract_info, dict):
        ydl.extract_info.return_value = extract_info
    else:
        ydl.extract_info.side_effect = extract_info
    return ydl


def _raw_info():
    return {
        "id": "abc123",
        "title": "测试视频",
        "uploader": "测试作者",
        "duration": 63,
        "webpage_url": "https://www.bilibili.com/video/BV123",
        "formats": [
            {
                "format_id": "80",
                "ext": "mp4",
                "resolution": "1280x720",
                "vcodec": "avc1",
                "acodec": "mp4a",
            }
        ],
    }


class ParseTimeoutTests(unittest.TestCase):
    def test_normal_metadata_parse_still_succeeds(self) -> None:
        ydl = _make_ydl(_raw_info())
        with patch(
            "app.services.ytdlp_service.YoutubeDL",
            return_value=ydl,
        ) as youtube_dl:
            result = YtDlpService().extract_video_info(
                "https://www.bilibili.com/video/BV123"
            )

        self.assertEqual(result.video_id, "abc123")
        self.assertEqual(result.title, "测试视频")
        self.assertEqual(len(result.formats), 1)
        options = youtube_dl.call_args.args[0]
        self.assertEqual(
            options["socket_timeout"],
            _INFO_SOCKET_TIMEOUT_SECONDS,
        )
        self.assertEqual(
            options["extractor_retries"],
            _INFO_EXTRACTOR_RETRIES,
        )

    def test_network_timeout_has_specific_chinese_message(self) -> None:
        ydl = _make_ydl(TimeoutError("timed out"))
        with patch(
            "app.services.ytdlp_service.YoutubeDL",
            return_value=ydl,
        ):
            with self.assertRaises(VideoParseError) as context:
                YtDlpService().extract_video_info("https://example.com/video/1")

        self.assertEqual(
            context.exception.user_message,
            "解析超时，请检查网络后重试",
        )
        self.assertNotIn("视频不存在", context.exception.user_message)

    def test_connection_failure_has_specific_chinese_message(self) -> None:
        ydl = _make_ydl(OSError("Connection refused"))
        with patch(
            "app.services.ytdlp_service.YoutubeDL",
            return_value=ydl,
        ):
            with self.assertRaises(VideoParseError) as context:
                YtDlpService().extract_video_info("https://example.com/video/1")

        self.assertEqual(
            context.exception.user_message,
            "网络连接失败，请检查网络后重试",
        )

    def test_other_platform_error_is_not_mapped_to_missing_video(self) -> None:
        ydl = _make_ydl(RuntimeError("HTTP Error 500: Internal Server Error"))
        with patch(
            "app.services.ytdlp_service.YoutubeDL",
            return_value=ydl,
        ):
            with self.assertRaises(VideoParseError) as context:
                YtDlpService().extract_video_info("https://example.com/video/1")

        self.assertEqual(
            context.exception.user_message,
            "解析失败，请检查链接后重试",
        )
        self.assertNotIn("视频不存在", context.exception.user_message)

    def test_parse_limits_are_centralized_and_download_limits_unchanged(self) -> None:
        info_options = _build_info_options()
        self.assertEqual(info_options["socket_timeout"], 12.0)
        self.assertEqual(info_options["extractor_retries"], 1)
        self.assertNotIn("retries", info_options)
        self.assertEqual(info_options["js_runtimes"], {"node": {}})

        download_options = _build_download_options(Path("downloads"))
        self.assertEqual(download_options["socket_timeout"], 15)
        self.assertEqual(download_options["retries"], 2)
        self.assertEqual(download_options["fragment_retries"], 2)
        self.assertNotIn("extractor_retries", download_options)
        self.assertEqual(download_options["js_runtimes"], {"node": {}})

    def test_cancel_event_is_checked_before_request_and_at_logger_checkpoint(self) -> None:
        service = YtDlpService()

        already_cancelled = threading.Event()
        already_cancelled.set()
        with patch("app.services.ytdlp_service.YoutubeDL") as youtube_dl:
            with self.assertRaises(VideoParseCancelled):
                service.extract_video_info(
                    "https://example.com/video/1",
                    cancel_event=already_cancelled,
                )
        youtube_dl.assert_not_called()

        checkpoint_event = threading.Event()
        captured_options = {}

        def factory(options):
            captured_options.update(options)
            ydl = MagicMock()
            ydl.__enter__.return_value = ydl
            ydl.__exit__.return_value = False

            def extract_info(*_args, **_kwargs):
                checkpoint_event.set()
                options["logger"].debug("metadata request checkpoint")
                return _raw_info()

            ydl.extract_info.side_effect = extract_info
            return ydl

        with patch(
            "app.services.ytdlp_service.YoutubeDL",
            side_effect=factory,
        ):
            with self.assertRaises(VideoParseCancelled):
                service.extract_video_info(
                    "https://example.com/video/1",
                    cancel_event=checkpoint_event,
                )

        self.assertIs(
            captured_options["logger"]._cancel_event,
            checkpoint_event,
        )


if __name__ == "__main__":
    unittest.main()
