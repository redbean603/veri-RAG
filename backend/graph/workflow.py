from langgraph.graph import StateGraph
from langgraph.graph import END

from graph_builder import build_base_graph

from news_ingestion import (
    add_news_node,
    link_news_entities
)

from graph_updater import (
    update_relation
)

from claim_handler import (
    add_claim_node,
    verify_claim
)

from llm_knowledge_extractor import (
    extract_knowledge_from_llm
)

from utils.visualization import visualize_graph

import json
import glob

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
            confidence=relation.get("confidence", 0.8),
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




G = build_base_graph()

news_files = glob.glob(

    "/Users/jangbinlee/Desktop/Projects/Veri-RAG/data/processed_news_backup/*.json"

)

for file_path in news_files:

    with open(

        file_path,

        "r",

        encoding="utf-8"

    ) as f:

        news_data = json.load(f)

    result = app.invoke({

        "graph": G,

        "news_data": news_data

    })

    G = result["graph"]

print("All news processed.")
visualize_graph(G)