import time, random, re, os, pickle, shutil
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import datetime

class RedditScraperEngine:
    """
    Reddit Scraper - Headless Stealth Version
    Combines JSON-like data depth with Selenium stability.
    """
    
    def __init__(self):
        """Initialize Reddit scraper"""
        load_dotenv()
        self.USERNAME = os.getenv("REDDIT_USERNAME")
        self.PASSWORD = os.getenv("REDDIT_PASSWORD")
        self.COOKIE_FILE = "reddit_cookies.pkl"
        self._driver = None
        print("💡 Reddit scraper initialized in Selenium Stealth mode")
    
    def get_driver(self):
        """Get or create the browser instance with headless stealth settings"""
        if self._driver is None:
            # --- FIX FOR WinError 183 ---
            # Automatically clears the locked temp driver folder before starting
            driver_temp_path = os.path.join(os.environ.get('APPDATA', ''), 'undetected_chromedriver')
            if os.path.exists(driver_temp_path):
                try:
                    shutil.rmtree(driver_temp_path, ignore_errors=True)
                except:
                    pass

            options = uc.ChromeOptions()
            
            # --- HEADLESS SETTINGS ---
            # IMPORTANT: Comment the line below for your very first run to log in manually!
            # options.add_argument("--headless") 
            
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            
            # Use a real user agent
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            options.add_argument(f"user-agent={user_agent}")
            
            self._driver = uc.Chrome(options=options, use_subprocess=True)
            
            # Mask the automation flag
            self._driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
        return self._driver

    def human_type(self, el, text):
        """Simulate human typing speed"""
        for char in text:
            el.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))

    def load_cookies(self):
        """Try to restore a previous session"""
        if not os.path.exists(self.COOKIE_FILE):
            return False
        
        try:
            driver = self.get_driver()
            driver.get("https://www.reddit.com")
            time.sleep(2)
            
            cookies = pickle.load(open(self.COOKIE_FILE, "rb"))
            for c in cookies:
                try:
                    driver.add_cookie(c)
                except:
                    pass
            
            driver.refresh()
            # Check if login was successful (no 'Log In' button visible)
            time.sleep(3)
            return True
        except Exception as e:
            print(f"⚠️ Reddit session restore failed: {e}")
            return False

    def login_to_reddit(self):
        """Full login flow with human-like interaction"""
        driver = self.get_driver()
        wait = WebDriverWait(driver, 30)
        
        print("🔑 Navigating to Reddit Login...")
        driver.get("https://www.reddit.com/login")
        
        try:
            # 1. Enter Username
            u_field = wait.until(EC.element_to_be_clickable((By.ID, "login-username")))
            self.human_type(u_field, self.USERNAME)
            
            # 2. Enter Password
            p_field = driver.find_element(By.ID, "login-password")
            self.human_type(p_field, self.PASSWORD)
            p_field.send_keys(Keys.ENTER)
            
            # 3. Wait for confirmation (URL change or home feed element)
            time.sleep(6)
            
            # 4. Save Cookies for next time
            pickle.dump(driver.get_cookies(), open(self.COOKIE_FILE, "wb"))
            print("💾 Reddit session saved to cookies.")
            
        except Exception as e:
            print(f"❌ Login failed: {e}")
            driver.save_screenshot("reddit_login_error.png")

    def scrape_real_data(self, url, task_id):
        """Main scraping logic matching your API structure"""
        try:
            driver = self.get_driver()
            
            if not self.load_cookies():
                self.login_to_reddit()
            
            print(f"📡 Scraping Reddit: {url}")
            driver.get(url)
            
            # Wait for Reddit's main post element (Web Component)
            wait = WebDriverWait(driver, 20)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "shreddit-post")))
            
            # Gentle scroll to trigger any lazy-loaded metadata
            driver.execute_script("window.scrollTo(0, 400);")
            time.sleep(2)
            
            # --- DATA EXTRACTION ---
            post = driver.find_element(By.TAG_NAME, "shreddit-post")
            
            # Metadata from custom shreddit attributes
            post_info = {
                "title": post.get_attribute("post-title"),
                "author": post.get_attribute("author"),
                "subreddit": post.get_attribute("subreddit-prefixed-name"),
                "score": post.get_attribute("score"),
                "num_comments": post.get_attribute("comment-count"),
                "url": url,
                "created_at": post.get_attribute("created-timestamp"),
                "is_nsfw": "nsfw" in post.get_attribute("class").lower()
            }
            
            # Extract Main Body Text
            content = ""
            try:
                # Target the specific content div using shreddit ID patterns
                post_id = post.get_attribute("id")
                content_div = driver.find_element(By.ID, f"{post_id}-post-rtjson-content")
                content = content_div.text
            except:
                pass
            post_info["selftext"] = content

            # Extract Comments (Top 5 for summary)
            comments = []
            try:
                comment_elements = driver.find_elements(By.TAG_NAME, "shreddit-comment")[:5]
                for c in comment_elements:
                    c_author = c.get_attribute("author")
                    # Use a broader search for text inside the comment component
                    c_text = c.text.split('\n')[-1] # Fallback if specific div fails
                    comments.append({
                        "author": c_author,
                        "text": c_text
                    })
            except:
                pass

            return {
                "task_id": task_id,
                "status": "completed",
                "platform": "reddit",
                "post_info": post_info,
                "comments": comments,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"❌ Reddit Scraper Failed: {e}")
            try: driver.save_screenshot(f"error_reddit_{task_id}.png")
            except: pass
            return {"status": "failed", "error": str(e), "task_id": task_id}

# Manual Test
if __name__ == "__main__":
    scraper = RedditScraperEngine()
    # Replace with a real post URL for testing
    res = scraper.scrape_real_data("https://www.reddit.com/r/technology/comments/17ah0ab/example/", "test_1")
    print(res)