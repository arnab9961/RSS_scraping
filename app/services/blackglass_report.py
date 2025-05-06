import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import uuid
import json
import os
from pathlib import Path

from app.services import rss_scrapping
from app.config.config import settings

# In-memory storage for report data (in production, use a database)
_reports = {}

class ReportStatus:
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

async def start_report_generation(
    report_id: str, 
    keywords: List[str], 
    location: Optional[str] = None, 
    asset_class: Optional[str] = "any"
) -> Dict[str, Any]:
    """
    Initialize the report generation process
    
    Args:
        report_id: Unique ID for the report
        keywords: Search keywords provided by the user
        location: Optional location to focus on
        asset_class: Type of asset to focus on
        
    Returns:
        Report metadata
    """
    # Create report metadata
    report_metadata = {
        "id": report_id,
        "status": ReportStatus.QUEUED,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "params": {
            "keywords": keywords,
            "location": location,
            "asset_class": asset_class
        },
        "sources_processed": [],
        "completion_percentage": 0,
        "estimated_completion_time": None
    }
    
    # Store report metadata
    _reports[report_id] = report_metadata
    
    # Start background generation
    asyncio.create_task(generate_report(report_id, keywords, location, asset_class))
    
    return report_metadata

async def generate_report(
    report_id: str, 
    keywords: List[str], 
    location: Optional[str] = None, 
    asset_class: Optional[str] = "any"
) -> None:
    """
    Generate a threat intelligence report based on the provided parameters
    
    Args:
        report_id: Unique ID for the report
        keywords: Search keywords provided by the user
        location: Optional location to focus on
        asset_class: Type of asset to focus on
    """
    try:
        # Update report status
        update_report_status(report_id, ReportStatus.PROCESSING, 10)
        
        # Step 1: Collect data from RSS feeds
        search_query = " ".join(keywords)
        if location:
            search_query += f" {location}"
            
        # Include asset class keywords if applicable
        if asset_class != "any":
            asset_keywords = get_asset_class_keywords(asset_class)
            if asset_keywords:
                search_query += " " + " OR ".join(asset_keywords)
        
        update_report_status(report_id, ReportStatus.PROCESSING, 20, ["Searching RSS feeds"])
        
        # Search RSS feeds
        rss_results = await rss_scrapping.search_feeds(
            query=search_query, 
            limit=100, 
            include_alerts=True,
            location=location
        )
        
        update_report_status(report_id, ReportStatus.PROCESSING, 40, ["RSS feeds processed"])
        
        # Step 2: Process and analyze collected data
        update_report_status(report_id, ReportStatus.PROCESSING, 60, ["Analyzing collected data"])
        
        # Analyze threats based on collected data
        report_data = await process_intelligence_data(rss_results, keywords, location, asset_class)
        
        update_report_status(report_id, ReportStatus.PROCESSING, 80, ["Data analysis completed"])
        
        # Step 3: Generate the report document
        update_report_status(report_id, ReportStatus.PROCESSING, 90, ["Generating report document"])
        
        # Save the report data (this would generate a PDF in production)
        report_path = save_report_data(report_id, report_data)
        
        # Mark as completed
        update_report_status(
            report_id, 
            ReportStatus.COMPLETED, 
            100, 
            ["Report generation completed"],
            output_path=report_path
        )
        
    except Exception as e:
        # Handle errors
        update_report_status(
            report_id, 
            ReportStatus.FAILED, 
            0, 
            [f"Error generating report: {str(e)}"]
        )

def update_report_status(
    report_id: str, 
    status: str, 
    completion_percentage: int, 
    sources_processed: List[str] = None,
    output_path: str = None
) -> None:
    """
    Update the status of a report
    
    Args:
        report_id: ID of the report to update
        status: New status of the report
        completion_percentage: Percentage of completion
        sources_processed: List of sources that have been processed
        output_path: Path to the output file
    """
    if report_id not in _reports:
        return
        
    report = _reports[report_id]
    report["status"] = status
    report["updated_at"] = datetime.now(timezone.utc).isoformat()
    report["completion_percentage"] = completion_percentage
    
    if sources_processed:
        if "sources_processed" not in report:
            report["sources_processed"] = []
        report["sources_processed"].extend(sources_processed)
    
    if output_path:
        report["output_path"] = output_path
        
    # Update estimated completion time if still processing
    if status == ReportStatus.PROCESSING:
        # Simple estimation based on completion percentage
        report["estimated_completion_time"] = (
            datetime.now(timezone.utc) + 
            (datetime.now(timezone.utc) - datetime.fromisoformat(report["created_at"])) * 
            (100 - completion_percentage) / max(1, completion_percentage)
        ).isoformat()

def get_report_status(report_id: str) -> Dict[str, Any]:
    """
    Get the status of a report
    
    Args:
        report_id: ID of the report to check
        
    Returns:
        Report metadata or None if not found
    """
    return _reports.get(report_id)

def get_asset_class_keywords(asset_class: str) -> List[str]:
    """
    Get keywords associated with an asset class
    
    Args:
        asset_class: Asset class name
        
    Returns:
        List of relevant keywords
    """
    asset_filters = {
        "person": ["individual", "person", "personnel", "employee", "staff"],
        "organization": ["company", "organization", "business", "corporation", "enterprise", "firm"],
        "infrastructure": ["facility", "infrastructure", "building", "plant", "grid", "network"],
        "digital_asset": ["server", "database", "cloud", "software", "application", "system"],
        "physical_asset": ["equipment", "hardware", "device", "machine", "vehicle"],
    }
    
    return asset_filters.get(asset_class, [])

