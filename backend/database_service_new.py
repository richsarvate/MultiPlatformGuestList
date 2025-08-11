#!/usr/bin/env python3
"""
Main database service - simplified and modular
"""

from backend.services.database_connection import DatabaseConnection
from backend.services.contact_service import ContactService  
from backend.services.comedian_service import ComedianService
from backend.services.analytics_service import AnalyticsService
from backend.services.sync_job_service import SyncJobService

class DatabaseService:
    """Main database service with focused service components"""
    
    def __init__(self, config_path: str = None):
        self.connection = DatabaseConnection(config_path)
        self.contacts = ContactService(self.connection)
        self.comedians = ComedianService(self.connection)
        self.analytics = AnalyticsService(self.connection)
        self.sync_jobs = SyncJobService(self.connection)
    
    # Contact operations
    def create_contact(self, contact_data):
        return self.contacts.create_contact(contact_data)
    
    def bulk_create_contacts(self, contacts_data):
        return self.contacts.bulk_create_contacts(contacts_data)
    
    def get_contacts_by_show(self, venue, show_datetime):
        return self.contacts.get_contacts_by_show(venue, show_datetime)
    
    def get_guests_for_show(self, venue, show_date):
        return self.contacts.get_guests_for_show(venue, show_date)
    
    # Comedian operations
    def create_comedian(self, comedian_data):
        return self.comedians.create_comedian(comedian_data)
    
    def get_comedians_by_show(self, venue, show_date):
        return self.comedians.get_comedians_by_show(venue, show_date)
    
    def update_comedian_payment(self, comedian_id, payment_data):
        return self.comedians.update_comedian_payment(comedian_id, payment_data)
    
    # Analytics operations
    def get_show_analytics(self, venue, show_date):
        return self.analytics.get_show_analytics(venue, show_date)
    
    def get_venues(self, active_only=True):
        return self.analytics.get_venues(active_only)
    
    def get_venue_shows(self, venue, days_back=30):
        return self.analytics.get_venue_shows(venue, days_back)
    
    def health_check(self):
        return self.analytics.health_check()
    
    # Sync job operations
    def create_sync_job(self, job_type):
        return self.sync_jobs.create_sync_job(job_type)
    
    def update_sync_job(self, job_id, update_data):
        return self.sync_jobs.update_sync_job(job_id, update_data)
    
    def get_recent_sync_jobs(self, job_type=None, limit=10):
        return self.sync_jobs.get_recent_sync_jobs(job_type, limit)

# Global instance
db_service = DatabaseService()
