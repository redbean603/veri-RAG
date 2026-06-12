import requests
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from neo4j import GraphDatabase
import os
import base64
import io
import re
from PIL import Image
import pytesseract
import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import chromadb

# 우리가 방금 만든 마스터 파이프라인 임포트
from backend.etl.pipeline import run_news_etl_pipeline


LAMBDA_API_URL = os.getenv(
    "LAMBDA_API_URL",
    "https://ouc16h2gw2.execute-api.us-east-1.amazonaws.com/default/veri-rag-agent"
)

app = FastAPI()
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend" / "web"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


# API 요청을 받을 데이터 구조 정의 (뉴스 ID와 임시 벡터를 받도록 설정)
class BuildGraphRequest(BaseModel):
    news_id: str
    text_vector: List[float]
    image_vector: Optional[List[float]] = None

@app.get("/", include_in_schema=False)
def root():
    index_file = FRONTEND_DIR / "index.html"

    if index_file.exists():
        return FileResponse(index_file)

    return {"status": "ok", "message": "frontend/web/index.html not found"}

@app.post("/build-graph")
def build_graph(req: BuildGraphRequest):
    try:
        # S3에서 raw 데이터를 가져와 전처리 후 듀얼 DB에 적재하는 파이프라인 실행
        result = run_news_etl_pipeline(
            news_id=req.news_id,
            text_vector=req.text_vector,
            image_vector=req.image_vector
        )
        return {"status": "success", "message": f"Pipeline completed for {req.news_id}", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
from sentence_transformers import SentenceTransformer
from search import evidence_search

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
embedding_model = SentenceTransformer(MODEL_NAME)

CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"
clip_device = "cuda" if torch.cuda.is_available() else "cpu"

clip_model = CLIPModel.from_pretrained(CLIP_MODEL_NAME).to(clip_device)
clip_processor = CLIPProcessor.from_pretrained(CLIP_MODEL_NAME)

def get_graph_context(news_id: str, limit: int = 20):
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")

    driver = GraphDatabase.driver(uri, auth=(user, password))

    query = """
    MATCH (n:News {id: $news_id})-[r]->(m)
    RETURN
        n.id AS news_id,
        type(r) AS relation,
        labels(m) AS target_labels,
        m.id AS target_id,
        m.name AS target_name,
        m.type AS target_type
    LIMIT $limit
    """

    with driver.session() as session:
        rows = session.run(query, news_id=news_id, limit=limit)

        entities = []
        relations = []

        for row in rows:
            entity = {
                "id": row["target_id"],
                "name": row["target_name"],
                "type": row["target_type"],
                "labels": row["target_labels"],
            }

            entities.append(entity)

            relations.append({
                "source": news_id,
                "relation": row["relation"],
                "target": row["target_id"],
                "target_name": row["target_name"],
            })

    driver.close()

    return {
        "entities": entities,
        "relations": relations,
    }
def extract_image_text_from_base64(image_base64: str):
    try:
        if "," in image_base64:
            image_base64 = image_base64.split(",", 1)[1]

        image_bytes = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        ocr_text = pytesseract.image_to_string(
            image,
            config="--psm 6"
        )

        numbers = re.findall(r"\d{3,5}", ocr_text)

        return {
            "ocr_text": ocr_text.strip(),
            "numbers": numbers
        }

    except Exception as e:
        return {
            "ocr_text": "",
            "numbers": [],
            "error": str(e)
        }
def search_similar_images(image_base64: str, top_k: int = 5):
    try:
        if "," in image_base64:
            image_base64 = image_base64.split(",", 1)[1]

        image_bytes = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        inputs = clip_processor(
            images=image,
            return_tensors="pt"
        ).to(clip_device)

        with torch.no_grad():
            outputs = clip_model.vision_model(**inputs)
            features = outputs.pooler_output
            features = clip_model.visual_projection(features)

        features = features / features.norm(dim=-1, keepdim=True)
        image_vector = features[0].cpu().numpy().tolist()

        client = chromadb.HttpClient(host="localhost", port=8001)
        collection = client.get_collection("news_image_clip")

        result = collection.query(
            query_embeddings=[image_vector],
            n_results=top_k,
            include=["metadatas", "documents", "distances"]
        )

        matches = []

        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        documents = result.get("documents", [[]])[0]

        for i, img_id in enumerate(ids):
            distance = distances[i]
            metadata = metadatas[i] or {}

            matches.append({
                "image_id": img_id,
                "news_id": metadata.get("news_id", img_id),
                "image_path": metadata.get("image_path") or documents[i],
                "distance": distance,
                "similarity": 1 - distance
            })

        return matches

    except Exception as e:
        return [{
            "error": str(e)
        }]

@app.post("/search")
def search_news(req: SearchRequest):
    try:

        query_vector = embedding_model.encode(req.query).tolist()

        results = evidence_search(
            query=req.query,
            query_vector=query_vector,
        )
        enriched_results = []

        for item in results[:req.top_k]:
            news_id = item.get("news_id")

            graph_context = get_graph_context(news_id) if news_id else {
                "entities": [],
                "relations": []
            }

            enriched_item = dict(item)
            enriched_item["graph_context"] = graph_context
            enriched_results.append(enriched_item)

        return {
            "query": req.query,
            "results": enriched_results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent-search")
def agent_search(req: SearchRequest):

    query_vector = embedding_model.encode(req.query).tolist()

    results = evidence_search(
        query=req.query,
        query_vector=query_vector,
    )

    evidence = []

    for item in results[:req.top_k]:

        graph = get_graph_context(item["news_id"])

        evidence.append({
            "news_id": item["news_id"],
            "score": item.get("score"),
            "summary": item.get("summary", "")[:500],
            "entities": [
                e["name"]
                for e in graph["entities"]
                if e.get("name")
            ]
        })

    return {
        "query": req.query,
        "evidence": evidence
    }

class VerifyNewsRequest(BaseModel):
    title: str = ""
    content: str
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    top_k: int = 5

@app.post("/verify-news")
def verify_news(req: VerifyNewsRequest):
    try:
        input_text = "\n".join(
            part for part in [req.title, req.content]
            if part
        )

        query_vector = embedding_model.encode(input_text).tolist()

        results = evidence_search(
            query=input_text,
            query_vector=query_vector,
        )

        evidence = []

        for item in results[:req.top_k]:
            news_id = item.get("news_id")
            graph = get_graph_context(news_id) if news_id else {
                "entities": [],
                "relations": []
            }

            evidence.append({
                "news_id": news_id,
                "title": item.get("title"),
                "score": item.get("score"),
                "summary": item.get("summary", "")[:500],
                "entities": [
                    e.get("name")
                    for e in graph["entities"]
                    if e.get("name")
                ],
                "relations": graph["relations"][:10],
            })
        image_analysis = None

        if req.image_base64:
            image_analysis = extract_image_text_from_base64(req.image_base64)


        image_matches = []

        if req.image_base64:
            image_matches = search_similar_images(
                req.image_base64,
                top_k=req.top_k
            )
        return {
            "input": {
                "title": req.title,
                "content_preview": req.content[:300],
                "image_url": req.image_url,
            },
            "similar_news": evidence,
            "image_analysis": image_analysis,
            "image_matches": image_matches,
            "verdict": "needs_review",
            "message": "유사 뉴스와 그래프 근거를 기반으로 추가 검증이 필요합니다."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class QueryRequest(BaseModel):
    query: str = ""
    title: str = ""
    content: str = ""
    image_base64: Optional[str] = None
    image_url: Optional[str] = None
    top_k: int = 3


@app.post("/query")
def query(req: QueryRequest):
    """
    Frontend 호환용 endpoint.
    브라우저는 같은 EC2 origin의 /query를 호출하고,
    EC2 서버가 API Gateway Lambda를 대신 호출한다.
    """
    try:
        value = (req.query or "").strip()

        if value.startswith("http://") or value.startswith("https://"):
            payload = {
                "news_url": value,
                "top_k": req.top_k
            }
        else:
            payload = {
                "title": req.title or "",
                "content": req.content or value,
                "top_k": req.top_k
            }

        if req.image_base64:
            payload["image_base64"] = req.image_base64

        if req.image_url:
            payload["image_url"] = req.image_url

        last_error_text = ""

        for attempt in range(2):
            res = requests.post(
                LAMBDA_API_URL,
                json=payload,
                timeout=120
            )

            last_error_text = res.text

            if res.status_code < 500:
                break

            import time
            time.sleep(2)

        if res.status_code >= 400:
            raise HTTPException(
                status_code=500,
                detail={
                    "lambda_status": res.status_code,
                    "lambda_response": last_error_text
                }
            )

        data = res.json()

        if isinstance(data, dict) and isinstance(data.get("body"), str):
            import json
            try:
                return json.loads(data["body"])
            except Exception:
                return data

        return data

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
