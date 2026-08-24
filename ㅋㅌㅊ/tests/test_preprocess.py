import unittest

from inven_tip_rag.preprocess import (
    canonicalize_url,
    normalize_text,
    preprocess_rows,
)


def raw_row(**overrides):
    row = {
        "url": "https://www.inven.co.kr/board/maple/2304/48082?query=1#part",
        "category": " 실험 ",
        "title": " 제목 &amp; 안내 ",
        "author": "",
        "created_at": "2026-08-03 12:43",
        "views": "12,988",
        "likes": "18",
        "content": "첫 문장\r\n\r\n  둘째   문장 &amp; 설명 ",
        "__source_file": "tips.csv",
        "__source_row": 2,
    }
    row.update(overrides)
    return row


class PreprocessTests(unittest.TestCase):
    def test_normalizes_url_text_numbers_and_date(self):
        """원문 정규화나 타입 변환이 빠지는 변경을 검출한다."""
        processed, rejected, stats = preprocess_rows([raw_row()])

        self.assertEqual(rejected, [])
        self.assertEqual(
            processed[0]["url"],
            "https://www.inven.co.kr/board/maple/2304/48082",
        )
        self.assertEqual(processed[0]["title"], "제목 & 안내")
        self.assertEqual(processed[0]["content"], "첫 문장\n\n둘째 문장 & 설명")
        self.assertEqual(processed[0]["created_at"], "2026-08-03T12:43:00")
        self.assertEqual(processed[0]["views"], 12988)
        self.assertEqual(processed[0]["likes"], 18)
        self.assertEqual(processed[0]["document_id"], "inven_tip_48082")
        self.assertEqual(stats["accepted_rows"], 1)

    def test_rejects_empty_content_with_source_location(self):
        """근거 없는 빈 본문을 RAG 문서로 통과시키는 변경을 검출한다."""
        processed, rejected, stats = preprocess_rows([raw_row(content="   ")])

        self.assertEqual(processed, [])
        self.assertEqual(rejected[0]["reason"], "empty_content")
        self.assertEqual(rejected[0]["source_row"], 2)
        self.assertEqual(stats["rejected_rows"], 1)

    def test_marks_short_nonempty_content_without_rejecting_it(self):
        """이미지 중심의 짧은 글을 무조건 삭제하는 변경을 검출한다."""
        processed, rejected, _ = preprocess_rows([raw_row(content="짧은 팁")])

        self.assertEqual(rejected, [])
        self.assertEqual(processed[0]["text_quality"], "short")

    def test_last_valid_duplicate_url_wins(self):
        """추가 CSV의 최신 레코드가 반영되지 않는 변경을 검출한다."""
        first = raw_row(title="이전 제목")
        second = raw_row(title="최신 제목", __source_row=3)

        processed, rejected, stats = preprocess_rows([first, second])

        self.assertEqual([item["title"] for item in processed], ["최신 제목"])
        self.assertEqual(rejected[0]["reason"], "duplicate_url_replaced")
        self.assertEqual(stats["duplicate_rows"], 1)

    def test_helpers_are_deterministic(self):
        """URL query 제거 또는 Unicode·문단 정규화가 회귀하는 변경을 검출한다."""
        self.assertEqual(
            canonicalize_url("https://a.test/1/?x=1#y"),
            "https://a.test/1",
        )
        self.assertEqual(normalize_text("Ａ  B\r\n\r\n C"), "A B\n\nC")


if __name__ == "__main__":
    unittest.main()
