#!/usr/bin/env python3
"""
Database Service Layer
Professional MongoDB service with proper error handling and logging
"""

import json
import logging
import os
import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from bson import ObjectId
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from contextlib import contextmanager
from backend.models import Contact, Comedian, Venue, SyncJob, validate_contact, validate_comedian

# Setup logging
logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom database error"""
    pass


class DatabaseService:
    """
    Professional database service for MongoDB operations
    Handles connections, error recovery, and data operations
    """
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            # Try to find config relative to project root
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            config_path = os.path.join(project_root, "config", "bucketlistConfig.json")
        
        self.config_path = config_path
        self._client = None
        self._db = None
        self._load_config()
        self._setup_collections()
    
    def _load_config(self):
        """Load MongoDB configuration from config file"""
        try:
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)
            
            self.mongo_uri = config_data["MONGO_URI"]
            self.database_name = "guest_list_contacts"
            
            # Collection names
            self.collections = {
                'contacts': 'contacts',
                'comedians': 'comedians',
                'venues': 'venues',
                'sync_jobs': 'sync_jobs'
            }
            
            logger.info("Database configuration loaded successfully")
            
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            error_msg = f"Failed to load database configuration: {e}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)
    
    def _setup_collections(self):
        """Setup database collections with proper indexes"""
        try:
            self._ensure_connection()
            
            # Contacts collection indexes
            contacts_collection = self._db[self.collections['contacts']]
            contacts_collection.create_index([("email", 1), ("show_date", 1), ("venue", 1)], 
                                           background=True)
            contacts_collection.create_index([("venue", 1), ("show_date", 1)], background=True)
            contacts_collection.create_index([("transaction_id", 1)], sparse=True, background=True)
            contacts_collection.create_index([("order_id", 1)], sparse=True, background=True)
            
            # Comedians collection indexes
            comedians_collection = self._db[self.collections['comedians']]
            comedians_collection.create_index([("name", 1), ("venue", 1), ("show_date", 1)], 
                                            unique=True, background=True)
            comedians_collection.create_index([("venue", 1), ("show_date", 1)], background=True)
            comedians_collection.create_index([("last_synced", 1)], sparse=True, background=True)
            
            # Venues collection indexes
            venues_collection = self._db[self.collections['venues']]
            venues_collection.create_index([("name", 1)], unique=True, background=True)
            venues_collection.create_index([("active", 1)], background=True)
            
            # Sync jobs collection indexes
            sync_jobs_collection = self._db[self.collections['sync_jobs']]
            sync_jobs_collection.create_index([("job_id", 1)], unique=True, background=True)
            sync_jobs_collection.create_index([("status", 1), ("created_at", 1)], background=True)
            
            logger.info("Database collections and indexes setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup collections: {e}")
            raise DatabaseError(f"Database setup failed: {e}")
    
    def _ensure_connection(self):
        """Ensure database connection is active"""
        try:
            if self._client is None:
                self._client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
                self._db = self._client[self.database_name]
            
            # Test connection
            self._client.admin.command('ping')
            
        except ConnectionFailure as e:
            logger.error(f"Database connection failed: {e}")
            self._client = None
            self._db = None
            raise DatabaseError(f"Cannot connect to database: {e}")
    
    @contextmanager
    def get_collection(self, collection_name: str):
        """Context manager for collection operations with error handling"""
        try:
            self._ensure_connection()
            collection = self._db[self.collections[collection_name]]
            yield collection
        except Exception as e:
            logger.error(f"Collection operation failed for {collection_name}: {e}")
            raise DatabaseError(f"Database operation failed: {e}")
    
    # =================================================================
    # CONTACT OPERATIONS
    # =================================================================
    
    def create_contact(self, contact_data: Dict[str, Any]) -> str:
        """Create a new contact record"""
        try:
            contact = validate_contact(contact_data)
            
            with self.get_collection('contacts') as collection:
                # Check for duplicates
                duplicate_query = self._build_duplicate_query(contact_data)
                existing = collection.find_one(duplicate_query)
                
                if existing:
                    # Update existing record
                    update_data = contact.to_dict()
                    update_data['updated_at'] = datetime.utcnow()
                    collection.update_one(
                        duplicate_query,
                        {"$set": update_data}
                    )
                    logger.info(f"Updated existing contact: {contact.email}")
                    return str(existing['_id'])
                else:
                    # Insert new record
                    result = collection.insert_one(contact.to_dict())
                    logger.info(f"Created new contact: {contact.email}")
                    return str(result.inserted_id)
                    
        except Exception as e:
            logger.error(f"Failed to create contact: {e}")
            raise DatabaseError(f"Contact creation failed: {e}")
    
    def bulk_create_contacts(self, contacts_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Bulk create/update contact records"""
        try:
            created = 0
            updated = 0
            errors = 0
            
            with self.get_collection('contacts') as collection:
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
            
            logger.info(f"Bulk contact operation: {created} created, {updated} updated, {errors} errors")
            return {"created": created, "updated": updated, "errors": errors}
            
        except Exception as e:
            logger.error(f"Bulk contact operation failed: {e}")
            raise DatabaseError(f"Bulk contact operation failed: {e}")
    
    def get_contacts_by_show(self, venue: str, show_datetime: datetime) -> List[Dict[str, Any]]:
        """Get all contacts for a specific show using show_datetime"""
        try:
            with self.get_collection('contacts') as collection:
                query = {"venue": venue, "show_datetime": show_datetime}
                contacts = list(collection.find(query).sort("first_name", 1))
                
                # Convert ObjectId to string
                for contact in contacts:
                    contact['_id'] = str(contact['_id'])
                
                logger.info(f"Retrieved {len(contacts)} contacts for {venue} on {show_datetime}")
                return contacts
                
        except Exception as e:
            logger.error(f"Failed to get contacts for show: {e}")
            raise DatabaseError(f"Failed to retrieve contacts: {e}")
    
    def _build_duplicate_query(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build query for duplicate detection"""
        # Priority order for duplicate detection
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
    
    # =================================================================
    # COMEDIAN OPERATIONS
    # =================================================================
    
    def create_comedian(self, comedian_data: Dict[str, Any]) -> str:
        """Create or update comedian record"""
        try:
            comedian = validate_comedian(comedian_data)
            
            with self.get_collection('comedians') as collection:
                query = {
                    "name": comedian.name,
                    "venue": comedian.venue,
                    "show_date": comedian.show_date
                }
                
                existing = collection.find_one(query)
                
                if existing:
                    # Update existing record, preserving user-entered data
                    update_data = comedian.to_dict()
                    update_data['updated_at'] = datetime.utcnow()
                    
                    # Preserve important user data if it exists
                    preserve_fields = ['venmo_handle', 'payment_rate', 'payment_notes', 'sync_mode']
                    for field in preserve_fields:
                        if existing.get(field) and not update_data.get(field):
                            update_data[field] = existing[field]
                    
                    collection.update_one(query, {"$set": update_data})
                    logger.info(f"Updated comedian: {comedian.name}")
                    return str(existing['_id'])
                else:
                    # Insert new record
                    result = collection.insert_one(comedian.to_dict())
                    logger.info(f"Created new comedian: {comedian.name}")
                    return str(result.inserted_id)
                    
        except Exception as e:
            logger.error(f"Failed to create comedian: {e}")
            raise DatabaseError(f"Comedian creation failed: {e}")
    
    def get_comedians_by_show(self, venue: str, show_date: str) -> List[Dict[str, Any]]:
        """Get all comedians for a specific show"""
        try:
            with self.get_collection('comedians') as collection:
                query = {"venue": venue, "show_date": show_date}
                comedians = list(collection.find(query).sort("name", 1))
                
                # Convert ObjectId to string
                for comedian in comedians:
                    comedian['_id'] = str(comedian['_id'])
                
                logger.info(f"Retrieved {len(comedians)} comedians for {venue} on {show_date}")
                return comedians
                
        except Exception as e:
            logger.error(f"Failed to get comedians for show: {e}")
            raise DatabaseError(f"Failed to retrieve comedians: {e}")
    
    def update_comedian_payment(self, comedian_id: str, payment_data: Dict[str, Any]) -> bool:
        """Update comedian payment information"""
        try:
            with self.get_collection('comedians') as collection:
                update_data = {
                    'updated_at': datetime.utcnow()
                }
                
                # Add payment fields if provided
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
                    logger.info(f"Updated payment info for comedian {comedian_id}")
                else:
                    logger.warning(f"No comedian found with id {comedian_id}")
                
                return success
                
        except Exception as e:
            logger.error(f"Failed to update comedian payment: {e}")
            raise DatabaseError(f"Payment update failed: {e}")
    
    # =================================================================
    # VENUE OPERATIONS  
    # =================================================================
    
    def get_venues(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all venues"""
        try:
            with self.get_collection('venues') as collection:
                query = {"active": True} if active_only else {}
                venues = list(collection.find(query).sort("name", 1))
                
                # Convert ObjectId to string
                for venue in venues:
                    venue['_id'] = str(venue['_id'])
                
                logger.info(f"Retrieved {len(venues)} venues")
                return venues
                
        except Exception as e:
            logger.error(f"Failed to get venues: {e}")
            raise DatabaseError(f"Failed to retrieve venues: {e}")
    
    def get_venue_shows(self, venue: str, days_back: int = 30) -> List[Dict[str, Any]]:
        """Get distinct show dates for a venue, sorted chronologically using show_datetime"""
        try:
            with self.get_collection('contacts') as collection:
                # Get all distinct show_datetime values for the venue, sorted chronologically
                pipeline = [
                    {"$match": {"venue": venue, "show_datetime": {"$ne": None}}},
                    {"$group": {
                        "_id": "$show_datetime",
                        "show_date": {"$first": "$show_date"}  # Keep original for display
                    }},
                    {"$sort": {"_id": 1}}  # Sort by datetime ascending (oldest first)
                ]
                
                result = list(collection.aggregate(pipeline))
                
                # Filter by date range if specified
                if days_back > 0:
                    cutoff_date = datetime.now() - timedelta(days=days_back)
                    result = [doc for doc in result if doc['_id'] >= cutoff_date]
                
                # Return both datetime and formatted display
                shows = []
                for doc in result:
                    dt = doc['_id']
                    # Format as "Aug 30, 2025 9:00 PM"
                    formatted_date = dt.strftime("%b %d, %Y %I:%M %p").replace(" 0", " ").replace("  ", " ")
                    shows.append({
                        'show_datetime': dt,
                        'show_date_display': formatted_date,
                        'show_date_original': doc['show_date']  # Keep for backwards compatibility
                    })
                
                logger.info(f"Retrieved {len(shows)} recent shows for {venue} (using show_datetime)")
                return shows
                
        except Exception as e:
            logger.error(f"Failed to get venue shows: {e}")
            raise DatabaseError(f"Failed to retrieve venue shows: {e}")
    
    # =================================================================
    # SYNC JOB OPERATIONS
    # =================================================================
    
    def create_sync_job(self, job_type: str) -> str:
        """Create a new sync job record"""
        try:
            import uuid
            
            sync_job = SyncJob(
                job_id=str(uuid.uuid4()),
                job_type=job_type,
                status="pending"
            )
            
            with self.get_collection('sync_jobs') as collection:
                result = collection.insert_one(sync_job.to_dict())
                logger.info(f"Created sync job: {sync_job.job_id}")
                return sync_job.job_id
                
        except Exception as e:
            logger.error(f"Failed to create sync job: {e}")
            raise DatabaseError(f"Sync job creation failed: {e}")
    
    def update_sync_job(self, job_id: str, update_data: Dict[str, Any]) -> bool:
        """Update sync job status and details"""
        try:
            with self.get_collection('sync_jobs') as collection:
                update_data['updated_at'] = datetime.utcnow()
                
                result = collection.update_one(
                    {"job_id": job_id},
                    {"$set": update_data}
                )
                
                success = result.modified_count > 0
                if success:
                    logger.info(f"Updated sync job: {job_id}")
                
                return success
                
        except Exception as e:
            logger.error(f"Failed to update sync job: {e}")
            raise DatabaseError(f"Sync job update failed: {e}")
    
    def get_recent_sync_jobs(self, job_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent sync jobs"""
        try:
            with self.get_collection('sync_jobs') as collection:
                query = {"job_type": job_type} if job_type else {}
                jobs = list(collection.find(query).sort("created_at", -1).limit(limit))
                
                # Convert ObjectId to string
                for job in jobs:
                    job['_id'] = str(job['_id'])
                
                logger.info(f"Retrieved {len(jobs)} sync jobs")
                return jobs
                
        except Exception as e:
            logger.error(f"Failed to get sync jobs: {e}")
            raise DatabaseError(f"Failed to retrieve sync jobs: {e}")
    
    # =================================================================
    # ANALYTICS AND REPORTING
    # =================================================================
    
    def get_show_analytics(self, venue: str, show_date: str) -> Dict[str, Any]:
        """Get comprehensive show analytics"""
        try:
            with self.get_collection('contacts') as collection:
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
                
        except Exception as e:
            logger.error(f"Failed to get show analytics: {e}")
            raise DatabaseError(f"Analytics generation failed: {e}")
    
    def get_guests_for_show(self, venue: str, show_date: str) -> List[Dict[str, Any]]:
        """Get all guests/contacts for a specific show using show_date string"""
        try:
            with self.get_collection('contacts') as collection:
                query = {"venue": venue, "show_date": show_date}
                contacts = list(collection.find(query).sort("first_name", 1))
                
                # Convert ObjectId to string
                for contact in contacts:
                    contact['_id'] = str(contact['_id'])
                
                logger.info(f"Retrieved {len(contacts)} guests for {venue} on {show_date}")
                return contacts
                
        except Exception as e:
            logger.error(f"Failed to get guests for show: {e}")
            raise DatabaseError(f"Failed to retrieve guests: {e}")

    def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        try:
            self._ensure_connection()
            
            # Get collection stats
            with self.get_collection('contacts') as contacts_collection:
                contact_count = contacts_collection.count_documents({})
                
            with self.get_collection('comedians') as comedians_collection:
                comedian_count = comedians_collection.count_documents({})
                
            with self.get_collection('venues') as venues_collection:
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


# Global database service instance
db_service = DatabaseService()
