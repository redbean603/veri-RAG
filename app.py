Python 3.12.2 (tags/v3.12.2:6abddd9, Feb  6 2024, 21:26:36) [MSC v.1937 64 bit (AMD64)] on win32
Type "help", "copyright", "credits" or "license()" for more information.
import os
import json
import time
import requests
import boto3
import traceback
from bs4 import BeautifulSoup
from datetime import datetime
from PIL import Image
from sentence_transformers import SentenceTransformer
import google.generativeai as genai

# ==========================================
# 1. Environment Variables Configuration
# ==========================================
# In a production environment, these should be injected via AWS Lambda Environment Variables.
ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY", "YOUR_AWS_ACCESS_KEY")
SECRET_KEY = os.environ.get("AWS_SECRET_KEY", "YOUR_AWS_SECRET_KEY")
SESSION_TOKEN = os.environ.get("AWS_SESSION_TOKEN", "YOUR_AWS_SESSION_TOKEN")
BUCKET_NAME = os.environ.get("BUCKET_NAME", "project-news-embedding-2026")
GENAI_API_KEY = os.environ.get("GENAI_API_KEY", "YOUR_GEMINI_API_KEY")

genai.configure(api_key=GENAI_API_KEY)

# AWS Lambda only allows write access to the /tmp directory (up to 512MB).
TEMP_DIR = "/tmp"

# ==========================================
# 2. Global Initialization (Clients & Models)
# ==========================================
# Initialized outside the handler to leverage Lambda execution context reuse (Warm Start).
s3 = boto3.client(
    service_name='s3',
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    aws_session_token=SESSION_TOKEN,
    region_name='us-east-1'
)

gemini_model = genai.GenerativeModel('gemini-2.5-flash')
clip_img_model = SentenceTransformer('clip-ViT-B-32')
clip_text_model = SentenceTransformer('clip-ViT-B-32-multilingual-v1')

SOURCE_METADATA = {
    "연합뉴스": {"id": "src_yonhap",   "name": "Yonhap News"},
    "한국경제": {"id": "src_hankyung", "name": "Korea Economic Daily"},
    "매일경제": {"id": "src_maeil",    "name": "Maeil Business Newspaper"},
    "네이버뉴스": {"id": "src_naver",    "name": "Naver News"}
}

