"""
Payment Utilities - Handle venue and comedian payment operations
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def update_venue_payment_status(venue: str, show_date: str, paid_status: bool) -> bool:
    """Update venue payment status for a specific show"""
    try:
        from ..database_service import db_service
        
        # Ensure required contact fields
        payment_data = {
            'venue': venue,
            'show_date': show_date,
            'type': 'venue_payment',
            'venue_paid': paid_status,
            'venue_payment_date': datetime.now() if paid_status else None,
            'updated_at': datetime.now()
        }
        
        # Use database service to save
        result = db_service.upsert_venue_payment(venue, show_date, payment_data)
        
        logger.info(f"Updated venue payment status for {venue} - {show_date}: {paid_status}")
        return result
        
    except Exception as e:
        logger.error(f"Error updating venue payment status: {e}")
        return False

def get_venue_payment_status(venue: str, show_date: str) -> bool:
    """Get venue payment status for a specific show"""
    try:
        from ..database_service import db_service
        
        payment_data = db_service.get_venue_payment(venue, show_date)
        
        if payment_data:
            return payment_data.get('venue_paid', False)
        else:
            return False
            
    except Exception as e:
        logger.error(f"Error getting venue payment status: {e}")
        return False