async def process_intelligence_data(
    intel_data: List[Dict[str, Any]], 
    keywords: List[str], 
    location: Optional[str], 
    asset_class: str
) -> Dict[str, Any]:
    """
    Process and analyze intelligence data to generate insights
    
    Args:
        intel_data: Raw intelligence data from various sources
        keywords: Search keywords
        location: Geographic location focus
        asset_class: Type of asset to focus on
        
    Returns:
        Processed intelligence data with insights
    """
    # Group articles by source credibility
    high_credibility = []
    medium_credibility = []
    standard_credibility = []
    
    for article in intel_data:
        credibility = (
            article.get("blackglass_metadata", {}).get("source_credibility") or 
            rss_scrapping.determine_source_credibility(article.get("source", ""))
        )
        
        if credibility == "high":
            high_credibility.append(article)
        elif credibility == "medium":
            medium_credibility.append(article)
        else:
            standard_credibility.append(article)
    
    # Categorize by intelligence type
    categories = {}
    for article in intel_data:
        intel_cats = (
            article.get("blackglass_metadata", {}).get("intelligence_category") or 
            rss_scrapping.determine_intelligence_category(article.get("title", ""), article.get("summary", ""))
        )
        
        for category in intel_cats:
            if category not in categories:
                categories[category] = []
            categories[category].append(article)
    
    # Extract entities (locations, organizations)
    locations = set()
    organizations = set()
    
    for article in intel_data:
        # Extract locations
        article_locs = (
            article.get("extracted_locations") or 
            rss_scrapping.extract_locations(article.get("summary", "") + article.get("title", ""))
        )
        locations.update(article_locs)
        
        # Extract organizations
        article_orgs = (
            article.get("extracted_organizations") or 
            rss_scrapping.extract_organizations(article.get("summary", "") + article.get("title", ""))
        )
        organizations.update(article_orgs)
    
    # Prepare the final report data structure
    report_data = {
        "summary": {
            "keywords": keywords,
            "location_focus": location,
            "asset_class": asset_class,
            "total_sources": len(intel_data),
            "high_credibility_sources": len(high_credibility),
            "medium_credibility_sources": len(medium_credibility),
            "intelligence_categories": list(categories.keys()),
            "identified_locations": list(locations),
            "identified_organizations": list(organizations)
        },
        "threat_assessment": {
            "overall_threat_level": calculate_threat_level(intel_data, keywords, location),
            "categories": {
                category: {
                    "count": len(articles),
                    "top_articles": sorted(articles, key=lambda x: x.get("relevance_score", 0), reverse=True)[:3]
                }
                for category, articles in categories.items()
            }
        },
        "sources": {
            "high_credibility": high_credibility,
            "medium_credibility": medium_credibility,
            "standard_credibility": standard_credibility
        },
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
    
    return report_data

def calculate_threat_level(intel_data: List[Dict[str, Any]], keywords: List[str], location: Optional[str]) -> str:
    """
    Calculate overall threat level based on collected intelligence
    
    Args:
        intel_data: Processed intelligence data
        keywords: Search keywords
        location: Geographic location focus
        
    Returns:
        Threat level (LOW, MEDIUM, HIGH, CRITICAL)
    """
    if not intel_data:
        return "LOW"
    
    # Calculate threat score based on various factors
    threat_score = 0
    
    # Factor 1: Volume of high-relevance articles
    high_relevance_count = sum(1 for article in intel_data if article.get("relevance_score", 0) > 80)
    threat_score += min(40, high_relevance_count * 2)
    
    # Factor 2: Recent articles with high credibility
    recent_high_cred = sum(
        1 for article in intel_data 
        if (
            article.get("blackglass_metadata", {}).get("source_credibility") == "high" and
            (datetime.now(timezone.utc) - datetime.fromisoformat(article.get("published", datetime.now(timezone.utc).isoformat()))).days < 3
        )
    )
    threat_score += min(30, recent_high_cred * 5)
    
    # Factor 3: Cybersecurity-related content
    cyber_count = sum(
        1 for article in intel_data
        if "cybersecurity" in article.get("blackglass_metadata", {}).get("intelligence_category", [])
    )
    threat_score += min(30, cyber_count * 3)
    
    # Map score to threat level
    if threat_score > 70:
        return "CRITICAL"
    elif threat_score > 50:
        return "HIGH"
    elif threat_score > 30:
        return "MEDIUM"
    else:
        return "LOW"

def save_report_data(report_id: str, report_data: Dict[str, Any]) -> str:
    """
    Save report data to a file
    
    Args:
        report_id: ID of the report
        report_data: Processed report data
        
    Returns:
        Path to the saved report
    """
    # Create reports directory if it doesn't exist
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    # Save as JSON for now (in production, this would generate a PDF)
    report_path = reports_dir / f"{report_id}.json"
    
    with open(report_path, "w") as f:
        json.dump(report_data, f, indent=2)
    
    return str(report_path)

def get_report_download_path(report_id: str) -> Optional[str]:
    """
    Get the download path for a completed report
    
    Args:
        report_id: ID of the report
        
    Returns:
        Path to the report file or None if not found/completed
    """
    report = _reports.get(report_id)
    if not report or report["status"] != ReportStatus.COMPLETED:
        return None
    
    return report.get("output_path")