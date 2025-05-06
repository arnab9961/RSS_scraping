# import tweepy
# import asyncio
# from datetime import datetime, timezone
# from typing import List, Dict, Any, Optional
# import re

# from app.config.config import settings

# # Twitter API client (v1 for more comprehensive access)
# def get_twitter_api_v1():
#     """Get Twitter API v1 client"""
#     auth = tweepy.OAuth1UserHandler(
#         settings.TWITTER_API_KEY,
#         settings.TWITTER_API_SECRET,
#         settings.TWITTER_ACCESS_TOKEN,
#         settings.TWITTER_ACCESS_SECRET
#     )
#     return tweepy.API(auth)

# # Twitter API client (v2 for newer features)
# def get_twitter_api_v2():
#     """Get Twitter API v2 client"""
#     return tweepy.Client(
#         bearer_token=settings.TWITTER_BEARER_TOKEN,
#         consumer_key=settings.TWITTER_API_KEY,
#         consumer_secret=settings.TWITTER_API_SECRET,
#         access_token=settings.TWITTER_ACCESS_TOKEN,
#         access_token_secret=settings.TWITTER_ACCESS_SECRET
#     )

# def format_tweet(tweet) -> Dict[str, Any]:
#     """
#     Format tweet data into a standardized format
    
#     Args:
#         tweet: Tweet object from tweepy
        
#     Returns:
#         Dictionary with formatted tweet data
#     """
#     # Extract user data
#     user = tweet.user if hasattr(tweet, 'user') else None
#     user_data = {}
#     if user:
#         user_data = {
#             "id": user.id_str,
#             "username": user.screen_name,
#             "display_name": user.name,
#             "verified": user.verified,
#             "followers_count": user.followers_count,
#             "profile_image_url": user.profile_image_url_https
#         }
    
#     # Extract tweet media
#     media_data = []
#     if hasattr(tweet, 'entities') and 'media' in tweet.entities:
#         for media in tweet.entities['media']:
#             media_item = {
#                 "media_url": media.get('media_url_https', ''),
#                 "type": media.get('type', 'photo'),
#                 "width": media.get('sizes', {}).get('large', {}).get('w', 0),
#                 "height": media.get('sizes', {}).get('large', {}).get('h', 0)
#             }
#             media_data.append(media_item)
    
#     # Format the tweet
#     tweet_data = {
#         "id": tweet.id_str,
#         "text": tweet.full_text if hasattr(tweet, 'full_text') else tweet.text,
#         "created_at": tweet.created_at.replace(tzinfo=timezone.utc).isoformat(),
#         "url": f"https://twitter.com/{user.screen_name if user else 'twitter'}/status/{tweet.id_str}",
#         "source_type": "twitter",
#         "retweet_count": tweet.retweet_count,
#         "favorite_count": tweet.favorite_count if hasattr(tweet, 'favorite_count') else 0,
#         "is_retweet": hasattr(tweet, 'retweeted_status') and tweet.retweeted_status is not None,
#         "is_quote": hasattr(tweet, 'is_quote_status') and tweet.is_quote_status,
#         "language": tweet.lang,
#         "user": user_data,
#         "media": media_data,
#         "hashtags": [h['text'] for h in tweet.entities['hashtags']] if hasattr(tweet, 'entities') else [],
#         "mentions": [m['screen_name'] for m in tweet.entities['user_mentions']] if hasattr(tweet, 'entities') else [],
#     }
    
#     return tweet_data

# async def get_user_tweets(
#     username: str, 
#     limit: int = 20, 
#     include_retweets: bool = False, 
#     include_replies: bool = False
# ) -> List[Dict[str, Any]]:
#     """
#     Get tweets from a specific Twitter/X user
    
#     Args:
#         username: Twitter/X username
#         limit: Maximum number of tweets to fetch
#         include_retweets: Whether to include retweets
#         include_replies: Whether to include replies
        
#     Returns:
#         List of tweets from the user
#     """
#     # Run Twitter API calls in a separate thread
#     def _get_tweets():
#         try:
#             api = get_twitter_api_v1()
            
#             # Decide if we need to exclude replies
#             exclude_replies = not include_replies
            
#             # Get tweets from user
#             tweets = api.user_timeline(
#                 screen_name=username,
#                 count=limit,
#                 tweet_mode='extended',
#                 exclude_replies=exclude_replies,
#                 include_rts=include_retweets
#             )
            
#             # Format tweets
#             return [format_tweet(tweet) for tweet in tweets]
#         except tweepy.errors.NotFound:
#             raise ValueError(f"User '{username}' not found")
#         except tweepy.errors.Unauthorized:
#             raise Exception("Twitter API authentication failed")
#         except Exception as e:
#             raise Exception(f"Error getting user tweets: {str(e)}")
    
#     # Run in executor to avoid blocking
#     loop = asyncio.get_running_loop()
#     result = await loop.run_in_executor(None, _get_tweets)
#     return result

# async def search_tweets(
#     query: str, 
#     limit: int = 50, 
#     language: str = 'en', 
#     result_type: str = 'mixed',
#     location: Optional[str] = None
# ) -> List[Dict[str, Any]]:
#     """
#     Enhanced search for tweets on Twitter/X with BlackGlass intelligence features
    
