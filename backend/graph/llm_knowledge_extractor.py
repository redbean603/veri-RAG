import json
from openai import OpenAI
import os
import re
import hashlib
from dotenv import load_dotenv
from backend.graph.data.ontology import nodes
from pathlib import Path


# load_dotenv()
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

client = OpenAI(
    api_key=os.getenv("LUXIA_API_KEY"),
    base_url="https://<luxia-api-endpoint>/v1"
)


ONTOLOGY_BY_ID = {
    node["id"]: node
    for node in nodes
}

ONTOLOGY_ID_BY_NAME = {
    node.get("name"): node["id"]
    for node in nodes
    if node.get("name")
}

EXTRA_CANONICAL_ENTITIES = {
    "asset:domestic_stock_market": {
        "type": "Asset",
        "name": "국내 증시",
    },
    "company:holding_companies": {
        "type": "Company",
        "name": "지주회사",
    },
    "policy:dividend_income_separate_taxation": {
        "type": "Policy",
        "name": "배당소득 분리과세",
    },
    "policy:mandatory_treasury_stock_cancellation": {
        "type": "Policy",
        "name": "자사주 의무 소각",
    },
    "policy:dual_listing_ban": {
        "type": "Policy",
        "name": "중복상장 금지",
    },
    "company:dl_enc": {
        "type": "Company",
        "name": "DL이앤씨",
    },
    "company:hyundai_engineering_construction": {
        "type": "Company",
        "name": "현대건설",
    },
    "event:apgujeong_district_5_reconstruction": {
        "type": "Event",
        "name": "압구정5구역 재건축",
    },
}

KNOWN_ENTITY_NAME_TO_ID = {
    "정용진": "person:jeong_yongjin",
    "구윤철": "person:gu_yooncheol",
    "송미령": "person:song_miryeong",
    "Agriculture Minister": "person:song_miryeong",
    "스타벅스코리아": "company:starbucks_korea",
    "신세계그룹": "organization:shinsegae_group",
    "농림축산식품부": "organization:mafra",
    "한국 정부": "organization:government_of_korea",
    "정부": "organization:government_of_korea",
    "Government": "organization:government_of_korea",
    "소비자": "economicagent:consumers",
    "소비자들": "economicagent:consumers",
    "고객": "economicagent:consumers",
    "노조": "economicagent:union",
    "외국인 투자자": "economicagent:foreign_investors",
    "외국인": "economicagent:foreign_investors",
    "foreign investors": "economicagent:foreign_investors",
    "Foreign investors": "economicagent:foreign_investors",
    "개인 투자자": "economicagent:retail_investors",
    "개인": "economicagent:retail_investors",
    "retail investors": "economicagent:retail_investors",
    "농민": "economicagent:farmers",
    "farmers": "economicagent:farmers",
    "원·달러 환율": "asset:usdkrw",
    "원/달러 환율": "asset:usdkrw",
    "원달러 환율": "asset:usdkrw",
    "고환율": "asset:usdkrw",
    "IT하드웨어": "industry:it_platform",
    "농업": "industry:agriculture",
    "Agriculture": "industry:agriculture",
    "양파 가격": "asset:onion_price",
    "Onion Price": "asset:onion_price",
    "domestic stock market": "asset:domestic_stock_market",
    "Domestic stock market": "asset:domestic_stock_market",
    "국내증시": "asset:domestic_stock_market",
    "holding companies": "company:holding_companies",
    "Holding companies": "company:holding_companies",
    "major holding companies": "company:holding_companies",
    "Major holding companies": "company:holding_companies",
    "주요 지주회사": "company:holding_companies",
    "지주회사": "company:holding_companies",
    "dividend tax policy": "policy:dividend_income_separate_taxation",
    "dividend income separation tax": "policy:dividend_income_separate_taxation",
    "배당소득 분리과세": "policy:dividend_income_separate_taxation",
    "mandatory stock cancellation": "policy:mandatory_treasury_stock_cancellation",
    "mandatory treasury stock cancellation": "policy:mandatory_treasury_stock_cancellation",
    "자사주 의무 소각": "policy:mandatory_treasury_stock_cancellation",
    "prohibition of dual listings": "policy:dual_listing_ban",
    "ban on dual listings": "policy:dual_listing_ban",
    "중복상장 금지": "policy:dual_listing_ban",
    "DL이앤씨": "company:dl_enc",
    "현대건설": "company:hyundai_engineering_construction",
    "압구정5구역 재건축": "event:apgujeong_district_5_reconstruction",
}

