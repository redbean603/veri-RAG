# Veri-RAG Vector DB

Veri-RAG의 Vector DB 컴포넌트입니다. 뉴스 텍스트와 카드뉴스 이미지를 각각 임베딩하여 Chroma에 저장하고, Agent가 텍스트/이미지 기반 유사 뉴스 검색을 호출할 수 있도록 제공합니다.

## 현재 상태

- Chroma 서버: `3.93.218.110:8000`
- 텍스트 컬렉션: `news_text_openai`
- 이미지 컬렉션: `news_image_clip`
- 텍스트 임베딩 모델: OpenAI `text-embedding-3-small`
- 이미지 임베딩 모델: CLIP `openai/clip-vit-base-patch32`
- 유사도 기준: cosine
- 저장 완료: 텍스트 10개, 이미지 10개
- 중복 저장 방지 및 score threshold 필터 적용 완료

## 프로젝트 구조

```text
veri-rag-vectordb/
├── config.py                 # Chroma, 컬렉션, 모델, 경로 설정
├── embeddings.py             # OpenAI/CLIP 임베딩 생성
├── search.py                 # Agent 호출용 vector_search(), image_search()
├── ingest.py                 # 이미지 저장, 중복 체크, metadata 정리
├── main.py                   # 로컬 실행 및 smoke test
├── AGENTS.md                 # contributor guide
├── processed_news_backup/    # 전처리 JSON 결과물
└── raw_news_backup/          # 원본 이미지 및 텍스트 파일
```

## 입력 데이터 규칙

전처리 JSON은 `processed_news_backup/` 아래에 저장합니다.

```json
{
  "news_id": "news_20260519_0001",
  "title": "뉴스 제목",
  "content": "뉴스 요약 또는 본문",
  "published_at": "2026-05-19 16:53:11",
  "source": "src_naver",
  "url": "https://..."
}
```

이미지는 같은 `news_id`를 기준으로 `raw_news_backup/`에 저장합니다.

```text
processed_news_backup/news_20260519_0001_result.json
raw_news_backup/news_20260519_0001.jpg
```

## 설치

```bash
pip install chromadb openai python-dotenv torch torchvision transformers Pillow
```

`.env`에 OpenAI API 키를 설정합니다.

```env
OPENAI_API_KEY=sk-proj-...
```

## 실행

이미지 컬렉션 적재 및 샘플 이미지 검색을 실행합니다.

```bash
python main.py
```

이미 저장된 `news_id`는 중복 저장하지 않고 건너뜁니다.

## Agent 검색 인터페이스

Agent는 `search.py`의 함수만 import하면 됩니다.

```python
from search import vector_search, image_search

text_results = vector_search(
    query="지주회사 주가",
    top_k=3,
    score_threshold=0.3,
)

image_results = image_search(
    image_path="raw_news_backup/news_20260519_0001.jpg",
    top_k=3,
    score_threshold=0.5,
)
```

반환 형식:

```python
[
    {
        "title": "뉴스 제목",
        "url": "https://...",
        "published_at": "2026-05-19 16:53:11",
        "source": "src_naver",
        "image_path": "raw_news_backup/news_20260519_0001.jpg",
        "content": "뉴스 요약 또는 제목",
        "score": 0.53,
        "distance": 0.46
    }
]
```

`score_threshold`가 지정되면 score가 기준값보다 낮은 결과는 반환하지 않습니다.

## 검증 명령

문법 확인:

```bash
python -m py_compile config.py embeddings.py search.py ingest.py main.py
```

텍스트 검색 직접 호출:

```bash
python -c "from search import vector_search; print(vector_search('지주회사 주가', top_k=2, score_threshold=0.0))"
```

이미지 검색 직접 호출:

```bash
python -c "from search import image_search; print(image_search('raw_news_backup/news_20260519_0001.jpg', top_k=3, score_threshold=0.5))"
```

## 외부 파이프라인 연동 예정

### 전처리 파이프라인

전처리 결과물 포맷이 확정되면 다음 항목을 맞춰 자동 저장 파이프라인으로 연결합니다.

- JSON 필드명
- 이미지 파일명 규칙
- 결과물 저장 위치
- batch 실행 또는 새 파일 감지 방식

### Agent 인터페이스

Agent와 다음 호출 방식을 합의해야 합니다.

- Python 함수 직접 import
- 또는 FastAPI/HTTP endpoint 호출
- 기본 `top_k`, `score_threshold`
- Agent가 요구하는 반환 필드

현재는 Python import 방식으로 사용할 수 있습니다.
