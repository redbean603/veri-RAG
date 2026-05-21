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

from utils.visualization import visualize_graph




# =========================================================
# Main Pipeline
# =========================================================

if __name__ == "__main__":

    # -------------------------------------------------
    # Step 1. Build Base Graph
    # -------------------------------------------------
    G = build_base_graph()

    # -------------------------------------------------
    # Step 2. Incoming News JSON
    # -------------------------------------------------
    news_data = {

        "news_id": "news_001",

        "title":
            "삼성전자 강세에 코스피 상승",

        "content":
            """
            삼성전자 상승세에
            코스피 지수가 상승했다.
            """,

        "published_at":
            "2026-05-17",

        "source":
            "src_reuters",

        "embedding_id":
            "emb_001"
    }

    # -------------------------------------------------
    # Step 3. Add News Node
    # -------------------------------------------------
    add_news_node(

        G,
        news_data
    )

    # -------------------------------------------------
    # Step 4. Entity Linking
    # -------------------------------------------------
    entities = [

        {
            "entity_id": "c_samsung"
        },

        {
            "entity_id": "a_kospi"
        }
    ]

    link_news_entities(

        G,

        "news_001",

        entities
    )

    # -------------------------------------------------
    # Step 5. Update Graph Relation
    # -------------------------------------------------
    update_relation(

        G,

        source="c_samsung",

        target="a_kospi",

        relation="AFFECTS",

        effect="positive",

        strength=0.82,

        confidence=0.91,

        evidence_chunk=
            "삼성전자 상승세에 코스피 상승",

        source_news="news_001"
    )

    # -------------------------------------------------
    # Step 6. Add Claim
    # -------------------------------------------------
    add_claim_node(

        G,

        news_id="news_001",

        claim_id="claim_001",

        claim_text=
            """
            삼성전자 상승이
            코스피 상승을 견인했다
            """,

        about_entity="c_samsung"
    )

    # -------------------------------------------------
    # Step 7. Verify Claim
    # -------------------------------------------------
    verify_claim(

        G,

        "claim_001"
    )

    # -------------------------------------------------
    # Final Status
    # -------------------------------------------------
    print("\n====================")
    print("📌 FINAL GRAPH")
    print("====================")

    print(f"Nodes: {G.number_of_nodes()}")
    print(f"Edges: {G.number_of_edges()}")

    # -------------------------------------------------
    # Step 8. Visualize Graph
    # -------------------------------------------------
    visualize_graph(G, output_file="knowledge_graph.html")