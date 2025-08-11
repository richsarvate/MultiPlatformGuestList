"""
Show Routes - All show-related endpoints (analytics, breakdowns, guest details)
"""

from flask import Blueprint, jsonify, request
import logging

logger = logging.getLogger(__name__)
show_bp = Blueprint('shows', __name__)

@show_bp.route('/')
def get_shows():
    """Get shows for a specific venue"""
    try:
        venue = request.args.get('venue')
        if not venue:
            return jsonify({'error': 'Venue parameter required'}), 400
        
        from ..database_service import db_service
        shows = db_service.get_venue_shows(venue, days_back=60)
        
        # Shows are already sorted by show_datetime (most recent first)
        # Format for frontend: return display format but keep datetime for breakdown queries
        formatted_shows = []
        for show in shows:
            formatted_shows.append({
                'show_date': show['show_date_display'],  # Nice formatted date for dropdown
                'show_datetime': show['show_datetime'].isoformat(),  # ISO format for API queries
                'show_date_original': show.get('show_date_original')  # Keep original for compatibility
            })
        
        result = {
            'venue': venue,
            'shows': formatted_shows
        }
        
        logger.info(f"Returned {len(formatted_shows)} shows for {venue} (sorted chronologically by show_datetime)")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error fetching shows: {e}")
        return jsonify({'error': str(e)}), 500

@show_bp.route('/breakdown')
def get_show_breakdown():
    """Get detailed breakdown for a specific show"""
    try:
        venue = request.args.get('venue')
        show_datetime_str = request.args.get('show_date')  # Actually contains ISO datetime now
        
        if not venue or not show_datetime_str:
            return jsonify({'error': 'Venue and show_date parameters required'}), 400
        
        from ..database_service import db_service
        from ..utils.analytics_utils import calculate_show_analytics
        from datetime import datetime
        
        # Parse the GMT datetime string back to datetime object
        try:
            # Handle GMT format: "Sun, 29 Jun 2025 19:30:00 GMT"
            show_datetime = datetime.strptime(show_datetime_str, "%a, %d %b %Y %H:%M:%S GMT")
        except ValueError:
            try:
                # Fallback: try ISO format
                show_datetime = datetime.fromisoformat(show_datetime_str)
            except ValueError:
                return jsonify({'error': f'Invalid datetime format: {show_datetime_str}'}), 400
        
        # Get raw data from database using datetime
        contacts = db_service.get_contacts_by_show(venue, show_datetime)
        
        if not contacts:
            return jsonify({'error': 'No data found for this show'}), 404
        
        # Calculate analytics - use datetime string for display
        show_date_display = show_datetime.strftime("%b %d, %Y %I:%M %p").replace(" 0", " ")
        analytics = calculate_show_analytics(contacts, venue, show_date_display)
        
        logger.info(f"Show breakdown for {venue} - {show_date_display}: {analytics['total_tickets']} tickets")
        return jsonify(analytics)
        
    except Exception as e:
        logger.error(f"Error getting show breakdown: {e}")
        return jsonify({'error': str(e)}), 500

@show_bp.route('/guests')
def get_guest_details():
    """Get detailed guest list for a specific show"""
    try:
        venue = request.args.get('venue')
        show_datetime_str = request.args.get('show_date')  # Actually contains ISO datetime now
        
        if not venue or not show_datetime_str:
            return jsonify({'error': 'Venue and show_date parameters required'}), 400
        
        from datetime import datetime
        # Parse the GMT datetime string back to datetime object
        try:
            # Handle GMT format: "Sun, 29 Jun 2025 19:30:00 GMT"
            show_datetime = datetime.strptime(show_datetime_str, "%a, %d %b %Y %H:%M:%S GMT")
        except ValueError:
            try:
                # Fallback: try ISO format
                show_datetime = datetime.fromisoformat(show_datetime_str)
            except ValueError:
                return jsonify({'error': f'Invalid datetime format: {show_datetime_str}'}), 400
        
        # Import from the correct location
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from ..database_service import db_service
        
        # Get contacts from database service using datetime
        contacts = db_service.get_contacts_by_show(venue, show_datetime)
        
        show_date_display = show_datetime.strftime("%b %d, %Y %I:%M %p").replace(" 0", " ")
        
        if not contacts:
            return jsonify({
                'venue': venue,
                'show_date': show_date_display,
                'contacts': [],
                'message': 'No guests found for this show'
            })
        
        response = {
            'venue': venue,
            'show_date': show_date_display,
            'total_guests': len(contacts),
            'total_tickets': sum(contact.get('tickets', 1) for contact in contacts),
            'contacts': contacts
        }
        
        logger.info(f"Guest details for {venue} - {show_date_display}: {len(contacts)} guests")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error fetching guest details: {e}")
        return jsonify({'error': str(e)}), 500
