from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import instaloader
from pydantic import BaseModel
from contextlib import asynccontextmanager

from dotenv import load_dotenv
import os

# Import MongoDB functions
from database import init_mongodb, close_mongodb, get_cached_post, save_post

# Import MinIO functions
from minio_client import init_minio, store_instagram_media, store_profile_picture

load_dotenv()


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting application...")
    await init_mongodb()
    init_minio()  # Initialize MinIO
    yield
    # Shutdown
    print("👋 Shutting down...")
    await close_mongodb()


app = FastAPI(lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

L = instaloader.Instaloader()

# Instagram Login with session management
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "").strip()
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "").strip()
SESSION_FILE = "instagram_session"

if INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD:
    try:
        # Try to load existing session first
        try:
            L.load_session_from_file(INSTAGRAM_USERNAME, SESSION_FILE)
            print(f"✅ Loaded existing session for @{INSTAGRAM_USERNAME}")
        except FileNotFoundError:
            # No session file, perform login
            print(f"🔐 Logging in as @{INSTAGRAM_USERNAME}...")
            L.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            # Save session for future use
            L.save_session_to_file(SESSION_FILE)
            print(f"✅ Login successful! Session saved.")
    except Exception as e:
        print(f"⚠️ Login failed: {e}")
        print("ℹ️ Continuing in anonymous mode - scraping public posts only")
else:
    print("ℹ️ No Instagram credentials found - running in anonymous mode")
    print("💡 Add INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD to .env for higher rate limits")



class URLRequest(BaseModel):
    url: str


