# Test script to verify Instaloader session and download
import instaloader
import os
import sys

IG_USERNAME = "epicmemeoclock"
IG_PASSWORD = "S@p<3f4ever2025!"

def test_download():
    print("=" * 50)
    print("Testing Instaloader login and download...")
    print("=" * 50)
    
    loader = instaloader.Instaloader(
        download_videos=True,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        post_metadata_txt_pattern=""
    )
    
    session_file = os.path.join(os.path.dirname(__file__), f"session-{IG_USERNAME}")
    
    # Always try fresh login first
    print(f"\n[LOGIN] Logging in as {IG_USERNAME}...")
    try:
        loader.login(IG_USERNAME, IG_PASSWORD)
        print("[OK] Login successful!")
        
        # Save session for future use
        loader.save_session_to_file(session_file)
        print(f"[OK] Session saved to {session_file}")
    except instaloader.exceptions.TwoFactorAuthRequiredException as e:
        print(f"[ERROR] Two-factor auth required!")
        print("Please disable 2FA or use app-specific password")
        return False
    except instaloader.exceptions.BadCredentialsException as e:
        print(f"[ERROR] Bad credentials! Check username/password")
        return False
    except instaloader.exceptions.ConnectionException as e:
        print(f"[ERROR] Connection error: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Login error: {type(e).__name__}: {e}")
        return False
    
    # Test download a single reel
    test_url = "https://www.instagram.com/couple4infiny/reel/DTNlHdaDL13/"
    shortcode = test_url.rstrip('/').split('/')[-1]
    
    print(f"\n[DOWNLOAD] Testing download of reel: {shortcode}")
    
    try:
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        print(f"   Found post by: @{post.owner_username}")
        print(f"   Likes: {post.likes}")
        print(f"   Is Video: {post.is_video}")
        
        # Actually download
        target = os.path.join(os.path.dirname(__file__), "..", "downloaded_reels", "test")
        os.makedirs(target, exist_ok=True)
        loader.download_post(post, target=target)
        print(f"\n[OK] Downloaded successfully to: {target}")
        return True
        
    except instaloader.exceptions.LoginRequiredException as e:
        print(f"[ERROR] Login required (session expired?): {e}")
        return False
    except instaloader.exceptions.QueryReturnedNotFoundException as e:
        print(f"[ERROR] Post not found: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Download error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_download()
    print("\n" + "=" * 50)
    if success:
        print("TEST PASSED! Downloads are working.")
    else:
        print("TEST FAILED! See errors above.")
    print("=" * 50)
    sys.exit(0 if success else 1)
