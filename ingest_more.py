"""
Veri-RAG: 고장난 API 수정 패치
================================
이 파일을 실행하면 기존 ingest_real_data.py에서 실패한 항목들을 수집합니다.
- 코스피/코스닥 → ECOS API (pykrx 대신)
- 원/달러 환율 → ECOS API (stat_code 수정)
- GDP 성장률 → ECOS API (stat_code 수정)
- 서울 아파트/전세 → PublicDataReader (파라미터 수정)
- 국가채무 → 열린재정 (파싱 수정)

사용법:
    $env:ECOS_API_KEY="your_key"
    $env:OPENFISCAL_API_KEY="your_key"
    python fix_broken_apis.py
"""

import os
import json
import requests
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timedelta


def get_db():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", 5432)),
        database=os.environ.get("DB_NAME", "verirag"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", "verirag123"),
    )


def ecos_fetch(api_key, stat_code, cycle, start, end, item_code1, item_code2=""):
    """ECOS API 공통 호출 함수"""
    url = (
        f"https://ecos.bok.or.kr/api/StatisticSearch/"
        f"{api_key}/json/kr/1/100/{stat_code}/{cycle}/{start}/{end}/{item_code1}"
    )
    if item_code2:
        url += f"/{item_code2}"

    resp = requests.get(url, timeout=30)
    data = resp.json()

    if "StatisticSearch" not in data:
        msg = data.get("RESULT", {}).get("MESSAGE", "unknown")
        print(f"    ECOS 오류 ({stat_code}): {msg}")
        return []

    return data["StatisticSearch"]["row"]


# ============================================================
# 1. 코스피/코스닥 (ECOS API - pykrx 대신)
#    stat_code: 802Y001 (증권/재정 - 주식거래 및 주가지수)
#    코스피 item_code: 0001000
#    코스닥 item_code: 2001000
# ============================================================


def fix_kospi_kosdaq():
    api_key = os.environ.get("ECOS_API_KEY")
    if not api_key:
        print("  코스피: ECOS_API_KEY 필요")
        return 0

    end = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=60)).strftime("%Y%m%d")

    conn = get_db()
    cur = conn.cursor()
    total = 0

    indices = {
        "KOSPI": "0001000",
        "KOSDAQ": "2001000",
    }

    for name, item_code in indices.items():
        rows_data = ecos_fetch(api_key, "802Y001", "D", start, end, item_code)

        rows = []
        for item in rows_data:
            try:
                time_str = item["TIME"]
                date_str = f"{time_str[:4]}-{time_str[4:6]}-{time_str[6:]}"
                value = float(item["DATA_VALUE"])
                rows.append((name, date_str, value, None, "한국은행"))
            except ValueError, KeyError:
                continue

        if rows:
            execute_values(
                cur,
                """
                INSERT INTO market_data (symbol, date, close_price, volume, source)
                VALUES %s
                ON CONFLICT (symbol, date, source) DO UPDATE
                SET close_price = EXCLUDED.close_price, fetched_at = NOW()
                """,
                rows,
            )
            total += len(rows)
            print(f"  {name}: {len(rows)}일치")

    conn.commit()
    cur.close()
    conn.close()
    return total


# ============================================================
# 2. 원/달러 환율 (ECOS - stat_code 수정)
#    stat_code: 731Y001 (평균환율/기간말환율)
#    item_code1: 0000001 (원/미달러)
#    item_code2: 0000200 (매매기준율)
# ============================================================


def fix_exchange_rate():
    api_key = os.environ.get("ECOS_API_KEY")
    if not api_key:
        print("  환율: ECOS_API_KEY 필요")
        return 0

    end = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=60)).strftime("%Y%m%d")

    rows_data = ecos_fetch(api_key, "731Y001", "D", start, end, "0000001", "0000200")

    conn = get_db()
    cur = conn.cursor()

    rows = []
    for item in rows_data:
        try:
            time_str = item["TIME"]
            date_str = f"{time_str[:4]}-{time_str[4:6]}-{time_str[6:]}"
            value = float(item["DATA_VALUE"].replace(",", ""))
            rows.append(("USD_KRW", date_str, value, None, "한국은행"))
        except ValueError, KeyError:
            continue

    if rows:
        execute_values(
            cur,
            """
            INSERT INTO market_data (symbol, date, close_price, volume, source)
            VALUES %s
            ON CONFLICT (symbol, date, source) DO UPDATE
            SET close_price = EXCLUDED.close_price, fetched_at = NOW()
            """,
            rows,
        )

    conn.commit()
    cur.close()
    conn.close()
    print(f"  USD_KRW: {len(rows)}일치")
    return len(rows)


