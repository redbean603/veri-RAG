import json
import os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

class Neo4jLoader:

    def __init__(self, uri=None, user=None, password=None):
        uri = uri or os.getenv("NEO4J_URI")
        user = user or os.getenv("NEO4J_USERNAME") or os.getenv("NEO4J_USER")
        password = password or os.getenv("NEO4J_PASSWORD")

        if not uri or not user or not password:
            raise ValueError(
                "Neo4j connection settings are not fully configured. "
                "Set NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD."
            )

        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def add_entity(self, entity_type, name):

        query = f"""
        MERGE (n:{entity_type} {{name:$name}})
        """

        with self.driver.session() as session:
            session.run(query, name=name)

    def add_relation(
        self,
        source,
        source_type,
        relation,
        target,
        target_type
    ):

        query = f"""
        MERGE (a:{source_type} {{name:$source}})
        MERGE (b:{target_type} {{name:$target}})
        MERGE (a)-[:{relation}]->(b)
        """

        with self.driver.session() as session:
            session.run(
                query,
                source=source,
                target=target
            )

    @staticmethod
    def _sanitize(props):
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

    def save_graph(self, G):

        with self.driver.session() as session:

            # Nodes
            for node_id, attrs in G.nodes(data=True):

                label = attrs.get(
                    "type",
                    "Entity"
                )

                props = self._sanitize(dict(attrs))
                props["id"] = node_id

                session.run(
                    f"""
                    MERGE (n:{label} {{id:$id}})
                    SET n += $props
                    """,
                    id=node_id,
                    props=props
                )

            # Relations
            for source, target, key, attrs in G.edges(
                keys=True,
                data=True
            ):

                relation = attrs.get(
                    "relation",
                    "RELATED_TO"
                )

                props = self._sanitize({
                    k: v
                    for k, v in attrs.items()
                    if k != "relation"
                })

                session.run(
                    f"""
                    MATCH (a {{id:$source}})
                    MATCH (b {{id:$target}})
                    MERGE (a)-[r:{relation}]->(b)
                    SET r += $props
                    """,
                    source=source,
                    target=target,
                    props=props
                )

    def close(self):
        self.driver.close()