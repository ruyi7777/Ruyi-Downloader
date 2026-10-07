"""Tests for extracting URLs from arbitrary pasted text."""
from __future__ import annotations

import unittest

from app.core.url_extractor import extract_http_urls, is_valid_http_url


class ExtractHttpUrlsTests(unittest.TestCase):
    def test_extracts_url_between_chinese_text(self) -> None:
        text = "视频地址：https://youtu.be/abc123，快去看看！"
        self.assertEqual(
            extract_http_urls(text),
            ["https://youtu.be/abc123"],
        )

    def test_removes_ascii_and_chinese_wrappers(self) -> None:
        cases = (
            "[https://youtu.be/abc123]",
            "(https://youtu.be/abc123)",
            "<https://youtu.be/abc123>",
            '"https://youtu.be/abc123"',
            "' https://youtu.be/abc123 '",
            "地址：https://www.bilibili.com/video/BV123【推荐】",
        )
        for text in cases:
            with self.subTest(text=text):
                self.assertEqual(
                    extract_http_urls(text),
                    ["https://youtu.be/abc123"]
                    if "bilibili" not in text
                    else ["https://www.bilibili.com/video/BV123"],
                )

    def test_extracts_multiple_urls_from_one_line_and_multiple_lines(self) -> None:
        one_line = (
            "YouTube：https://youtu.be/aaa "
            "B站：https://www.bilibili.com/video/BV123 "
            "抖音：https://www.douyin.com/xxx"
        )
        multiple_lines = (
            "视频1：https://youtu.be/aaa\n"
            "视频2：https://www.bilibili.com/video/BV123\n"
            "视频3：https://www.douyin.com/xxx"
        )
        expected = [
            "https://youtu.be/aaa",
            "https://www.bilibili.com/video/BV123",
            "https://www.douyin.com/xxx",
        ]
        self.assertEqual(extract_http_urls(one_line), expected)
        self.assertEqual(extract_http_urls(multiple_lines), expected)

    def test_preserves_query_fragment_and_internal_url_characters(self) -> None:
        text = (
            "地址：https://www.youtube.com/watch?v=abc123&t=30"
            "#detail，点击查看。"
        )
        self.assertEqual(
            extract_http_urls(text),
            ["https://www.youtube.com/watch?v=abc123&t=30#detail"],
        )

    def test_supports_http_and_unknown_platforms(self) -> None:
        text = "http://example.com/video/123 https://unknown.example.org/watch?v=1"
        self.assertEqual(
            extract_http_urls(text),
            [
                "http://example.com/video/123",
                "https://unknown.example.org/watch?v=1",
            ],
        )

    def test_deduplicates_while_preserving_first_occurrence_order(self) -> None:
        text = """
        https://youtu.be/abc123
        https://youtu.be/abc123
        https://youtu.be/def456
        https://youtu.be/abc123
        """
        self.assertEqual(
            extract_http_urls(text),
            [
                "https://youtu.be/abc123",
                "https://youtu.be/def456",
            ],
        )

    def test_skips_empty_or_invalid_http_candidates(self) -> None:
        self.assertEqual(extract_http_urls(""), [])
        self.assertEqual(extract_http_urls("没有链接 http://"), [])
        self.assertFalse(is_valid_http_url("https://"))
        self.assertFalse(is_valid_http_url("ftp://example.com/video"))


if __name__ == "__main__":
    unittest.main()
