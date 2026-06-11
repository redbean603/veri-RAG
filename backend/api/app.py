from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend" / "web"

app = FastAPI(title="Veri-RAG", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str  # 뉴스 URL


# 프론트엔드 정적 파일 서빙
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/", include_in_schema=False)
def root():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query")
async def query(req: QueryRequest):
    # TODO: 실제 agent 연결 전 에코 테스트
    return {
        "answer": f"[에코] 입력된 URL: {req.query}\n\nAgent 연결 전 테스트 응답입니다."
    }