CANONICAL_ENTITY_NAMES = {
    "person:jeong_yongjin": "정용진",
    "person:gu_yooncheol": "구윤철",
    "person:song_miryeong": "송미령",
    "company:starbucks_korea": "스타벅스코리아",
    "organization:shinsegae_group": "신세계그룹",
    "organization:mafra": "농림축산식품부",
    "organization:government_of_korea": "한국 정부",
    "economicagent:consumers": "소비자",
    "economicagent:union": "노조",
    "economicagent:foreign_investors": "외국인 투자자",
    "economicagent:retail_investors": "개인 투자자",
    "economicagent:farmers": "농민",
    "asset:usdkrw": "원달러 환율",
    "industry:it_platform": "IT/플랫폼",
    "industry:agriculture": "농업",
    "asset:onion_price": "양파 가격",
}

CANONICAL_ENTITY_NAMES.update({
    entity_id: entity["name"]
    for entity_id, entity in EXTRA_CANONICAL_ENTITIES.items()
})

CANONICAL_ENTITY_TYPES = {
    node["id"]: node.get("type")
    for node in nodes
}

CANONICAL_ENTITY_TYPES.update({
    entity_id: entity["type"]
    for entity_id, entity in EXTRA_CANONICAL_ENTITIES.items()
})

GENERIC_ENTITY_NAMES = {
    "증시",
    "재건축",
    "시장",
    "경제",
}

ENTITY_TYPE_TO_PREFIX = {
    "Company": "company",
    "Policy": "policy",
    "Event": "event",
    "Industry": "industry",
    "Asset": "asset",
    "Person": "person",
    "Organization": "organization",
    "EconomicAgent": "economicagent",
}

ID_PREFIX_TO_ENTITY_TYPE = {
    prefix: entity_type
    for entity_type, prefix in ENTITY_TYPE_TO_PREFIX.items()
}

SYSTEM_PROMPT = """
You are an economic knowledge graph extractor.

Return ONLY valid JSON.

Extract:

1. claims
2. entities
3. relations

Follow this workflow:

Step 1.
Extract 1-4 important economic claims.

Step 2.
Extract entities appearing in those claims.
Include economically meaningful groups or instruments when they are direct
participants in a selected claim, even if they are not proper nouns.
Examples: holding companies, domestic stock market, foreign investors,
retail investors, dividend tax policy, treasury yields, exchange rates.

Step 3.
Extract relations only if explicitly stated.
Extract a relation when the article explicitly says one entity caused,
supported, pressured, bought/sold, improved, weakened, measured, or changed
another entity.

Do NOT infer.

Do NOT use external knowledge.

Do NOT create speculative relations.

If uncertain, omit.
But do not omit a relation when the article explicitly uses evidence such as
"because", "as a result", "impact", "policy momentum", "buying/selling",
"improved", "weakened", "rose", "fell", "supports", or "pressures".

---

Entity schema:

{
    "type": "...",
    "name": "..."
}

DO NOT generate entity IDs.
For Korean articles, use Korean official/common entity names whenever possible.
Do not translate Korean entity names into English unless the entity is normally
known by an English name in Korea.

Entity types:

- Company
- Policy
- Event
- Industry
- Asset
- Person
- Organization
- EconomicAgent

Use:

EconomicAgent:
foreign investors,
institutional investors,
retail investors,
consumers,
workers,
labor unions,
farmers

Organization:
government,
regulators,
public institutions,
associations,
international organizations

Company:
listed firms,
private firms,
banks

Asset:
exchange rates,
commodity prices,
indices,
interest rates

---

Relation schema:

{
    "source": "<entity name>",
    "target": "<entity name>",
    "relation": "...",
    "effect": "..."
}

Valid relations:

- AFFECTS
- SUPPORTS
- MEASURES

Valid effects:

- active
- strengthening
- weakening
- inactive
- neutral

Relation source and target names MUST exactly match
entity names in entities[].
Do not use aliases.
Do not use shortened forms.


Relations must be explicitly supported by the article.

Do not create relations merely because two entities appear together.

Relation direction:

- Cause/action/source entity -> affected/target entity.
- Buying or selling pressure: investor group -> asset/company/market.
- Policy support or reform: policy/government -> affected company, industry,
  asset, or economic agent.
- Market indicators or prices: measured indicator -> affected asset/company
  only if the article states the effect explicitly.

Examples:

- If foreign investors are buying holding company stocks:
  foreign investors AFFECTS holding companies with effect "strengthening".
- If dividend tax policy and treasury stock cancellation are described as
  policy momentum for holding company value:
  each policy SUPPORTS holding companies with effect "strengthening".
- If consumer boycott and membership cancellation are spreading against a
  company:
  consumers AFFECTS the company with effect "weakening".

---

Claim schema:

{
    "claim": "...",
    "confidence": 0.0
}

Confidence must be between 0 and 1.

---

Output format:

{
    "entities": [],
    "relations": [],
    "claims": []
}
"""
# SYSTEM_PROMPT = """
# You are an economic knowledge graph extractor.

