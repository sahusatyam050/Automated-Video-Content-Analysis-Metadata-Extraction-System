import time, random, re, os, pickle
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from dotenv import load_dotenv
from datetime import datetime

class TwitterScraperEngine:
    def __init__(self):
        load_dotenv()
        self.USERNAME = os.getenv("TWITTER_USERNAME")
        self.PASSWORD = os.getenv("TWITTER_PASSWORD")
        self.EMAIL_OR_PHONE = os.getenv("TWITTER_EMAIL_OR_PHONE")
        self.COOKIE_FILE = "twitter_cookies.pkl"
        self._driver = None
    
    def get_driver(self):
        if self._driver is None:
            options = uc.ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--no-sandbox")
            
            # Updated user agent
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            options.add_argument(f"user-agent={ua}")
            
            # Stealth options
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            self._driver = uc.Chrome(options=options, use_subprocess=True)
            
            # Hide webdriver property
            self._driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
            })
        return self._driver

    def human_type(self, el, text):
        for ch in text:
            el.send_keys(ch)
            time.sleep(random.uniform(0.05, 0.15))

    def load_cookies(self):
        if not os.path.exists(self.COOKIE_FILE): 
            return False
        try:
            driver = self.get_driver()
            driver.get("https://x.com")
            time.sleep(random.uniform(1, 2))
            
            with open(self.COOKIE_FILE, "rb") as f:
                cookies = pickle.load(f)
            
            for c in cookies: 
                try:
                    driver.add_cookie(c)
                except:
                    pass
            
            driver.refresh()
            time.sleep(random.uniform(2, 3))
            
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "nav[aria-label='Primary']"))
            )
            return True
        except: 
            return False

    def login_to_x(self):
        driver = self.get_driver()
        wait = WebDriverWait(driver, 30)
        driver.get("https://x.com/i/flow/login")
        time.sleep(random.uniform(2, 3))
        
        # 1. Username - try multiple selectors
        username_input = None
        selectors = [
            (By.XPATH, "//input[@name='text']"),
            (By.XPATH, "//input[@autocomplete='username']"),
            (By.CSS_SELECTOR, "input[name='text']")
        ]
        
        for selector_type, selector_value in selectors:
            try:
                username_input = wait.until(EC.element_to_be_clickable((selector_type, selector_value)))
                break
            except:
                continue
        
        if not username_input:
            raise Exception("Could not find username input field")
        
        time.sleep(random.uniform(0.5, 1))
        self.human_type(username_input, self.USERNAME)
        time.sleep(random.uniform(0.5, 1))
        username_input.send_keys(Keys.ENTER)
        time.sleep(random.uniform(2, 3))
        
        # 2. Handle potential email/phone challenge
        try:
            challenge = wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[@data-testid='ocfEnterTextTextInput']"))
            )
            print("🛡️ Security Challenge: Entering Email/Phone...")
            time.sleep(random.uniform(1, 2))
            self.human_type(challenge, self.EMAIL_OR_PHONE)
            time.sleep(random.uniform(0.5, 1))
            challenge.send_keys(Keys.ENTER)
            time.sleep(random.uniform(2, 3))
        except TimeoutException:
            pass

        # 3. Password
        p = wait.until(EC.element_to_be_clickable((By.NAME, "password")))
        time.sleep(random.uniform(0.5, 1))
        self.human_type(p, self.PASSWORD)
        time.sleep(random.uniform(0.5, 1))
        p.send_keys(Keys.ENTER)
        
        # 4. Success check and cookie save
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "nav[aria-label='Primary']")))
        
        with open(self.COOKIE_FILE, "wb") as f:
            pickle.dump(driver.get_cookies(), f)
        print("✅ Login successful, cookies saved")

    def scrape_real_data(self, url, task_id):
        try:
            print(f"\n{'='*60}")
            print(f"🐦 Scraping: {url}")
            print(f"{'='*60}\n")
            
            driver = self.get_driver()
            
            # Load cookies or login
            if not self.load_cookies():
                print("⚠️ Cookie auth failed, logging in...")
                self.login_to_x()
                time.sleep(random.uniform(2, 3))
            
            # Navigate to tweet
            driver.get(url)
            time.sleep(random.uniform(3, 5))
            
            # Check for login redirect
            if "login" in driver.current_url:
                print("⚠️ Redirected to login, re-authenticating...")
                self.login_to_x()
                driver.get(url)
                time.sleep(random.uniform(3, 5))
            
            # Wait for tweet to load - try multiple strategies
            tweet_loaded = False
            wait_selectors = [
                (By.CSS_SELECTOR, "article[data-testid='tweet']"),
                (By.CSS_SELECTOR, "div[data-testid='tweetText']"),
                (By.TAG_NAME, "article")
            ]
            
            for selector_type, selector_value in wait_selectors:
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((selector_type, selector_value))
                    )
                    tweet_loaded = True
                    break
                except TimeoutException:
                    continue
            
            if not tweet_loaded:
                print("⚠️ Tweet failed to load")
            
            time.sleep(random.uniform(2, 4))
            
            # Extract tweet text
            tweet_text = ""
            text_strategies = [
                lambda: driver.find_element(By.CSS_SELECTOR, "div[data-testid='tweetText']").text,
                lambda: driver.find_element(By.CSS_SELECTOR, "article div[lang]").text,
                lambda: driver.title.split(" on X: \"")[1].split("\" / X")[0] if " on X: \"" in driver.title else None
            ]
            
            for strategy in text_strategies:
                try:
                    result = strategy()
                    if result:
                        tweet_text = result
                        print(f"✅ Text: {tweet_text[:50]}...")
                        break
                except:
                    continue
            
            # Extract engagement metrics
            engagement_metrics = {
                "likes": None,
                "retweets": None,
                "replies": None,
                "views": None
            }
            
            metrics_config = {
                "replies": "reply",
                "retweets": "retweet",
                "likes": "like"
            }
            
            for metric_name, testid in metrics_config.items():
                try:
                    elem = driver.find_element(By.CSS_SELECTOR, f"button[data-testid='{testid}']")
                    label = elem.get_attribute("aria-label") or ""
                    
                    # Extract number with K/M/B support
                    match = re.search(r'([\d,.]+)\s*([KMB])?', label)
                    if match:
                        num_str = match.group(1).replace(',', '')
                        multiplier_str = match.group(2)
                        
                        multiplier = 1
                        if multiplier_str == 'K':
                            multiplier = 1000
                        elif multiplier_str == 'M':
                            multiplier = 1000000
                        elif multiplier_str == 'B':
                            multiplier = 1000000000
                        
                        engagement_metrics[metric_name] = int(float(num_str) * multiplier)
                        print(f"✅ {metric_name.capitalize()}: {engagement_metrics[metric_name]}")
                except:
                    pass
            
            # Extract views
            try:
                view_elem = driver.find_element(By.CSS_SELECTOR, "a[href*='/analytics']")
                view_label = view_elem.get_attribute("aria-label") or view_elem.text or ""
                match = re.search(r'([\d,.]+)\s*([KMB])?', view_label)
                if match:
                    num_str = match.group(1).replace(',', '')
                    multiplier_str = match.group(2)
                    
                    multiplier = 1
                    if multiplier_str == 'K':
                        multiplier = 1000
                    elif multiplier_str == 'M':
                        multiplier = 1000000
                    
                    engagement_metrics["views"] = int(float(num_str) * multiplier)
                    print(f"✅ Views: {engagement_metrics['views']}")
            except:
                pass
            
            # Extract profile info
            profile_info = {"username": None, "display_name": None}
            
            try:
                # Display name
                name_elem = driver.find_element(By.CSS_SELECTOR, "article[data-testid='tweet'] div[dir='ltr'] span")
                profile_info["display_name"] = name_elem.text
                
                # Username
                handle_elem = driver.find_element(By.CSS_SELECTOR, "article[data-testid='tweet'] a[role='link']")
                href = handle_elem.get_attribute("href")
                if href and ("twitter.com/" in href or "x.com/" in href):
                    username = href.split('/')[-1]
                    if not username.startswith('status'):
                        profile_info["username"] = "@" + username
                
                print(f"✅ Profile: {profile_info['display_name']} ({profile_info['username']})")
            except:
                pass
            
            # Extract timestamp
            timestamp = None
            try:
                time_elem = driver.find_element(By.TAG_NAME, "time")
                timestamp = time_elem.get_attribute("datetime")
                print(f"✅ Timestamp: {timestamp}")
            except:
                pass
            
            # Extract tweet ID
            tweet_id = None
            try:
                tweet_id_match = re.search(r'/status/(\d+)', url)
                if tweet_id_match:
                    tweet_id = tweet_id_match.group(1)
            except:
                pass
            
            print(f"\n{'='*60}")
            print("✅ SCRAPING COMPLETED")
            print(f"{'='*60}\n")
            
            return {
                "status": "completed",
                "task_id": task_id,
                "tweet_info": {
                    "tweet_text": tweet_text,
                    "url": url,
                    "tweet_id": tweet_id
                },
                "engagement_metrics": engagement_metrics,
                "profile_info": profile_info,
                "timestamp": timestamp
            }
            
        except Exception as e:
            # Save screenshot on error
            try: 
                self._driver.save_screenshot(f"error_{task_id}.png")
                print(f"📸 Screenshot saved: error_{task_id}.png")
            except: 
                pass
            
            print(f"\n{'='*60}")
            print(f"❌ SCRAPER FAILED: {e}")
            print(f"{'='*60}\n")
            
            import traceback
            traceback.print_exc()
            
            return {
                "status": "failed",
                "error": str(e),
                "task_id": task_id
            }
    
    def close(self):
        """Clean up driver"""
        if self._driver:
            try:
                self._driver.quit()
            except:
                pass
            self._driver = None


# Example usage
if __name__ == "__main__":
    scraper = TwitterScraperEngine()
    
    try:
        url = "https://x.com/elonmusk/status/TWEET_ID_HERE"
        result = scraper.scrape_real_data(url, task_id="test_001")
        
        print("\nRESULT:")
        import json
        print(json.dumps(result, indent=2))
        
    finally:
        scraper.close()