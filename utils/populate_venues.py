#!/usr/bin/env python3
"""
Venue Population Script
Extracts venue names from existing contacts and creates venue records
"""

import logging
from backend.database_service import db_service
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def populate_venues_from_contacts():
    """
    Extract unique venue names from existing contacts and create venue records
    """
    try:
        # Get health check to see current state
        health = db_service.health_check()
        logger.info(f"Database health: {health['status']}")
        logger.info(f"Current records: {health.get('collections', {})}")
        
        # Get all contacts to extract venue names using context manager
        with db_service.get_collection('contacts') as contacts_collection:
            unique_venues = contacts_collection.distinct('venue')
        
        logger.info(f"Found {len(unique_venues)} unique venue names in contacts: {unique_venues}")
        
        if not unique_venues:
            logger.warning("No venues found in contacts. Make sure contacts collection has venue data.")
            return
        
        # Create venue records
        venues_created = 0
        with db_service.get_collection('venues') as venues_collection:
            for venue_name in unique_venues:
                if not venue_name or venue_name.strip() == '':
                    continue
                    
                venue_name = venue_name.strip()
                
                # Check if venue already exists
                existing_venue = venues_collection.find_one({'name': venue_name})
                
                if existing_venue:
                    logger.info(f"Venue '{venue_name}' already exists")
                    continue
                
                # Create new venue record
                venue_data = {
                    'name': venue_name,
                    'active': True,
                    'city': 'Unknown',  # Can be updated later
                    'state': 'Unknown',  # Can be updated later
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
                
                result = venues_collection.insert_one(venue_data)
                if result.inserted_id:
                    venues_created += 1
                    logger.info(f"Created venue: {venue_name}")
                else:
                    logger.error(f"Failed to create venue: {venue_name}")
        
        logger.info(f"Successfully created {venues_created} venue records")
        
        # Get updated health check
        health = db_service.health_check()
        logger.info(f"Updated database stats: {health.get('collections', {})}")
        
        return venues_created
        
    except Exception as e:
        logger.error(f"Error populating venues: {e}")
        raise


if __name__ == "__main__":
    try:
        venues_created = populate_venues_from_contacts()
        print(f"\n🎉 Successfully populated {venues_created} venues!")
        print("\nYour dashboard should now show venues. Try refreshing the web page.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Check the logs for more details.")
