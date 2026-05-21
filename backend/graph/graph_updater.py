from datetime import datetime


# =========================================================
# Dynamic Relation Update
# =========================================================

def update_relation(

        G,

        source,
        target,

        relation,

        effect=None,

        strength=0.7,

        confidence=0.8,

        evidence_chunk=None,

        source_news=None
):

    existing_edge = None

    # -------------------------------------------------
    # Search Existing Relation
    # -------------------------------------------------
    if G.has_edge(source, target):

        edge_dict = G.get_edge_data(source, target)

        for key, edge_data in edge_dict.items():

            if (
                edge_data.get("relation") == relation
                and
                edge_data.get("effect") == effect
            ):

                existing_edge = (key, edge_data)

                break

    # -------------------------------------------------
    # Update Existing Edge
    # -------------------------------------------------
    if existing_edge:

        key, edge_data = existing_edge

        edge_data["support_count"] += 1

        edge_data["confidence"] = min(

            1.0,

            edge_data["confidence"] + 0.05
        )

        edge_data["strength"] = (

            edge_data["strength"]
            +
            strength

        ) / 2

        if source_news:

            edge_data["supporting_news"].append(
                source_news
            )

    # -------------------------------------------------
    # Create New Edge
    # -------------------------------------------------
    else:

        G.add_edge(

            source,
            target,

            relation=relation,

            effect=effect,

            strength=strength,

            confidence=confidence,

            evidence_chunk=evidence_chunk,

            support_count=1,

            supporting_news=[source_news],

            updated_at=datetime.now().isoformat()
        )