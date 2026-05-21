import requests
from bs4 import BeautifulSoup
import json, os, time, re
from datetime import datetime
from urllib.parse import urljoin
 
# ── 설정 ──────────────────────────────────────────────────────────────────────
BASE_URL     = "https://www.ytn.co.kr"
LIST_URL     = "https://www.ytn.co.kr/news/list.php?mcd=0102"
OUTPUT_JSON  = "ytn_news.json"
IMAGE_DIR    = "images"
MAX_ARTICLES = 20       # None = 무제한
REQUEST_DELAY = 1.0

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": BASE_URL,
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ── 제거할 노이즈 패턴 ────────────────────────────────────────────────────────
_NOISE = re.compile(
    r"^※\s*['']?당신의 제보"
    r"|^\[저작권자"
    r"|^Copyright"
    r"|^\[카카오톡\]"
    r"|^\[전화\]"
    r"|^\[메일\]"
    r"|^AD$"
    r"|^많이 본 뉴스$"
    r"|^경제$"
    r"|^기사목록 전체보기$"
    r"|^https?://ad\."
    r"|^https?://.*smartin"
)
_BYLINE = re.compile(r"^YTN\s+\S+\s*[\(（]?\S+@ytn\.co\.kr[\)）]?")

# ── HTTP 유틸 ─────────────────────────────────────────────────────────────────
def get_soup(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except requests.RequestException as e:
        print(f"  [WARN] GET 실패: {url} — {e}")
        return None

def download_image(img_url, save_dir):
    if not img_url:
        return None
    os.makedirs(save_dir, exist_ok=True)
    filename = re.sub(r"[^a-zA-Z0-9_.\-]", "_", img_url.split("/")[-1])
    filepath = os.path.join(save_dir, filename)
    if os.path.exists(filepath):
        return filepath
    try:
        r = requests.get(img_url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        with open(filepath, "wb") as f:
            f.write(r.content)
        return filepath
    except requests.RequestException as e:
        print(f"  [WARN] 이미지 다운로드 실패: {img_url} — {e}")
        return None

# ── 목록 파싱 ─────────────────────────────────────────────────────────────────
def parse_article_urls(soup):
    urls, seen = [], set()
    for a in soup.find_all("a"):
        attrs = a.attrs or {}
        href = attrs.get("href", "")
        if href and re.search(r"/_ln/0102_\d+", href):
            full = urljoin(BASE_URL, href)
            canonical = re.sub(r"_\d{3}$", "", full)
            if canonical not in seen:
                seen.add(canonical)
                urls.append(canonical)
    return urls

# ── 본문 추출 ─────────────────────────────────────────────────────────────────
def extract_body(soup):
    selectors = [
        '#articleWrap', '#articleBody', '#news_con', '.article-body', 
        '.article_view', '.news_bm', '.view-content', 'article'
    ]
    
    container = None
    for sel in selectors:
        element = soup.select_one(sel)
        if element and len(element.get_text(strip=True)) > 50:
            container = element
            break
            
    if not container:
        divs = soup.find_all(['div', 'article'])
        if divs:
            container = max(divs, key=lambda d: len(d.get_text(strip=True)))
        else:
            return "", []

    for tag in container.find_all(['script', 'style', 'iframe', 'figure', 'button']):
        tag.decompose()
        
    for tag in container.find_all('div'):
        attrs = tag.attrs or {}
        cls = attrs.get('class', [])
        if isinstance(cls, str):
            cls = [cls]
        elif not cls:
            cls = []
            
        cls_str = " ".join(cls).lower()
        # 주의: 텍스트 날림 방지를 위해 copy, photo 등의 키워드는 삭제 제외 목록에서 뺐습니다.
        if any(noise in cls_str for noise in ['ad', 'sns', 'share', 'reply', 'footer', 'related']):
            tag.decompose()

    for br in container.find_all("br"):
        br.replace_with("\n")
    for p in container.find_all("p"):
        p.insert_before("\n")
        p.insert_after("\n")

    raw_text = container.get_text(separator="\n", strip=True)
    
    lines = []
    speeches = []
    
    for line in raw_text.split('\n'):
        line = line.strip()
        if not line:
            continue

        # 노이즈 문장 무시 (길이가 너무 짧거나 특정 불필요 패턴)
        if _NOISE.search(line) or len(line) < 3:
            continue

        # 저작권 관련 문구는 수집 종료(break)가 아닌 건너뛰기(continue)로 처리하여 라디오 기사 단절 방지
        if "저작권자(c) YTN" in line or "AI 데이터 활용 금지" in line or "무단 전재" in line or "재배포 금지" in line:
            continue

        # 서명이나 이메일이 하단에 나오면 수집을 종료하되, 기사 상단에 있는 경우를 대비해 수집된 줄 수가 적을 땐 건너뜀
        if _BYLINE.search(line) or line.endswith("@ytn.co.kr"):
            if len(lines) > 5:
                break
            else:
                continue

        lines.append(line)

        # 발화자 추출 개선: [앵커], [기자], [조태현], ◇ 앵커:, ◆ 진행: 등 라디오 포맷 완벽 대응
        role_match = re.match(r"^(\[.*?\]|[◇◆■]\s*[^:\s]+)", line)
        if role_match:
            role = role_match.group(1).strip()
        else:
            role = "본문"
            
        speeches.append({"role": role, "text": line})

    body_text = "\n\n".join(lines).strip()
    return body_text, speeches

# ── 이미지 수집 ───────────────────────────────────────────────────────────────
def extract_images(soup, og_image):
    img_urls = []
    if og_image:
        img_urls.append(og_image)
    for img in soup.find_all("img"):
        attrs = img.attrs or {}
        src = attrs.get("src", "")
        if not src:
            continue
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            src = urljoin(BASE_URL, src)
        if "image.ytn.co.kr" in src and src not in img_urls:
            img_urls.append(src)
    return img_urls

# ── 기사 파싱 ─────────────────────────────────────────────────────────────────
def parse_article(url):
    soup = get_soup(url)
    if soup is None:
        return None

    meta = {}
    for tag in soup.find_all("meta"):
        attrs = tag.attrs or {}
        key = attrs.get("property") or attrs.get("name") or ""
        val = attrs.get("content", "").strip()
        if key and val:
            meta[key] = val

    og_image     = meta.get("og:image", "")
    og_title     = meta.get("og:title", "")
    og_desc      = meta.get("og:description", "")
    author       = meta.get("twitter:creator") or meta.get("author", "")
    published_at = meta.get("article:published_time", "")
    modified_at  = meta.get("article:modified_time", "")
    category     = meta.get("article:section2") or meta.get("article:section", "")
    keywords     = meta.get("news_keywords") or meta.get("keywords", "")

    title = og_title
    if not title:
        t = soup.find("title")
        if t:
            title = re.sub(r"\s*\|\s*YTN$", "", t.get_text(strip=True))
            title = re.sub(r"^\[.*?\]\s*", "", title).strip()

    body_text, speeches = extract_body(soup)
    if not body_text:
        body_text = og_desc

    img_urls = extract_images(soup, og_image)

    m = re.search(r"_ln/\d+_(\d+)", url)
    article_id = m.group(1) if m else ""

    return {
        "id":           article_id,
        "title":        title,
        "url":          url,
        "category":     category or "경제",
        "author":       author,
        "published_at": published_at,
        "modified_at":  modified_at,
        "keywords":     keywords,
        "description":  og_desc,
        "body":         body_text,
        "speeches":     speeches,
        "images": {
            "urls":        img_urls,
            "local_paths": [],
        },
        "metadata": {
            k: v for k, v in meta.items()
            if k.startswith(("og:", "article:", "twitter:"))
        },
        "crawled_at": datetime.now().isoformat(),
    }

# ── 메인 ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("YTN 경제 뉴스 크롤러 v2.3 (라디오 대담 텍스트 단절 패치)")
    print(f"  대상: {LIST_URL}")
    print(f"  최대: {MAX_ARTICLES or '무제한'}개")
    print("=" * 60)

    print("\n[1/3] 목록 수집...")
    list_soup = get_soup(LIST_URL)
    if not list_soup:
        return
    article_urls = parse_article_urls(list_soup)
    if MAX_ARTICLES:
        article_urls = article_urls[:MAX_ARTICLES]
    print(f"  → {len(article_urls)}개 URL")

    print("\n[2/3] 기사 크롤링...")
    articles = []
    for i, url in enumerate(article_urls, 1):
        print(f"  [{i:02d}/{len(article_urls)}] {url}")
        article = parse_article(url)
        if article:
            blen = len(article["body"])
            print(f"        → 본문 {blen}자 / 발화 {len(article['speeches'])}블록 / 이미지 {len(article['images']['urls'])}장")
            articles.append(article)
        time.sleep(REQUEST_DELAY)

    print("\n[3/3] 이미지 다운로드...")
    for article in articles:
        for img_url in article["images"]["urls"]:
            local = download_image(img_url, IMAGE_DIR)
            if local:
                article["images"]["local_paths"].append(local)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    has_body   = sum(1 for a in articles if len(a["body"]) > 50)
    total_imgs = sum(len(a["images"]["local_paths"]) for a in articles)

    print("\n" + "=" * 60)
    print(f"완료!")
    print(f"  기사 수       : {len(articles)}개")
    print(f"  본문 추출 성공: {has_body}개  (실패: {len(articles)-has_body}개)")
    print(f"  이미지        : {total_imgs}장  →  {IMAGE_DIR}/")
    print(f"  결과 JSON     : {OUTPUT_JSON}")
    print("=" * 60)

if __name__ == "__main__":
    main()