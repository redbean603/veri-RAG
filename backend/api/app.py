from fastapi import FastAPI

from backend.graph.workflow import run_news_pipeline

from pydantic import BaseModel

class RetrieveRequest(BaseModel):
    entities: list[str]

from backend.graph.retrieval.graph_retrieval import ( # pyright: ignore[reportMissingImports]
    retrieve_news_ids
)

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

@app.post("/retrieve")
def retrieve(req: RetrieveRequest):

    news_ids = retrieve_news_ids(
        req.entities
    )

    return {
        "entities": req.entities,
        "news_ids": news_ids
    }