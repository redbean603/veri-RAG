# =========================================================
# Retrieval Functions
# =========================================================

def retrieve_related_entities(

        G,

        node_id
):

    if not G.has_node(node_id):

        return []

    results = []

    for neighbor in G.successors(node_id):

        results.append({

            "node":
                neighbor,

            "relation":
                G.edges[node_id, neighbor, 0]
        })

    return results