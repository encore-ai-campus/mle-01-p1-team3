# ChromaDB Schema and OpenAI System Prompt

이 문서는 실제 SQLite 파일 `chroma_db/chroma.sqlite3`를 기준으로 정리한 ChromaDB 스키마와, 해당 스키마를 OpenAI API 모델에 알려주기 위한 system prompt 예시를 담고 있다.

## Source

- Database file: `chroma_db/chroma.sqlite3`
- Inspected date: 2026-08-23

## Schema Overview

이 데이터베이스는 대체로 다음 계층으로 이해할 수 있다.

`tenants -> databases -> collections -> segments -> embeddings`

메타데이터는 컬렉션, 세그먼트, 임베딩 각각에 대해 별도 테이블로 분리되어 있으며, 문자열 검색을 위한 FTS5 가상 테이블도 포함되어 있다.

## Tables

### 1. `tenants`

테넌트 식별자 저장 테이블.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | `TEXT` | `PRIMARY KEY` | Tenant identifier |

### 2. `databases`

테넌트 하위 데이터베이스 정보.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | `TEXT` | `PRIMARY KEY` | Database identifier |
| `name` | `TEXT` | `NOT NULL` | Database name, unique per tenant |
| `tenant_id` | `TEXT` | `NOT NULL`, `REFERENCES tenants(id) ON DELETE CASCADE` | Owning tenant |

제약 조건:

- `UNIQUE (tenant_id, name)`

### 3. `collections`

벡터 컬렉션 정의 테이블.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | `TEXT` | `PRIMARY KEY` | Collection identifier |
| `name` | `TEXT` | `NOT NULL` | Collection name, unique per database |
| `dimension` | `INTEGER` |  | Embedding dimension |
| `database_id` | `TEXT` | `NOT NULL`, `REFERENCES databases(id) ON DELETE CASCADE` | Owning database |
| `config_json_str` | `TEXT` |  | Collection config JSON |
| `schema_str` | `TEXT` |  | Collection schema JSON/string |

제약 조건:

- `UNIQUE (name, database_id)`

### 4. `collection_metadata`

컬렉션 메타데이터를 key-value 형태로 저장.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `collection_id` | `TEXT` | `REFERENCES collections(id) ON DELETE CASCADE` | Target collection |
| `key` | `TEXT` | `NOT NULL` | Metadata key |
| `str_value` | `TEXT` |  | String value |
| `int_value` | `INTEGER` |  | Integer value |
| `float_value` | `REAL` |  | Float value |
| `bool_value` | `INTEGER` |  | Boolean-like value stored as integer |

제약 조건:

- `PRIMARY KEY (collection_id, key)`

### 5. `segments`

컬렉션 내부 세그먼트 정의 테이블.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | `TEXT` | `PRIMARY KEY` | Segment identifier |
| `type` | `TEXT` | `NOT NULL` | Segment type |
| `scope` | `TEXT` | `NOT NULL` | Segment scope |
| `collection` | `TEXT` | `NOT NULL` | Owning collection reference |

주의:

- 실제 DDL은 `collection TEXT REFERENCES collection(id) NOT NULL` 로 정의되어 있다.
- 의미상으로는 `collections.id` 를 참조하는 관계로 해석하는 것이 자연스럽다.

### 6. `segment_metadata`

세그먼트 메타데이터를 key-value 형태로 저장.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `segment_id` | `TEXT` | `REFERENCES segments(id) ON DELETE CASCADE` | Target segment |
| `key` | `TEXT` | `NOT NULL` | Metadata key |
| `str_value` | `TEXT` |  | String value |
| `int_value` | `INTEGER` |  | Integer value |
| `float_value` | `REAL` |  | Float value |
| `bool_value` | `INTEGER` |  | Boolean-like value stored as integer |

제약 조건:

- `PRIMARY KEY (segment_id, key)`

### 7. `embeddings`

개별 임베딩 엔트리의 핵심 레코드.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `PRIMARY KEY` | Internal embedding row id |
| `segment_id` | `TEXT` | `NOT NULL` | Owning segment id |
| `embedding_id` | `TEXT` | `NOT NULL` | External or logical embedding id |
| `seq_id` | `BLOB` | `NOT NULL` | Sequence identifier |
| `created_at` | `TIMESTAMP` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Creation time |

제약 조건:

- `UNIQUE (segment_id, embedding_id)`

### 8. `embedding_metadata`

임베딩 단일값 메타데이터 저장 테이블.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `REFERENCES embeddings(id)` | Target embedding row id |
| `key` | `TEXT` | `NOT NULL` | Metadata key |
| `string_value` | `TEXT` |  | String value |
| `int_value` | `INTEGER` |  | Integer value |
| `float_value` | `REAL` |  | Float value |
| `bool_value` | `INTEGER` |  | Boolean-like value stored as integer |

제약 조건:

