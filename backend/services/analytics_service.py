#!/usr/bin/env python3
"""
Analytics and reporting operations
"""

import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta
from backend.services.database_connection import DatabaseConnection

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Handles analytics and reporting operations"""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
    def get_show_analytics(self, venue: str, show_date: str) -> Dict[str, Any]:
        """Get comprehensive show analytics"""
        with self.db.get_collection('contacts') as collection:
            pipeline = [
                {"$match": {"venue": venue, "show_date": show_date}},
                {
                    "$group": {
                        "_id": "$source",
                        "total_tickets": {"$sum": "$tickets"},
                        "total_attendees": {"$sum": 1},
                        "total_revenue": {"$sum": {"$ifNull": ["$total_price", 0]}}
                    }
                }
            ]
            
            results = list(collection.aggregate(pipeline))
            
            analytics = {
                "by_source": results,
                "total_tickets": sum(r["total_tickets"] for r in results),
                "total_attendees": sum(r["total_attendees"] for r in results),
                "total_revenue": sum(r["total_revenue"] for r in results)
            }
            
            logger.info(f"Generated analytics for {venue} on {show_date}")
            return analytics
    
    def get_venues(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all venues"""
        with self.db.get_collection('venues') as collection:
            query = {"active": True} if active_only else {}
            venues = list(collection.find(query).sort("name", 1))
            
            for venue in venues:
                venue['_id'] = str(venue['_id'])
            
            logger.info(f"Retrieved {len(venues)} venues")
            return venues
    
    def get_venue_shows(self, venue: str, days_back: int = 30) -> List[Dict[str, Any]]:
        """Get distinct show dates for venue, sorted chronologically"""
        with self.db.get_collection('contacts') as collection:
            pipeline = [
                {"$match": {"venue": venue, "show_datetime": {"$ne": None}}},
                {"$group": {
                    "_id": "$show_datetime",
                    "show_date": {"$first": "$show_date"}
                }},
                {"$sort": {"_id": 1}}
            ]
            
            result = list(collection.aggregate(pipeline))
            
            if days_back > 0:
                cutoff_date = datetime.now() - timedelta(days=days_back)
                result = [doc for doc in result if doc['_id'] >= cutoff_date]
            
            shows = []
            for doc in result:
                dt = doc['_id']
                formatted_date = dt.strftime("%b %d, %Y %I:%M %p").replace(" 0", " ").replace("  ", " ")
                shows.append({
                    'show_datetime': dt,
                    'show_date_display': formatted_date,
                    'show_date_original': doc['show_date']
                })
            
            logger.info(f"Retrieved {len(shows)} shows for {venue}")
            return shows
    
    def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        try:
            with self.db.get_collection('contacts') as contacts_collection:
                contact_count = contacts_collection.count_documents({})
                
            with self.db.get_collection('comedians') as comedians_collection:
                comedian_count = comedians_collection.count_documents({})
                
            with self.db.get_collection('venues') as venues_collection:
                venue_count = venues_collection.count_documents({"active": True})
            
            return {
                "status": "healthy",
                "collections": {
                    "contacts": contact_count,
                    "comedians": comedian_count,
                    "venues": venue_count
                },
                "total_records": contact_count + comedian_count + venue_count,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
