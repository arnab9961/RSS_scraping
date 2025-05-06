import feedparser
import asyncio
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import time
import re

from app.config.config import settings

# Simple cache implementation
_cache = {}
_cache_timestamps = {}

async def fetch_feed(url: str, use_cache: bool = True) -> List[Dict[str, Any]]:
    """
    Fetch and parse a single RSS feed
    
    Args:
        url: RSS feed URL
        use_cache: Whether to use cached results if available
        
    Returns:
        List of articles from the feed
    """
    # Check cache first if enabled
    if use_cache and url in _cache and url in _cache_timestamps:
        cache_time = _cache_timestamps[url]
        if time.time() - cache_time < settings.CACHE_TTL:
            return _cache[url]
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            
        # Parse the feed with feedparser
        feed = feedparser.parse(response.text)
        
        articles = []
        for entry in feed.entries[:20]:  # Limit to 20 most recent articles
            published_date = entry.get('published_parsed') or entry.get('updated_parsed')
            if published_date:
                published = datetime(*published_date[:6]).isoformat()
            else:
                published = datetime.now().isoformat()
                
            article = {
                "title": entry.get("title", "No title"),
                "link": entry.get("link", ""),
                "published": published,
                "summary": entry.get("summary", entry.get("description", "No summary")),
                "source": feed.feed.get("title", url),
                "feed_url": url,
                "id": entry.get("id", entry.get("link", "")),
                "source_type": "rss"
            }
            articles.append(article)
        
        # Update cache
        _cache[url] = articles
        _cache_timestamps[url] = time.time()
        
        return articles
    except Exception as e:
        print(f"Error fetching feed {url}: {str(e)}")
        # Return cached version if available, even if expired
        if url in _cache:
            return _cache[url]
        return []