- `PRIMARY KEY (id, key)`

인덱스:

- `embedding_metadata_string_value`
- `embedding_metadata_int_value`
- `embedding_metadata_float_value`

### 9. `embedding_metadata_array`

임베딩 다중값 메타데이터 저장 테이블.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `NOT NULL`, `REFERENCES embeddings(id)` | Target embedding row id |
| `key` | `TEXT` | `NOT NULL` | Metadata key |
| `string_value` | `TEXT` |  | String value |
| `int_value` | `INTEGER` |  | Integer value |
| `float_value` | `REAL` |  | Float value |
| `bool_value` | `INTEGER` |  | Boolean-like value stored as integer |

인덱스:

- `embedding_metadata_array_id_key`
- `embedding_metadata_array_key_string`
- `embedding_metadata_array_key_int`
- `embedding_metadata_array_key_float`

### 10. `embeddings_queue`

임베딩 처리 작업 또는 이벤트 큐.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `seq_id` | `INTEGER` | `PRIMARY KEY` | Queue sequence id |
| `created_at` | `TIMESTAMP` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Queue insertion time |
| `operation` | `INTEGER` | `NOT NULL` | Operation code |
| `topic` | `TEXT` | `NOT NULL` | Queue topic |
| `id` | `TEXT` | `NOT NULL` | Target record id |
| `vector` | `BLOB` |  | Serialized vector payload |
| `encoding` | `TEXT` |  | Vector encoding |
| `metadata` | `TEXT` |  | Metadata payload |

### 11. `embeddings_queue_config`

큐 설정 저장 테이블.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `PRIMARY KEY` | Config row id |
| `config_json_str` | `TEXT` |  | Queue config JSON |

### 12. `max_seq_id`

세그먼트별 최대 시퀀스 추적.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `segment_id` | `TEXT` | `PRIMARY KEY` | Segment id |
| `seq_id` | `INTEGER` |  | Max sequence id |

### 13. `acquire_write`

쓰기 락 관리 테이블.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `PRIMARY KEY` | Lock row id |
| `lock_status` | `INTEGER` | `NOT NULL` | Lock status |

### 14. `maintenance_log`

유지보수 작업 기록 테이블.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | `INT` | `PRIMARY KEY` | Log id |
| `timestamp` | `INT` | `NOT NULL` | Operation time |
| `operation` | `TEXT` | `NOT NULL` | Operation name |

### 15. `migrations`

마이그레이션 이력 테이블.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `dir` | `TEXT` | `NOT NULL` | Migration directory |
| `version` | `INTEGER` | `NOT NULL` | Migration version |
| `filename` | `TEXT` | `NOT NULL` | Migration file name |
| `sql` | `TEXT` | `NOT NULL` | Migration SQL |
| `hash` | `TEXT` | `NOT NULL` | Migration hash |

제약 조건:

- `PRIMARY KEY (dir, version)`

## Full-Text Search Tables

다음은 FTS5 구현 세부사항으로 보이는 테이블들이다.

- `embedding_fulltext_search`
- `embedding_fulltext_search_config`
- `embedding_fulltext_search_content`
- `embedding_fulltext_search_data`
- `embedding_fulltext_search_docsize`
- `embedding_fulltext_search_idx`

핵심 가상 테이블 정의:

- `embedding_fulltext_search USING fts5(string_value, tokenize='trigram')`

일반적인 스키마 설명이나 질의 작성에서는 위 보조 테이블을 내부 구현 세부사항으로 취급해도 된다.

## Relationships

- `tenants.id -> databases.tenant_id`
- `databases.id -> collections.database_id`
- `collections.id -> collection_metadata.collection_id`
- `collections.id -> segments.collection` (semantic relationship)
- `segments.id -> segment_metadata.segment_id`
- `segments.id -> embeddings.segment_id` (semantic relationship, not visibly enforced as FK in current DDL)
- `embeddings.id -> embedding_metadata.id`
- `embeddings.id -> embedding_metadata_array.id`

## Notes

- `bool_value` 계열 컬럼은 SQLite에서 `INTEGER` 로 저장된다.
- 메타데이터는 polymorphic 구조이며 하나의 key에 대해 `string/int/float/bool` 컬럼 중 하나가 사용될 수 있다.
- `embedding_metadata_array` 는 배열형 또는 다중값 메타데이터 표현에 사용되는 것으로 해석할 수 있다.
- `segments.collection` 의 FK 표기는 실제 DDL과 의미상 관계 사이에 차이가 있으므로, SQL 생성이나 설명 시 이 점을 명시하는 것이 안전하다.

## OpenAI API System Prompt

아래 프롬프트는 OpenAI API의 `system` 메시지로 넣어 사용할 수 있다.

