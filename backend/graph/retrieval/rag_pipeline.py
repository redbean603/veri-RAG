from utils.logger import get_logger

logger = get_logger(__name__)

class RAGPipeline:
    def __init__(self, graph):
        self.graph = graph

    def run_pipeline(self, query):
        """
        검색 증강 생성(RAG) 파이프라인을 실행합니다.
        """
        logger.info(f"Running RAG pipeline for query: {query}")
        # TODO: Implement RAG pipeline logic
        pass
