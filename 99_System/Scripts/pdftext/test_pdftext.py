import json
from pathlib import Path
import tempfile
import unittest

import pdftext as app


def line(text, x, y, width=180, height=16):
    return dict(text=text, x0=x, y0=y, x1=x + width, y1=y + height, score=.99)


class Tests(unittest.TestCase):
    def test_page_range_validation(self):
        self.assertEqual(app.page_range("1-3,2,5", 5), [1, 2, 3, 5])
        for value in ["0", "6", "3-2", "x", "1,"]:
            with self.assertRaises(ValueError):
                app.page_range(value, 5)

    def test_spread_reading_order_and_override(self):
        lines = [line(f"左{i}", 40, 80 + i*28) for i in range(9)]
        lines += [line(f"右{i}", 540, 80 + i*28) for i in range(9)]
        layout, regions, _ = app.partition_lines(lines, 1000, 700, "auto")
        self.assertEqual(layout, "spread")
        self.assertTrue(all(r["text"].startswith("左") for r in regions[0]["lines"]))
        self.assertTrue(all(r["text"].startswith("右") for r in regions[1]["lines"]))
        self.assertEqual(app.select_layout(lines, 1000, 700, "single")[0], "single")

    def test_landscape_single_not_cut(self):
        lines = [line("full width line", 40, 80 + i*28, 850) for i in range(10)]
        self.assertEqual(app.select_layout(lines, 1000, 700, "auto")[0], "single")

    def test_portrait_columns_are_flagged_not_split(self):
        lines = [line("column", x, 180 + i*28, 180) for x in [40, 380] for i in range(12)]
        layout, _, warnings = app.select_layout(lines, 650, 900, "auto")
        self.assertEqual(layout, "single")
        self.assertTrue(warnings)

    def test_crossing_text_not_lost(self):
        text = line("center title", 450, 40, 100)
        _, regions, warnings = app.partition_lines([text], 1000, 700, "spread")
        self.assertEqual(sum(len(r["lines"]) for r in regions), 1)
        self.assertTrue(warnings)

    def test_margin_cleanup_preserves_body_repetition(self):
        pages = []
        for n in range(1, 5):
            lines = [line("页眉", 40, 10), line("页眉", 40, 250), line(f"一{n}—", 200, 940)]
            pages.append(dict(page=n, height=1000, warnings=[], regions=[dict(lines=lines)]))
        app.clean_pages(pages, False)
        self.assertEqual(pages[0]["regions"][0]["text"], "页眉")
        self.assertEqual(len(pages[0]["regions"][0]["removed_margins"]), 2)

    def test_english_and_chinese_spacing(self):
        self.assertEqual(app.join_words("你好", "世界"), "你好世界")
        self.assertEqual(app.join_words("hello", "world"), "hello world")

    def test_cache_rejects_partial_tamper_or_parameters(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            app.atomic_text(root / "document.md", "正文")
            report = dict(identity={"x": 1}, status="review", files={"document.md": app.digest(root / "document.md")})
            app.save_json(root / "report.json", report)
            self.assertTrue(app.cache_valid(root, {"x": 1}))
            self.assertFalse(app.cache_valid(root, {"x": 2}))
            report["status"] = "partial"
            app.save_json(root / "report.json", report)
            self.assertFalse(app.cache_valid(root, {"x": 1}))
            report["status"] = "review"
            app.save_json(root / "report.json", report)
            app.atomic_text(root / "document.md", "修改")
            self.assertFalse(app.cache_valid(root, {"x": 1}))


if __name__ == "__main__":
    unittest.main()
