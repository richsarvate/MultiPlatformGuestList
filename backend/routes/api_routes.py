"""
API Routes - Basic health and utility endpoints
"""

from flask import Blueprint, jsonify, request
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
api_bp = Blueprint('api', __name__)

@api_bp.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Import here to avoid circular imports
        from ..database_service import db_service
        
        health_data = db_service.health_check()
        
        response = {
            'status': health_data['status'],
            'total_records': health_data.get('total_records', 0),
            'collections': health_data.get('collections', {}),
            'mode': 'mongodb-direct',
            'timestamp': health_data.get('timestamp')
        }
        
        logger.info(f"Health check: {health_data['status']} - {health_data.get('total_records', 0)} total records")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@api_bp.route('/recent')
def get_most_recent():
    """Get the show closest to today's date across all venues"""
    try:
        from ..database_service import db_service
        from datetime import datetime
        
        # Get all venues and find the show closest to today across all venues
        venues_data = db_service.get_venues(active_only=True)
        closest_venue = None
        closest_show_display = None
        closest_datetime = None
        min_days_difference = float('inf')
        
        today = datetime.now()
        
        for venue_data in venues_data:
            venue_name = venue_data['name']
            shows = db_service.get_venue_shows(venue_name, days_back=0)  # Get all shows (no time limit)
            
            if shows:
                # Find the show with minimum distance from today
                for show in shows:
                    show_datetime = show['show_datetime']
                    if show_datetime:
                        days_difference = abs((show_datetime - today).days)
                        
                        if days_difference < min_days_difference:
                            min_days_difference = days_difference
                            closest_venue = venue_name
                            closest_show_display = show_datetime.isoformat()  # ISO format for frontend compatibility
                            closest_datetime = show_datetime
        
        result = {
            'recent_venue': closest_venue or '',
            'recent_show': closest_show_display or ''
        }
        
        logger.info(f"Closest show to today: {closest_venue} on {closest_show_display} ({min_days_difference} days away)")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error fetching recent show: {e}")
        return jsonify({'error': str(e)}), 500