async def fetch_all_feeds(feed_urls: Optional[Dict[str, str]] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch multiple RSS feeds in parallel
    
    Args:
        feed_urls: Dictionary of feed names and URLs, defaults to settings.RSS_FEEDS
        
    Returns:
        Dictionary with feed names as keys and list of articles as values
    """
    if feed_urls is None:
        feed_urls = settings.RSS_FEEDS
    
    tasks = {name: fetch_feed(url) for name, url in feed_urls.items()}
    results = {}
    
    for name, task in tasks.items():
        results[name] = await task
    
    return results

async def fetch_google_alerts(use_cache: bool = True) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch Google Alerts RSS feeds with enhanced metadata extraction for BlackGlass
    
    Args:
        use_cache: Whether to use cached results if available
        
    Returns:
        Dictionary with alert names as keys and lists of articles as values
    """
    results = {}
    errors = {}
    
    # Validate if Google Alerts are configured
    if not hasattr(settings, 'GOOGLE_ALERTS') or not settings.GOOGLE_ALERTS:
        print("Warning: No Google Alerts configured in settings")
        return {}
    
    for alert_name, feed_url in settings.GOOGLE_ALERTS.items():
        try:
            # Fetch the alert feed
            articles = await fetch_feed(feed_url, use_cache=use_cache)
            
            if not articles:
                print(f"Warning: No articles found for Google Alert '{alert_name}'")
                results[alert_name] = []
                continue
            
            # Process Google Alert specific data
            for article in articles:
                # Add source type and alert name
                article["source_type"] = "google_alert"
                article["alert_name"] = alert_name
                
                # Extract publisher if available (Google Alerts often include this in the title)
                if " - " in article["title"]:
                    title_parts = article["title"].split(" - ")
                    article["publisher"] = title_parts[-1]
                    # Clean up the title (remove publisher suffix for cleaner display)
                    if len(title_parts) > 1:
                        article["original_title"] = article["title"]
                        article["title"] = " - ".join(title_parts[:-1])
                
                # Extract location data if available
                locations = extract_locations(article["summary"])
                if locations:
                    article["extracted_locations"] = locations
                
                # Extract companies/organizations if mentioned
                organizations = extract_organizations(article["summary"] + " " + article["title"])
                if organizations:
                    article["extracted_organizations"] = organizations
                
                # Add confidence score for the alert relevance
                article["alert_confidence"] = calculate_alert_confidence(article, alert_name)
                
                # Add BlackGlass specific metadata
                article["blackglass_metadata"] = {
                    "source_credibility": determine_source_credibility(article.get("publisher", "")),
                    "intelligence_category": determine_intelligence_category(article["title"], article["summary"]),
                    "processing_timestamp": datetime.now().isoformat()
                }
            
            results[alert_name] = articles
        except Exception as e:
            error_msg = f"Error fetching Google Alert '{alert_name}': {str(e)}"
            print(error_msg)
            errors[alert_name] = error_msg
            results[alert_name] = []
    
    # Add error information to the results
    if errors:
        results["_errors"] = errors
    
    return results

def extract_locations(text: str) -> List[str]:
    """Extract potential location names from text"""
    # This is a simplified version - in production, consider using NLP libraries
    common_locations = [
        "afghanistan", "africa", "albania", "algeria", "america", "argentina", "asia", "australia", 
        "bangladesh", "belarus", "belgium", "brazil", "bulgaria", "canada", "china", "colombia",
        "denmark", "egypt", "europe", "france", "germany", "greece", "hong kong", "hungary", "india",
        "indonesia", "iran", "iraq", "ireland", "israel", "italy", "japan", "kazakhstan", "kenya",
        "korea", "kuwait", "latvia", "libya", "malaysia", "mexico", "middle east", "morocco",
        "netherlands", "new zealand", "nigeria", "norway", "pakistan", "palestine", "philippines",
        "poland", "portugal", "qatar", "romania", "russia", "saudi arabia", "serbia", "singapore",
        "south africa", "spain", "sweden", "switzerland", "syria", "taiwan", "thailand", "turkey",
        "ukraine", "united kingdom", "uk", "united states", "usa", "venezuela", "vietnam", "yemen"
    ]
    
    found_locations = []
    text_lower = text.lower()
    
    for location in common_locations:
        if location in text_lower:
            found_locations.append(location)
    
    return found_locations

def extract_organizations(text: str) -> List[str]:
    """Extract potential organization names from text"""
    # This is a simplified version - in production, consider using NLP libraries
    common_organizations = [
        "google", "microsoft", "apple", "amazon", "facebook", "meta", "twitter", "tesla", "ibm", 
        "intel", "cisco", "huawei", "samsung", "sony", "nokia", "ericsson", "oracle", "sap", 
        "alibaba", "tencent", "baidu", "xiaomi", "lenovo", "dell", "hp", "nato", "un", "who", 
        "world bank", "imf", "wto", "european union", "eu", "opec", "fbi", "cia", "nsa", "gchq", 
        "fsb", "pentagon", "white house", "kremlin", "congress", "senate", "parliament"
    ]
    
    found_organizations = []
    text_lower = text.lower()
    
    for org in common_organizations:
        if org in text_lower:
            found_organizations.append(org)
    
    return found_organizations

def determine_source_credibility(source: str) -> str:
    """Determine the credibility of a source for BlackGlass intelligence analysis"""
    high_credibility = ["reuters", "bbc", "economist", "time", "bloomberg", "associated press", "ap", 
                       "wall street journal", "wsj", "washington post", "new york times", "nyt", 
                       "financial times", "ft"]
    
    medium_credibility = ["cnn", "fox", "aljazeera", "the guardian", "the hill", "politico", 
                         "usa today", "business insider", "forbes", "zdnet", "techcrunch"]
    
    source_lower = source.lower()
    
    if any(source in source_lower for source in high_credibility):
        return "high"
    elif any(source in source_lower for source in medium_credibility):
        return "medium"
    else:
        return "standard"

def determine_intelligence_category(title: str, summary: str) -> List[str]:
    """Categorize intelligence content for BlackGlass platform"""
    combined_text = (title + " " + summary).lower()
    categories = []
    
    # Cybersecurity
    if any(term in combined_text for term in ["cyber", "hack", "malware", "ransomware", "phishing", 
                                            "data breach", "vulnerability", "exploit"]):
        categories.append("cybersecurity")
    
    # Geopolitical
    if any(term in combined_text for term in ["government", "election", "president", "minister", 
                                            "military", "war", "conflict", "treaty", "summit", 
                                            "diplomatic", "embassy", "sanction"]):
        categories.append("geopolitical")
    
    # Economic
    if any(term in combined_text for term in ["economy", "market", "stock", "finance", "bank", 
                                            "inflation", "trade", "investment", "currency", "gdp"]):
        categories.append("economic")
    
    # Infrastructure
    if any(term in combined_text for term in ["infrastructure", "power grid", "pipeline", "telecom", 
                                            "network", "bridge", "airport", "railway", "energy"]):
        categories.append("infrastructure")
    
    # If no specific category is identified
    if not categories:
        categories.append("general")
    
    return categories

def calculate_alert_confidence(article: Dict[str, Any], alert_name: str) -> int:
    """Calculate confidence score for the Google Alert relevance"""
    score = 70  # Base score
    
    # Boost score based on title relevance
    if alert_name.lower() in article["title"].lower():
        score += 15
    
    # Consider credibility of source
    publisher = article.get("publisher", "")
    if publisher:
        if determine_source_credibility(publisher) == "high":
            score += 10
        elif determine_source_credibility(publisher) == "medium":
            score += 5
    
    # Penalize for generic or vague content
    summary_length = len(article["summary"])
    if summary_length < 100:
        score -= 5
    
    return min(100, max(0, score))  # Ensure score is between 0-100

async def search_feeds(query: str, limit: int = 20, include_alerts: bool = True, location: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Enhanced search for articles across all RSS feeds and Google Alerts for BlackGlass
    
    Args:
        query: Search term or keywords
        limit: Maximum number of results
        include_alerts: Whether to include Google Alerts
        location: Optional geographic location filter
        
    Returns:
        List of articles matching the query with relevance scores
    """
    # Get articles from regular feeds
    all_feeds = await fetch_all_feeds()
    
    # Flatten all articles
    all_articles = []
    for source, articles in all_feeds.items():
        for article in articles:
            article["source_name"] = source
            all_articles.append(article)
    
    # Get Google Alerts if requested
    if include_alerts:
        alerts = await fetch_google_alerts()
        for alert_name, articles in alerts.items():
            for article in articles:
                article["source_name"] = f"alert_{alert_name}"
                all_articles.append(article)
    
    # Parse keywords
    keywords = query.lower().split()
    
    # Filter and score articles
    matching_articles = []
    for article in all_articles:
        article_text = (article["title"].lower() + " " + article["summary"].lower())
        
        # Check if any keyword matches
        keywords_matched = [kw for kw in keywords if kw in article_text]
        
        # Skip if no keywords match
        if not keywords_matched:
            continue
            
        # Check location match if provided
        location_match = False
        if location:
            location_match = location.lower() in article_text
            
            # If location is specified but not found, lower priority significantly
            if not location_match and location.lower() not in query.lower():
                continue
        
        # Store matching information
        article["keywords_matched"] = keywords_matched
        article["location_match"] = location_match if location else None
        
        # Calculate relevance score
        # Base score on number of keywords matched
        keyword_matches = len(keywords_matched)
        keyword_score = keyword_matches / len(keywords) if keywords else 0
        
        # Boost based on location match
        location_boost = 0.2 if location_match else 0
        
        # Consider source credibility 
        source_boost = 0
        high_credibility_sources = ["reuters", "bbc", "economist", "stratfor", "foreignpolicy", "janes"]
        medium_credibility_sources = ["aljazeera", "cnn"]
        
        if any(s in article["source"].lower() for s in high_credibility_sources):
            source_boost = 0.15
        elif any(s in article["source"].lower() for s in medium_credibility_sources):
            source_boost = 0.10
            
        # Boost recent articles
        try:
            published = datetime.fromisoformat(article["published"])
            now = datetime.now(published.tzinfo) if published.tzinfo else datetime.now()
            days_old = (now - published).days
            recency_score = max(0, 1 - (days_old / 7))  # Higher score for newer articles
        except (ValueError, TypeError):
            recency_score = 0.5  # Default if date parsing fails
            
        # Calculate final relevance (0-100 scale)
        article["relevance_score"] = int((keyword_score * 0.5 + location_boost + source_boost + recency_score * 0.15) * 100)
        
        matching_articles.append(article)
    
    # Sort by relevance score (highest first)
    matching_articles.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    return matching_articles[:limit]

async def get_latest_intel_news(include_alerts: bool = True) -> List[Dict[str, Any]]:
    """
    Get latest intelligence news from all feeds including Google Alerts
    
    Args:
        include_alerts: Whether to include Google Alerts
        
    Returns:
        Combined and sorted list of recent articles
    """
    # Get news from regular RSS feeds
    all_feeds = await fetch_all_feeds()
    
    # Flatten all articles
    all_articles = []
    for source, articles in all_feeds.items():
        all_articles.extend(articles)
    
    # Get Google Alerts if requested
    if include_alerts:
        alerts = await fetch_google_alerts()
        for alert_name, articles in alerts.items():
            all_articles.extend(articles)
    
    # Sort by date (most recent first)
    all_articles.sort(
        key=lambda x: x["published"], 
        reverse=True
    )
    
    return all_articles[:50]  # Return top 50 most recent