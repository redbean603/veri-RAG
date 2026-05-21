# =========================================================
# Claim Handling
# =========================================================

def add_claim_node(

        G,

        news_id,

        claim_id,

        claim_text,

        about_entity=None
):

    # -------------------------
    # Claim Node
    # -------------------------
    G.add_node(

        claim_id,

        type="Claim",

        text=claim_text
    )

    # -------------------------
    # News -> Claim
    # -------------------------
    G.add_edge(

        news_id,
        claim_id,

        relation="CONTAINS"
    )

    # -------------------------
    # Claim -> Entity
    # -------------------------
    if about_entity:

        G.add_edge(

            claim_id,
            about_entity,

            relation="ABOUT"
        )


# =========================================================
# Claim Verification
# =========================================================

def verify_claim(

        G,

        claim_id
):

    if not G.has_node(claim_id):

        print("❌ Claim not found")

        return

    print(f"\n🔍 Verifying Claim: {claim_id}")

    found = False

    for target in G.successors(claim_id):

        edge_data = G.edges[
            claim_id,
            target,
            0
        ]

        if edge_data["relation"] == "CONTRADICTS":

            found = True

            print("⚠️ CONTRADICTION FOUND")

            print(G.nodes[target])

    if not found:

        print("✅ No contradiction detected")