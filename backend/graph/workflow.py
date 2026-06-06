from langgraph.graph import StateGraph
from langgraph.graph import END

from backend.graph.graph_builder import build_base_graph
from backend.graph.news_ingestion import add_news_node
from backend.graph.graph_updater import update_relation
from backend.graph.claim_handler import add_claim_node
from backend.graph.llm_knowledge_extractor import extract_knowledge_from_llm
from backend.graph.utils.visualization import visualize_graph
from backend.graph.utils.io import save_graph
from backend.graph.neo4j_loader import Neo4jLoader


from backend.graph.news_ingestion import (
    add_news_node,
    link_news_entities
)

from backend.graph.graph_updater import (
    update_relation
)

from backend.graph.claim_handler import (
    add_claim_node,
    verify_claim
)

from backend.graph.llm_knowledge_extractor import (
    extract_knowledge_from_llm
)


import json
import glob
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
NEWS_INPUT_DIR = PROJECT_ROOT / "data" / "processed_news_backup"
GRAPH_OUTPUT_FILE = "backend/graph/data/latest_graph.pkl"
HTML_OUTPUT_FILE = "graph.html"

# with open(

#     "/Users/jangbinlee/Desktop/Projects/Veri-RAG/backend/graph/data/sample_news1.json",
#     "r",
#     encoding="utf-8"

# ) as f:

#     news_data = json.load(f)


def ingest_news_node(state):

    G = state["graph"]

    news_data = state["news_data"]

    add_news_node(

        G,

        news_data
    )

    return {
        **state,
        "graph": G,
        "news_data": news_data

    }

def extract_knowledge_node(state):

    G = state["graph"]

    news_data = state["news_data"]

    # LLM Knowledge Extraction
    try:

        extracted_entities = extract_knowledge_from_llm(
            news_data["content"]
        )

    except Exception as e:

        print(f"LLM extraction failed: {e}")

        extracted_entities = {
            "entities": [],
            "relations": [],
            "claims": []
        }
    return{
        **state,
        "graph": G,
        "news_data": state["news_data"],
        "entities": extracted_entities["entities"],
        "relations": extracted_entities["relations"],
        "claims": extracted_entities["claims"]
    }


def update_KG_node(state):
    
    G = state["graph"]
    news_data = state["news_data"]
    entities = state["entities"]
    relations = state["relations"]
    claims = state["claims"]

    link_news_entities(
        G,
        news_data["news_id"],
        entities

    )

    for relation in relations:

        update_relation(
            G,
            source=relation["source"],
            target=relation["target"],
            relation=relation["relation"],
            effect=relation.get("effect"),
            strength=relation.get("strength", 0.7),
            source_news=news_data["news_id"],
            published_at=news_data.get("published_at")
            # confidence=relation.get("confidence", 0.8),
        )
    for idx, claim in enumerate(claims):

        claim_id = f"{news_data['news_id']}:claim:{idx}"

        add_claim_node(

            G,

            news_data["news_id"],

            claim_id,

            claim["claim"]

        )

    return {
        **state,
        "graph": G,
        "entities": state["entities"],
        "relations": state["relations"],
        "claims": state["claims"]
    }

workflow = StateGraph(dict)



# Ingest News
workflow.add_node(

    "ingest_news",

    ingest_news_node

)


# set entry point
workflow.set_entry_point(
    "ingest_news"
)

# Extract Entity
workflow.add_node(

    "extract_knowledge",

    extract_knowledge_node

)
workflow.add_edge(

    "ingest_news",

    "extract_knowledge"

)

# Update Knowledge Graph
workflow.add_node(

    "update_knowledge_graph",

    update_KG_node

)
workflow.add_edge(

    "extract_knowledge",

    "update_knowledge_graph"
)

workflow.add_edge(
    "update_knowledge_graph",
    END
)      


# Visualize Graph

app = workflow.compile()


def run_news_pipeline():

    G = build_base_graph()

    news_files = glob.glob(str(NEWS_INPUT_DIR / "*.json"))

    for file_path in news_files:

        with open(file_path, "r", encoding="utf-8") as f:
            news_data = json.load(f)

        result = app.invoke({
            "graph": G,
            "news_data": news_data
        })

        G = result["graph"]

    save_graph(G, GRAPH_OUTPUT_FILE)
    visualize_graph(G, output_file=HTML_OUTPUT_FILE)

    neo4j_status = "skipped"
    try:
        loader = Neo4jLoader()
        loader.save_graph(G)
        loader.close()
        neo4j_status = "synced"
    except Exception as e:
        print(f"Neo4j sync failed: {e}")
        neo4j_status = "failed"

    return {
        "nodes": len(G.nodes),
        "edges": len(G.edges),
        "graph_file": GRAPH_OUTPUT_FILE,
        "neo4j_sync": neo4j_status
    }

if __name__ == "__main__":

    result = run_news_pipeline()

    print(result)



# G = build_base_graph()

# news_files = glob.glob(str(NEWS_INPUT_DIR / "*.json"))

# for file_path in news_files:

#     with open(

#         file_path,

#         "r",

#         encoding="utf-8"

#     ) as f:

#         news_data = json.load(f)

#     result = app.invoke({

#         "graph": G,

#         "news_data": news_data

#     })

#     G = result["graph"]

# print("All news processed.")
# save_graph(G, GRAPH_OUTPUT_FILE)
# print(f"Graph saved to {GRAPH_OUTPUT_FILE}")
# visualize_graph(G, output_file=HTML_OUTPUT_FILE)
