# Flask backend for Instagram Reel Downloader
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import instaloader
import os
import threading
import uuid
import time
import re
import pandas as pd

app = Flask(__name__)
CORS(app)

# Store download progress
download_tasks = {}

# Use hardcoded absolute path to avoid any unicode conversion issues
DOWNLOAD_FOLDER = r"F:\Sandy\S+Study\CODING\insta_reel_down\downloaded_reels"

# Ensure download folder exists
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
print(f"Download folder: {DOWNLOAD_FOLDER}")

# Instagram credentials (from user's original fetch.py)
IG_USERNAME = "epicmemeoclock"
IG_PASSWORD = "S@p<3f4ever2025!"

# Global Instaloader instance with login (initialized once at startup)
GLOBAL_LOADER = None

def get_logged_in_loader():
    """Get or create a logged-in Instaloader instance"""
    global GLOBAL_LOADER
    
    if GLOBAL_LOADER is not None:
        return GLOBAL_LOADER
    
    print("🔑 Initializing Instaloader with login...")
    loader = instaloader.Instaloader(
        download_videos=True,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        post_metadata_txt_pattern=""
    )
    
    # Try loading existing session first
    session_file = os.path.join(os.path.dirname(__file__), f"session-{IG_USERNAME}")
    try:
        loader.load_session_from_file(IG_USERNAME, session_file)
        print(f"✅ Loaded existing session for {IG_USERNAME}")
        GLOBAL_LOADER = loader
        return loader
    except Exception as e:
        print(f"⚠️ No existing session found: {e}")
    
    # Login fresh
    try:
        print(f"🔐 Logging in as {IG_USERNAME}...")
        loader.login(IG_USERNAME, IG_PASSWORD)
        print("✅ Login successful!")
        
        # Save session for future use
        loader.save_session_to_file(session_file)
        print(f"💾 Session saved to {session_file}")
        
        GLOBAL_LOADER = loader
        return loader
    except instaloader.exceptions.TwoFactorAuthRequiredException:
        print("❌ Two-factor authentication required! Please run insta_reel.py manually first to login.")
        return None
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return None