# Your task is to extract:

# 1. Economic claims
# 2. Economic entities grounded in those claims
# 3. Economic relations grounded in those claims

# Return ONLY valid JSON.

# Do NOT include markdown.
# Do NOT explain anything.
# Do NOT generate text outside JSON.


# # =========================================================
# # EXTRACTION PRINCIPLES
# # =========================================================

# - Extract claims FIRST.
# - Then extract entities from the selected claims.
# - Then extract relations only from the selected claims.
# - Extract ONLY information explicitly supported by the article.
# - Do NOT infer speculative macroeconomic relations.
# - Do NOT hallucinate causal structure.
# - Prefer precision over recall.
# - If uncertain, omit the relation/entity.
# - Prefer event/behavior relationships over static affiliation.
# - Do NOT extract static affiliation or ownership relations
#   unless the article's main economic claim is about that affiliation.


# # =========================================================
# # ENTITY NORMALIZATION RULES
# # =========================================================

# - Normalize entity names consistently.
# - Use official Korean economic entity names for "name".
# - IDs must be deterministic and stable.
# - IDs must NEVER be random.
# - Reuse existing ontology IDs whenever possible.
# - Reuse an existing ontology ID ONLY when the entity name
#   refers to the exact same real-world entity.
# - If the entity name does not match the existing ontology entity,
#   create a new canonical ID instead of reusing a similar-looking ID.
# - If two entities refer to the same real-world entity,
#   reuse the same canonical ID.
# - Do NOT create duplicate entities.


# # =========================================================
# # ENTITY ID FORMAT
# # =========================================================

# ID rules:

# - lowercase only
# - snake_case only
# - English canonical names only
# - no spaces
# - no Korean in IDs
# - deterministic and stable

# Examples:

# - company:samsung_electronics
# - company:sk_hynix
# - industry:semiconductor
# - organization:bank_of_korea
# - asset:usdkrw
# - person:lee_jaeyong


# # =========================================================
# # EXISTING ONTOLOGY IDS
# # =========================================================

# Use these IDs EXACTLY when matching entities appear.


# ## INDUSTRY

# - industry:semiconductor
# - industry:battery
# - industry:auto
# - industry:finance
# - industry:biohealth
# - industry:shipbuilding
# - industry:steel_material
# - industry:it_platform
# - industry:construction_realestate
# - industry:energy


# ## COMPANY

# - company:samsung_electronics
# - company:sk_hynix
# - company:hyundai_motor
# - company:kia
# - company:lg_energy_solution
# - company:posco_holdings
# - company:kakao
# - company:naver
# - company:celltrion
# - company:hanwha_aerospace
# - company:kb_bank
# - company:shinhan_bank
# - company:kakaobank
# - company:toss
# - company:krafton
# - company:hd_hyundai_heavy


# ## PERSON

# - person:lee_jaeyong
# - person:choi_taewon
# - person:chung_euisun
# - person:lee_haejin
# - person:rhee_changyong
# - person:choi_sangmok
# - person:kim_byunghwan


# ## ORGANIZATION

