"""
src/graph/graph_builder.py
"""

import networkx as nx

from datetime import datetime

from data.ontology import nodes
from data.base_relations import links


# =========================================================
# Graph Initialization
# =========================================================

def init_graph():

    """
    Economic Knowledge Graph
    """

    return nx.MultiDiGraph()


# =========================================================
# Add Nodes
# =========================================================

def add_base_nodes(G):

    for node in nodes:

        node_id = node["id"]

        attrs = {

            k: v
            for k, v in node.items()
            if k != "id"
        }

        # metadata 추가
        attrs["created_at"] = datetime.now().isoformat()

        G.add_node(node_id, **attrs)


# =========================================================
# Add Relations
# =========================================================

def add_base_relations(G):

    for rel in links:

        G.add_edge(

            rel["source"],
            rel["target"],

            relation=rel["rel"],

            confidence=1.0,

            support_count=1,

            created_at=datetime.now().isoformat()
        )


# =========================================================
# Build Base Graph
# =========================================================

def build_base_graph():

    G = init_graph()

    print("🚀 Building Base Economic Graph...")

    # -------------------------
    # Add Nodes
    # -------------------------
    add_base_nodes(G)

    # -------------------------
    # Add Relations
    # -------------------------
    add_base_relations(G)

    print(f"✅ Nodes: {G.number_of_nodes()}")
    print(f"✅ Edges: {G.number_of_edges()}")

    return G


# =========================================================
# Debug
# =========================================================

if __name__ == "__main__":

    G = build_base_graph()

    print("\n📌 Sample Nodes")
    print(list(G.nodes(data=True))[:3])

    print("\n📌 Sample Edges")
    print(list(G.edges(data=True))[:3])