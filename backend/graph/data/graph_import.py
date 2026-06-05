from neo4j import GraphDatabase
import pickle

URI = "bolt://34.230.30.134:7687"
USER = "neo4j"
PASSWORD = "password123"

driver = GraphDatabase.driver(
    URI,
    auth=(USER, PASSWORD)
)

import json

def sanitize(props):
    result = {}

    for k, v in props.items():
        if isinstance(v, dict):
            result[k] = json.dumps(v, ensure_ascii=False)

        elif isinstance(v, list):
            if all(isinstance(item, (str, int, float, bool, type(None))) for item in v):
                result[k] = v
            else:
                result[k] = json.dumps(v, ensure_ascii=False)

        else:
            result[k] = v

    return result

with open("/Users/jangbinlee/Desktop/Projects/Veri-RAG/backend/graph/data/latest_graph.pkl", "rb") as f:
    G = pickle.load(f)

with driver.session() as session:

    # Nodes
    for node_id, attrs in G.nodes(data=True):

        label = attrs.get("type", "Entity")

        props = sanitize(dict(attrs))
        props["id"] = node_id

        session.run(
            f"""
            MERGE (n:{label} {{id:$id}})
            SET n += $props
            """,
            id=node_id,
            props=props
        )

    for src, dst, attrs in G.edges(data=True):
        props = sanitize(dict(attrs))

        for k, v in props.items():
            if not isinstance(v, (str, int, float, bool, list, type(None))):
                print("BAD EDGE")
                print(src, dst)
                print(k, type(v), v)
                raise Exception("Unsupported type")

        rel_type = attrs.get("relation", "RELATED_TO")

        session.run(
            f"""
            MATCH (a {{id:$src}})
            MATCH (b {{id:$dst}})
            MERGE (a)-[r:{rel_type}]->(b)
            SET r += $props
            """,
            src=src,
            dst=dst,
            props=props
        )

driver.close()
