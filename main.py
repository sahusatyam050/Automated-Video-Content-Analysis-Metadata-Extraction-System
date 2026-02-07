# import os
# import uuid
# import asyncio
# import uvicorn
# import traceback
# import json
# import io
# import shutil 
# import time
# from datetime import datetime, timedelta 

# # --- LOAD DOTENV FIRST ---
# from pathlib import Path
# from dotenv import load_dotenv

# env_path = Path(__file__).parent / ".env"
# load_dotenv(dotenv_path=env_path) 

# # ============================================================
# # NETWORK CONFIGURATION
# # ============================================================
# REMOTE_AI_IP = "10.94.157.37" 
# DB_STORAGE_IP = "10.94.157.201"

# REMOTE_SERVER_URL = f"http://{REMOTE_AI_IP}:8002"
# WHISPER_API_URL = f"http://{REMOTE_AI_IP}:8001/transcribe"
# SUMMARY_API_URL = f"{REMOTE_SERVER_URL}/summary"
# SENTIMENT_API_URL = f"{REMOTE_SERVER_URL}/sentiment"

# print("============================================================")
# print(f"DEBUG: Connecting to AI Services at: {REMOTE_AI_IP}")
# print(f"DEBUG: Connecting to DB/Storage at: {DB_STORAGE_IP}")
# print("✅ Mode: Memory Streaming")
# print("============================================================")

# os.environ['WDM_SSL_VERIFY'] = '0'
# os.environ['WDM_LOG_LEVEL'] = '0'

# from fastapi import FastAPI, BackgroundTasks, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import JSONResponse
# from pydantic import BaseModel
# from pymongo import MongoClient
# from bson import ObjectId
# from minio import Minio 
# from yt_dlp import YoutubeDL
# import requests

# from scrapers.youtube import YouTubeScraperEngine
# from scrapers.instagram import InstagramScraperEngine
# from scrapers.twitter import TwitterScraperEngine
# from scrapers.reddit import RedditScraperEngine

# # ============================================================
# # UNIFIED SCHEMA TRANSFORMER
# # ============================================================
# class UnifiedSchema:
#     @staticmethod
#     def transform(platform: str, raw_data: dict, analysis_data: dict = None) -> dict:
#         platform = platform.lower()
#         transformers = {
#             'youtube': UnifiedSchema._transform_youtube,
#             'twitter': UnifiedSchema._transform_twitter,
#             'x': UnifiedSchema._transform_twitter,
#             'instagram': UnifiedSchema._transform_instagram,
#             'reddit': UnifiedSchema._transform_reddit
#         }
        
#         transformer = transformers.get(platform, UnifiedSchema._transform_generic)
#         unified_data = transformer(raw_data)

#         if analysis_data:
#             unified_data["transcription"] = analysis_data.get("transcript")
#             unified_data["summary"] = analysis_data.get("summary")
#             unified_data["analysis_results"] = {
#                 "sentiment": analysis_data.get("sentiment")
#             }
            
#         return unified_data

#     @staticmethod
#     def _transform_youtube(data: dict) -> dict:
#         v_info = data.get("video_info", {})
#         c_info = data.get("channel_info", {})
#         return {
#             "platform": "youtube",
#             "scraped_at": datetime.utcnow().isoformat(),
#             "video_info": {
#                 "title": v_info.get("title"),
#                 "description": v_info.get("description"),
#                 "likes": v_info.get("likes"),
#                 "views": v_info.get("views"),
#                 "duration": v_info.get("duration"),
#                 "upload_date": v_info.get("upload_date"),
#                 "comment_count": v_info.get("comment_count"),
#                 "video_id": v_info.get("video_id")
#             },
#             "channel_info": {
#                 "name": c_info.get("name"),
#                 "handle": c_info.get("handle"),
#                 "subscriber_count": c_info.get("subscriber_count"),
#                 "video_count": c_info.get("video_count"),
#                 "description": c_info.get("description")
#             },
#             "comments": data.get("comments", {"total": 0, "data": []}),
#             "minio_video_path": data.get("minio_video_path")
#         }