#     Args:
#         query: Search term or keywords
#         limit: Maximum number of results
#         language: Language filter (e.g., 'en' for English)
#         result_type: Result type (mixed, recent, popular)
#         location: Optional location filter
        
#     Returns:
#         List of matching tweets with relevance scores
#     """
#     def _search():
#         try:
#             api = get_twitter_api_v1()
            
#             # Process keywords and location
#             keywords = query.split()
            
#             # Add location to the search if provided
#             search_query = query
#             if location and location.lower() not in query.lower():
#                 search_query = f"{query} {location}"
            
#             # Search for tweets
#             tweets = api.search_tweets(
#                 q=search_query,
#                 count=limit * 2,  # Get more to allow for filtering
#                 lang=language,
#                 result_type=result_type,
#                 tweet_mode='extended'
#             )
            
#             # Format and score tweets
#             results = []
#             for tweet in tweets:
#                 # Format basic tweet data
#                 tweet_data = format_tweet(tweet)
                
#                 # Extract tweet text for matching
#                 tweet_text = tweet_data["text"].lower()
                
#                 # Find matching keywords
#                 keywords_matched = [
#                     kw for kw in keywords 
#                     if kw.lower() in tweet_text
#                 ]
                
#                 # Skip if no keywords match
#                 if not keywords_matched:
#                     continue
                
#                 # Check for location match
#                 location_match = False
#                 if location:
#                     location_match = location.lower() in tweet_text
                
#                 # Add matching metadata
#                 tweet_data["keywords_matched"] = keywords_matched
#                 tweet_data["location_match"] = location_match if location else None
                
#                 # Calculate relevance score
#                 # Base score on keyword matches
#                 keyword_score = len(keywords_matched) / len(keywords) if keywords else 0
                
#                 # Boost for location match
#                 location_boost = 0.2 if location_match else 0
                
#                 # Factor in tweet engagement
#                 engagement_score = min(1.0, (tweet_data.get("favorite_count", 0) + 
#                                           tweet_data.get("retweet_count", 0)) / 100) * 0.3
                
#                 # Boost for verified accounts as more trustworthy sources
#                 verification_boost = 0.15 if tweet_data.get("user", {}).get("verified", False) else 0
                
#                 # Media boost for tweets with images/videos (often more informative for intelligence)
#                 media_boost = 0.05 if tweet_data.get("media", []) else 0
                
#                 # Calculate final relevance (0-100)
#                 relevance = (keyword_score * 0.5 + location_boost + 
#                            engagement_score + verification_boost + media_boost)
#                 tweet_data["relevance_score"] = int(relevance * 100)
                
#                 results.append(tweet_data)
            
#             # Sort by relevance score
#             results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            
#             return results[:limit]
#         except tweepy.errors.Unauthorized:
#             raise Exception("Twitter API authentication failed")
#         except Exception as e:
#             raise Exception(f"Error searching tweets: {str(e)}")
    
#     # Run in executor to avoid blocking
#     loop = asyncio.get_running_loop()
#     result = await loop.run_in_executor(None, _search)
#     return result

# async def get_intel_tweets(
#     accounts: Optional[List[str]] = None, 
#     limit: int = 50
# ) -> List[Dict[str, Any]]:
#     """
#     Get latest intelligence and news tweets from tracked accounts
    
#     Args:
#         accounts: List of account usernames to fetch tweets from
#         limit: Maximum number of tweets to fetch
        
#     Returns:
#         List of tweets from intelligence and news accounts
#     """
#     if not accounts:
#         accounts = settings.DEFAULT_TWITTER_ACCOUNTS
    
#     # Calculate tweets per account
#     tweets_per_account = max(5, limit // len(accounts))
#     all_tweets = []
    
#     # Get tweets from each account
#     for account in accounts:
#         try:
#             tweets = await get_user_tweets(
#                 account, 
#                 limit=tweets_per_account, 
#                 include_retweets=False
#             )
#             all_tweets.extend(tweets)
#         except Exception as e:
#             print(f"Error getting tweets from {account}: {str(e)}")
#             continue
    
#     # Sort by date (newest first)
#     all_tweets.sort(key=lambda x: x["created_at"], reverse=True)
    
#     return all_tweets[:limit]

# async def get_trends(woeid: int = 1) -> List[Dict[str, Any]]:
#     """
#     Get trending topics on Twitter/X
    
#     Args:
#         woeid: Where On Earth ID (1 for global, 23424977 for US, etc.)
        
#     Returns:
#         List of trending topics
#     """
#     def _get_trends():
#         try:
#             api = get_twitter_api_v1()
            
#             # Get trends
#             trends = api.get_place_trends(id=woeid)[0]
            
#             # Format trends
#             result = []
#             for trend in trends['trends']:
#                 trend_data = {
#                     "name": trend['name'],
#                     "url": trend['url'],
#                     "query": trend['query'],
#                     "tweet_volume": trend['tweet_volume'],
#                     "timestamp": datetime.now(timezone.utc).isoformat()
#                 }
#                 result.append(trend_data)
            
#             return result
#         except Exception as e:
#             raise Exception(f"Error getting trends: {str(e)}")
    
#     # Run in executor to avoid blocking
#     loop = asyncio.get_running_loop()
#     result = await loop.run_in_executor(None, _get_trends)
#     return result