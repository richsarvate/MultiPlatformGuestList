#!/usr/bin/env python3
"""
Database connection and configuration management
"""

import json
import logging
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from contextlib import contextmanager
from typing import Dict

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Custom database error"""
    pass

class DatabaseConnection:
    """Manages MongoDB connection and configuration"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            config_path = os.path.join(project_root, "config", "bucketlistConfig.json")
        
        self.config_path = config_path
        self._client = None
        self._db = None
        self._load_config()
        self._setup_collections()
    
    def _load_config(self):
        """Load MongoDB configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)
            
            self.mongo_uri = config_data["MONGO_URI"]
            self.database_name = "guest_list_contacts"
            self.collections = {
                'contacts': 'contacts',
                'comedians': 'comedians', 
                'venues': 'venues',
                'sync_jobs': 'sync_jobs'
            }
            logger.info("Database configuration loaded")
            
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            raise DatabaseError(f"Config loading failed: {e}")
    
    def _setup_collections(self):
        """Setup database collections and indexes"""
        try:
            self._ensure_connection()
            
            # Contacts indexes
            contacts = self._db[self.collections['contacts']]
            contacts.create_index([("email", 1), ("show_date", 1), ("venue", 1)], background=True)
            contacts.create_index([("venue", 1), ("show_date", 1)], background=True)
            contacts.create_index([("transaction_id", 1)], sparse=True, background=True)
            contacts.create_index([("order_id", 1)], sparse=True, background=True)
            
            # Comedians indexes
            comedians = self._db[self.collections['comedians']]
            comedians.create_index([("name", 1), ("venue", 1), ("show_date", 1)], unique=True, background=True)
            comedians.create_index([("venue", 1), ("show_date", 1)], background=True)
            
            # Venues indexes
            venues = self._db[self.collections['venues']]
            venues.create_index([("name", 1)], unique=True, background=True)
            venues.create_index([("active", 1)], background=True)
            
            # Sync jobs indexes
            jobs = self._db[self.collections['sync_jobs']]
            jobs.create_index([("job_id", 1)], unique=True, background=True)
            jobs.create_index([("status", 1), ("created_at", 1)], background=True)
            
            logger.info("Database collections setup completed")
            
        except Exception as e:
            raise DatabaseError(f"Database setup failed: {e}")
    
    def _ensure_connection(self):
        """Ensure active database connection"""
        try:
            if self._client is None:
                self._client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
                self._db = self._client[self.database_name]
            
            self._client.admin.command('ping')
            
        except ConnectionFailure as e:
            self._client = None
            self._db = None
            raise DatabaseError(f"Cannot connect to database: {e}")
    
    @contextmanager
    def get_collection(self, collection_name: str):
        """Context manager for collection operations"""
        try:
            self._ensure_connection()
            collection = self._db[self.collections[collection_name]]
            yield collection
        except Exception as e:
            logger.error(f"Collection operation failed for {collection_name}: {e}")
            raise DatabaseError(f"Database operation failed: {e}")
