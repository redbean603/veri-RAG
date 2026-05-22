###테스트 2
import json
import time
import requests
import urllib3
from IPython.display import display, HTML
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 1. 핵심 검증 함수 (Vector, Graph 로직 추가)
# ==========================================
MY_LUXIA_KEY = "U2FsdGVkX1/J6RT6IpLGsTFST05CVDjrVL8nX8YHhx5PrckgbioYrIe1SWGq6QsZfG/36uRQE9HbU/0g/Y0gbT7quyIexhaLHGkUBnNpNq1ZkVnzDcpcQkOTAH7PFm3N/Er7wvy1pEVBpCe0Dy4+WIcJrzOZL6a8MKcb4CRfFI/zgxKYwpKjv0waTHjzwrZkgtwOklHtdHOoL3U8wD+AcA=="

def verify_full_rag(news_data, db_data):
    system_prompt = """
    # ROLE
    너는 금융 리포트의 기만(Deception)을 다차원으로 탐지하는 팩트 체크 에이전트다.

    # CONSTRAINTS
    1. SQL 증거주의: [SQL DB]의 수치 데이터는 절대적인 1순위 팩트다. 뉴스 수치와 다르면 무조건 뉴스가 기만이다.
    2. 관계망 파악: [Graph DB]의 지분/인물 관계도를 바탕으로 뉴스가 숨기고 있는 이해관계나 거짓말을 찾아내라.
    3. 맥락 일치: [Vector DB]의 과거 문맥과 현재 뉴스의 논조가 갑자기 180도 바뀌었다면 기만을 의심하라.

    # OUTPUT FORMATTING
    오직 아래 JSON 스키마만 출력하라.
    {
      "verification_result": {
        "is_manipulated": true/false,
        "confidence_score": 0~100,
        "reasoning": "어떤 DB(SQL, Vector, Graph)와 충돌하는지 명시하여 이유를 3문장 이내로 작성"
      }
    }
    """

    # 4가지 데이터가 모두 조립되는 프롬프트 템플릿
    user_prompt = f"""
    [1. 뉴스 입력 데이터 (크롤링 파트)]
    - 기사 제목: {news_data['title']}
    - 핵심 요약본: {news_data['content']}

    [2. SQL 정형 데이터 (수치 파트)]
    - SQL 검색 결과: {db_data.get('sql', '데이터 없음')}

    [3. Vector DB 비정형 데이터 (유사 맥락 파트)]
    - 과거 유사 문헌: {db_data.get('vector', '데이터 없음')}

    [4. Graph DB 관계망 데이터 (네트워크 파트)]
    - 엔티티 관계도: {db_data.get('graph', '데이터 없음')}
    """

    url = "https://bridge.luxiacloud.com/luxia/v1/chat"
    headers = {"Content-Type": "application/json", "apikey": MY_LUXIA_KEY}
    payload = {
        "model": "luxia3-llm-32b-0731",
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "temperature": 0
    }

    try:
        response = requests.post(url, headers=headers, json=payload, verify=False)
        if response.status_code == 200:
            return json.loads(response.json()['choices'][0]['message']['content'])
        return {"error": response.status_code}
    except Exception as e:
        return {"error": str(e)}

# ==========================================
# 2. 극한의 다차원 기만 시나리오 세팅
# ==========================================
# 가짜 뉴스: A기업이 B기업과 아무 관련이 없으며, 독자적으로 엄청난 흑자를 냈다고 주장
mock_news = {
    "title": "[단독] A기업, 사상 최대 흑자 달성! B기업과의 합병설은 '사실무근'으로 밝혀져 독자 생존 청신호",
    "content": "A기업이 1분기에 엄청난 영업이익을 기록하며 흑자 전환에 성공했다. 또한 시장에 돌던 B기업 대주주 관련설은 완전한 거짓으로 판명되었다."
}

예시 문장
mock_dbs = {
    "sql": "DART 공시 기준 A기업 1분기 영업이익: -500억원 (적자 지속)", # 수치 조작 (SQL과 충돌)
    "vector": "최근 1주일 유사 기사 요약: A기업의 분식회계 의혹에 대해 금감원 조사가 임박했다는 업계의 우려가 팽배함.", # 맥락 조작 (Vector와 충돌)
    "graph": "[관계망 도출] 'B기업' --(지분 45% 보유)--> 'A기업' (A기업의 실질적 대주주는 B기업임)" # 관계망 조작 (Graph와 충돌)
}

# ==========================================
# 3. 통합 검증 실행 엔진
# ==========================================
display(HTML("<h2>🌐 Full RAG (4종 데이터 통합) 검증 테스트</h2><hr>"))
display(HTML("<b>🤖 4가지 파트의 데이터를 분석하여 기만을 판별 중입니다...</b> ⏳<br><br>"))

result = verify_full_rag(mock_news, mock_dbs)

if "error" not in result:
    is_mani = result.get('verification_result', {}).get('is_manipulated', False)
    reason = result.get('verification_result', {}).get('reasoning', '')
    score = result.get('verification_result', {}).get('confidence_score', 0)

    color = "red" if is_mani else "green"
    status_text = "🚨 복합적 기만 탐지됨 (거짓 리포트)" if is_mani else "✅ 정상"

    output_html = f"""
    <div style="border: 2px solid {color}; padding: 15px; border-radius: 10px; background-color: #fcfcfc;">
        <h3 style="color: {color}; margin-top: 0;">{status_text} (확신도: {score}%)</h3>
        <p><b>[LLM 검증결과]</b></p>
        <p style="font-size: 1.1em; line-height: 1.5;">{reason}</p>
    </div>
    """
    display(HTML(output_html))
else:
    display(HTML(f"<p style='color: orange;'>⚠️ 에러 발생: {result['error']}</p>"))
