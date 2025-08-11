#!/usr/bin/env python3
"""
Comedian operations for database  
"""

import logging
from typing import Dict, List, Any
from datetime import datetime
from bson import ObjectId
from backend.models import validate_comedian
from backend.services.database_connection import DatabaseConnection

logger = logging.getLogger(__name__)

class ComedianService:
    """Handles all comedian-related database operations"""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
    def create_comedian(self, comedian_data: Dict[str, Any]) -> str:
        """Create or update comedian record"""
        comedian = validate_comedian(comedian_data)
        
        with self.db.get_collection('comedians') as collection:
            query = {
                "name": comedian.name,
                "venue": comedian.venue,
                "show_date": comedian.show_date
            }
            
            existing = collection.find_one(query)
            
            if existing:
                update_data = comedian.to_dict()
                update_data['updated_at'] = datetime.utcnow()
                
                # Preserve user-entered data
                preserve_fields = ['venmo_handle', 'payment_rate', 'payment_notes', 'sync_mode']
                for field in preserve_fields:
                    if existing.get(field) and not update_data.get(field):
                        update_data[field] = existing[field]
                
                collection.update_one(query, {"$set": update_data})
                logger.info(f"Updated comedian: {comedian.name}")
                return str(existing['_id'])
            else:
                result = collection.insert_one(comedian.to_dict())
                logger.info(f"Created comedian: {comedian.name}")
                return str(result.inserted_id)
    
    def get_comedians_by_show(self, venue: str, show_date: str) -> List[Dict[str, Any]]:
        """Get all comedians for specific show"""
        with self.db.get_collection('comedians') as collection:
            query = {"venue": venue, "show_date": show_date}
            comedians = list(collection.find(query).sort("name", 1))
            
            for comedian in comedians:
                comedian['_id'] = str(comedian['_id'])
            
            logger.info(f"Retrieved {len(comedians)} comedians for {venue} on {show_date}")
            return comedians
    
    def update_comedian_payment(self, comedian_id: str, payment_data: Dict[str, Any]) -> bool:
        """Update comedian payment information"""
        with self.db.get_collection('comedians') as collection:
            update_data = {'updated_at': datetime.utcnow()}
            
            payment_fields = ['venmo_handle', 'payment_rate', 'payment_notes']
            for field in payment_fields:
                if field in payment_data:
                    update_data[field] = payment_data[field]
            
            result = collection.update_one(
                {"_id": ObjectId(comedian_id)},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Updated payment for comedian {comedian_id}")
            else:
                logger.warning(f"No comedian found with id {comedian_id}")
            
            return success
