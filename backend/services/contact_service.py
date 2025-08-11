#!/usr/bin/env python3
"""
Contact operations for database
"""

import logging
from typing import Dict, List, Any
from datetime import datetime
from backend.models import validate_contact
from backend.services.database_connection import DatabaseConnection, DatabaseError

logger = logging.getLogger(__name__)

class ContactService:
    """Handles all contact-related database operations"""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
    def create_contact(self, contact_data: Dict[str, Any]) -> str:
        """Create or update contact record"""
        contact = validate_contact(contact_data)
        
        with self.db.get_collection('contacts') as collection:
            duplicate_query = self._build_duplicate_query(contact_data)
            existing = collection.find_one(duplicate_query)
            
            if existing:
                update_data = contact.to_dict()
                update_data['updated_at'] = datetime.utcnow()
                collection.update_one(duplicate_query, {"$set": update_data})
                logger.info(f"Updated contact: {contact.email}")
                return str(existing['_id'])
            else:
                result = collection.insert_one(contact.to_dict())
                logger.info(f"Created contact: {contact.email}")
                return str(result.inserted_id)
    
    def bulk_create_contacts(self, contacts_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Bulk create/update contact records"""
        created = updated = errors = 0
        
        with self.db.get_collection('contacts') as collection:
            for contact_data in contacts_data:
                try:
                    contact = validate_contact(contact_data)
                    duplicate_query = self._build_duplicate_query(contact_data)
                    existing = collection.find_one(duplicate_query)
                    
                    if existing:
                        update_data = contact.to_dict()
                        update_data['updated_at'] = datetime.utcnow()
                        collection.update_one(duplicate_query, {"$set": update_data})
                        updated += 1
                    else:
                        collection.insert_one(contact.to_dict())
                        created += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to process contact {contact_data.get('email', 'unknown')}: {e}")
                    errors += 1
        
        logger.info(f"Bulk operation: {created} created, {updated} updated, {errors} errors")
        return {"created": created, "updated": updated, "errors": errors}
    
    def get_contacts_by_show(self, venue: str, show_datetime: datetime) -> List[Dict[str, Any]]:
        """Get contacts for specific show using show_datetime"""
        with self.db.get_collection('contacts') as collection:
            query = {"venue": venue, "show_datetime": show_datetime}
            contacts = list(collection.find(query).sort("first_name", 1))
            
            for contact in contacts:
                contact['_id'] = str(contact['_id'])
            
            logger.info(f"Retrieved {len(contacts)} contacts for {venue} on {show_datetime}")
            return contacts
    
    def get_guests_for_show(self, venue: str, show_date: str) -> List[Dict[str, Any]]:
        """Get guests for specific show using show_date string"""
        with self.db.get_collection('contacts') as collection:
            query = {"venue": venue, "show_date": show_date}
            contacts = list(collection.find(query).sort("first_name", 1))
            
            for contact in contacts:
                contact['_id'] = str(contact['_id'])
            
            logger.info(f"Retrieved {len(contacts)} guests for {venue} on {show_date}")
            return contacts
    
    def _build_duplicate_query(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build query for duplicate detection"""
        if contact_data.get('transaction_id'):
            return {"transaction_id": contact_data['transaction_id']}
        elif contact_data.get('order_id'):
            return {"order_id": contact_data['order_id']}
        else:
            return {
                "email": contact_data['email'],
                "show_date": contact_data['show_date'],
                "venue": contact_data['venue']
            }