@app.post("/get-post-data")
async def get_data(request: URLRequest):
    try:
        # Extract shortcode - handle both /p/ and /reels/ patterns
        # First, remove query parameters (everything after ?)
        clean_url = request.url.split("?")[0]
        url_parts = clean_url.strip("/").split("/")
        
        if "reels" in url_parts:
            shortcode = url_parts[url_parts.index("reels") + 1]
        elif "reel" in url_parts:  # Also handle /reel/ (singular)
            shortcode = url_parts[url_parts.index("reel") + 1]
        elif "p" in url_parts:
            shortcode = url_parts[url_parts.index("p") + 1]
        else:
            shortcode = url_parts[-1]
        
        print(f"\n{'='*60}")
        print(f"📍 Processing shortcode: {shortcode}")
        print(f"🔗 Original URL: {request.url}")
        print(f"🧹 Cleaned URL: {clean_url}")
        
        # Check MongoDB cache first
        print(f"🔍 Checking MongoDB cache...")
        cached_data = await get_cached_post(shortcode)
        if cached_data:
            print(f"✅ Cache HIT for {shortcode}")
            print(f"📦 Returning cached data (age: {cached_data.get('fetched_at', 'unknown')})")
            # Remove MongoDB-specific fields before returning
            cached_data.pop("_id", None)
            cached_data.pop("fetched_at", None)
            cached_data.pop("cache_expiry", None)
            print(f"{'='*60}\n")
            return cached_data
        
        print(f"❌ Cache MISS for {shortcode}")
        print(f"🌐 Scraping from Instagram...")
        
        # Log session status
        print(f"🔐 Session Status:")
        print(f"   - Logged in: {L.context.is_logged_in}")
        print(f"   - Username: {L.context.username if L.context.is_logged_in else 'Anonymous'}")
        print(f"   - User agent: {L.context._session.headers.get('User-Agent', 'Not set')[:50]}...")
        
        # Cache miss - scrape Instagram
        print(f"📡 Making request to Instagram API...")
        print(f"   - Endpoint: graphql/query")
        print(f"   - Shortcode: {shortcode}")
        
        try:
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            print(f"✅ Successfully fetched post from Instagram")
        except Exception as e:
            print(f"❌ Instagram API Error:")
            print(f"   - Error Type: {type(e).__name__}")
            print(f"   - Error Message: {str(e)}")
            print(f"   - Shortcode: {shortcode}")
            print(f"   - Session: {'Logged in' if L.context.is_logged_in else 'Anonymous'}")
            print(f"\n💡 Diagnosis:")
            if "401" in str(e) or "Unauthorized" in str(e):
                print(f"   ⚠️ RATE LIMIT - Instagram is blocking your IP/session")
                print(f"   - Reason: Too many requests in short time")
                print(f"   - Solution: Wait 15-30 minutes before trying again")
                print(f"   - Logged in: {L.context.is_logged_in} (login helps but doesn't prevent all blocks)")
            elif "403" in str(e) or "Forbidden" in str(e):
                print(f"   ⚠️ FORBIDDEN - Instagram detected bot behavior")
                print(f"   - Solution: Try logging in or use different session")
            elif "404" in str(e):
                print(f"   ⚠️ NOT FOUND - Post doesn't exist or is private")
            else:
                print(f"   ⚠️ UNKNOWN ERROR - Check error message above")
            print(f"{'='*60}\n")
            raise
        
        profile = post.owner_profile
        print(f"👤 Post owner: @{profile.username}")
        
        # Extract hashtags
        hashtags = []
        if post.caption:
            hashtags = [word for word in post.caption.split() if word.startswith('#')]
        
        # Prepare response data (without MinIO URLs initially)
        media_type = "Video/Reel" if post.is_video else "Image"
        response_data = {
            "shortcode": shortcode,
            "url": request.url,
            
            # Creator Metrics
            "username": profile.username,
            "full_name": profile.full_name,
            "bio": profile.biography if hasattr(profile, 'biography') else "No bio available",
            "followers": profile.followers,
            "following": profile.followees,
            "total_posts": profile.mediacount,
            "is_verified": profile.is_verified,
            
            # Post Metrics
            "likes": post.likes,
            "comments_count": post.comments,
            "media_type": media_type,
            "caption": post.caption if post.caption else "No caption",
            "publish_date": post.date_local.strftime("%Y-%m-%d %H:%M:%S") if post.date_local else "Unknown",
            "hashtags": hashtags[:5],
            "video_view_count": post.video_view_count if post.is_video else 0,
        }
        
        # STEP 1: Save to MongoDB first to get the _id
        print(f"💾 Saving to MongoDB to get _id...")
        mongo_id = await save_post(response_data)
        
        if not mongo_id:
            print(f"⚠️ Failed to get MongoDB _id, using Instagram URLs")
            # Return data with Instagram URLs as fallback
            if post.is_video:
                response_data["display_url"] = post.video_url
                response_data["video_url"] = post.video_url
                response_data["thumbnail_url"] = post.url
            else:
                response_data["display_url"] = post.url
                response_data["thumbnail_url"] = post.url
                response_data["video_url"] = None
            response_data["profile_pic_url"] = profile.profile_pic_url
            return response_data
        
        # STEP 2: Use MongoDB _id to upload to MinIO
        print(f"📦 Using MongoDB _id ({mongo_id}) for MinIO filenames...")
        
        # Get Instagram URLs
        if post.is_video:
            media_url = post.video_url
            print(f"🎥 Video detected - using video_url: {media_url[:50]}...")
        else:
            media_url = post.url
            print(f"🖼️ Image detected - using url: {media_url[:50]}...")
        
        # Store media in MinIO using MongoDB _id
        stored_media_url = await store_instagram_media(media_url, mongo_id, media_type)
        
        # Also store thumbnail separately for videos
        if post.is_video:
            thumbnail_url = await store_instagram_media(post.url, f"{mongo_id}_thumb", "Image")
            print(f"📸 Thumbnail stored separately")
        else:
            thumbnail_url = stored_media_url
        
        # Store profile picture using MongoDB _id
        profile_pic_url = await store_profile_picture(profile.profile_pic_url, mongo_id)
        
        # STEP 3: Update MongoDB with MinIO URLs
        print(f"🔄 Updating MongoDB with MinIO URLs...")
        response_data["display_url"] = stored_media_url
        response_data["thumbnail_url"] = thumbnail_url
        response_data["video_url"] = stored_media_url if post.is_video else None
        response_data["profile_pic_url"] = profile_pic_url
        response_data["minio_id"] = mongo_id  # Store the MongoDB _id for reference
        
        # Update MongoDB with MinIO URLs
        await save_post(response_data)
        
        return response_data
        
    except Exception as e:
        print(f"\n❌ FINAL ERROR HANDLER:")
        print(f"   - Error Type: {type(e).__name__}")
        print(f"   - Error Message: {str(e)}")
        print(f"   - Shortcode: {shortcode if 'shortcode' in locals() else 'N/A'}")
        print(f"{'='*60}\n")
        return {"error": str(e)}


@app.get("/")
async def root():
    return {"message": "Instagram Scraper API", "status": "running"}


# Add to main.py
@app.get("/test-mongodb")
async def test_mongodb():
    test_data = {
        "shortcode": "TEST123",
        "username": "test_user",
        "likes": 100
    }
    await save_post(test_data)
    return {"message": "Test data saved to MongoDB"}