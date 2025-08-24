"""
Simple Comedian Routes - Basic comedian management endpoints
"""

from flask import Blueprint, request, jsonify
import logging
from backend.database_service import db_service

logger = logging.getLogger(__name__)

# Create comedian blueprint
comedian_bp = Blueprint('comedians', __name__, url_prefix='/api/comedians')

@comedian_bp.route('/', methods=['GET'])
def get_comedians():
    """Get comedians for a specific show"""
    try:
        venue = request.args.get('venue')
        show_date = request.args.get('show_date')
        
        if not venue or not show_date:
            return jsonify({'error': 'Missing venue or show_date parameter'}), 400
        
        # Get comedians from database
        comedians = db_service.get_comedians(venue, show_date)
        
        logger.info(f"Retrieved {len(comedians)} comedians for {venue} - {show_date}")
        
        return jsonify({
            'comedians': comedians,
            'venue': venue,
            'show_date': show_date
        })
        
    except Exception as e:
        logger.error(f"Error fetching comedians: {e}")
        return jsonify({'error': 'Failed to fetch comedians'}), 500

@comedian_bp.route('/', methods=['POST'])
def save_comedians():
    """Save comedians for a specific show (replaces existing)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        venue = data.get('venue')
        show_date = data.get('show_date')
        comedians = data.get('comedians', [])
        
        if not venue or not show_date:
            return jsonify({'error': 'Missing venue or show_date'}), 400
        
        # Save comedians to database (replaces existing)
        result = db_service.save_comedians(venue, show_date, comedians)
        
        logger.info(f"Saved {len(comedians)} comedians for {venue} - {show_date}")
        
        return jsonify({
            'success': True,
            'venue': venue,
            'show_date': show_date,
            'comedians_saved': len(comedians)
        })
        
    except Exception as e:
        logger.error(f"Error saving comedians: {e}")
        return jsonify({'error': 'Failed to save comedians'}), 500