from fastapi import FastAPI

from backend.graph.workflow import run_news_pipeline

from pydantic import BaseModel

class RetrieveRequest(BaseModel):
    entities: list[str]
app = FastAPI(
    title="Veri-RAG",
    version="0.1"
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/build-graph")
def build_graph():

    result = run_news_pipeline()

    return result