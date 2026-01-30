import instaloader
import getpass
import json
from datetime import datetime

# 1. Setup Instaloader
L = instaloader.Instaloader()

# 2. Login Logic
USER = input("Enter your IG Username: ")
PASS = getpass.getpass("Enter your IG Password: ")

try:
    # It's better to load a session if you have one, 
    # but for a basic script, login works:
    L.login(USER, PASS) 
    print("✅ Login Successful!")
except Exception as e:
    print(f"⚠️ Login failed: {e}")
    print("Continuing with public data only (might fail for many posts)...")

# 3. Get Post URL
url = input("\n🔗 Paste Instagram Post/Reel Link: ").strip()

try:
    # 4. Improved Shortcode Extraction
    # Handles links like: instagram.com/p/SHORTCODE/ or instagram.com/reels/SHORTCODE/
    parts = url.rstrip('/').split('/')
    shortcode = parts[-1] if 'p' not in parts and 'reels' not in parts else parts[parts.index('p')+1] if 'p' in parts else parts[parts.index('reels')+1]
    
    print(f"🔍 Analyzing shortcode: {shortcode}")
    
    # 5. Get Data
    post = instaloader.Post.from_shortcode(L.context, shortcode)
    profile = post.owner_profile
    
    print("\n" + "="*60)
    print("📊 INSTAGRAM POST & CREATOR CORE METRICS")
    print("="*60)
    
    # ===== POST METRICS =====
    print(f"📎 Post Shortcode      : {post.shortcode}")
    print(f"📅 Publish Date        : {post.date_local}")
    print(f"👍 Likes Count         : {post.likes}")
    print(f"💬 Comments Count      : {post.comments}")
    
    # ===== CREATOR METRICS =====
    print(f"\n👤 Username            : {profile.username}")
    print(f"👥 Followers Count     : {profile.followers}")
    
    # ===== COMMENTS SCRAPING =====
    max_comments = int(input("\nHow many comments to fetch? (0 for all): ") or "10")
    comments_data = []
    
    print(f"⏳ Fetching comments...")
    count = 0
    for comment in post.get_comments():
        if max_comments > 0 and count >= max_comments:
            break
        
        comments_data.append({
            "username": comment.owner.username,
            "text": comment.text,
            "likes": comment.likes_count
        })
        count += 1

    # Save to JSON
    filename = f"data_{shortcode}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(comments_data, f, indent=4)
    print(f"✅ Saved to {filename}")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n📋 Task Complete.")