# - organization:bank_of_korea
# - organization:moef
# - organization:fsc
# - organization:ftc
# - organization:krx
# - organization:fss
# - organization:kdi
# - organization:federal_reserve
# - organization:imf
# - organization:kcci
# - organization:fki


# ## ASSET

# - asset:kospi
# - asset:usdkrw
# - asset:treasury_3y
# - asset:cofix
# - asset:dubai_oil
# - asset:dram_spot_price
# - asset:lithium_price


# # =========================================================
# # VALID ENTITY TYPES
# # =========================================================

# VALID_ENTITY_TYPES = [

#     "Company",
#     "Policy",
#     "Event",
#     "Industry",
#     "Asset",
#     "Person",
#     "Organization",
#     "EconomicAgent"

# ]


# # =========================================================
# # ENTITY TYPE RULES
# # =========================================================

# Use "Company" for:

# - commercial corporations
# - banks
# - listed firms
# - private firms


# Use "Organization" ONLY for:

# - governments
# - regulators
# - public institutions
# - associations
# - NGOs
# - international organizations


# Use "Asset" for:

# - stock index
# - exchange rate
# - interest rate
# - commodity price
# - economic indicators


# Use "EconomicAgent" for:

# - foreign investors
# - institutional investors
# - retail investors
# - market participants
# - consumers
# - customers
# - labor unions
# - workers
# - farmers


# # =========================================================
# # ENTITY FILTERING RULES
# # =========================================================

# Extract ONLY:

# - economically meaningful
# - specific
# - named entities
# - entities directly relevant to the article's
#   economic narrative


# Do NOT extract:

# - vague concepts
# - generic economic terms
# - abstract nouns
# - unnamed groups unless they are explicit economic actors
#   in a selected claim
# - broad industries unless directly discussed
# - entities only weakly mentioned


# # =========================================================
# # CLAIM-FIRST EXTRACTION WORKFLOW
# # =========================================================

# Step 1. Select 1 to 4 core claims.

# Core claims should describe economically meaningful
# events, actions, conflicts, risks, reactions, or impacts.

# Step 2. Extract entities only if they participate
# in at least one selected claim.

# Step 3. Extract relations only if the selected claim
# states an action, impact, conflict, support,
# or measurement between two entities.

# Do NOT create relations merely because two entities
# are mentioned in the same sentence.

# For example:

# - "정용진 신세계그룹 회장이 사과했다"
#   is a claim.
#   It does NOT imply that Starbucks SUPPORTS 정용진.

# - "소비자들의 불매운동과 회원 탈퇴가 확산됐다"
#   should produce:
#   consumers AFFECTS Starbucks Korea
#   with effect "weakening".

# - "부적절한 이벤트로 스타벅스코리아가 비난을 받고 있다"
#   should produce:
#   consumers AFFECTS Starbucks Korea
#   with effect "weakening"
#   if consumers/public backlash is explicitly stated.


# # =========================================================
# # RELATION RULES
# # =========================================================

# Relations must follow causal direction.

# Cause/source entity
#     →
# Affected/target entity


# VALID_RELATION_TYPES = [

#     "AFFECTS",
#     "SUPPORTS",
#     "MEASURES"

# ]


# # =========================================================
# # RELATION SEMANTICS
# # =========================================================

# AFFECTS:
# Directly impacts the target entity through
# explicitly stated economic influence.

# SUPPORTS:
# Provides direct support, cooperation,
# investment, policy assistance,
# or favorable influence explicitly stated
# in the article.

# MEASURES:
# Represents metric or indicator relationships.


# Relations represent semantic relation categories.

# Effects represent the CURRENT relation state,
# directional change, or intensity
# described in THIS article.

# The same relation between two entities
# may persist over time while its effect/state changes.

# Do NOT create new relation types
# for state changes.

# Use the same relation type
# and update the effect.


# # =========================================================
# # RELATION EXTRACTION CONSTRAINTS
# # =========================================================

# Extract ONLY relations explicitly supported
# by the article.

# Do NOT infer macroeconomic,
# financial, or causal relations
# unless directly stated.

# Do NOT create speculative relations.

# Do NOT create relations from general world knowledge.

# If the article merely mentions two entities together,
# do NOT assume a relation exists.


