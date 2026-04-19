import unittest

from app.utils.case_points_text import format_case_points, parse_case_points_text


class TestCasePointsText(unittest.TestCase):
    def test_parse_ok(self) -> None:
        raw = "2024-01-02, 杭州\n\n2024-03-01,上海"
        pts, err = parse_case_points_text(raw)
        self.assertIsNone(err)
        self.assertEqual(pts, [("2024-01-02", "杭州"), ("2024-03-01", "上海")])

    def test_parse_error_comma(self) -> None:
        pts, err = parse_case_points_text("nodatecity")
        self.assertIn("逗号", err or "")
        self.assertEqual(pts, [])

    def test_format_roundtrip(self) -> None:
        pairs = [("a", "b")]
        text = format_case_points(pairs)
        pts, err = parse_case_points_text(text)
        self.assertIsNone(err)
        self.assertEqual(pts, pairs)


if __name__ == "__main__":
    unittest.main()