#     @staticmethod
#     def _transform_twitter(data: dict) -> dict:
#         v_info = data.get("video_info", {}) or data
#         return {
#             "platform": "twitter",
#             "scraped_at": datetime.utcnow().isoformat(),
#             "video_info": {
#                 "title": v_info.get("title") or (data.get("tweet_text", "")[:50]),
#                 "description": data.get("tweet_text"),
#                 "video_id": v_info.get("video_id") or data.get("tweet_id")
#             },
#             "channel_info": {"handle": data.get("profile_info", {}).get("username")},
#             "comments": data.get("comments", {"data": []}),
#             "minio_video_path": data.get("minio_video_path")
#         }

#     @staticmethod
#     def _transform_instagram(data: dict) -> dict:
#         v_info = data.get("video_info", {}) or data.get("post_metrics", {})
#         return {
#             "platform": "instagram",
#             "scraped_at": datetime.utcnow().isoformat(),
#             "video_info": {"video_id": v_info.get("video_id") or v_info.get("shortcode")},
#             "channel_info": {"handle": data.get("creators_metrics", {}).get("username")},
#             "comments": data.get("comments", {"data": []}),
#             "minio_video_path": data.get("minio_video_path")
#         }

#     @staticmethod
#     def _transform_reddit(data: dict) -> dict:
#         v_info = data.get("video_info", {}) or data.get("post_details", {})
#         return {
#             "platform": "reddit",
#             "scraped_at": datetime.utcnow().isoformat(),
#             "video_info": {"video_id": v_info.get("video_id") or v_info.get("post_id")},
#             "channel_info": {"handle": data.get("creators_details", {}).get("username")},
#             "comments": data.get("comments", {"data": []}),
#             "minio_video_path": data.get("minio_video_path")
#         }

#     @staticmethod
#     def _transform_generic(data: dict) -> dict:
#         return {"platform": "unknown", "raw_data": data, "scraped_at": datetime.utcnow().isoformat()}

# # ============================================================
# # API CORE SETUP
# # ============================================================

# app = FastAPI(title="Social Media Scraper API")

# youtube_scraper = YouTubeScraperEngine()
# instagram_scraper = InstagramScraperEngine()
# twitter_scraper = TwitterScraperEngine()
# reddit_scraper = RedditScraperEngine()

# try:
#     client = MongoClient(f"mongodb://{DB_STORAGE_IP}:27017/", serverSelectionTimeoutMS=5000)
#     db = client["social_media_analyzer"]
#     collection = db["scraped_data"]
#     print("✅ MongoDB Connected")
# except Exception as e:
#     print(f"⚠️ MongoDB Connection Warning: {e}")

# try:
#     minio_client = Minio(
#         f"{DB_STORAGE_IP}:9000",
#         access_key="minioadmin",
#         secret_key="minioadmin",
#         secure=False
#     )
#     bucket_name = "scraped-results"
#     if not minio_client.bucket_exists(bucket_name):
#         minio_client.make_bucket(bucket_name)
#     print("✅ MinIO Connected")
# except Exception as e:
#     print(f"⚠️ MinIO Connection Warning: {e}")

# app.add_middleware(
#     CORSMiddleware, 
#     allow_origins=["*"], 
#     allow_credentials=True,
#     allow_methods=["*"], 
#     allow_headers=["*"]
# )

# class ScrapeRequest(BaseModel):
#     url: str
#     platform: str 

# task_memory = {}

# # --- HELPER FUNCTIONS ---

# def serialize(obj):
#     if isinstance(obj, ObjectId): return str(obj)
#     if isinstance(obj, datetime): return obj.isoformat()
#     if isinstance(obj, dict): return {k: serialize(v) for k, v in obj.items()}
#     if isinstance(obj, list): return [serialize(item) for item in obj]
#     return obj

