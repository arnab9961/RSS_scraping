import asyncio
import sys
import os
from typing import Dict, Any
from dotenv import load_dotenv
import time
import traceback

# Load environment variables
load_dotenv()

async def test_reddit_credentials():
    """Test Reddit API credentials"""
    print("\n==== Testing Reddit API Credentials ====")
    
    try:
        import praw
        
        reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
        reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        reddit_user_agent = os.getenv("REDDIT_USER_AGENT", "NewsScraperBot/1.0")
        reddit_username = os.getenv("REDDIT_USERNAME")
        reddit_password = os.getenv("REDDIT_PASSWORD")
        
        # Check if credentials are set
        if not reddit_client_id or not reddit_client_secret:
            print("❌ Reddit API credentials not found in environment variables")
            return False
        
        print("ℹ️ Attempting to connect to Reddit API...")
        
        # Initialize Reddit client
        reddit = praw.Reddit(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            user_agent=reddit_user_agent,
            username=reddit_username,
            password=reddit_password
        )
        
        # Test connection by getting user info or subreddit
        if reddit_username and reddit_password:
            me = reddit.user.me()
            print(f"✅ Successfully authenticated as Reddit user: {me.name}")
        else:
            # Just try to access public data if no user credentials
            subreddit = reddit.subreddit("worldnews")
            print(f"✅ Successfully connected to Reddit API (read-only mode)")
            print(f"   Subreddit /r/worldnews has {subreddit.subscribers:,} subscribers")
        
        return True
    
    except Exception as e:
        print(f"❌ Reddit API test failed: {str(e)}")
        traceback.print_exc()
        return False

async def test_twitter_credentials():
    """Test Twitter/X API credentials"""
    print("\n==== Testing Twitter/X API Credentials ====")
    
    try:
        import tweepy
        
        twitter_api_key = os.getenv("TWITTER_API_KEY")
        twitter_api_secret = os.getenv("TWITTER_API_SECRET")
        twitter_access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        twitter_access_secret = os.getenv("TWITTER_ACCESS_SECRET")
        twitter_bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        
        # Check if credentials are set
        if not twitter_api_key or not twitter_api_secret:
            print("❌ Twitter API credentials not found in environment variables")
            return False
        
        print("ℹ️ Attempting to connect to Twitter API v1...")
        
        # Try v1 auth
        auth = tweepy.OAuth1UserHandler(
            twitter_api_key,
            twitter_api_secret,
            twitter_access_token,
            twitter_access_secret
        )
        api = tweepy.API(auth)
        
        # Test the connection
        user = api.verify_credentials()
        print(f"✅ Successfully authenticated with Twitter API v1 as: @{user.screen_name}")

        # Test v2 authentication if bearer token is available
        if twitter_bearer_token:
            print("ℹ️ Testing Twitter API v2 connection...")
            client = tweepy.Client(bearer_token=twitter_bearer_token)
            user = client.get_user(username="Twitter")
            print("✅ Successfully connected to Twitter API v2")
        
        return True
    
    except Exception as e:
        print(f"❌ Twitter API test failed: {str(e)}")
        traceback.print_exc()
        return False

async def test_telegram_credentials():
    """Test Telegram API credentials"""
    print("\n==== Testing Telegram API Credentials ====")
    
    try:
        from telethon import TelegramClient
        
        telegram_api_id = os.getenv("TELEGRAM_API_ID")
        telegram_api_hash = os.getenv("TELEGRAM_API_HASH")
        
        # Check if credentials are set
        if not telegram_api_id or not telegram_api_hash:
            print("❌ Telegram API credentials not found in environment variables")
            return False
        
        print("ℹ️ Attempting to connect to Telegram API...")
        
        # Initialize Telegram client
        client = TelegramClient("test_session", int(telegram_api_id), telegram_api_hash)
        
        # Start the client and test connection
        await client.start()
        
        if await client.is_user_authorized():
            me = await client.get_me()
            print(f"✅ Successfully authenticated with Telegram API as: {me.first_name}")
        else:
            print("✅ Connected to Telegram API (not logged in, but credentials work)")
            print("ℹ️ Note: You will need to log in to access certain features")
            
        await client.disconnect()
        return True
    
    except Exception as e:
        print(f"❌ Telegram API test failed: {str(e)}")
        traceback.print_exc()
        return False

