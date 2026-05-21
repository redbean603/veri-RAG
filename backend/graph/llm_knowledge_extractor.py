import json
from google import genai
from openai import OpenAI
import os
from dotenv import load_dotenv


## sample news data
with open(

    "data/processed_news_backup/news_20260519_0001_result.json",
    "r",
    encoding="utf-8"

) as f:

    news_data = json.load(f)

# =========================================================
# Gemini Client
# =========================================================



load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


SYSTEM_PROMPT = """
You are an economic knowledge graph extractor.

Your task is to extract:

1. Economic entities
2. Economic relations
3. Economic claims

Return ONLY valid JSON.

Do NOT include markdown.
Do NOT explain anything.
Do NOT generate text outside JSON.


# =========================================================
# ENTITY NORMALIZATION RULES
# =========================================================

- Normalize entity names consistently.
- Use official Korean economic entity names for "name".
- IDs must be deterministic and stable.
- IDs must NEVER be random.
- Reuse existing ontology IDs whenever possible.
- Do NOT create duplicate entities.


# =========================================================
# ENTITY ID FORMAT
# =========================================================

ID rules:

- lowercase only
- snake_case only
- English canonical names only
- no spaces
- no Korean in IDs
- deterministic and stable

Examples:

- company:samsung_electronics
- company:sk_hynix
- industry:semiconductor
- organization:bank_of_korea
- asset:usdkrw
- person:lee_jaeyong


# =========================================================
# EXISTING ONTOLOGY IDS
# =========================================================

Use these IDs EXACTLY when matching entities appear.


## INDUSTRY

- industry:semiconductor
- industry:battery
- industry:auto
- industry:finance
- industry:biohealth
- industry:shipbuilding
- industry:steel_material
- industry:it_platform
- industry:construction_realestate
- industry:energy


## COMPANY

- company:samsung_electronics
- company:sk_hynix
- company:hyundai_motor
- company:kia
- company:lg_energy_solution
- company:posco_holdings
- company:kakao
- company:naver
- company:celltrion
- company:hanwha_aerospace
- company:kb_bank
- company:shinhan_bank
- company:kakaobank
- company:toss
- company:krafton
- company:hd_hyundai_heavy


## PERSON

- person:lee_jaeyong
- person:choi_taewon
- person:chung_euisun
- person:lee_haejin
- person:rhee_changyong
- person:choi_sangmok
- person:kim_byunghwan


## ORGANIZATION

- organization:bank_of_korea
- organization:moef
- organization:fsc
- organization:ftc
- organization:krx
- organization:fss
- organization:kdi
- organization:federal_reserve
- organization:imf
- organization:kcci
- organization:fki


## ASSET

- asset:kospi
- asset:usdkrw
- asset:treasury_3y
- asset:cofix
- asset:dubai_oil
- asset:dram_spot_price
- asset:lithium_price


# =========================================================
# VALID ENTITY TYPES
# =========================================================

VALID_ENTITY_TYPES = [

    "Company",
    "Policy",
    "Event",
    "Industry",
    "Asset",
    "Person",
    "Organization",
    "EconomicAgent"

]


Use "Asset" for:

- stock index
- exchange rate
- interest rate
- commodity price
- economic indicators


Use "EconomicAgent" for:

- foreign investors
- institutional investors
- retail investors
- market participants


Extract ONLY:

- economically meaningful
- specific
- named entities


Do NOT extract:

- vague concepts
- generic economic terms
- abstract nouns
- unnamed groups


# =========================================================
# RELATION RULES
# =========================================================

Relations must follow causal direction.

Cause/source entity
    →
Affected/target entity


VALID_RELATION_TYPES = [

    "AFFECTS",
    "SUPPORTS",
    "MEASURES"

]


Effect values:

- positive
- negative
- neutral


Examples:

- 금리 인상
    AFFECTS
    코스피

- 유가 상승
    AFFECTS
    항공주


Confidence must be between 0 and 1.


# =========================================================
# CLAIM RULES
# =========================================================

Claims are textual evidence.

Claims should summarize important economic statements from the article.

Claims are NOT entities.

Keep claims concise and factual.


# =========================================================
# OUTPUT FORMAT
# =========================================================

{
    "entities": [
        {
            "id": "...",
            "type": "...",
            "name": "..."
        }
    ],

    "relations": [
        {
            "source": "...",
            "target": "...",
            "relation": "...",
            "effect": "...",
            "confidence": 0.0
        }
    ],

    "claims": [
        {
            "claim": "...",
            "confidence": 0.0
        }
    ]
}
"""



# =========================================================
# Extract Knowledge from News
# =========================================================

def extract_knowledge_from_llm(content):
    # -------------------------------------------------
    # OpenAI API Call
    # -------------------------------------------------

    response = client.chat.completions.create(

        model="gpt-4o-mini",

        temperature=0,

        response_format={
            "type": "json_object"
        },

        messages=[

            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },

            {
                "role": "user",
                "content": content
            }

        ]

    )

    raw_text = response.choices[0].message.content.strip()

    # # -------------------------------------------------
    # # Remove Markdown JSON Fence
    # # -------------------------------------------------

    # raw_text = raw_text.replace(
    #     "```json",
    #     ""
    # )

    # raw_text = raw_text.replace(
    #     "```",
    #     ""
    # )

    raw_text = raw_text.strip()

    # -------------------------------------------------
    # Parse JSON
    # -------------------------------------------------

    try:

        result = json.loads(raw_text)

    except json.JSONDecodeError:

        print(raw_text)

        raise ValueError("Invalid JSON response")
    
    print(

        json.dumps(

            result,

            ensure_ascii=False,

            indent=2

            )   
        )      

    return result

if __name__ == "__main__":
    print(news_data["content"])
    result = extract_knowledge_from_llm(news_data["content"])

    print(

        json.dumps(

            result,

            ensure_ascii=False,

            indent=2

        )

    )