# def extract_video_id(url: str, platform: str) -> str:
#     try:
#         if platform == "youtube":
#             if "youtu.be/" in url: return url.split("youtu.be/")[1].split("?")[0]
#             elif "v=" in url: return url.split("v=")[1].split("&")[0]
#         return url
#     except:
#         return url

# def check_existing_video(url: str, platform: str):
#     video_id = extract_video_id(url, platform)
#     return collection.find_one({"platform": platform, "video_info.video_id": video_id})

# # --- AI API CALLS ---

# def call_ai_service(url, payload, task_id, service_name):
#     try:
#         # Increased initial connect timeout to 10s and read timeout to 600s
#         r = requests.post(url, json=payload, timeout=(10, 600))
#         if r.status_code == 200:
#             return r.json()
#     except Exception as e:
#         print(f"❌ {service_name} Error [Task {task_id}]: {e}")
#     return None

# def call_transcribe_from_memory(video_buffer: io.BytesIO, task_id: str):
#     try:
#         video_buffer.seek(0)
#         files = {'file': (f"video_{task_id}.mp4", video_buffer, 'video/mp4')}
#         # timeout=(connect_timeout, read_timeout)
#         r = requests.post(WHISPER_API_URL, files=files, timeout=(15, 900))
#         if r.status_code == 200:
#             print(f"✅ [TASK {task_id}] Transcription completed")
#             return r.json()
#     except Exception as e:
#         print(f"❌ Transcribe Connection Error: {e}")
#     return None

# def download_video_to_memory(url: str, task_id: str):
#     ydl_opts = {'format': 'best[ext=mp4]/best', 'quiet': True}
#     try:
#         with YoutubeDL(ydl_opts) as ydl:
#             info = ydl.extract_info(url, download=False)
#             stream_url = info.get('url')
#             response = requests.get(stream_url, stream=True, timeout=30)
#             buffer = io.BytesIO()
#             for chunk in response.iter_content(chunk_size=1024*1024):
#                 if chunk: buffer.write(chunk)
#             buffer.seek(0)
#             return buffer
#     except Exception as e:
#         print(f"❌ Download Error: {e}")
#         return None

# # --- CORE LOGIC FLOW ---

# async def run_analysis(task_id: str, url: str, platform: str):
#     try:
#         task_memory[task_id] = {"status": "running", "platform": platform}
#         loop = asyncio.get_event_loop()
        

#         video_buffer = await loop.run_in_executor(None, download_video_to_memory, url, task_id)
#         transcript_text = None
#         if video_buffer:
#             res = await loop.run_in_executor(None, call_transcribe_from_memory, video_buffer, task_id)
#             transcript_text = res.get("transcript") if res else None

#         # 1. Scraper
#         s_engine = {"youtube": youtube_scraper, "instagram": instagram_scraper, 
#                     "twitter": twitter_scraper, "x": twitter_scraper}.get(platform, reddit_scraper)
        
#         scraper_data = await loop.run_in_executor(None, s_engine.scrape_real_data, url, task_id)
#         if not scraper_data: return

#         # 2. Download & Transcribe
#         # video_buffer = await loop.run_in_executor(None, download_video_to_memory, url, task_id)
#         # transcript_text = None
#         # if video_buffer:
#         #     res = await loop.run_in_executor(None, call_transcribe_from_memory, video_buffer, task_id)
#         #     transcript_text = res.get("transcript") if res else None

#         # 3. MinIO Upload
#         minio_path = None
#         if video_buffer:
#             minio_path = f"{task_id}/{task_id}.mp4"
#             video_buffer.seek(0)
#             minio_client.put_object(bucket_name, minio_path, video_buffer, len(video_buffer.getvalue()), "video/mp4")

#         # 4. LLM Analysis (Summary & Sentiment)
#         summary = None
#         sentiment = None
#         if transcript_text:
#             summary_res = await loop.run_in_executor(None, call_ai_service, SUMMARY_API_URL, {"text": transcript_text}, task_id, "Summary")
#             summary = summary_res.get("summary") if summary_res else None
            