# # =========================================================
# # EFFECT RULES
# # =========================================================

# VALID_EFFECT_VALUES = [

#     "active",
#     "strengthening",
#     "weakening",
#     "inactive",
#     "neutral"

# ]


# Effects describe:

# - current relation state
# - directional change
# - relation intensity

# Effects do NOT represent sentiment.


# Examples:

# - 협력 확대
#     → strengthening

# - 공급 축소
#     → weakening

# - 계약 종료
#     → inactive

# - 협력 유지
#     → active


# # =========================================================
# # CLAIM RULES
# # =========================================================

# Claims are textual evidence.

# Claims should summarize important
# economic statements from the article.

# Claims are NOT entities.

# Keep claims concise and factual.

# Claim confidence reflects extraction certainty,
# NOT factual truth.

# Claim confidence must be between 0 and 1.


# # =========================================================
# # OUTPUT FORMAT
# # =========================================================

# {
#     "entities": [
#         {
#             "id": "...",
#             "type": "...",
#             "name": "..."
#         }
#     ],

#     "relations": [
#         {
#             "source": "...",
#             "target": "...",
#             "relation": "...",
#             "effect": "..."
#         }
#     ],

#     "claims": [
#         {
#             "claim": "...",
#             "confidence": 0.0
#         }
#     ]
# }

# """

def normalize_entity_id(entity_id):

    entity_id = entity_id.lower()

    entity_id = entity_id.replace("-", "_")

    entity_id = entity_id.replace("&", "_and_")

    entity_id = entity_id.replace(
        "economic_agent",
        "economicagent"
    )

    entity_id = entity_id.replace(
        "economicagent",
        "economicagent"
    )

    if ":" in entity_id:

        prefix, value = entity_id.split(":", 1)

        value = re.sub(r"[^a-z0-9_]+", "_", value)

        value = re.sub(r"_+", "_", value).strip("_")

        return f"{prefix}:{value}"

    entity_id = re.sub(r"[^a-z0-9_]+", "_", entity_id)

    entity_id = re.sub(r"_+", "_", entity_id).strip("_")

    return entity_id


def normalize_alias_key(value):

    if not value:

        return ""

    value = str(value).casefold()

    value = re.sub(r"[\s·ㆍ/()\-_,.]+", "", value)

    return value


KNOWN_ENTITY_ALIAS_TO_ID = {
    normalize_alias_key(name): entity_id
    for name, entity_id in KNOWN_ENTITY_NAME_TO_ID.items()
}

ONTOLOGY_ID_BY_ALIAS = {
    normalize_alias_key(node.get("name")): node["id"]
    for node in nodes
    if node.get("name")
}


def normalize_name(name):

    if not name:

        return ""

    return re.sub(r"\s+", "", str(name)).strip()


def is_valid_entity_id(entity_id):

    if not entity_id or ":" not in entity_id:

        return False

    prefix, value = entity_id.split(":", 1)

    return bool(prefix and value)


def should_drop_entity(entity):

    entity_name = entity.get("name")

    entity_id = entity.get("id")

    if not is_valid_entity_id(entity_id):

        return True

    if entity_name in GENERIC_ENTITY_NAMES:

        return True

    return False


def names_match(left, right):

    return normalize_name(left) == normalize_name(right)


def fallback_entity_id(entity_type, name):

    prefix = ENTITY_TYPE_TO_PREFIX.get(entity_type, "entity")

    normalized_name = normalize_name(name)

    if re.search(r"[a-zA-Z]", normalized_name):

        slug = normalized_name.casefold()

        slug = slug.replace("&", " and ")

        slug = re.sub(r"[^a-z0-9]+", "_", slug)

        slug = re.sub(r"_+", "_", slug).strip("_")

        if slug:

            return f"{prefix}:{slug}"

    digest = hashlib.sha1(
        normalized_name.encode("utf-8")
    ).hexdigest()[:10]

    return f"{prefix}:entity_{digest}"


