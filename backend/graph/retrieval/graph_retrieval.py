from neo4j import GraphDatabase

URI = "bolt://100.52.246.218:7687"
USER = "neo4j"
PASSWORD = "password123"

driver = GraphDatabase.driver(
    URI,
    auth=(USER, PASSWORD)
)

# def retrieve_subgraph(entities):    

#     query = """
#     MATCH p=(n)-[*1..2]-(m)
#     WHERE n.name IN $entities
#     RETURN p
#     LIMIT 100
#     """

#     with driver.session() as session:
#         result = session.run(
#             query,
#             entities=entities
#         )

#         return [record for record in result]
    
# if __name__ == "__main__":
#     print("URI =", URI)
#     entities = ["AWS", "반도체"]

#     results = retrieve_subgraph(entities)

#     for record in results:
#         print(record)

def retrieve_news_ids(entities):

    query = """
    MATCH (n)-[*1..2]-(news:News)
    WHERE n.name IN $entities
    RETURN DISTINCT news.id AS news_id
    """

    with driver.session() as session:
        result = session.run(
            query,
            entities=entities
        )

        return [record["news_id"] for record in result]


if __name__ == "__main__":

    print("URI =", URI)

    entities = ["AWS", "반도체"]

    news_ids = retrieve_news_ids(entities)

    print("Retrieved News IDs:")
    for news_id in news_ids:
        print(news_id)