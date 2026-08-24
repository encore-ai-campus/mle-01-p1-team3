import unittest

from inven_tip_rag.chunking import build_embedding_text, chunk_records, count_tokens
from tests.fakes import FakeTokenizer


class ChunkingTests(unittest.TestCase):
    def setUp(self):
        self.tokenizer = FakeTokenizer()
        self.record = {
            "document_id": "inven_tip_48082",
            "article_id": "48082",
            "url": "https://www.inven.co.kr/board/maple/2304/48082",
            "category": "실험",
            "title": "쿨타임 시스템 안내",
            "created_at": "2026-08-03T12:43:00",
            "views": 12988,
            "likes": 18,
            "content": " ".join(f"단어{index}" for index in range(30)),
            "text_quality": "normal",
        }

    def test_creates_stable_unique_ids_and_metadata(self):
        """청크 식별자 또는 기존 가이드 라우팅 계약이 깨지는 변경을 검출한다."""
        chunks = chunk_records(
            [self.record],
            self.tokenizer,
            chunk_tokens=10,
            overlap_tokens=2,
            max_tokens=18,
        )

        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0]["id"], "inven_tip_48082_0")
        self.assertEqual(chunks[0]["metadata"]["source"], "guide")
        self.assertEqual(chunks[0]["metadata"]["origin"], "inven_tip")
        self.assertEqual(len({item["id"] for item in chunks}), len(chunks))

    def test_every_embedding_text_fits_model_limit(self):
        """모델이 입력 뒷부분을 잘라내는 청크를 생성하는 변경을 검출한다."""
        chunks = chunk_records(
            [self.record],
            self.tokenizer,
            chunk_tokens=10,
            overlap_tokens=2,
            max_tokens=18,
        )

        for chunk in chunks:
            text = build_embedding_text(chunk, self.tokenizer, max_tokens=18)
            self.assertLessEqual(
                count_tokens(self.tokenizer, text, special_tokens=True),
                18,
            )

    def test_rejects_invalid_chunk_options(self):
        """0 크기나 청크보다 큰 중첩으로 무한 분할하는 변경을 검출한다."""
        with self.assertRaisesRegex(ValueError, "chunk_tokens"):
            chunk_records(
                [self.record],
                self.tokenizer,
                chunk_tokens=0,
                overlap_tokens=0,
            )
        with self.assertRaisesRegex(ValueError, "overlap_tokens"):
            chunk_records(
                [self.record],
                self.tokenizer,
                chunk_tokens=10,
                overlap_tokens=10,
            )


if __name__ == "__main__":
    unittest.main()
