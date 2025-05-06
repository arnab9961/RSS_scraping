import os
from dotenv import load_dotenv
from typing import Dict, List, Any

# Load environment variables
load_dotenv()

class Settings:
    # API Configuration
    API_NAME = "News Scraper API"
    API_VERSION = "1.0.0"
    API_DESCRIPTION = "API for scraping news from RSS sources"
    
    # Intelligence-related RSS feeds
    RSS_FEEDS = {
        "reuters": "https://www.reuters.com/world/rss.xml",
        "aljazeera": "https://www.aljazeera.com/xml/rss/all.xml",
        "foreignpolicy": "https://foreignpolicy.com/feed/",
        "stratfor": "https://worldview.stratfor.com/rss.xml",
        "economist": "https://www.economist.com/international/rss.xml",
        "bbc_world": "http://feeds.bbci.co.uk/news/world/rss.xml",
        "cnn_world": "http://rss.cnn.com/rss/edition_world.rss",
        "cfr": "https://www.cfr.org/rss.xml",
        "war_on_rocks": "https://warontherocks.com/feed/",
        "defense_one": "https://www.defenseone.com/rss/",
        "jane_defense": "https://www.janes.com/feeds/news"
    }
    
    # Google Alerts RSS feeds
    GOOGLE_ALERTS = {
        "intelligence_news": "https://www.google.com/alerts/feeds/09607098981934978130/464922632354509776"
        # Add additional alerts as needed
    }
    
    # Cache settings
    CACHE_TTL = 3600  # 1 hour cache for feeds
    
    # Rate limiting
    RATE_LIMIT = 100  # requests per minute

settings = Settings()