async def test_rss_feeds():
    """Test RSS feed connections"""
    print("\n==== Testing RSS Feed Connections ====")
    
    try:
        import feedparser
        import httpx
        
        # Test feeds - a few common intelligence/news feeds
        test_feeds = {
            "Reuters": "https://www.reuters.com/world/rss.xml",
            "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
            "BBC": "http://feeds.bbci.co.uk/news/world/rss.xml",
        }
        
        results = {}
        
        async with httpx.AsyncClient() as client:
            for name, url in test_feeds.items():
                print(f"ℹ️ Testing feed: {name} ({url})")
                
                try:
                    response = await client.get(url, timeout=10.0)
                    response.raise_for_status()
                    
                    # Parse the feed
                    feed = feedparser.parse(response.text)
                    
                    if feed.bozo:
                        print(f"⚠️ Warning for {name}: {feed.bozo_exception}")
                    
                    if hasattr(feed, 'entries') and len(feed.entries) > 0:
                        print(f"✅ {name}: Found {len(feed.entries)} entries")
                        results[name] = True
                    else:
                        print(f"❌ {name}: No entries found")
                        results[name] = False
                
                except Exception as e:
                    print(f"❌ {name} failed: {str(e)}")
                    results[name] = False
        
        success = any(results.values())
        print(f"RSS Feed Test Summary: {sum(results.values())}/{len(results)} feeds working")
        return success
    
    except Exception as e:
        print(f"❌ RSS feed test failed: {str(e)}")
        traceback.print_exc()
        return False

async def test_google_alerts():
    """Test Google Alerts RSS feed"""
    print("\n==== Testing Google Alerts RSS Feed ====")
    
    try:
        import feedparser
        import httpx
        
        # Get Google Alerts feed if configured
        google_alert_url = os.getenv("GOOGLE_ALERT_URL")
        
        if not google_alert_url:
            print("ℹ️ No Google Alert URL found in environment variables, skipping test")
            return True  # Not a failure, just skipped
        
        print(f"ℹ️ Testing Google Alert feed: {google_alert_url}")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(google_alert_url, timeout=10.0)
                response.raise_for_status()
                
                # Parse the feed
                feed = feedparser.parse(response.text)
                
                if hasattr(feed, 'entries') and len(feed.entries) > 0:
                    print(f"✅ Google Alert: Found {len(feed.entries)} entries")
                    return True
                else:
                    print(f"❌ Google Alert: No entries found")
                    return False
                
            except Exception as e:
                print(f"❌ Google Alert test failed: {str(e)}")
                return False
    
    except Exception as e:
        print(f"❌ Google Alert test failed: {str(e)}")
        traceback.print_exc()
        return False

async def test_network_connectivity():
    """Test network connectivity to all required services"""
    print("\n==== Testing Network Connectivity ====")
    
    services = {
        "Reddit": "https://www.reddit.com",
        "Twitter": "https://twitter.com",
        "Telegram": "https://telegram.org",
        "Reuters": "https://www.reuters.com",
        "Al Jazeera": "https://www.aljazeera.com",
        "Google": "https://www.google.com"
    }
    
    results = {}
    
    try:
        import httpx
        
        async with httpx.AsyncClient() as client:
            for name, url in services.items():
                try:
                    print(f"ℹ️ Testing connectivity to {name}...")
                    response = await client.get(url, timeout=5.0)
                    response.raise_for_status()
                    print(f"✅ {name} is accessible (HTTP {response.status_code})")
                    results[name] = True
                except Exception as e:
                    print(f"❌ Cannot connect to {name}: {str(e)}")
                    results[name] = False
        
        success_rate = sum(results.values()) / len(results) if results else 0
        print(f"Connectivity Test Summary: {sum(results.values())}/{len(results)} services reachable")
        return success_rate > 0.75  # Pass if more than 75% of services are reachable
    
    except Exception as e:
        print(f"❌ Connectivity test failed: {str(e)}")
        traceback.print_exc()
        return False

async def test_fastapi_dependencies():
    """Test FastAPI and related dependencies"""
    print("\n==== Testing FastAPI Dependencies ====")
    
    try:
        import fastapi
        import uvicorn
        import pydantic
        
        print(f"✅ FastAPI v{fastapi.__version__} is installed")
        print(f"✅ Uvicorn is installed")
        print(f"✅ Pydantic v{pydantic.__version__} is installed")
        
        return True
    
    except ImportError as e:
        print(f"❌ Missing dependency: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Dependency check failed: {str(e)}")
        traceback.print_exc()
        return False

async def main():
    """Run all tests and report summary"""
    start_time = time.time()
    print("======================================")
    print("     News Scraper Environment Test    ")
    print("======================================")
    
    # Run all tests
    tests = {
        "Network Connectivity": await test_network_connectivity(),
        "FastAPI Dependencies": await test_fastapi_dependencies(),
        "RSS Feeds": await test_rss_feeds(),
        "Google Alerts": await test_google_alerts(),
        "Reddit API": await test_reddit_credentials(),
        "Twitter/X API": await test_twitter_credentials(),
        "Telegram API": await test_telegram_credentials()
    }
    
    # Print summary
    print("\n======================================")
    print("             Test Summary             ")
    print("======================================")
    
    for name, passed in tests.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    # Overall result
    passed_tests = sum(tests.values())
    total_tests = len(tests)
    
    print("\n======================================")
    print(f"Passed {passed_tests}/{total_tests} tests")
    
    # Environment summary
    print("\nEnvironment Summary:")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Operating System: {sys.platform}")
    print(f"Test Duration: {time.time() - start_time:.2f} seconds")
    print("======================================")
    
    # Return code based on success/failure
    return 0 if passed_tests == total_tests else 1

if __name__ == "__main__":
    # Run the async main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)