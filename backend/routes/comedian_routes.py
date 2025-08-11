"""
Comedian Routes - All comedian-related endpoints (MongoDB only, no Google Sheets)
"""

from flask import Blueprint, jsonify, request
import logging

logger = logging.getLogger(__name__)
comedian_bp = Blueprint('comedians', __name__)

@comedian_bp.route('/')
def get_comedians():
    """Get comedians for a specific show - MongoDB only"""
    try:
        venue = request.args.get('venue')
        show_date = request.args.get('show_date')
        
        if not venue or not show_date:
            return jsonify({'error': 'Venue and show_date parameters required'}), 400
        
        from ..database_service import db_service
        
        # Get comedians from MongoDB only
        comedians = db_service.get_comedians_by_show(venue, show_date)
        
        response = {
            'venue': venue,
            'show_date': show_date,
            'comedians': comedians,
            'total_comedians': len(comedians),
            'source': 'mongodb'  # Always MongoDB now
        }
        
        logger.info(f"Returned {len(comedians)} comedians for {venue} - {show_date} (MongoDB)")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error fetching comedians: {e}")
        return jsonify({'error': str(e)}), 500

@comedian_bp.route('/', methods=['POST'])
def save_comedians():
    """Save comedians for a specific show - MongoDB only"""
    try:
        data = request.get_json()
        venue = data.get('venue')
        show_date = data.get('show_date')
        comedians = data.get('comedians', [])
        
        if not venue or not show_date:
            return jsonify({'error': 'Venue and show_date required'}), 400
        
        from ..database_service import db_service
        from ..models import SyncMode
        
        # Save each comedian to MongoDB
        saved_comedians = []
        for comedian_data in comedians:
            # Ensure required fields
            comedian_data.update({
                'venue': venue,
                'show_date': show_date,
                'sync_mode': SyncMode.MANUAL.value  # Always manual since we removed Google Sheets sync
            })
            
            try:
                comedian_id = db_service.create_comedian(comedian_data)
                comedian_data['_id'] = comedian_id
                saved_comedians.append(comedian_data)
            except Exception as e:
                logger.warning(f"Failed to save comedian {comedian_data.get('name', 'unknown')}: {e}")
        
        logger.info(f"Saved {len(saved_comedians)} comedians for {venue} - {show_date} (MongoDB)")
        return jsonify({'success': True, 'comedians': saved_comedians, 'source': 'mongodb'})
            
    except Exception as e:
        logger.error(f"Error saving comedians: {e}")
        return jsonify({'error': str(e)}), 500

@comedian_bp.route('/<comedian_id>/payment', methods=['PUT'])
def update_comedian_payment(comedian_id):
    """Update comedian payment information"""
    try:
        data = request.get_json()
        payment_data = data.get('payment_data', {})
        
        from ..database_service import db_service
        success = db_service.update_comedian_payment(comedian_id, payment_data)
        
        if success:
            logger.info(f"Updated payment info for comedian {comedian_id}")
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Comedian not found or update failed'}), 404
            
    except Exception as e:
        logger.error(f"Error updating comedian payment: {e}")
        return jsonify({'error': str(e)}), 500