# ============================================================
# 3. GDP 성장률 (ECOS - stat_code 수정)
#    stat_code: 200Y002 (국내총생산에 대한 지출(실질, 원계열))
#    item_code1: 10111 (국내총생산(GDP))
# ============================================================


def fix_gdp():
    api_key = os.environ.get("ECOS_API_KEY")
    if not api_key:
        print("  GDP: ECOS_API_KEY 필요")
        return 0

    # 분기 데이터: QQ 형식 (예: 2024Q1)
    rows_data = ecos_fetch(api_key, "200Y002", "Q", "2024Q1", "2026Q4", "10111")

    conn = get_db()
    cur = conn.cursor()

    rows = []
    for item in rows_data:
        try:
            time_str = item["TIME"]  # "2025Q1"
            year = time_str[:4]
            quarter = int(time_str[-1])
            month = {1: "01", 2: "04", 3: "07", 4: "10"}[quarter]
            date_str = f"{year}-{month}-01"
            value = float(item["DATA_VALUE"].replace(",", ""))
            rows.append(
                (
                    "GDP_GROWTH_RATE",
                    "GDP 성장률(전기대비)",
                    value,
                    "percent_qoq",
                    date_str,
                    "한국은행",
                )
            )
        except ValueError, KeyError:
            continue

    if rows:
        execute_values(
            cur,
            """
            INSERT INTO economic_indicators
                (indicator_code, indicator_name, value, unit, observation_date, source)
            VALUES %s
            ON CONFLICT (indicator_code, observation_date, source) DO UPDATE
            SET value = EXCLUDED.value, fetched_at = NOW()
            """,
            rows,
        )

    conn.commit()
    cur.close()
    conn.close()
    print(f"  GDP: {len(rows)}건")
    return len(rows)


# ============================================================
# 4. 서울 아파트 매매/전세 (PublicDataReader 파라미터 수정)
# ============================================================


def fix_apt_price():
    try:
        from PublicDataReader import Kbland

        api = Kbland()
        conn = get_db()
        cur = conn.cursor()
        total = 0

        configs = [
            ("01", "APT_PRICE_INDEX_SEOUL", "서울 아파트 매매가격지수"),
            ("02", "JEONSE_INDEX_SEOUL", "서울 아파트 전세가격지수"),
        ]

        for trade_code, indicator_code, indicator_name in configs:
            try:
                df = api.get_price_index(
                    월간주간구분코드="01", 매물종별구분="01", 매매전세코드=trade_code
                )
                df = df[df["지역명"] == "서울"].tail(12)

                rows = []
                for _, r in df.iterrows():
                    rows.append(
                        (
                            indicator_code,
                            indicator_name,
                            float(r["가격지수"]),
                            "index",
                            str(r["날짜"])[:10],
                            "KB부동산",
                        )
                    )

                if rows:
                    execute_values(
                        cur,
                        """
                        INSERT INTO economic_indicators
                            (indicator_code, indicator_name, value, unit, observation_date, source)
                        VALUES %s
                        ON CONFLICT (indicator_code, observation_date, source) DO UPDATE
                        SET value = EXCLUDED.value, fetched_at = NOW()
                        """,
                        rows,
                    )
                    total += len(rows)
                    print(f"  {indicator_code}: {len(rows)}건")

            except Exception as e:
                print(f"  {indicator_code}: 오류 - {e}")

        conn.commit()
        cur.close()
        conn.close()
        return total

    except ImportError:
        print("  아파트: PublicDataReader 설치 필요")
        return 0
    except Exception as e:
        print(f"  아파트: 오류 - {e}")
        return 0


# ============================================================
# 5. 기준금리 (한국은행 ECOS API)
# ============================================================


