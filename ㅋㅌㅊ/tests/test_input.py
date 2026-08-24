import csv
import tempfile
import unittest
from pathlib import Path

from inven_tip_rag.input import InputSchemaError, discover_input_files, load_csv_rows


class InputTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_csv(self, name, fieldnames, rows):
        path = self.root / name
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_discovers_literal_repeated_and_glob_inputs_without_duplicates(self):
        """중복 파일을 반환하는 변경을 검출한다."""
        first = self.write_csv("tips_1.csv", ["url", "title", "content"], [])
        second = self.write_csv("tips_2.csv", ["url", "title", "content"], [])

        found = discover_input_files([str(first), str(self.root / "tips_*.csv")])

        self.assertEqual(found, [first.resolve(), second.resolve()])

    def test_raises_when_pattern_matches_nothing(self):
        """잘못된 입력 패턴을 조용히 무시하는 변경을 검출한다."""
        with self.assertRaisesRegex(FileNotFoundError, "입력 CSV를 찾지 못했습니다"):
            discover_input_files([str(self.root / "missing_*.csv")])

    def test_raises_with_missing_required_columns(self):
        """본문 컬럼 없이 처리를 계속하는 변경을 검출한다."""
        path = self.write_csv("bad.csv", ["url", "title"], [])

        with self.assertRaisesRegex(InputSchemaError, "content"):
            load_csv_rows([path])

    def test_loads_utf8_sig_and_records_source_location(self):
        """BOM 또는 원본 행 추적 정보를 잃는 변경을 검출한다."""
        path = self.write_csv(
            "tips.csv",
            ["url", "title", "content"],
            [{"url": "https://example.com/1", "title": "제목", "content": "본문"}],
        )

        rows = load_csv_rows([path])

        self.assertEqual(rows[0]["title"], "제목")
        self.assertEqual(rows[0]["__source_file"], str(path.resolve()))
        self.assertEqual(rows[0]["__source_row"], 2)


if __name__ == "__main__":
    unittest.main()