def canonicalize_entity(entity):

    entity_id = normalize_entity_id(entity.get("id", ""))

    entity_name = entity.get("name")

    entity_type = entity.get("type")

    entity_alias = normalize_alias_key(entity_name)

    if entity_name in ONTOLOGY_ID_BY_NAME:

        return ONTOLOGY_ID_BY_NAME[entity_name]

    if entity_name in KNOWN_ENTITY_NAME_TO_ID:

        return KNOWN_ENTITY_NAME_TO_ID[entity_name]

    if entity_alias in ONTOLOGY_ID_BY_ALIAS:

        return ONTOLOGY_ID_BY_ALIAS[entity_alias]

    if entity_alias in KNOWN_ENTITY_ALIAS_TO_ID:

        return KNOWN_ENTITY_ALIAS_TO_ID[entity_alias]

    if not is_valid_entity_id(entity_id):

        return fallback_entity_id(
            entity_type,
            entity_name or "unknown"
        )

    ontology_entity = ONTOLOGY_BY_ID.get(entity_id)

    if ontology_entity and names_match(
        entity_name,
        ontology_entity.get("name")
    ):

        return entity_id

    if ontology_entity and not names_match(
        entity_name,
        ontology_entity.get("name")
    ):

        return fallback_entity_id(
            entity_type,
            entity_name or entity_id
        )

    return entity_id


def apply_canonical_entity_name(entity):

    canonical_name = CANONICAL_ENTITY_NAMES.get(entity.get("id"))

    if canonical_name:

        entity["name"] = canonical_name


def apply_canonical_entity_type(entity):

    canonical_type = CANONICAL_ENTITY_TYPES.get(entity.get("id"))

    if not canonical_type and ":" in entity.get("id", ""):

        prefix = entity["id"].split(":", 1)[0]

        canonical_type = ID_PREFIX_TO_ENTITY_TYPE.get(prefix)

    if canonical_type:

        entity["type"] = canonical_type


# def normalize_extraction_result(result):

#     id_remap = {}
#     dropped_ids = set()
#     normalized_entities = []
#     seen_entity_ids = set()

#     for entity in result.get("entities", []):

#         if "id" not in entity:

#             continue

#         original_id = normalize_entity_id(entity["id"])

#         canonical_id = canonicalize_entity(entity)

#         entity["id"] = canonical_id

#         if original_id != canonical_id:

#             id_remap[original_id] = canonical_id

#         apply_canonical_entity_name(entity)

#         if should_drop_entity(entity):

#             dropped_ids.add(canonical_id)
#             dropped_ids.add(original_id)

#             continue

#         if canonical_id in seen_entity_ids:

#             continue

#         seen_entity_ids.add(canonical_id)

#         normalized_entities.append(entity)

#     result["entities"] = normalized_entities

#     normalized_relations = []

#     for relation in result.get("relations", []):

#         if "source" in relation:

#             source = normalize_entity_id(relation["source"])

#             relation["source"] = id_remap.get(source, source)

#         if "target" in relation:

#             target = normalize_entity_id(relation["target"])

#             relation["target"] = id_remap.get(target, target)

#         if (
#             relation.get("source") in dropped_ids
#             or relation.get("target") in dropped_ids
#             or not is_valid_entity_id(relation.get("source"))
#             or not is_valid_entity_id(relation.get("target"))
#         ):

#             continue

#         normalized_relations.append(relation)

#     result["relations"] = normalized_relations

#     return result