def ingest_base_rate():
    """
    한국은행 기준금리
    stat_code: 722Y001 (한국은행 기준금리)
    """
    import requests

    api_key = os.environ.get("ECOS_API_KEY")
    if not api_key:
        print("  기준금리: ECOS_API_KEY 필요")
        return 0

    url = (
        f"https://ecos.bok.or.kr/api/StatisticSearch/"
        f"{api_key}/json/kr/1/100/722Y001/M/202501/202612/0101000"
    )

    resp = requests.get(url, timeout=30)
    data = resp.json()

    if "StatisticSearch" not in data:
        print(
            f"  기준금리: API 오류 - {data.get('RESULT', {}).get('MESSAGE', 'unknown')}"
        )
        return 0

    conn = get_db()
    cur = conn.cursor()

    rows = []
    for item in data["StatisticSearch"]["row"]:
        try:
            date_str = f"{item['TIME'][:4]}-{item['TIME'][4:6]}-01"
            value = float(item["DATA_VALUE"])
            rows.append(
                (
                    "BASE_RATE_KR",
                    "한국은행 기준금리",
                    value,
                    "percent",
                    date_str,
                    "한국은행",
                )
            )
        except ValueError, KeyError:
            continue

    execute_values(
        cur,
        """
        INSERT INTO economic_indicators
            (indicator_code, indicator_name, value, unit, observation_date, source)
        VALUES %s
        ON CONFLICT (indicator_code, observation_date, source) DO UPDATE
        SET value = EXCLUDED.value, fetched_at = NOW()
        """,
        rows,
    )

    conn.commit()
    cur.close()
    conn.close()
    print(f"  기준금리: {len(rows)}건")
    return len(rows)


# ============================================================
# 6. 소비자물가지수 CPI (한국은행 ECOS API)
# ============================================================


def ingest_cpi():
    """
    소비자물가지수
    stat_code: 901Y009 (소비자물가지수 총지수)
    """
    import requests

    api_key = os.environ.get("ECOS_API_KEY")
    if not api_key:
        print("  CPI: ECOS_API_KEY 필요")
        return 0

    url = (
        f"https://ecos.bok.or.kr/api/StatisticSearch/"
        f"{api_key}/json/kr/1/100/901Y009/M/202501/202612/0"
    )

    resp = requests.get(url, timeout=30)
    data = resp.json()

    if "StatisticSearch" not in data:
        print(f"  CPI: API 오류 - {data.get('RESULT', {}).get('MESSAGE', 'unknown')}")
        return 0

    conn = get_db()
    cur = conn.cursor()

    rows = []
    for item in data["StatisticSearch"]["row"]:
        try:
            date_str = f"{item['TIME'][:4]}-{item['TIME'][4:6]}-01"
            value = float(item["DATA_VALUE"])
            rows.append(
                ("CPI_KR", "소비자물가지수", value, "index", date_str, "통계청")
            )
        except ValueError, KeyError:
            continue

    execute_values(
        cur,
        """
        INSERT INTO economic_indicators
            (indicator_code, indicator_name, value, unit, observation_date, source)
        VALUES %s
        ON CONFLICT (indicator_code, observation_date, source) DO UPDATE
        SET value = EXCLUDED.value, fetched_at = NOW()
        """,
        rows,
    )

    conn.commit()
    cur.close()
    conn.close()
    print(f"  CPI: {len(rows)}건")
    return len(rows)


# ============================================================
# 7. 기름값 (오피넷 API - 한국석유공사)
#    API 신청: https://www.opinet.co.kr → 유가정보 API → 회원가입 → 키 발급
# ============================================================


def ingest_oil_price():
    """
    오피넷 API: 전국 주유소 평균 유가
    API: /avgAllPrice.do (전국 평균 유가 현재)
    API: /avgSidoPrice.do (시도별 평균 유가)
    """
    import requests

    api_key = os.environ.get("OPINET_API_KEY")
    if not api_key:
        print("  기름값: OPINET_API_KEY 필요")
        print("  발급: https://www.opinet.co.kr → 유가정보 API → 회원가입")
        return 0

    # 전국 평균 유가 (현재)
    url = f"http://www.opinet.co.kr/api/avgAllPrice.do?out=json&code={api_key}"

    try:
        resp = requests.get(url, timeout=30)
        data = resp.json()

        oil_data = data.get("RESULT", {}).get("OIL", [])
        if not oil_data:
            print("  기름값: 데이터 없음")
            return 0

        conn = get_db()
        cur = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")

        rows = []
        for item in oil_data:
            prod_code = item.get("PRODCD")
            price = float(item.get("PRICE", 0))
            trade_date = item.get("TRADE_DT", today)

            # 날짜 포맷 변환: YYYYMMDD → YYYY-MM-DD
            if len(trade_date) == 8:
                trade_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}"

            # 유종 매핑
            prod_map = {
                "B027": ("OIL_GASOLINE", "휘발유 전국평균가격", "won_per_liter"),
                "D047": ("OIL_DIESEL", "경유 전국평균가격", "won_per_liter"),
                "C004": ("OIL_LPG", "LPG 전국평균가격", "won_per_liter"),
                "B034": ("OIL_PREMIUM", "고급휘발유 전국평균가격", "won_per_liter"),
            }

            if prod_code in prod_map:
                code, name, unit = prod_map[prod_code]
                rows.append((code, name, price, unit, trade_date, "오피넷"))

        if rows:
            execute_values(
                cur,
                """
                INSERT INTO economic_indicators
                    (indicator_code, indicator_name, value, unit, observation_date, source)
                VALUES %s
                ON CONFLICT (indicator_code, observation_date, source) DO UPDATE
                SET value = EXCLUDED.value, fetched_at = NOW()
                """,
                rows,
            )

        conn.commit()
        cur.close()
        conn.close()
        print(f"  기름값: {len(rows)}건 (휘발유/경유/LPG/고급)")
        return len(rows)

    except Exception as e:
        print(f"  기름값: 오류 - {e}")
        return 0