#             sentiment_res = await loop.run_in_executor(None, call_ai_service, SENTIMENT_API_URL, {"text": transcript_text}, task_id, "Sentiment")
#             sentiment = sentiment_res.get("sentiment") if sentiment_res else None

#         # 5. Final Processing & Save
#         scraper_data["minio_video_path"] = minio_path
#         analysis_payload = {
#             "transcript": transcript_text,
#             "summary": summary,
#             "sentiment": sentiment
#         }
        
#         final_data = UnifiedSchema.transform(platform, scraper_data, analysis_payload)
#         final_data["task_id"] = task_id
#         final_data["status"] = "completed"
        
#         collection.insert_one(final_data)
#         task_memory[task_id] = final_data
#         print(f"🏁 [TASK {task_id}] COMPLETED")
            
#     except Exception as e:
#         print(f"❌ [TASK {task_id}] FAILED: {e}")
#         traceback.print_exc()
#         task_memory[task_id] = {"status": "failed", "error": str(e)}

# # --- ENDPOINTS ---

# @app.get("/video-url/{task_id}")
# async def get_video_url(task_id: str):
#     """Generates a direct temporary link to the video file stored in MinIO."""
#     try:
#         res = collection.find_one({"task_id": task_id})
#         if not res or not res.get("minio_video_path"):
#             raise HTTPException(status_code=404, detail="Video not found in database")
        
#         # Use the DB_STORAGE_IP for the URL so the frontend can find it
#         url = minio_client.presigned_get_object(
#             bucket_name, 
#             res["minio_video_path"], 
#             expires=timedelta(hours=1) 
#         )
#         return {"url": url}
#     except Exception as e:
#         return JSONResponse(status_code=500, content={"error": str(e)})

# @app.post("/scrape")
# async def start_scraping(req: ScrapeRequest, background_tasks: BackgroundTasks):
#     existing = check_existing_video(req.url, req.platform.lower())
#     if existing: 
#         return JSONResponse(content=serialize(existing))
    
#     task_id = str(uuid.uuid4())
#     background_tasks.add_task(run_analysis, task_id, req.url, req.platform.lower())
#     return {"task_id": task_id, "status": "started"}

# @app.get("/results/{task_id}")
# async def get_results(task_id: str):
#     res = task_memory.get(task_id) or collection.find_one({"task_id": task_id})
#     if not res: return {"status": "pending"}
#     return JSONResponse(content=serialize(res))

# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)


import os
import uuid
import asyncio
import uvicorn
import io
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime, timedelta 
from pathlib import Path
from dotenv import load_dotenv
from minio import Minio 
from yt_dlp import YoutubeDL
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient

# --- INITIALIZE LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("SocialScraper")

# --- LOAD ENVIRONMENT ---
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path) 

# ============================================================
# CONFIGURATION & CONNECTIONS
# ============================================================
REMOTE_AI_IP = "127.0.0.1" 
DB_STORAGE_IP = "10.94.157.201"

REMOTE_SERVER_URL = f"http://{REMOTE_AI_IP}:8002"
WHISPER_API_URL = f"http://{REMOTE_AI_IP}:8001/transcribe"
SUMMARY_API_URL = f"{REMOTE_SERVER_URL}/summary"
SENTIMENT_API_URL = f"{REMOTE_SERVER_URL}/sentiment"

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pymongo import MongoClient
from bson import ObjectId
from minio import Minio 
from yt_dlp import YoutubeDL

# Import your scraper engines
from scrapers.youtube import YouTubeScraperEngine
from scrapers.instagram import InstagramScraperEngine
from scrapers.twitter import TwitterScraperEngine
from scrapers.reddit import RedditScraperEngine

