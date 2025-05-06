# import asyncio
# from telethon import TelegramClient
# from telethon.errors import ChannelPrivateError, ChannelInvalidError
# from telethon.tl.functions.messages import SearchRequest
# from telethon.tl.types import InputMessagesFilterPhotos, InputMessagesFilterVideo, InputMessagesFilterDocument
# from datetime import datetime, timezone, timedelta
# from typing import List, Dict, Any, Optional, Union
# import re
# import os

# from app.config.config import settings

# # Initialize the client
# client = None
# client_initialized = False

# async def get_client() -> TelegramClient:
#     """Initialize and return the Telegram client"""
#     global client, client_initialized
    
#     if client is None:
#         # Use a session name that's convenient for your use case
#         session_path = "telegram_session"
        
#         # Create the client
#         client = TelegramClient(
#             session_path,
#             settings.TELEGRAM_API_ID,
#             settings.TELEGRAM_API_HASH
#         )
    
#     if not client_initialized:
#         await client.start()
#         client_initialized = True
        
#     return client

# async def get_channel_messages(
#     channel_username: str, 
#     limit: int = 20, 
#     offset: int = 0
# ) -> List[Dict[str, Any]]:
#     """
#     Get messages from a Telegram public channel
    
#     Args:
#         channel_username: Username of the channel (without @)
#         limit: Maximum number of messages to fetch
#         offset: Offset for pagination
        
#     Returns:
#         List of messages with relevant information
#     """
#     client = await get_client()
    
#     try:
#         entity = await client.get_entity(channel_username)
        
#         # Get messages from the channel
#         messages = await client.get_messages(
#             entity,
#             limit=limit,
#             offset_id=offset if offset > 0 else 0
#         )
        
#         results = []
#         for message in messages:
#             # Basic message info
#             msg_data = {
#                 "id": message.id,
#                 "date": message.date.replace(tzinfo=timezone.utc).isoformat(),
#                 "text": message.text,
#                 "has_media": bool(message.media),
#                 "channel": channel_username,
#                 "source_type": "telegram",
#                 "views": getattr(message, "views", None),
#                 "forwards": getattr(message, "forwards", None),
#                 "url": f"https://t.me/{channel_username}/{message.id}"
#             }
            
#             results.append(msg_data)
        
#         return results
#     except (ChannelPrivateError, ChannelInvalidError) as e:
#         raise ValueError(f"Channel '{channel_username}' not found or is private: {str(e)}")
#     except Exception as e:
#         raise Exception(f"Error getting channel messages: {str(e)}")

# async def get_latest_news(
#     channels: List[str] = None, 
#     limit: int = 50, 
#     days: int = 7
# ) -> List[Dict[str, Any]]:
#     """
#     Get latest news from Telegram channels
    
#     Args:
#         channels: List of channel usernames
#         limit: Maximum number of messages to fetch
#         days: Only fetch messages from the last X days
        
#     Returns:
#         List of messages with relevant information
#     """
#     if not channels:
#         channels = settings.DEFAULT_TELEGRAM_CHANNELS
        
#     # Calculate messages per channel
#     msgs_per_channel = max(5, limit // len(channels))
    
#     # Get messages from all channels
#     all_messages = []
#     for channel in channels:
#         try:
#             messages = await get_channel_messages(channel, limit=msgs_per_channel)
#             all_messages.extend(messages)
#         except Exception as e:
#             print(f"Error getting messages from {channel}: {str(e)}")
#             continue
    
#     # Filter by date if needed
#     if days > 0:
#         cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
#         all_messages = [
#             msg for msg in all_messages 
#             if datetime.fromisoformat(msg["date"]) >= cutoff_date
#         ]
    
#     # Sort by date (newest first)
#     all_messages.sort(
#         key=lambda x: x["date"], 
#         reverse=True
#     )
    
#     return all_messages[:limit]

# async def search_messages(
#     query: str,
#     channels: List[str] = None,
#     limit: int = 50,
#     days: int = 7,
#     location: Optional[str] = None
# ) -> List[Dict[str, Any]]:
#     """
#     Enhanced search functionality for Telegram messages with BlackGlass features
    