# ============================================================
# 8. 국가채무 (열린재정 - 파싱 수정)
# ============================================================


def fix_fiscal():
    api_key = os.environ.get("OPENFISCAL_API_KEY")
    if not api_key:
        print("  국가채무: OPENFISCAL_API_KEY 필요")
        return 0

    url = "https://openapi.openfiscaldata.go.kr/GovernmentDebtMonth"
    params = {
        "Key": api_key,
        "Type": "json",
        "pIndex": "1",
        "pSize": "100",
    }

    try:
        resp = requests.get(url, params=params, timeout=30)
        print(repr(resp.text[:100]))
        data = json.loads(json.loads(resp.text))
        print(f"    응답 키: {list(data.keys())}")

        # 응답 구조 디버깅
        print(
            f"    응답 키: {list(data.keys()) if isinstance(data, dict) else type(data)}"
        )

        items = []
        for key in data:
            val = data[key]
            if isinstance(val, list):
                for entry in val:
                    if isinstance(entry, dict) and "row" in entry:
                        items = entry["row"]
                        break
                    elif isinstance(entry, list):
                        items = entry
                        break
            elif isinstance(val, dict) and "row" in val:
                items = val["row"]

        if not items:
            print("  국가채무: 데이터 파싱 실패")
            # 전체 구조 출력 (디버깅용)
            print(f"    전체 응답: {json.dumps(data, ensure_ascii=False)[:500]}")
            return 0

        conn = get_db()
        cur = conn.cursor()

        rows = []
        for item in items:
            try:
                year = str(item.get("OJ_YY", ""))
                month = str(item.get("OJ_M", "")).strip().zfill(2)
                total_debt = item.get("GOD_SUM_AMT")

                if not year or not total_debt:
                    continue

                date_str = f"{year}-{month}-01"
                value = float(str(total_debt).replace(",", ""))

                rows.append(
                    (
                        "GOVT_DEBT_TOTAL",
                        "국가채무총계",
                        value,
                        "억원",
                        date_str,
                        "기획재정부",
                    )
                )
            except ValueError, KeyError, TypeError:
                continue

        if rows:
            execute_values(
                cur,
                """
                INSERT INTO economic_indicators
                    (indicator_code, indicator_name, value, unit, observation_date, source)
                VALUES %s
                ON CONFLICT (indicator_code, observation_date, source) DO UPDATE
                SET value = EXCLUDED.value, fetched_at = NOW()
                """,
                rows,
            )

        conn.commit()
        cur.close()
        conn.close()
        print(f"  국가채무: {len(rows)}건")
        return len(rows)

    except Exception as e:
        print(f"  국가채무: 오류 - {e}")
        return 0


# ============================================================
# 메인
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("Veri-RAG: 고장난 API 수정 패치")
    print("=" * 50)

    results = {}

    ecos_key = os.environ.get("ECOS_API_KEY")

    if ecos_key:
        print("\n📈 코스피/코스닥 (ECOS API)")
        results["kospi"] = fix_kospi_kosdaq()

        print("\n💱 원/달러 환율 (ECOS API)")
        results["usd_krw"] = fix_exchange_rate()

        print("\n📊 GDP 성장률 (ECOS API)")
        results["gdp"] = fix_gdp()
    else:
        print("\n⚠️  ECOS_API_KEY 없음")

    print("\n🏠 서울 아파트 매매/전세 (KB부동산)")
    results["apt"] = fix_apt_price()

    openfiscal_key = os.environ.get("OPENFISCAL_API_KEY")
    if openfiscal_key:
        print("\n💰 국가채무 (열린재정)")
        results["fiscal"] = fix_fiscal()
    else:
        print("\n⚠️  OPENFISCAL_API_KEY 없음")

    print("\n" + "=" * 50)
    total = sum(results.values())
    print(f"✅ 패치 완료! 총 {total}건 추가/업데이트")
    for name, count in results.items():
        status = "✅" if count > 0 else "❌"
        print(f"   {status} {name}: {count}건")
