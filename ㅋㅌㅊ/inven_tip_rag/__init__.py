"""메이플 인벤 팁 데이터를 RAG 산출물로 변환하는 파이프라인."""

MODEL_NAME = "jhgan/ko-sroberta-multitask"
MODEL_MAX_TOKENS = 128
DEFAULT_CHUNK_TOKENS = 100
DEFAULT_CHUNK_OVERLAP = 20

__version__ = "0.1.0"
