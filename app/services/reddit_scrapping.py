# import praw
# import asyncio
# from typing import List, Dict, Any, Optional
# from datetime import datetime, timezone

# from app.config.config import settings

# def get_reddit_client():
#     """Create and return a Reddit API client"""
#     return praw.Reddit(
#         client_id=settings.REDDIT_CLIENT_ID,
#         client_secret=settings.REDDIT_CLIENT_SECRET,
#         username=settings.REDDIT_USERNAME,
#         password=settings.REDDIT_PASSWORD,
#         user_agent=settings.REDDIT_USER_AGENT
#     )

# async def fetch_subreddit_posts(subreddit_name: str, limit: int = 15, sort_by: str = "hot") -> List[Dict[Any, Any]]:
#     """
#     Fetch posts from a specific subreddit
    
#     Args:
#         subreddit_name: Name of the subreddit to fetch posts from
#         limit: Maximum number of posts to fetch
#         sort_by: How to sort posts ("hot", "new", "top", "rising")
    
#     Returns:
#         List of posts with relevant information
#     """
#     reddit = get_reddit_client()
#     subreddit = reddit.subreddit(subreddit_name)
    
#     # Get posts based on sort method
#     if sort_by == "hot":
#         posts = subreddit.hot(limit=limit)
#     elif sort_by == "new":
#         posts = subreddit.new(limit=limit)
#     elif sort_by == "top":
#         posts = subreddit.top(limit=limit)
#     elif sort_by == "rising":
#         posts = subreddit.rising(limit=limit)
#     else:
#         posts = subreddit.hot(limit=limit)
    
#     result = []
#     for post in posts:
#         # Skip stickied posts if needed
#         if post.stickied:
#             continue
            
#         # Format post data
#         post_data = {
#             "id": post.id,
#             "title": post.title,
#             "url": post.url,
#             "permalink": f"https://www.reddit.com{post.permalink}",
#             "created_utc": datetime.fromtimestamp(post.created_utc, tz=timezone.utc).isoformat(),
#             "score": post.score,
#             "upvote_ratio": post.upvote_ratio,
#             "num_comments": post.num_comments,
#             "author": post.author.name if post.author else "[deleted]",
#             "is_self": post.is_self,
#             "selftext": post.selftext if post.is_self else "",
#             "subreddit": post.subreddit.display_name,
#         }
#         result.append(post_data)
    
#     return result

# async def search_posts(
#     query: str, 
#     subreddits: List[str] = None, 
#     limit: int = 30,
#     location: Optional[str] = None
# ) -> List[Dict[Any, Any]]:
#     """
#     Search for posts across multiple subreddits with enhanced filtering for BlackGlass
    
#     Args:
#         query: Search term or keywords
#         subreddits: List of subreddits to search in, defaults to intelligence-related subs
#         limit: Maximum number of results
#         location: Optional location filter
        
#     Returns:
#         List of matching posts
#     """
#     if not subreddits:
#         subreddits = settings.DEFAULT_SUBREDDITS
        
#     reddit = get_reddit_client()
#     results = []
    
#     # Process search query
#     keywords = query.split()
    
#     # Handle location filtering
#     combined_query = query
#     if location:
#         combined_query = f"{query} {location}"
    
#     for subreddit_name in subreddits:
#         subreddit = reddit.subreddit(subreddit_name)
#         try:
#             for post in subreddit.search(combined_query, limit=limit // len(subreddits)):
#                 post_data = {
#                     "id": post.id,
#                     "title": post.title,
#                     "url": post.url,
#                     "permalink": f"https://www.reddit.com{post.permalink}",
#                     "created_utc": datetime.fromtimestamp(post.created_utc, tz=timezone.utc).isoformat(),
#                     "score": post.score,
#                     "num_comments": post.num_comments,
#                     "author": post.author.name if post.author else "[deleted]",
#                     "subreddit": post.subreddit.display_name,
#                     "source": "reddit",
#                     "selftext": post.selftext if hasattr(post, 'selftext') else "",
#                     "is_self": post.is_self if hasattr(post, 'is_self') else False,
#                     # Add keyword matching metadata
#                     "keywords_matched": [
#                         kw for kw in keywords 
#                         if kw.lower() in post.title.lower() or 
#                            (hasattr(post, 'selftext') and kw.lower() in post.selftext.lower())
#                     ],
#                     "location_match": location.lower() in post.title.lower() or 
#                                     (hasattr(post, 'selftext') and location and location.lower() in post.selftext.lower()) 
#                                     if location else None
#                 }
#                 results.append(post_data)
#         except Exception as e:
#             print(f"Error searching in subreddit {subreddit_name}: {str(e)}")
#             continue
    
#     # Calculate relevance score for sorting
#     for post in results:
#         # Base score on number of keywords matched
#         keyword_matches = len(post.get("keywords_matched", []))
#         keyword_score = keyword_matches / len(keywords) if keywords else 0
        
#         # Boost posts with location matches
#         location_boost = 0.2 if post.get("location_match") else 0
        
#         # Factor in Reddit metrics
#         engagement_score = min(1.0, post.get("score", 0) / 100) * 0.3 + min(1.0, post.get("num_comments", 0) / 50) * 0.2
        
#         # Calculate final relevance (0-100)
#         post["relevance_score"] = int(((keyword_score * 0.5) + location_boost + engagement_score) * 100)
    
#     # Sort by relevance score (most relevant first)
#     results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    
#     return results[:limit]

# async def get_intelligence_news(limit: int = 50) -> Dict[str, List[Dict[Any, Any]]]:
#     """
#     Get intelligence and geopolitical news from multiple relevant subreddits
    
#     Args:
#         limit: Maximum number of posts per subreddit
        
#     Returns:
#         Dictionary with subreddits as keys and list of posts as values
#     """
#     results = {}
#     tasks = []
    
#     for subreddit in settings.DEFAULT_SUBREDDITS:
#         tasks.append(fetch_subreddit_posts(subreddit, limit=limit))
    
#     subreddit_posts = await asyncio.gather(*tasks)
    
#     for i, subreddit in enumerate(settings.DEFAULT_SUBREDDITS):
#         results[subreddit] = subreddit_posts[i]
    
#     return results