# [UnifiedSchema class remains unchanged from your snippet]
class UnifiedSchema:
    @staticmethod
    def transform(platform: str, raw_data: dict, analysis_data: dict = None) -> dict:
        platform = platform.lower()
        transformers = {
            'youtube': UnifiedSchema._transform_youtube,
            # 'twitter': UnifiedSchema._transform_twitter,
            # 'x': UnifiedSchema._transform_twitter,
            # 'instagram': UnifiedSchema._transform_instagram,
            # 'reddit': UnifiedSchema._transform_reddit
        }
        transformer = transformers.get(platform, UnifiedSchema._transform_generic)
        unified_data = transformer(raw_data)
        if analysis_data:
            unified_data["transcription"] = analysis_data.get("transcript")
            unified_data["summary"] = analysis_data.get("summary")
            unified_data["analysis_results"] = {"sentiment": analysis_data.get("sentiment")}
        return unified_data

    @staticmethod
    def _transform_youtube(data: dict) -> dict:
        v_info = data.get("video_info", {})
        c_info = data.get("channel_info", {})
        return {
            "platform": "youtube",
            "scraped_at": datetime.utcnow().isoformat(),
            "video_info": v_info,
            "channel_info": c_info,
            "comments": data.get("comments", {"total": 0, "data": []}),
            "minio_video_path": data.get("minio_video_path")
        }
    @staticmethod
    def _transform_generic(data: dict) -> dict:
        return {"platform": "unknown", "raw_data": data, "scraped_at": datetime.utcnow().isoformat()}

# ============================================================
# INITIALIZATION
# ============================================================
app = FastAPI(title="Social Media Scraper API")

youtube_scraper = YouTubeScraperEngine()
instagram_scraper = InstagramScraperEngine()
twitter_scraper = TwitterScraperEngine()
reddit_scraper = RedditScraperEngine()

try:
    client = MongoClient(f"mongodb://{DB_STORAGE_IP}:27017/", serverSelectionTimeoutMS=5000)
    db = client["social_media_analyzer"]
    collection = db["scraped_data"]
    logger.info("✅ MongoDB Connected")
except Exception as e:
    logger.error(f"⚠️ MongoDB Warning: {e}")

