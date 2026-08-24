import numpy as np


class FakeTokenizer:
    """공백 단위 토큰 수를 반환하는 빠른 테스트용 tokenizer."""

    def encode(self, text, add_special_tokens=True, truncation=False):
        del truncation
        token_ids = [index + 10 for index, _ in enumerate(text.split())]
        return [1, *token_ids, 2] if add_special_tokens else token_ids


class FakeEmbeddingModel:
    """입력 순서를 구분할 수 있는 deterministic vector를 반환한다."""

    def __init__(self):
        self.tokenizer = FakeTokenizer()

    def encode(
        self,
        texts,
        batch_size,
        show_progress_bar,
        convert_to_numpy,
        normalize_embeddings,
    ):
        del batch_size, show_progress_bar, convert_to_numpy, normalize_embeddings
        rows = []
        for index, text in enumerate(texts, start=1):
            rows.append([float(index), float(len(text.split())), 1.0, 2.0])
        return np.asarray(rows, dtype=np.float32)
