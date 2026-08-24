import csv
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from inven_tip_rag.pipeline import OutputPaths, run_all
from tests.fakes import FakeEmbeddingModel


class PipelineTests(unittest.TestCase):
    def test_runs_all_stages_and_writes_consistent_outputs(self):
        """단계별 파일의 행 순서·개수가 달라지는 변경을 검출한다."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_path = root / "raw.csv"
            with raw_path.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(
                    stream,
                    fieldnames=["url", "category", "title", "content"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "url": "https://www.inven.co.kr/board/maple/2304/1",
                        "category": "실험",
                        "title": "테스트 팁",
                        "content": " ".join(
                            f"본문{index}" for index in range(30)
                        ),
                    }
                )
                writer.writerow(
                    {
                        "url": "https://www.inven.co.kr/board/maple/2304/2",
                        "category": "기타",
                        "title": "빈 글",
                        "content": "",
                    }
                )

            outputs = OutputPaths.under(root / "out")
            report = run_all(
                input_patterns=[str(raw_path)],
                outputs=outputs,
                model=FakeEmbeddingModel(),
                model_name="fake-model",
                chunk_tokens=10,
                overlap_tokens=2,
                max_tokens=18,
                batch_size=2,
            )

            processed = json.loads(outputs.processed.read_text(encoding="utf-8"))
            rejected = json.loads(outputs.rejected.read_text(encoding="utf-8"))
            chunks = json.loads(outputs.chunks.read_text(encoding="utf-8"))
            vectors = np.load(outputs.embeddings, allow_pickle=False)
            manifest = json.loads(outputs.manifest.read_text(encoding="utf-8"))

            self.assertEqual(len(processed), 1)
            self.assertEqual(rejected[0]["reason"], "empty_content")
            self.assertEqual(len(chunks), vectors.shape[0])
            self.assertEqual(manifest["embedding_count"], len(chunks))
            self.assertEqual(report["input_rows"], 2)
            self.assertTrue(outputs.report.is_file())


if __name__ == "__main__":
    unittest.main()