try:
    minio_client = Minio(f"{DB_STORAGE_IP}:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)
    bucket_name = "scraped-results"
    if not minio_client.bucket_exists(bucket_name):
        minio_client.make_bucket(bucket_name)
    logger.info("✅ MinIO Connected")
except Exception as e:
    logger.error(f"⚠️ MinIO Warning: {e}")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ScrapeRequest(BaseModel):
    url: str
    platform: str 

task_memory = {}

# ============================================================
# WORKERS
# ============================================================
def download_video_to_memory(url: str, task_id: str):
    logger.info(f"[{task_id}] STEP 1: Downloading video...")
    ydl_opts = {'format': 'best[ext=mp4]/best', 'quiet': True}
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            res = requests.get(info.get('url'), stream=True, timeout=60)
            buffer = io.BytesIO()
            for chunk in res.iter_content(chunk_size=1024*1024):
                if chunk: buffer.write(chunk)
            buffer.seek(0)
            return buffer
    except Exception as e:
        logger.error(f"[{task_id}] Download Error: {e}")
        return None

def call_transcribe_from_memory(video_buffer: io.BytesIO, task_id: str):
    logger.info(f"[{task_id}] STEP 2: Transcribing on CPU (This may take several minutes)...")
    
    # Configure retries for unstable CPU processing
    session = requests.Session()
    retries = Retry(total=2, backoff_factor=1, status_forcelist=[502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))

    try:
        video_buffer.seek(0)
        files = {'file': (f"video_{task_id}.mp4", video_buffer, 'video/mp4')}
        
        # INCREASED TIMEOUT: (Connect timeout, Read timeout)
        # We give the CPU up to 20 minutes (1200s) to finish a long video
        response = session.post(
            WHISPER_API_URL, 
            files=files, 
            timeout=(15, 1200) 
        )
        
        if response.status_code == 200:
            logger.info(f"[{task_id}] Transcription Successful.")
            return response.json()
        else:
            logger.error(f"[{task_id}] Whisper Server returned error {response.status_code}: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error(f"[{task_id}] CRITICAL: Whisper timed out. CPU is too slow or video is too long.")
    except Exception as e:
        logger.error(f"[{task_id}] Transcription Exception: {e}")
    return None

# ============================================================
# CORE SEQUENTIAL FLOW
# ============================================================
async def run_analysis(task_id: str, url: str, platform: str):
    try:
        task_memory[task_id] = {"status": "running", "platform": platform}
        loop = asyncio.get_event_loop()
        
        # 1. DOWNLOAD
        video_buffer = await loop.run_in_executor(None, download_video_to_memory, url, task_id)
        if not video_buffer:
            raise Exception("Download failed.")

        # 2. TRANSCRIBE (WAIT HERE)
        trans_res = await loop.run_in_executor(None, call_transcribe_from_memory, video_buffer, task_id)
        
        # Flexibility check: Whisper sometimes returns 'text' instead of 'transcript'
        transcript_text = None
        if trans_res:
            transcript_text = trans_res.get("transcription") or trans_res.get("text")

        if not transcript_text:
            logger.error(f"[{task_id}] Transcription succeeded but returned no text content.")
            raise Exception("Step 2 Failed: Transcription result was empty.")
        
        logger.info(f"[{task_id}] ✅ Transcription Verified. Proceeding to Storage.")

        # 3. UPLOAD TO MINIO (Only after transcription success)
        logger.info(f"[{task_id}] STEP 3: Uploading to MinIO...")
        minio_path = f"{task_id}/{task_id}.mp4"
        video_buffer.seek(0)
        minio_client.put_object(bucket_name, minio_path, video_buffer, len(video_buffer.getvalue()), "video/mp4")

        # 4. SCRAPE DATA (Only after upload)
        logger.info(f"[{task_id}] STEP 4: Starting Scraper for {platform}")
        s_engine = {"youtube": youtube_scraper, "instagram": instagram_scraper, 
                    "twitter": twitter_scraper, "x": twitter_scraper}.get(platform, reddit_scraper)
        
        scraper_data = await loop.run_in_executor(None, s_engine.scrape_real_data, url, task_id)
        if not scraper_data:
            raise Exception("Scraping engine returned no data.")

        # 5. LLM ANALYSIS
        logger.info(f"[{task_id}] STEP 5: Running LLM Analysis...")
        summary_res = requests.post(SUMMARY_API_URL, json={"text": transcript_text}).json()
        sentiment_res = requests.post(SENTIMENT_API_URL, json={"text": transcript_text}).json()

        # 6. FINAL CONSOLIDATION & SAVE
        logger.info(f"[{task_id}] STEP 6: Saving to MongoDB")
        scraper_data["minio_video_path"] = minio_path
        analysis_payload = {
            "transcript": transcript_text,
            "summary": summary_res.get("summary"),
            "sentiment": sentiment_res.get("sentiment")
        }
        
        final_data = UnifiedSchema.transform(platform, scraper_data, analysis_payload)
        final_data.update({"task_id": task_id, "status": "completed"})
        
        collection.insert_one(final_data)
        task_memory[task_id] = final_data
        logger.info(f"🏁 [TASK {task_id}] COMPLETED SUCCESSFULLY")
            
    except Exception as e:
        logger.error(f"❌ [TASK {task_id}] FAILED: {str(e)}")
        task_memory[task_id] = {"status": "failed", "error": str(e)}

# ============================================================
# API ENDPOINTS
# ============================================================
@app.post("/scrape")
async def start_scraping(req: ScrapeRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    background_tasks.add_task(run_analysis, task_id, req.url, req.platform.lower())
    return {"task_id": task_id, "status": "started"}

@app.get("/results/{task_id}")
async def get_results(task_id: str):
    res = task_memory.get(task_id) or collection.find_one({"task_id": task_id})
    if not res: return {"status": "pending"}
    # Use a helper to make MongoDB object JSON serializable
    if "_id" in res: res["_id"] = str(res["_id"])
    return res

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)