"""
src/graph/graph_builder.py
"""

import networkx as nx

from datetime import datetime

from backend.graph.data.ontology import nodes
from data.ontology import nodes
from backend.graph.data.base_relations import links


LEGACY_ID_MAP = {

    "c_samsung": "company:samsung_electronics",
    "c_sk": "company:sk_hynix",
    "c_hyundai": "company:hyundai_motor",
    "c_kia": "company:kia",
    "c_lge": "company:lg_energy_solution",
    "c_posco": "company:posco_holdings",
    "c_kakao": "company:kakao",
    "c_naver": "company:naver",
    "c_celltrion": "company:celltrion",
    "c_hanwha": "company:hanwha_aerospace",
    "c_kb": "company:kb_bank",
    "c_shinhan": "company:shinhan_bank",
    "c_kakaobank": "company:kakaobank",
    "c_toss": "company:toss",
    "c_krafton": "company:krafton",
    "c_hhi": "company:hd_hyundai_heavy",

    "ind_semiconductor": "industry:semiconductor",
    "ind_battery": "industry:battery",
    "ind_auto": "industry:auto",
    "ind_finance": "industry:finance",
    "ind_bio": "industry:biohealth",
    "ind_shipbuilding": "industry:shipbuilding",
    "ind_steel": "industry:steel_material",
    "ind_it": "industry:it_platform",
    "ind_construction": "industry:construction_realestate",
    "ind_energy": "industry:energy",

    "p_lee_jw": "person:lee_jaeyong",
    "p_choi_tw": "person:choi_taewon",
    "p_chung_ej": "person:chung_euisun",
    "p_lee_hz": "person:lee_haejin",
    "p_rhee": "person:rhee_changyong",
    "p_choi_sg": "person:choi_sangmok",
    "p_kim_bs": "person:kim_byunghwan",

    "o_bok": "organization:bank_of_korea",
    "o_moef": "organization:moef",
    "o_fsc": "organization:fsc",
    "o_ftc": "organization:ftc",
    "o_krx": "organization:krx",
    "o_fss": "organization:fss",
    "o_kdi": "organization:kdi",
    "o_fed": "organization:federal_reserve",
    "o_imf": "organization:imf",
    "o_kcci": "organization:kcci",
    "o_fki": "organization:fki",

    "a_kospi": "asset:kospi",
    "a_usdkrw": "asset:usdkrw",
    "a_rate3y": "asset:treasury_3y",
    "a_cofix": "asset:cofix",
    "a_oil": "asset:dubai_oil",
    "a_dram": "asset:dram_spot_price",
    "a_lithium": "asset:lithium_price",
}


def normalize_base_id(node_id):

    return LEGACY_ID_MAP.get(node_id, node_id)


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

        source = normalize_base_id(rel["source"])

        target = normalize_base_id(rel["target"])

        if not G.has_node(source) or not G.has_node(target):

            print(
                "Skipping base relation with missing node: "
                f"{rel['source']} -> {rel['target']}"
            )

            continue

        G.add_edge(

            source,
            target,

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
