from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta

# MongoDB Configuration
MONGODB_URL = "mongodb://localhost:27017"
MONGODB_DB = "instagram_scraper"

# Async MongoDB client
async_client = AsyncIOMotorClient(MONGODB_URL)
async_db = async_client[MONGODB_DB]

# Collections
posts_collection = async_db["posts"]


async def init_mongodb():
    """Initialize MongoDB collections and indexes"""
    try:
        # Create index on shortcode for faster lookups
        await posts_collection.create_index("shortcode", unique=True)
        await posts_collection.create_index("fetched_at")
        
        print("✅ MongoDB initialized successfully")
        return True
    except Exception as e:
        print(f"❌ MongoDB initialization error: {e}")
        return False


async def get_cached_post(shortcode: str):
    """Get cached post from MongoDB if it exists and is not expired (7 days)"""
    try:
        post = await posts_collection.find_one({"shortcode": shortcode})
        
        if not post:
            return None
        
        # Check if cache is expired (7 days)
        cache_expiry = post.get("cache_expiry")
        if cache_expiry and datetime.now() > cache_expiry:
            # Cache expired, delete it
            await posts_collection.delete_one({"shortcode": shortcode})
            return None
        
        return post
    except Exception as e:
        print(f"❌ Error getting cached post: {e}")
        return None


async def save_post(post_data: dict):
    """Save post metadata to MongoDB with 7-day cache expiry"""
    try:
        shortcode = post_data.get("shortcode")
        
        # Add timestamps
        post_data["fetched_at"] = datetime.now()
        post_data["cache_expiry"] = datetime.now() + timedelta(days=7)
        
        # Upsert (update if exists, insert if not)
        result = await posts_collection.update_one(
            {"shortcode": shortcode},
            {"$set": post_data},
            upsert=True
        )
        
        # Get the document to return its _id
        saved_post = await posts_collection.find_one({"shortcode": shortcode})
        mongo_id = str(saved_post["_id"])
        
        print(f"✅ Saved post {shortcode} to MongoDB with _id: {mongo_id}")
        return mongo_id
    except Exception as e:
        print(f"❌ Error saving post: {e}")
        return None


async def close_mongodb():
    """Close MongoDB connection"""
    async_client.close()
    print("✅ MongoDB connection closed")