def normalize_extraction_result(result):

    dropped_ids = set()

    normalized_entities = []
    seen_entity_ids = set()

    name_to_id = {}

    # --------------------------------------------------
    # Entity Normalization
    # --------------------------------------------------

    for entity in result.get("entities", []):

        if "type" not in entity:
            continue

        if "name" not in entity:
            continue

        original_name = entity.get("name")

        original_id = normalize_entity_id(entity.get("id", ""))

        # canonical id 생성
        canonical_id = canonicalize_entity(entity)

        entity["id"] = canonical_id

        apply_canonical_entity_name(entity)

        apply_canonical_entity_type(entity)

        if should_drop_entity(entity):

            dropped_ids.add(canonical_id)

            continue

        if canonical_id in seen_entity_ids:

            continue

        seen_entity_ids.add(canonical_id)

        normalized_entities.append(entity)

        name_to_id[entity["name"]] = canonical_id
        name_to_id[normalize_name(entity["name"])] = canonical_id

        if original_name:

            name_to_id[original_name] = canonical_id
            name_to_id[normalize_name(original_name)] = canonical_id

        if is_valid_entity_id(original_id):

            name_to_id[original_id] = canonical_id

    result["entities"] = normalized_entities

    # --------------------------------------------------
    # Relation Normalization
    # --------------------------------------------------

    normalized_relations = []

    for relation in result.get("relations", []):

        source_name = relation.get("source")
        target_name = relation.get("target")

        if not source_name or not target_name:
            continue

        source_id = (
            name_to_id.get(source_name)
            or name_to_id.get(normalize_name(source_name))
            or (
                normalize_entity_id(source_name)
                if is_valid_entity_id(normalize_entity_id(source_name))
                else None
            )
        )

        target_id = (
            name_to_id.get(target_name)
            or name_to_id.get(normalize_name(target_name))
            or (
                normalize_entity_id(target_name)
                if is_valid_entity_id(normalize_entity_id(target_name))
                else None
            )
        )

        # relation이 존재하는 entity끼리만 연결
        if (
            not source_id
            or not target_id
            or source_id not in seen_entity_ids
            or target_id not in seen_entity_ids
        ):
            continue

        relation["source"] = source_id
        relation["target"] = target_id

        if (
            source_id in dropped_ids
            or target_id in dropped_ids
        ):
            continue

        normalized_relations.append(relation)

    result["relations"] = normalized_relations

    return result


# =========================================================
# Extract Knowledge from News
# =========================================================

# def extract_knowledge_from_llm(content):
#     # -------------------------------------------------
#     # OpenAI API Call
#     # -------------------------------------------------

#     response = client.chat.completions.create(

#         model="gpt-4o-mini",

#         temperature=0,

#         response_format={
#             "type": "json_object"
#         },

#         messages=[

#             {
#                 "role": "system",
#                 "content": SYSTEM_PROMPT
#             },

#             {
#                 "role": "user",
#                 "content": content
#             }

#         ]

#     )

#     raw_text = response.choices[0].message.content.strip()


#     raw_text = raw_text.strip()

#     # -------------------------------------------------
#     # Parse JSON
#     # -------------------------------------------------

#     try:

#         result = json.loads(raw_text)

#     except json.JSONDecodeError:

#         print(raw_text)

#         raise ValueError("Invalid JSON response")
    
#     result = normalize_extraction_result(result)
    
    
#     print(

#         json.dumps(

#             result,

#             ensure_ascii=False,

#             indent=2

#             )   
#         )      

#     return result

import os
import json
import requests


def parse_json_response(raw_text):

    raw_text = raw_text.strip()

    if raw_text.startswith("```"):

        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)

    try:

        return json.loads(raw_text)

    except json.JSONDecodeError:

        match = re.search(r"\{.*\}", raw_text, re.DOTALL)

        if match:

            return json.loads(match.group(0))

        print(raw_text)

        raise ValueError("Invalid JSON response")


def extract_knowledge_from_llm(content):

    response = requests.post(
        # "https://bridge.luxiacloud.com/luxia/v1/chat",
        "https://bridge.luxiacloud.com/llm/openai/chat/completions/gpt-4o-mini/create",
        headers={
            "apikey": os.getenv("LUXIA_API_KEY"),
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-4o-mini-2024-07-18",
            # "model": "luxia3-llm-32b-0731",
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": content
                }
            ]
        },
        timeout=120
    )

    if not response.ok:

        print(response.status_code)
        print(response.text)

    response.raise_for_status()

    response_json = response.json()

    # # 응답 구조 확인용
    # print(json.dumps(response_json, ensure_ascii=False, indent=2))

    raw_text = (
        response_json["choices"][0]
        ["message"]
        ["content"]
        .strip()
    )

    result = parse_json_response(raw_text)

    result = normalize_extraction_result(result)

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        )
    )

    return result




if __name__ == "__main__":

    with open(

        "data/processed_news_backup/news_20260519_0001_result.json",
        "r",
        encoding="utf-8"

    ) as f:

        news_data = json.load(f)

    print(news_data["content"])
    result = extract_knowledge_from_llm(news_data["content"])

    # print(

    #     json.dumps(

    #         result,

    #         ensure_ascii=False,

    #         indent=2

    #     )

    # )
