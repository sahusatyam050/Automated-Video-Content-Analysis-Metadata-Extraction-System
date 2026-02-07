import os
import time
import re
import json
from textblob import TextBlob
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse, parse_qs

class YouTubeScraperEngine:
    """
    ACCURATE ICON-BASED SCRAPER
    Based on actual YouTube channel popup icons
    Outputs JSON only (no local files, no PDFs)
    """
    
    def __init__(self):
        self.headless = os.getenv("HEADLESS_MODE", "false").lower() == "true"

    def extract_youtube_video_id(self, url):
        """Extract actual YouTube video ID from URL"""
        try:
            if "youtu.be/" in url:
                video_id = url.split("youtu.be/")[1].split("?")[0]
                return video_id
            elif "v=" in url:
                video_id = url.split("v=")[1].split("&")[0]
                return video_id
            elif "/embed/" in url:
                video_id = url.split("/embed/")[1].split("?")[0]
                return video_id
            return None
        except Exception as e:
            print(f"❌ Video ID extraction error: {e}")
            return None

    def extract_real_url(self, youtube_redirect_url):
        """Extract the actual URL from YouTube's redirect wrapper"""
        try:
            if "youtube.com/redirect" in youtube_redirect_url:
                parsed = urlparse(youtube_redirect_url)
                params = parse_qs(parsed.query)
                if 'q' in params:
                    return params['q'][0]
            return youtube_redirect_url
        except:
            return youtube_redirect_url

    def get_sentiment(self, text):
        if not text: return {"sentiment": "Neutral", "confidence": 0.5}
        blob = TextBlob(text)
        pol = blob.sentiment.polarity
        if pol > 0.1: return {"sentiment": "Positive", "confidence": round(pol, 2)}
        elif pol < -0.1: return {"sentiment": "Negative", "confidence": round(abs(pol), 2)}
        return {"sentiment": "Neutral", "confidence": round(1.0 - abs(pol), 2)}

    def clean_number(self, text):
        """Convert '2.46M subscribers' to 2460000"""
        if not text: return 0
        text = str(text).strip().upper().replace(',', '')
        text = re.sub(r'[^\d.KMB]', '', text)
        match = re.search(r'(\d+\.?\d*)', text)
        if not match: return 0
        num = float(match.group(1))
        if 'K' in text: num *= 1_000
        elif 'M' in text: num *= 1_000_000
        elif 'B' in text: num *= 1_000_000_000
        return int(num)

    def scrape_by_icon_rows(self, driver):
        """ICON-BASED EXTRACTION"""
        print("🎯 ICON-BASED CHANNEL SCRAPING")
        
        channel_info = {
            "name": "",
            "handle": "",
            "description": "",
            "subscriber_count": 0,
            "video_count": 0,
            "social_links": []
        }
        
        try:
            # Wait for content to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Social Links
            try:
                # Wait briefly for links
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-about-channel-renderer a, #link-list-container a"))
                )
                link_elements = driver.find_elements(By.CSS_SELECTOR, "ytd-about-channel-renderer a, #link-list-container a")
                processed_urls = set()
                
                for link_elem in link_elements:
                    href = link_elem.get_attribute("href")
                    if not href or href in processed_urls: continue
                    
                    real_url = self.extract_real_url(href)
                    platform = None
                    icon = "🌐"
                    
                    if "instagram.com" in real_url:
                        platform, icon = "Instagram", "📷"
                    elif "facebook.com" in real_url:
                        platform, icon = "Facebook", "📘"
                    elif "twitter.com" in real_url or "x.com" in real_url:
                        platform, icon = "Twitter", "🐦"
                    elif not any(x in real_url for x in ['youtube.com', 'google.com']):
                        platform, icon = "Website", "🌐"
                    
                    if platform:
                        channel_info["social_links"].append({
                            "platform": platform,
                            "icon": icon,
                            "url": real_url
                        })
                        processed_urls.add(real_url)
            except Exception:
                pass # Social links optional
            
            page_text = driver.find_element(By.TAG_NAME, "body").text
            
            # Handle
            try:
                match = re.search(r'www\.youtube\.com/@([\w.]+)', driver.current_url)
                if not match:
                    match = re.search(r'@([\w.]+)', page_text)
                if match:
                    channel_info["handle"] = "@" + match.group(1).split()[0]
            except: pass
            
            # Subscribers
            try:
                match = re.search(r'([\d,.KMB]+)\s*subscriber', page_text, re.IGNORECASE)
                if match:
                    channel_info["subscriber_count"] = self.clean_number(match.group(1))
            except: pass
            
            # Video Count
            try:
                match = re.search(r'([\d,.KMB]+)\s*video', page_text, re.IGNORECASE)
                if match:
                    channel_info["video_count"] = self.clean_number(match.group(1))
            except: pass
            
            # Description
            try:
                description_selectors = [
                    (By.CSS_SELECTOR, "yt-attributed-string#description-inner"),
                    (By.CSS_SELECTOR, "yt-formatted-string#description"),
                    (By.ID, "description-container")
                ]
                
                for selector in description_selectors:
                    try:
                        desc_elem = driver.find_element(*selector)
                        text = desc_elem.text.strip()
                        if text:
                            channel_info["description"] = text
                            break
                    except: continue
            except: pass
            
        except Exception as e:
            print(f"⚠️ Channel scraping error: {e}")
        
        return channel_info

    def scrape_comments(self, driver, max_comments=25):
        comments = []
        try:
            print("� Scraping comments...")
            
            # Scroll down to trigger comments load
            driver.execute_script("window.scrollTo(0, 600);")
            
            # Wait for comments section
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-comment-thread-renderer"))
                )
            except TimeoutException:
                # Try scrolling a bit more if not found yet
                driver.execute_script("window.scrollBy(0, 1000);")
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-comment-thread-renderer"))
                    )
                except TimeoutException:
                    print("⚠️ Comments section not found or disabled")
                    return comments

            # Load more comments
            for _ in range(3):
                driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(1) # Small sleep for dynamic loading
            
            threads = driver.find_elements(By.CSS_SELECTOR, "ytd-comment-thread-renderer")
            
            for idx, thread in enumerate(threads[:max_comments]):
                try:
                    text_elem = thread.find_element(By.CSS_SELECTOR, "#content-text")
                    comment_text = text_elem.text.strip()
                    if not comment_text: continue
                    
                    author = "Unknown"
                    try:
                        author_elem = thread.find_element(By.CSS_SELECTOR, "#author-text span")
                        author = author_elem.text.strip().replace("@", "")
                    except: pass
                    
                    likes = 0
                    try:
                        like_elem = thread.find_element(By.CSS_SELECTOR, "#vote-count-middle")
                        likes = self.clean_number(like_elem.text.strip())
                    except: pass
                    
                    timestamp = ""
                    try:
                        time_elem = thread.find_element(By.CSS_SELECTOR, "yt-formatted-string.published-time-text a")
                        timestamp = time_elem.text.strip()
                    except: pass
                    
                    sent = self.get_sentiment(comment_text)
                    comments.append({
                        "id": idx + 1, "author": author, "text": comment_text,
                        "likes": likes, "timestamp": timestamp,
                        "sentiment": sent["sentiment"], "confidence": sent["confidence"]
                    })
                except: continue
                
        except Exception as e:
            print(f"⚠️ Comment scraping error: {e}")
        return comments

    def scrape_real_data(self, video_url, task_id, mongodb_id=None):
        actual_video_id = self.extract_youtube_video_id(video_url)
        if not actual_video_id:
            actual_video_id = str(task_id)

        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        driver = None
        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            print(f"🎬 STARTING TASK: {task_id} | VIDEO ID: {actual_video_id}")
            
            driver.get(video_url)
            
            # Wait for video title to ensure page load
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1.ytd-watch-metadata, h1.title"))
                )
            except TimeoutException:
                print("⚠️ Valid video page did not load in time")
            
            video_info = {
                "title": None,
                "description": None,
                "views": None,
                "likes": None,
                "duration": None,
                "upload_date": None,
                "comment_count": None,
                "video_id": actual_video_id
            }
            
            # Title
            try:
                title_elem = driver.find_element(By.CSS_SELECTOR, "h1.ytd-watch-metadata yt-formatted-string, h1.title yt-formatted-string")
                video_info["title"] = title_elem.text.strip()
            except: pass
            
            # Views
            try:
                view_elem = driver.find_element(By.XPATH, "//span[contains(text(), 'views')]")
                video_info["views"] = self.clean_number(view_elem.text)
            except: 
                # Fallback to regex from source
                match = re.search(r'"viewCount":"(\d+)"', driver.page_source)
                if match: video_info["views"] = int(match.group(1))

            # Likes
            try:
                like_elem = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'like this video')]//div[contains(@class,'yt-spec-button-shape-next__button-text-content')]")
                video_info["likes"] = self.clean_number(like_elem.text.strip())
            except: pass
            
            # Description (Expand if needed)
            try:
                expand_btn = driver.find_element(By.ID, "expand")
                driver.execute_script("arguments[0].click();", expand_btn)
                time.sleep(1) # Wait for expansion animation
            except: pass

            try:
                desc_elem = driver.find_element(By.CSS_SELECTOR, "ytd-text-inline-expander#description-inline-expander, #description-container")
                video_info["description"] = desc_elem.text.strip()
            except: pass
            
            # Channel Info
            channel_name = ""
            channel_url = ""
            try:
                channel_link = driver.find_element(By.CSS_SELECTOR, "ytd-channel-name a")
                channel_name = channel_link.text.strip()
                channel_url = channel_link.get_attribute("href")
            except: pass
            
            channel_info = {
                "name": channel_name,
                "handle": None,
                "subscriber_count": None,
                "video_count": None,
                "description": None
            }
            
            # Navigate to channel page in NEW TAB to preserve video state
            if channel_url:
                try:
                    about_url = channel_url.rstrip('/') + "/about"
                    driver.execute_script(f"window.open('{about_url}', '_blank');")
                    driver.switch_to.window(driver.window_handles[1])
                    
                    channel_info = self.scrape_by_icon_rows(driver)
                    channel_info["name"] = channel_name
                    
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                except Exception as e:
                    print(f"⚠️ Channel navigation error: {e}")
                    # Ensure we are back on main tab
                    if len(driver.window_handles) > 1:
                        driver.switch_to.window(driver.window_handles[0])
            
            # Comments (now back on video page)
            comments = self.scrape_comments(driver)
            video_info["comment_count"] = len(comments)
            
            result = {
                "task_id": task_id,
                "video_id": actual_video_id,
                "video_info": video_info,
                "channel_info": channel_info,
                "comments": {"total": len(comments), "data": comments},
                "status": "completed",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            
            print(f"✅ COMPLETED: {video_info['title'][:30]}...")
            return result
            
        except Exception as e:
            print(f"❌ SCRAPER FAILED: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "failed", "error": str(e), "task_id": task_id}
        finally:
            if driver: driver.quit()