#     # Args
#         query: Search term or keywords
#         channels: List of channel usernames to search in
#         limit: Maximum number of messages to return
#         days: Only search messages from the last X days
#         location: Optional geographic location filter
        
#     Returns:
#         List of matching messages with relevance scores
#     """
#     if not channels:
#         channels = settings.DEFAULT_TELEGRAM_CHANNELS
        
#     # Calculate limit per channel
#     per_channel = max(10, limit // len(channels))
    
#     # Parse keywords
#     keywords = query.split()
    
#     client = await get_client()
#     all_results = []
    
#     # Get cutoff date
#     cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
#     # Search in each channel
#     for channel_username in channels:
#         try:
#             entity = await client.get_entity(channel_username)
            
#             # Get messages from the channel
#             messages = await client.get_messages(
#                 entity,
#                 limit=per_channel * 2,  # Get more than needed for filtering
#                 offset_id=0
#             )
            
#             # Filter messages by date
#             messages = [
#                 msg for msg in messages 
#                 if msg.date >= cutoff_date
#             ]
            
#             # Filter by keywords and location
#             channel_results = []
#             for message in messages:
#                 # Skip empty messages
#                 if not message.text:
#                     continue
                
#                 # Match keywords
#                 message_text = message.text.lower()
#                 keywords_matched = [kw for kw in keywords if kw.lower() in message_text]
                
#                 # Skip if no keywords match
#                 if not keywords_matched:
#                     continue
                
#                 # Check location match if provided
#                 location_match = False
#                 if location:
#                     location_match = location.lower() in message_text
#                     # Skip if location is critical but missing
#                     if not location_match and location.lower() not in query.lower():
#                         continue
                
#                 # Format message data
#                 msg_data = {
#                     "id": message.id,
#                     "date": message.date.replace(tzinfo=timezone.utc).isoformat(),
#                     "text": message.text,
#                     "has_media": bool(message.media),
#                     "channel": channel_username,
#                     "source_type": "telegram",
#                     "views": getattr(message, "views", None),
#                     "forwards": getattr(message, "forwards", None),
#                     "url": f"https://t.me/{channel_username}/{message.id}",
#                     "keywords_matched": keywords_matched,
#                     "location_match": location_match if location else None
#                 }
                
#                 # Calculate relevance score
#                 # Base score on keyword matches
#                 keyword_score = len(keywords_matched) / len(keywords) if keywords else 0
                
#                 # Boost for location match
#                 location_boost = 0.2 if location_match else 0
                
#                 # Factor in engagement metrics
#                 views_score = min(1.0, msg_data.get("views", 0) / 1000) * 0.1 if msg_data.get("views") else 0
#                 forwards_score = min(1.0, msg_data.get("forwards", 0) / 50) * 0.15 if msg_data.get("forwards") else 0
                
#                 # Media boost - messages with media might be more informative
#                 media_boost = 0.05 if msg_data.get("has_media") else 0
                
#                 # Calculate final relevance (0-100)
#                 msg_data["relevance_score"] = int(((keyword_score * 0.6) + location_boost + views_score + forwards_score + media_boost) * 100)
                
#                 channel_results.append(msg_data)
                
#                 # Stop once we have enough results
#                 if len(channel_results) >= per_channel:
#                     break
                    
#             all_results.extend(channel_results)
                
#         except (ChannelPrivateError, ChannelInvalidError) as e:
#             print(f"Error: Channel '{channel_username}' not found or is private: {str(e)}")
#             continue
#         except Exception as e:
#             print(f"Error searching in channel '{channel_username}': {str(e)}")
#             continue
    
#     # Sort by relevance score (highest first)
#     all_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    
#     return all_results[:limit]

# async def close_client():
#     """Close the Telegram client if it's running"""
#     global client, client_initialized
    
#     if client and client_initialized:
#         await client.disconnect()
#         client_initialized = False