# ==========================================
# 3. Core Pipeline Execution
# ==========================================
def run_end_to_end_pipeline(url, news_id):
    headers = {'User-Agent': 'Mozilla/5.0'}
    local_txt_path = os.path.join(TEMP_DIR, f"{news_id}.txt")
    local_img_path = os.path.join(TEMP_DIR, f"{news_id}.jpg")
    local_json_path = os.path.join(TEMP_DIR, f"{news_id}_result.json")
    
    try:
        # [Step 1] Web Scraping
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title_element = soup.select_one('#title_area')
        body_element = soup.select_one('#dic_area')
        if not title_element or not body_element:
            return False 
            
        title = title_element.text.strip()
        raw_text = body_element.text.strip()
        date_el = soup.select_one('.media_end_head_info_datestamp_time')
        published_at = date_el.get('data-date-time') if date_el else datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        source_el = soup.select_one('.media_end_head_top_logo img')
        source_name = source_el.get('title') or source_el.get('alt') or "네이버뉴스"
        source_id = SOURCE_METADATA.get(source_name, SOURCE_METADATA["네이버뉴스"])["id"]
        
        with open(local_txt_path, "w", encoding="utf-8") as f:
            f.write(f"Title: {title}\n\nBody:\n{raw_text}")
            
        img_element = soup.select_one('#img1')
        has_image = False
        if img_element and img_element.get('data-src'):
            img_data = requests.get(img_element.get('data-src'), headers=headers).content
            with open(local_img_path, "wb") as f:
                f.write(img_data)
            has_image = True
            
        # [Step 2] Upload RAW Assets to S3
        s3_text_key = f"raw-data/{news_id}.txt"
        s3.upload_file(local_txt_path, BUCKET_NAME, s3_text_key)
        
        s3_image_key = None
        if has_image:
            s3_image_key = f"raw-data/{news_id}.jpg"
            s3.upload_file(local_img_path, BUCKET_NAME, s3_image_key)
            
        # [Step 3] LLM Processing (DePlot & Summarization)
        extracted_markdown = "No image found."
        if has_image:
            img_obj = Image.open(local_img_path).convert('RGB')
            prompt_image = "If this image contains a chart or table, extract the numerical data into a Markdown table and summarize the core insights."
            extracted_markdown = gemini_model.generate_content([prompt_image, img_obj]).text
        
        prompt_text = f"Summarize the following news article in under 50 characters, focusing on visual or core descriptive keywords suitable for a CLIP image search model:\n{raw_text}"
        clip_ready_text = gemini_model.generate_content(prompt_text).text.strip()
        
        prompt_summary = f"Summarize the core content of the following news article in 3 sentences or less:\n{raw_text}"
        summary_content = gemini_model.generate_content(prompt_summary).text.strip()

        # [Step 4] Generate CLIP Embeddings
        text_vector = clip_text_model.encode(clip_ready_text).tolist()
        image_vector = clip_img_model.encode(img_obj).tolist() if has_image else []

        # [Step 5] Assemble Final JSON and Upload
        final_data = {
            "news_id": news_id,
            "embedding_id": f"emb_{news_id}",
            "source": source_id,
            "title": title,
            "content": summary_content,
            "published_at": published_at,
            "url": url,
            "source_image_s3": f"s3://{BUCKET_NAME}/{s3_image_key}" if has_image else None,
            "source_text_s3": f"s3://{BUCKET_NAME}/{s3_text_key}",
            "extracted_markdown": extracted_markdown,
            "processed_text_for_clip": clip_ready_text,
            "image_vector": image_vector,
            "text_vector": text_vector
        }
        
        with open(local_json_path, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=4)
            
        s3_upload_key = f"processed-data/{news_id}_result.json"
        s3.upload_file(local_json_path, BUCKET_NAME, s3_upload_key)
        return True
        
    except Exception as e:
        print(f"Error processing {news_id}: {e}")
        return False
        
    finally:
        # Crucial: Clean up /tmp to prevent out-of-storage errors on warm starts
        for filepath in [local_img_path, local_txt_path, local_json_path]:
            if os.path.exists(filepath):
                os.remove(filepath)

# ==========================================
# 4. Lambda Handler (Entry Point)
# ==========================================
def lambda_handler(event, context):
    """
    AWS Lambda entry point. 
    Accepts 'max_articles' dynamically from the event payload.
    """
...     max_articles = event.get('max_articles', 3)
...     date_prefix = datetime.now().strftime("%Y%m%d")
...     
...     url = "https://news.naver.com/section/101"
...     headers = {'User-Agent': 'Mozilla/5.0'}
...     
...     try:
...         response = requests.get(url, headers=headers)
...         soup = BeautifulSoup(response.text, 'html.parser')
...         
...         links = set()
...         for a_tag in soup.select('.sa_text_title'):
...             href = a_tag.get('href')
...             if href and 'article' in href:
...                 links.add(href)
...                 
...         links = list(links)
...         success_count = 0
...         
...         for link in links:
...             if success_count >= max_articles:
...                 break
...                 
...             news_id = f"news_{date_prefix}_{success_count+1:04d}"
...             if run_end_to_end_pipeline(link, news_id):
...                 success_count += 1
...                 time.sleep(1.0)
...                 
...         return {
...             'statusCode': 200,
...             'body': json.dumps(f"Pipeline finished! Successfully processed {success_count} articles.")
...         }
...         
...     except Exception as e:
...         return {
...             'statusCode': 500,
...             'body': json.dumps(f"Lambda execution failed: {traceback.format_exc()}")
