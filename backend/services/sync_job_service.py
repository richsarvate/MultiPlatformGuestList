#!/usr/bin/env python3
"""
Sync job operations for database
"""

import uuid
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from backend.models import SyncJob
from backend.services.database_connection import DatabaseConnection

logger = logging.getLogger(__name__)

class SyncJobService:
    """Handles sync job operations"""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
    def create_sync_job(self, job_type: str) -> str:
        """Create new sync job record"""
        sync_job = SyncJob(
            job_id=str(uuid.uuid4()),
            job_type=job_type,
            status="pending"
        )
        
        with self.db.get_collection('sync_jobs') as collection:
            result = collection.insert_one(sync_job.to_dict())
            logger.info(f"Created sync job: {sync_job.job_id}")
            return sync_job.job_id
    
    def update_sync_job(self, job_id: str, update_data: Dict[str, Any]) -> bool:
        """Update sync job status and details"""
        with self.db.get_collection('sync_jobs') as collection:
            update_data['updated_at'] = datetime.utcnow()
            
            result = collection.update_one(
                {"job_id": job_id},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Updated sync job: {job_id}")
            
            return success
    
    def get_recent_sync_jobs(self, job_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent sync jobs"""
        with self.db.get_collection('sync_jobs') as collection:
            query = {"job_type": job_type} if job_type else {}
            jobs = list(collection.find(query).sort("created_at", -1).limit(limit))
            
            for job in jobs:
                job['_id'] = str(job['_id'])
            
            logger.info(f"Retrieved {len(jobs)} sync jobs")
            return jobs
