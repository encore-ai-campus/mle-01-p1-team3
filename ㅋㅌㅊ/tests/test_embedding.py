import tempfile
import unittest
from pathlib import Path

import numpy as np

from inven_tip_rag.embedding import build_manifest, embed_chunks, sha256_file
from tests.fakes import FakeEmbeddingModel


class EmbeddingTests(unittest.TestCase):
    def setUp(self):
        self.chunks = [
            {
                "id": f"inven_tip_1_{index}",
                "page_content": f"본문 {index}",
                "metadata": {
                    "name": "제목",
                    "section_title": "실험",
                    "chunk_id": f"inven_tip_1_{index}",
                    "embedding_prefix": "문서 제목: 제목\n카테고리: 실험",
                },
            }
            for index in range(2)
        ]

    def test_returns_float32_unit_vectors_in_chunk_order(self):
        """행 순서를 바꾸거나 정규화를 생략하는 변경을 검출한다."""
        vectors = embed_chunks(
            self.chunks,
            FakeEmbeddingModel(),
            batch_size=2,
            max_tokens=128,
        )

        self.assertEqual(vectors.shape, (2, 4))
        self.assertEqual(vectors.dtype, np.float32)
        np.testing.assert_allclose(
            np.linalg.norm(vectors, axis=1),
            np.ones(2),
            atol=1e-6,
        )
        self.assertFalse(np.array_equal(vectors[0], vectors[1]))

    def test_builds_manifest_with_checksums_and_chunk_order(self):
        """다른 실행의 JSON과 NPY를 함께 전달하는 오류를 검출한다."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            chunks_path = root / "chunks.json"
            vectors_path = root / "vectors.npy"
            chunks_path.write_text("[]", encoding="utf-8")
            np.save(vectors_path, np.ones((2, 4), dtype=np.float32))

            manifest = build_manifest(
                chunks=self.chunks,
                vectors=np.ones((2, 4), dtype=np.float32),
                chunks_path=chunks_path,
                vectors_path=vectors_path,
                model_name="fake-model",
                chunk_tokens=100,
                overlap_tokens=20,
                max_tokens=128,
            )

            self.assertEqual(
                manifest["chunk_ids"],
                ["inven_tip_1_0", "inven_tip_1_1"],
            )
            self.assertEqual(manifest["embedding_dimension"], 4)
            self.assertEqual(
                manifest["chunks_sha256"],
                sha256_file(chunks_path),
            )


if __name__ == "__main__":
    unittest.main()
