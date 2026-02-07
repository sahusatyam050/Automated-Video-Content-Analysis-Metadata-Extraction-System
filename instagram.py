import os
import time
import json
import random
import io
from datetime import datetime
from bson import ObjectId

import instaloader
# Removed: from minio import Minio (Not needed anymore)
# Removed: import yt_dlp (Not needed anymore)


class InstagramScraperEngine:
    """
    Instagram Scraper - Class-based version
    Matches YouTubeScraperEngine structure
    
    IMPORTANT SETUP INSTRUCTIONS:
    1. Set environment variables:
       INSTAGRAM_USERNAME=your_username
       INSTAGRAM_PASSWORD=your_password
    2. First run will create session file for reuse
    3. Session file prevents repeated logins (reduces ban risk)
    """
    
    def __init__(self):
        """Initialize Instagram scraper"""
        self.loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=True,
            save_metadata=False,
            compress_json=False,
            quiet=True
        )
        
        # Credentials from environment
        self.username = os.getenv("INSTAGRAM_USERNAME", "")
        self.password = os.getenv("INSTAGRAM_PASSWORD", "")
        
        # Session file for persistence
        self.session_file = os.getenv("INSTAGRAM_SESSION_FILE", "instagram_session")
        
        # --- MinIO Configuration REMOVED ---
        self.minio_client = None
        
        # Try to load existing session
        self._load_session()
    
    def _load_session(self):
        """Load saved session to avoid repeated logins"""
        try:
            self.loader.load_session_from_file(self.username, self.session_file)
            print(f"✅ Loaded Instagram session for @{self.username}")
            return True
        except FileNotFoundError:
            print("⚠️ No saved session found, will login on first scrape")
            return False
        except Exception as e:
            print(f"⚠️ Error loading session: {e}")
            return False
    
    def _ensure_login(self):
        """Login to Instagram if not already logged in"""
        if not self.loader.context.is_logged_in:
            if not self.username or not self.password:
                raise ValueError(
                    "Instagram credentials not set! "
                    "Please set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD environment variables"
                )
            
            print(f"🔐 Logging in to Instagram as @{self.username}...")
            
            try:
                self.loader.login(self.username, self.password)
                self.loader.save_session_to_file(self.session_file)
                print("✅ Login successful, session saved")
            except instaloader.exceptions.BadCredentialsException:
                raise ValueError("Invalid Instagram credentials")
            except instaloader.exceptions.TwoFactorAuthRequiredException:
                raise ValueError("Two-factor authentication required - please disable or use session file")
            except Exception as e:
                raise ValueError(f"Login failed: {str(e)}")
    
    def _extract_shortcode(self, url):
        """Extract shortcode from Instagram URL"""
        try:
            url = url.rstrip('/')
            parts = url.split('/')
            
            if 'p' in parts:
                return parts[parts.index('p') + 1]
            elif 'reel' in parts:
                return parts[parts.index('reel') + 1]
            elif 'reels' in parts:
                return parts[parts.index('reels') + 1]
            else:
                # Try last part
                return parts[-1].split('?')[0]
        except Exception as e:
            raise ValueError(f"Could not extract shortcode from URL: {e}")
    
    # --- _download_media function REMOVED to prevent MinIO calls ---
    
    def _get_sentiment(self, text):
        """Simple sentiment analysis"""
        try:
            from textblob import TextBlob
            blob = TextBlob(text)
            pol = blob.sentiment.polarity
            
            if pol > 0.1:
                return {"sentiment": "Positive", "confidence": round(pol, 2)}
            elif pol < -0.1:
                return {"sentiment": "Negative", "confidence": round(abs(pol), 2)}
            else:
                return {"sentiment": "Neutral", "confidence": round(1.0 - abs(pol), 2)}
        except ImportError:
            # If TextBlob not available, return neutral
            return {"sentiment": "Neutral", "confidence": 0.5}
    
    def scrape_real_data(self, url, task_id):
        """
        Main scraping function - matches YouTube scraper interface
        
        Args:
            url: Instagram post URL
            task_id: Unique task identifier
            
        Returns:
            Dictionary with status and scraped data
        """
        
        try:
            print(f"\n{'='*60}")
            print(f"📷 INSTAGRAM POST: {url}")
            print(f"📝 Task ID: {task_id}")
            print(f"{'='*60}\n")
            
            # Ensure logged in
            self._ensure_login()
            
            # Extract shortcode
            shortcode = self._extract_shortcode(url)
            print(f"✓ Shortcode: {shortcode}")
            
            # Fetch post
            print("📡 Fetching post data...")
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)
            profile = post.owner_profile
            
            print(f"✓ Post Owner: @{profile.username}")
            print(f"✓ Likes: {post.likes:,}")
            print(f"✓ Comments: {post.comments:,}")
            
            # Extract post info
            post_info = {
                "shortcode": post.shortcode,
                "url": url,
                "caption": post.caption if post.caption else "",
                "likes": post.likes,
                "comments_count": post.comments,
                "is_video": post.is_video,
                "timestamp": post.date_utc.isoformat(),
                "location": post.location.name if post.location else None,
                "hashtags": list(post.caption_hashtags) if post.caption_hashtags else []
            }
            
            # Extract creator/profile info
            creator_info = {
                "username": profile.username,
                "full_name": profile.full_name,
                "followers": profile.followers,
                "following": profile.followees,
                "total_posts": profile.mediacount,
                "bio": profile.biography,
                "is_verified": profile.is_verified,
                "is_private": profile.is_private,
                "external_url": profile.external_url if profile.external_url else None
            }
            
            # Scrape comments
            print("\n💬 Scraping comments...")
            comments_data = []
            comment_count = 0
            max_comments = 25
            
            try:
                for comment in post.get_comments():
                    if comment_count >= max_comments:
                        break
                    
                    sentiment = self._get_sentiment(comment.text)
                    
                    comments_data.append({
                        "id": comment.id,
                        "author": comment.owner.username,
                        "text": comment.text,
                        "likes": comment.likes_count if hasattr(comment, 'likes_count') else 0,
                        "timestamp": comment.created_at_utc.isoformat(),
                        "sentiment": sentiment["sentiment"],
                        "confidence": sentiment["confidence"]
                    })
                    
                    comment_count += 1
                    
                    # Rate limiting
                    if comment_count % 10 == 0:
                        print(f"  ✓ Scraped {comment_count} comments...")
                        time.sleep(random.uniform(1, 3))
                
                print(f"✓ Total comments scraped: {len(comments_data)}")
            
            except instaloader.exceptions.LoginRequiredException:
                print("⚠️ Login required for comments, session may have expired")
                comments_data = []
            except Exception as e:
                print(f"⚠️ Comment scraping error: {e}")
                comments_data = []
            
            # --- Media Download Block REMOVED ---
            media_urls = []
            
            # Build result
            result = {
                "task_id": task_id,
                "post_info": post_info,
                "creator_info": creator_info,
                "comments": {
                    "total": len(comments_data),
                    "data": comments_data
                },
                "media": {
                    "minio_paths": media_urls
                },
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            print(f"\n{'='*60}")
            print("✅ INSTAGRAM SCRAPING COMPLETED")
            print(f"   📝 Caption: {post_info['caption'][:50]}...")
            print(f"   👤 Creator: @{creator_info['username']}")
            print(f"   👍 Likes: {post_info['likes']:,}")
            print(f"   💬 Comments: {len(comments_data)}")
            print(f"{'='*60}\n")
            
            return result
        
        except ValueError as e:
            # Configuration errors (credentials, etc.)
            print(f"\n{'='*60}")
            print(f"❌ CONFIGURATION ERROR: {e}")
            print(f"{'='*60}\n")
            return {
                "status": "failed",
                "error": str(e),
                "error_type": "configuration",
                "task_id": task_id
            }
        
        except instaloader.exceptions.LoginRequiredException:
            print(f"\n{'='*60}")
            print(f"❌ LOGIN REQUIRED: Session expired")
            print(f"{'='*60}\n")
            return {
                "status": "failed",
                "error": "Instagram session expired, please re-login",
                "error_type": "authentication",
                "task_id": task_id
            }
        
        except instaloader.exceptions.ConnectionException as e:
            print(f"\n{'='*60}")
            print(f"❌ CONNECTION ERROR: {e}")
            print(f"{'='*60}\n")
            return {
                "status": "failed",
                "error": f"Instagram connection error: {str(e)}",
                "error_type": "connection",
                "task_id": task_id
            }
        
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"❌ UNEXPECTED ERROR: {e}")
            print(f"{'='*60}\n")
            import traceback
            traceback.print_exc()
            
            return {
                "status": "failed",
                "error": str(e),
                "error_type": "unknown",
                "task_id": task_id
            }


# Test code
if __name__ == "__main__":
    # Setup test
    print("Instagram Scraper Test")
    print("="*60)
    print("IMPORTANT: Set these environment variables:")
    print("  export INSTAGRAM_USERNAME=your_username")
    print("  export INSTAGRAM_PASSWORD=your_password")
    print("="*60 + "\n")
    
    scraper = InstagramScraperEngine()
    
    # Example URL (replace with real URL)
    test_url = "https://www.instagram.com/p/EXAMPLE_SHORTCODE/"
    
    result = scraper.scrape_real_data(test_url, "test_001")
    
    if result["status"] == "completed":
        print("\n📊 FINAL SUMMARY:")
        print(f"  Caption: {result['post_info']['caption'][:60]}...")
        print(f"  Creator: @{result['creator_info']['username']}")
        print(f"  Followers: {result['creator_info']['followers']:,}")
        print(f"  Likes: {result['post_info']['likes']:,}")
        print(f"  Comments Scraped: {len(result['comments']['data'])}")
    else:
        print(f"\n❌ Scraping failed: {result['error']}")