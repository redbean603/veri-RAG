# =========================================================
# News Node Handling
# =========================================================

def add_news_node(G, news_data):

    news_id = news_data["news_id"]

    G.add_node(

        news_id,

        type="News",

        title=news_data["title"],

        content=news_data["content"],

        published_at=
            news_data["published_at"],

        embedding_id=
            news_data.get("embedding_id"),
    )

    # -------------------------
    # Source Relation
    # -------------------------
    source_id = news_data["source"]

    G.add_edge(

        news_id,
        source_id,

        relation="SOURCE_FROM",

        confidence=1.0
    )


def add_or_update_entity_node(G, entity):

    entity_id = entity.get("id") or entity.get("entity_id")

    if not entity_id:

        return None

    attrs = {

        "type": entity.get("type", "Entity"),

        "name": entity.get("name", entity_id)
    }

    if G.has_node(entity_id):

        G.nodes[entity_id].update({

            k: v
            for k, v in attrs.items()
            if v is not None
        })

    else:

        G.add_node(entity_id, **attrs)

    return entity_id


# =========================================================
# Entity Linking
# =========================================================

def link_news_entities(

        G,

        news_id,

        entities
):

    for ent in entities:

        entity_id = add_or_update_entity_node(
            G,
            ent
        )

        if entity_id:

            G.add_edge(

                news_id,
                entity_id,

                relation="MENTIONS",

                confidence=
                    ent.get("confidence", 0.8)
            )