def extract_shortcode(url):
    """Extract shortcode from Instagram reel URL"""
    if not url:
        return None
    
    # Clean the URL first
    url = url.strip()
    
    # Use the same method as original script: split("/")[-2]
    try:
        if '/reel/' in url or '/p/' in url:
            parts = url.rstrip('/').split('/')
            shortcode = parts[-1] if parts[-1] else parts[-2]
            print(f"Extracted shortcode: {shortcode} from URL: {url}")
            return shortcode
    except:
        pass
    
    # Fallback to regex
    patterns = [
        r'instagram\.com/reel/([A-Za-z0-9_-]+)',
        r'instagram\.com/p/([A-Za-z0-9_-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            shortcode = match.group(1)
            print(f"Extracted shortcode: {shortcode} from URL: {url}")
            return shortcode
    
    print(f"Failed to extract shortcode from URL: {url}")
    return None

def extract_username_from_profile(url):
    """Extract username from profile URL like instagram.com/username/reels/"""
    patterns = [
        r'instagram\.com/([A-Za-z0-9_.]+)/reels/?',
        r'instagram\.com/([A-Za-z0-9_.]+)/?$',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            username = match.group(1)
            if username not in ['reel', 'p', 'stories', 'explore', 'accounts', 'direct']:
                return username
    return None

def is_profile_url(url):
    """Check if URL is a profile URL (not a direct reel/post URL)"""
    return extract_username_from_profile(url) is not None and extract_shortcode(url) is None

def fetch_reels_from_profile(username, max_reels=300, task_id=None):
    """Fetch reel links from a profile using Selenium WITH LOGIN"""
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.keys import Keys
    
    if task_id:
        download_tasks[task_id]['status'] = f'Logging into Instagram...'
    
    options = Options()
    options.add_argument("--headless=new")  # Headless mode - no visible browser
    options.add_argument("--window-size=1200,800")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)
    
    try:
        # Login to Instagram first
        print(f"Logging into Instagram as {IG_USERNAME}...")
        driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(5)
        
        # Enter credentials
        driver.find_element(By.NAME, "username").send_keys(IG_USERNAME)
        driver.find_element(By.NAME, "password").send_keys(IG_PASSWORD)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(6)
        
        # Handle "Save your login info" popup
        try:
            driver.find_element(By.XPATH, "//button[contains(text(), 'Not Now')]").click()
            time.sleep(3)
        except:
            pass
        
        # Handle "Turn on notifications" popup
        try:
            driver.find_element(By.XPATH, "//button[contains(text(), 'Not Now')]").click()
            time.sleep(3)
        except:
            pass
        
        if task_id:
            download_tasks[task_id]['status'] = f'Fetching reels from @{username}...'
        
        # Go to /reels/ tab
        print(f"Navigating to https://www.instagram.com/{username}/reels/")
        driver.get(f"https://www.instagram.com/{username}/reels/")
        time.sleep(5)
        
        reel_links = set()
        scrolls = 0
        max_scrolls = 150  # Increased to allow fetching 300+ reels
        SCROLL_PAUSE = 2.5  # Slightly longer pause to let content load
        no_new_count = 0  # Track consecutive scrolls with no new reels

        while len(reel_links) < max_reels and scrolls < max_scrolls:
            anchors = driver.find_elements(By.XPATH, "//a[contains(@href, '/reel/')]")
            old_count = len(reel_links)
            
            for a in anchors:
                href = a.get_attribute("href")
                if href and "/reel/" in href:
                    reel_links.add(href)
                    if len(reel_links) >= max_reels:
                        break
            
            new_found = len(reel_links) - old_count
            print(f"Scroll {scrolls + 1}: Found {len(reel_links)} reels (+{new_found})")
            
            if task_id:
                download_tasks[task_id]['status'] = f'Found {len(reel_links)} reels from @{username}...'

            # Scroll to load more
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
            time.sleep(SCROLL_PAUSE)
            scrolls += 1
            
            # Check if we stopped getting new reels (wait for 5 consecutive empty scrolls)
            if new_found == 0:
                no_new_count += 1
                if no_new_count >= 5:
                    print(f"No new reels for {no_new_count} scrolls, assuming end reached")
                    break
            else:
                no_new_count = 0  # Reset counter when we find new reels

        result_links = list(reel_links)
        print(f"Total reels found: {len(result_links)}")
        
        # Save to Excel like original script
        if result_links:
            excel_path = os.path.join(DOWNLOAD_FOLDER, f"{username}_reels.xlsx")
            df = pd.DataFrame(result_links, columns=["Reel URL"])
            df.to_excel(excel_path, index=False)
            print(f"Saved reel links to: {excel_path}")
        
        return result_links
        
    except Exception as e:
        print(f"Error fetching reels: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        driver.quit()

def download_reel_task(task_id, urls, is_profile=False, max_reels=300):
    """Background task to download reels"""
    
    # If it's a profile URL, first fetch all reel links
    if is_profile and len(urls) == 1:
        username = extract_username_from_profile(urls[0])
        if username:
            download_tasks[task_id]['status'] = f'Fetching reels from @{username}...'
            download_tasks[task_id]['mode'] = 'profile'
            download_tasks[task_id]['username'] = username
            
            fetched_urls = fetch_reels_from_profile(username, max_reels, task_id)
            
            if not fetched_urls:
                download_tasks[task_id]['status'] = 'completed'
                download_tasks[task_id]['results'] = [{
                    'url': urls[0],
                    'success': False,
                    'error': f'Could not fetch reels from @{username}. Check login credentials or try again.'
                }]
                download_tasks[task_id]['completed_at'] = time.time()
                return
            
            urls = fetched_urls
            download_tasks[task_id]['total'] = len(urls)
            download_tasks[task_id]['fetched_count'] = len(urls)
    
    # Get the logged-in loader
    download_tasks[task_id]['status'] = 'Preparing Instagram connection...'
    loader = get_logged_in_loader()
    
    if loader is None:
        download_tasks[task_id]['status'] = 'completed'
        download_tasks[task_id]['results'] = [{
            'url': 'N/A',
            'success': False,
            'error': 'Failed to login to Instagram. Check credentials or run manual login first.'
        }]
        download_tasks[task_id]['completed_at'] = time.time()
        return
    
    results = []
    total = len(urls)
    
    for idx, url in enumerate(urls):
        download_tasks[task_id]['current'] = idx + 1
        download_tasks[task_id]['status'] = f"Downloading {idx + 1}/{total}"
        
        shortcode = extract_shortcode(url)
        if not shortcode:
            print(f"INVALID URL: {repr(url)}")
            results.append({
                'url': url,
                'success': False,
                'error': f'Invalid URL format - could not extract shortcode'
            })
            continue
            
        try:
            print(f"Downloading shortcode: {shortcode}")
            post = instaloader.Post.from_shortcode(loader.context, shortcode)
            target_folder = os.path.join(DOWNLOAD_FOLDER, task_id)
            os.makedirs(target_folder, exist_ok=True)
            loader.download_post(post, target=target_folder)
            
            results.append({
                'url': url,
                'success': True,
                'shortcode': shortcode
            })
            print(f"✅ Downloaded: {shortcode}")
        except Exception as e:
            print(f"❌ Download error for {shortcode}: {e}")
            results.append({
                'url': url,
                'success': False,
                'error': str(e)
            })
        
        # Small delay between downloads to avoid rate limiting
        time.sleep(1)
    
    download_tasks[task_id]['status'] = 'completed'
    download_tasks[task_id]['results'] = results
    download_tasks[task_id]['completed_at'] = time.time()
    
    success_count = len([r for r in results if r['success']])
    print(f"\n🎉 Download complete! {success_count}/{total} reels downloaded successfully.")

@app.route('/')
def index():
    """Serve the UI"""
    return render_template('index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Reel Downloader API is running'})

@app.route('/api/download', methods=['POST'])
def start_download():
    """Start downloading reels from provided URLs"""
    data = request.get_json()
    urls = data.get('urls', [])
    max_reels = data.get('maxReels', 300)
    
    if not urls:
        return jsonify({'error': 'No URLs provided'}), 400
    
    clean_urls = [url.strip() for url in urls if url.strip()]
    
    if not clean_urls:
        return jsonify({'error': 'No valid URLs provided'}), 400
    
    is_profile = len(clean_urls) == 1 and is_profile_url(clean_urls[0])
    
    task_id = str(uuid.uuid4())[:8]
    download_tasks[task_id] = {
        'id': task_id,
        'total': len(clean_urls) if not is_profile else 0,
        'current': 0,
        'status': 'starting',
        'mode': 'profile' if is_profile else 'direct',
        'results': [],
        'created_at': time.time()
    }
    
    if is_profile:
        username = extract_username_from_profile(clean_urls[0])
        download_tasks[task_id]['username'] = username
        download_tasks[task_id]['status'] = f'Preparing to fetch reels from @{username}...'
    
    thread = threading.Thread(target=download_reel_task, args=(task_id, clean_urls, is_profile, max_reels))
    thread.daemon = True
    thread.start()
    
    response_msg = f'Started fetching and downloading reels from profile' if is_profile else f'Started downloading {len(clean_urls)} reel(s)'
    
    return jsonify({
        'task_id': task_id,
        'message': response_msg,
        'total': len(clean_urls),
        'mode': 'profile' if is_profile else 'direct'
    })

@app.route('/api/download/<task_id>', methods=['GET'])
def get_download_status(task_id):
    """Get status of a download task"""
    if task_id not in download_tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    task = download_tasks[task_id]
    return jsonify(task)

@app.route('/api/validate', methods=['POST'])
def validate_url():
    """Validate if a URL is a valid Instagram reel or profile URL"""
    data = request.get_json()
    url = data.get('url', '')
    
    shortcode = extract_shortcode(url)
    if shortcode:
        return jsonify({'valid': True, 'type': 'reel', 'shortcode': shortcode})
    
    username = extract_username_from_profile(url)
    if username:
        return jsonify({'valid': True, 'type': 'profile', 'username': username})
    
    return jsonify({'valid': False, 'error': 'Invalid Instagram URL.'})

@app.route('/api/files/<task_id>', methods=['GET'])
def list_downloaded_files(task_id):
    """List downloaded files for a task"""
    folder = os.path.join(DOWNLOAD_FOLDER, task_id)
    if not os.path.exists(folder):
        return jsonify({'files': []})
    
    files = []
    for f in os.listdir(folder):
        if f.endswith('.mp4'):
            files.append({
                'name': f,
                'path': os.path.join(folder, f),
                'size': os.path.getsize(os.path.join(folder, f))
            })
    
    return jsonify({'files': files})

if __name__ == '__main__':
    print("🚀 Starting Instagram Reel Downloader API...")
    print(f"📁 Downloads will be saved to: {DOWNLOAD_FOLDER}")
    print("📌 Supported URL formats:")
    print("   - Direct reel: https://instagram.com/reel/ABC123...")
    print("   - Profile reels: https://instagram.com/username/reels/")
    print(f"🔑 Using Instagram account: {IG_USERNAME}")
    print()
    
    # Pre-login to Instaloader at startup
    print("⏳ Pre-logging in to Instagram (first request will be faster)...")
    get_logged_in_loader()
    print()
    
    app.run(host='0.0.0.0', port=5000, debug=True)
