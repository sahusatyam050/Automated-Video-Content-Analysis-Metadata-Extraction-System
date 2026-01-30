import os
import httpx
from minio import Minio
from minio.error import S3Error
from dotenv import load_dotenv
from io import BytesIO

load_dotenv()

# MinIO Configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "instagram-media")
MINIO_SECURE = os.getenv("MINIO_SECURE", "False").lower() == "true"

# Initialize MinIO client
minio_client = None


def init_minio():
    """Initialize MinIO client and create bucket if it doesn't exist"""
    global minio_client
    
    try:
        minio_client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE
        )
        
        # Create bucket if it doesn't exist
        if not minio_client.bucket_exists(MINIO_BUCKET):
            minio_client.make_bucket(MINIO_BUCKET)
            print(f"✅ Created MinIO bucket: {MINIO_BUCKET}")
        else:
            print(f"✅ MinIO bucket already exists: {MINIO_BUCKET}")
        
        # Set bucket policy to public read (so frontend can access images)
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{MINIO_BUCKET}/*"]
                }
            ]
        }
        import json
        minio_client.set_bucket_policy(MINIO_BUCKET, json.dumps(policy))
        print(f"✅ MinIO initialized successfully")
        return True
        
    except Exception as e:
        print(f"⚠️ MinIO initialization failed: {e}")
        print("ℹ️ Continuing without MinIO - images will use Instagram URLs")
        return False


async def download_image(url: str) -> bytes:
    """Download image from URL"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.content
    except Exception as e:
        print(f"⚠️ Failed to download image from {url}: {e}")
        return None


def upload_to_minio(file_data: bytes, filename: str, content_type: str = "image/jpeg") -> str:
    """Upload file to MinIO and return the URL"""
    if not minio_client:
        return None
    
    try:
        # Upload to MinIO
        minio_client.put_object(
            MINIO_BUCKET,
            filename,
            BytesIO(file_data),
            length=len(file_data),
            content_type=content_type
        )
        
        # Generate URL
        url = get_minio_url(filename)
        print(f"✅ Uploaded to MinIO: {filename}")
        return url
        
    except S3Error as e:
        print(f"⚠️ MinIO upload failed: {e}")
        return None


def get_minio_url(filename: str) -> str:
    """Generate accessible URL for MinIO object"""
    protocol = "https" if MINIO_SECURE else "http"
    return f"{protocol}://{MINIO_ENDPOINT}/{MINIO_BUCKET}/{filename}"


async def store_instagram_media(instagram_url: str, mongo_id: str, media_type: str) -> str:
    """
    Download media from Instagram and upload to MinIO using MongoDB _id as filename
    Returns MinIO URL or original Instagram URL if MinIO fails
    
    Args:
        instagram_url: Instagram media URL
        mongo_id: MongoDB document _id (used as filename)
        media_type: "Image" or "Video/Reel"
    """
    if not minio_client:
        return instagram_url
    
    try:
        # Download from Instagram
        file_data = await download_image(instagram_url)
        if not file_data:
            return instagram_url
        
        # Determine file extension and content type
        if media_type.lower() in ["video", "video/reel"]:
            extension = "mp4"
            content_type = "video/mp4"
        else:
            extension = "jpg"
            content_type = "image/jpeg"
        
        # Generate filename using MongoDB _id (flat structure for easy fetching)
        filename = f"{mongo_id}.{extension}"
        
        # Upload to MinIO
        minio_url = upload_to_minio(file_data, filename, content_type)
        
        return minio_url if minio_url else instagram_url
        
    except Exception as e:
        print(f"⚠️ Failed to store media in MinIO: {e}")
        return instagram_url


async def store_profile_picture(instagram_url: str, mongo_id: str) -> str:
    """
    Download profile picture from Instagram and upload to MinIO using MongoDB _id
    Returns MinIO URL or original Instagram URL if MinIO fails
    
    Args:
        instagram_url: Instagram profile picture URL
        mongo_id: MongoDB document _id (used as filename)
    """
    if not minio_client:
        return instagram_url
    
    try:
        # Download from Instagram
        file_data = await download_image(instagram_url)
        if not file_data:
            return instagram_url
        
        # Generate filename using MongoDB _id (flat structure for easy fetching)
        filename = f"profile_{mongo_id}.jpg"
        
        # Upload to MinIO
        minio_url = upload_to_minio(file_data, filename, "image/jpeg")
        
        return minio_url if minio_url else instagram_url
        
    except Exception as e:
        print(f"⚠️ Failed to store profile picture in MinIO: {e}")
        return instagram_url


# ============================================================================
# DIRECT FETCH FUNCTIONS (MongoDB-style)
# ============================================================================

def get_post_media_url(mongo_id: str, media_type: str = "image") -> str:
    """
    Get MinIO URL for a post media by MongoDB _id (direct fetch)
    
    Args:
        mongo_id: MongoDB document _id
        media_type: "image", "video", or "thumbnail"
    
    Returns:
        MinIO URL for the media
    
    Example:
        url = get_post_media_url("679a1b2c3d4e5f6789012345", "video")
        # Returns: http://localhost:9000/instagram-media/679a1b2c3d4e5f6789012345.mp4
    """
    if media_type.lower() in ["video", "video/reel"]:
        extension = "mp4"
    elif media_type.lower() == "thumbnail":
        mongo_id = f"{mongo_id}_thumb"
        extension = "jpg"
    else:
        extension = "jpg"
    
    filename = f"{mongo_id}.{extension}"
    return get_minio_url(filename)


def get_profile_picture_url(mongo_id: str) -> str:
    """
    Get MinIO URL for a profile picture by MongoDB _id (direct fetch)
    
    Args:
        mongo_id: MongoDB document _id
    
    Returns:
        MinIO URL for the profile picture
    
    Example:
        url = get_profile_picture_url("679a1b2c3d4e5f6789012345")
        # Returns: http://localhost:9000/instagram-media/profile_679a1b2c3d4e5f6789012345.jpg
    """
    filename = f"profile_{mongo_id}.jpg"
    return get_minio_url(filename)


def check_media_exists(mongo_id: str, media_type: str = "image") -> bool:
    """
    Check if media exists in MinIO by MongoDB _id
    
    Args:
        mongo_id: MongoDB document _id
        media_type: "image" or "video"
    
    Returns:
        True if media exists, False otherwise
    """
    if not minio_client:
        return False
    
    try:
        if media_type.lower() in ["video", "video/reel"]:
            extension = "mp4"
        else:
            extension = "jpg"
        
        filename = f"{mongo_id}.{extension}"
        minio_client.stat_object(MINIO_BUCKET, filename)
        return True
    except S3Error:
        return False
    except Exception as e:
        print(f"⚠️ Error checking media existence: {e}")
        return False