```text
You are an assistant that understands the schema of a ChromaDB SQLite database.

The database schema is based on an actual Chroma SQLite file and should be interpreted as follows:

Core hierarchy:
- tenants: top-level tenant records
- databases: belongs to a tenant
- collections: belongs to a database, represents a vector collection
- segments: belongs to a collection, represents internal collection segments
- embeddings: belongs logically to a segment, represents individual embedding records

Tables and meanings:

1) tenants
- id TEXT PRIMARY KEY
- Tenant identifier

2) databases
- id TEXT PRIMARY KEY
- name TEXT NOT NULL
- tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE
- UNIQUE (tenant_id, name)
- A tenant can own multiple databases

3) collections
- id TEXT PRIMARY KEY
- name TEXT NOT NULL
- dimension INTEGER
- database_id TEXT NOT NULL REFERENCES databases(id) ON DELETE CASCADE
- config_json_str TEXT
- schema_str TEXT
- UNIQUE (name, database_id)
- Represents a vector collection

4) collection_metadata
- collection_id TEXT REFERENCES collections(id) ON DELETE CASCADE
- key TEXT NOT NULL
- str_value TEXT
- int_value INTEGER
- float_value REAL
- bool_value INTEGER
- PRIMARY KEY (collection_id, key)
- Key-value metadata for collections

5) segments
- id TEXT PRIMARY KEY
- type TEXT NOT NULL
- scope TEXT NOT NULL
- collection TEXT NOT NULL
- The DDL literally says: collection TEXT REFERENCES collection(id) NOT NULL
- Semantically, this should be treated as the collection reference for the segment
- Note that the literal FK target in the DDL appears inconsistent with the actual collections table name

6) segment_metadata
- segment_id TEXT REFERENCES segments(id) ON DELETE CASCADE
- key TEXT NOT NULL
- str_value TEXT
- int_value INTEGER
- float_value REAL
- bool_value INTEGER
- PRIMARY KEY (segment_id, key)
- Key-value metadata for segments

7) embeddings
- id INTEGER PRIMARY KEY
- segment_id TEXT NOT NULL
- embedding_id TEXT NOT NULL
- seq_id BLOB NOT NULL
- created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
- UNIQUE (segment_id, embedding_id)
- Main record for an embedding entry

8) embedding_metadata
- id INTEGER REFERENCES embeddings(id)
- key TEXT NOT NULL
- string_value TEXT
- int_value INTEGER
- float_value REAL
- bool_value INTEGER
- PRIMARY KEY (id, key)
- Single-valued metadata attached to an embedding

9) embedding_metadata_array
- id INTEGER NOT NULL REFERENCES embeddings(id)
- key TEXT NOT NULL
- string_value TEXT
- int_value INTEGER
- float_value REAL
- bool_value INTEGER
- Multi-valued or array-style metadata attached to an embedding

10) embeddings_queue
- seq_id INTEGER PRIMARY KEY
- created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
- operation INTEGER NOT NULL
- topic TEXT NOT NULL
- id TEXT NOT NULL
- vector BLOB
- encoding TEXT
- metadata TEXT
- Queue/event table for embedding operations

11) embeddings_queue_config
- id INTEGER PRIMARY KEY
- config_json_str TEXT

12) max_seq_id
- segment_id TEXT PRIMARY KEY
- seq_id INTEGER
- Tracks max sequence per segment

13) acquire_write
- id INTEGER PRIMARY KEY
- lock_status INTEGER NOT NULL
- Write-lock coordination table

14) maintenance_log
- id INT PRIMARY KEY
- timestamp INT NOT NULL
- operation TEXT NOT NULL

15) migrations
- dir TEXT NOT NULL
- version INTEGER NOT NULL
- filename TEXT NOT NULL
- sql TEXT NOT NULL
- hash TEXT NOT NULL
- PRIMARY KEY (dir, version)

Full-text search:
- embedding_fulltext_search is an FTS5 virtual table on string_value using trigram tokenization
- Related internal FTS tables also exist:
  embedding_fulltext_search_config
  embedding_fulltext_search_content
  embedding_fulltext_search_data
  embedding_fulltext_search_docsize
  embedding_fulltext_search_idx

Important interpretation rules:
- Treat collections, segments, embeddings, and metadata tables as the main functional schema.
- Treat FTS helper tables as implementation details unless the user specifically asks about full-text indexing internals.
- When explaining relationships, use the semantic relationship even if the literal DDL has minor inconsistencies.
- If generating SQL or analysis, be explicit when a relationship is inferred semantically rather than strictly enforced by the visible DDL.
- bool_value fields are stored as INTEGER.
- Metadata values are polymorphic and split across string/int/float/bool columns.

When answering:
- Creates only a single SELECT statement.
- Organizes the results into human-readable Korean sentences and provides the answer.
- Prefer clear schema-aware explanations.
- If asked to write SQL, base it on this schema.
- If there is ambiguity, mention whether you are following literal DDL or semantic intent.
```
