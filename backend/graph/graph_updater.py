from datetime import datetime


def update_relation(

        G,

        source,
        target,

        relation,
        effect=None,

        strength=0.7,

        # evidence_chunk=None,
        source_news=None,

        published_at=None
):

    existing_edge = None
    

    # Search Existing Relation

    if G.has_edge(source, target):

        edge_dict = G.get_edge_data(source, target)

        for key, edge_data in edge_dict.items():

            if edge_data.get("relation") == relation:

                existing_edge = (key, edge_data)

                break


    # Update Existing Edge

    if existing_edge:

        key, edge_data = existing_edge

        edge_data["support_count"] += 1

        edge_data["strength"] = (

            edge_data["strength"]
            +
            strength

        ) / 2


        # Update Current State

        if (
            published_at
            and
            published_at >= edge_data["last_seen"]
        ):

            edge_data["current_state"] = effect
            edge_data["last_seen"] = published_at

        # Supporting News

        if (
            source_news
            and
            source_news not in edge_data["supporting_news"]
        ):

            edge_data["supporting_news"].append(
                source_news
            )

        # ---------------------------------------------
        # Optional Effect History
        # ---------------------------------------------
        if "effect_history" not in edge_data:

            edge_data["effect_history"] = []

        edge_data["effect_history"].append({

            "effect": effect,
            "published_at": published_at,
            "source_news": source_news

        })

    # create new edge
    else:

        G.add_edge(

            source,
            target,

            relation=relation,

            # current state
            current_state=effect,

            # historical importance
            strength=strength,

            # evidence_chunk=evidence_chunk,

            support_count=1,

            supporting_news=[source_news],

            first_seen=published_at,
            last_seen=published_at,

            effect_history=[{

                "effect": effect,
                "published_at": published_at,
                "source_news": source_news

            }]
        )