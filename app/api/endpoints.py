from fastapi import APIRouter, Query, HTTPException, Depends, BackgroundTasks, Response, Body, status
from typing import List, Dict, Any, Optional
from enum import Enum
import datetime
import uuid
import os
from pathlib import Path

from app.services import rss_scrapping
from app.services import blackglass_report
from app.config.config import settings

router = APIRouter()

# Asset class enum for intelligence platform
class AssetClass(str, Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    INFRASTRUCTURE = "infrastructure"
    DIGITAL_ASSET = "digital_asset"
    PHYSICAL_ASSET = "physical_asset"
    ANY = "any"

@router.get("/news/rss", tags=["RSS"])
async def get_rss_news(
    limit: int = Query(200, ge=1, le=1000, description="Maximum total number of results"),
    include_google_alerts: bool = Query(True, description="Include Google Alerts in RSS results")
):
    """
    Get all news from RSS feeds.
    
    - **limit**: Maximum total number of results
    - **include_google_alerts**: Include Google Alerts in RSS results
    """
    all_news = []
    errors = {}
    
    try:
        rss_news = await rss_scrapping.get_latest_intel_news(include_alerts=include_google_alerts)
        for article in rss_news:
            # Normalize data structure
            normalized_article = {
                "id": article.get("id", ""),
                "title": article.get("title", ""),
                "content": article.get("summary", ""),
                "url": article.get("link", ""),
                "external_url": article.get("link", ""),
                "published_at": article.get("published", ""),
                "source": article.get("source", ""),
                "source_platform": "rss",
                "author": article.get("author", ""),
                "feed_url": article.get("feed_url", ""),
                "raw_data": article
            }
            all_news.append(normalized_article)
    except Exception as e:
        errors["rss"] = str(e)
    
    return {
        "status": "success" if not errors else "error",
        "count": len(all_news),
        "errors": errors,
        "data": all_news[:limit]
    }

@router.post("/rss/search", tags=["RSS"])
async def search_rss_feeds(
    keywords: List[str] = Query(..., description="Required search keywords"),
    location: Optional[str] = Query(None, description="Optional geographic location to focus on"),
    asset_class: Optional[AssetClass] = Query(AssetClass.ANY, description="Type of asset to focus on"),
    limit: int = Query(200, ge=1, le=1000, description="Maximum total number of results"),
    include_google_alerts: bool = Query(True, description="Include Google Alerts in RSS results")
):
    """
    Search RSS feeds based on keywords, location, and asset class.
    
    - **keywords**: Required search terms (e.g., ["cybersecurity", "breach"])
    - **location**: Optional geographic location focus (e.g., "Eastern Europe")
    - **asset_class**: Type of asset to focus on
    - **limit**: Maximum total number of results to process
    - **include_google_alerts**: Include Google Alerts in RSS results
    """
    all_intel = []
    errors = {}
    
    # Construct search query from keywords and location
    search_query = " ".join(keywords)
    if location:
        search_query += f" {location}"
    
    # Filter based on asset class if specified
    asset_filters = {
        AssetClass.PERSON: ["individual", "person", "personnel", "employee", "staff"],
        AssetClass.ORGANIZATION: ["company", "organization", "business", "corporation", "enterprise", "firm"],
        AssetClass.INFRASTRUCTURE: ["facility", "infrastructure", "building", "plant", "grid", "network"],
        AssetClass.DIGITAL_ASSET: ["server", "database", "cloud", "software", "application", "system"],
        AssetClass.PHYSICAL_ASSET: ["equipment", "hardware", "device", "machine", "vehicle"],
    }
    
    asset_keywords = []
    if asset_class != AssetClass.ANY:
        asset_keywords = asset_filters.get(asset_class, [])
        if asset_keywords:
            # Add asset class keywords to the search if specified
            search_query += " " + " OR ".join(asset_keywords)
    
    try:
        # Search RSS feeds
        rss_intel = await rss_scrapping.search_feeds(query=search_query, limit=limit, include_alerts=include_google_alerts)
        
        for article in rss_intel:
            # Normalize data structure
            normalized_article = {
                "id": article.get("id", ""),
                "title": article.get("title", ""),
                "content": article.get("summary", ""),
                "url": article.get("link", ""),
                "external_url": article.get("link", ""),
                "published_at": article.get("published", ""),
                "source": article.get("source", ""),
                "source_platform": "rss",
                "author": article.get("author", ""),
                "feed_url": article.get("feed_url", ""),
                "raw_data": article,
                "keywords_matched": [kw for kw in keywords if kw.lower() in (article.get("title", "") + article.get("summary", "")).lower()],
                "relevance_score": article.get("relevance_score", 0)
            }
            all_intel.append(normalized_article)
    except Exception as e:
        errors["rss"] = str(e)
    
    return {
        "status": "success" if not errors else "error",
        "query": {
            "keywords": keywords,
            "location": location,
            "asset_class": asset_class
        },
        "count": len(all_intel),
        "errors": errors,
        "data": all_intel[:limit],
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

@router.post("/blackglass/generate-report", tags=["BlackGlass"])
async def generate_threat_report(
    background_tasks: BackgroundTasks,
    keywords: List[str] = Body(..., description="Required search keywords"),
    location: Optional[str] = Body(None, description="Optional geographic location to focus on"),
    asset_class: Optional[AssetClass] = Body(AssetClass.ANY, description="Type of asset to focus on")
):
    """
    Generate a comprehensive threat intelligence report based on specified parameters.
    
    - **keywords**: Required search terms (e.g., ["cybersecurity", "breach"])
    - **location**: Optional geographic location focus (e.g., "Eastern Europe")
    - **asset_class**: Type of asset to focus on (person, organization, infrastructure, etc.)
    
    Returns a report ID that can be used to check the report generation status and download
    the final report when ready.
    """
    # Validate input
    if not keywords:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="At least one keyword is required"
        )
    
    # Generate a unique report ID
    report_id = str(uuid.uuid4())
    
    # Initialize report generation
    report_metadata = await blackglass_report.start_report_generation(
        report_id,
        keywords,
        location,
        asset_class.value if asset_class else "any"
    )
    
    return {
        "status": "success",
        "message": "Report generation started",
        "report_id": report_id,
        "estimated_completion_time": report_metadata.get("estimated_completion_time")
    }

@router.get("/blackglass/report/{report_id}", tags=["BlackGlass"])
async def get_report_status(report_id: str):
    """
    Check the status of a report generation request.
    
    - **report_id**: The ID of the report to check
    
    Returns the status of the report generation and, if completed, a download link.
    """
    # Get report status
    report = blackglass_report.get_report_status(report_id)
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID {report_id} not found"
        )
    
    response = {
        "status": "success",
        "report": {
            "id": report_id,
            "status": report.get("status"),
            "completion_percentage": report.get("completion_percentage", 0),
            "created_at": report.get("created_at"),
            "updated_at": report.get("updated_at"),
        }
    }
    
    # Add sources processed if available
    if "sources_processed" in report:
        response["report"]["sources_processed"] = report["sources_processed"]
    
    # Add estimated completion time if processing
    if report.get("status") == blackglass_report.ReportStatus.PROCESSING:
        response["report"]["estimated_completion_time"] = report.get("estimated_completion_time")
    
    # Add download link if completed
    if report.get("status") == blackglass_report.ReportStatus.COMPLETED:
        response["report"]["download_url"] = f"/api/blackglass/download/{report_id}"
    
    return response

@router.get("/blackglass/download/{report_id}", tags=["BlackGlass"])
async def download_report(report_id: str, response: Response):
    """
    Download a completed intelligence report.
    
    - **report_id**: The ID of the report to download
    
    Returns the report as a PDF file.
    """
    # Get report path
    report_path = blackglass_report.get_report_download_path(report_id)
    
    if not report_path or not os.path.exists(report_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report file for ID {report_id} not found"
        )
    
    # In a real implementation, we would return a PDF
    # For now, we'll return the JSON data
    
    # Read the report file
    with open(report_path, "r") as f:
        report_data = f.read()
    
    # Set response headers
    response.headers["Content-Disposition"] = f"attachment; filename=blackglass_report_{report_id}.json"
    response.headers["Content-Type"] = "application/json"
    
    return Response(content=report_data, media_type="application/json")