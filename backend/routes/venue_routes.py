"""
Venue Routes - All venue-related endpoints
"""

from flask import Blueprint, jsonify, request
import logging

logger = logging.getLogger(__name__)
venue_bp = Blueprint('venues', __name__)

@venue_bp.route('/')
def get_venues():
    """Get all available venues from MongoDB"""
    try:
        from ..database_service import db_service
        
        venues_data = db_service.get_venues(active_only=True)
        venue_names = [venue['name'] for venue in venues_data]
        
        logger.info(f"Returned {len(venue_names)} venues from database")
        return jsonify({'venues': venue_names})
        
    except Exception as e:
        logger.error(f"Error fetching venues: {e}")
        return jsonify({'error': str(e)}), 500

@venue_bp.route('/<venue_name>/payment-info')
def get_venue_payment_info(venue_name):
    """Get payment information for a venue"""
    try:
        import json
        
        # Load venue payment configuration from file
        try:
            with open('config/payment_config.json', 'r') as f:
                config_data = json.load(f)
                venue_payment_info = config_data.get('venues', {})
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Could not load payment config: {e}")
            # Fallback to hardcoded configuration
            venue_payment_info = {
                'Palace': {
                    'payment_method': 'zelle',
                    'zelle_email': 'geoffrey.libby@tptsf.com',
                    'payment_name': 'Palace Theatre',
                    'instructions': 'Send Zelle payment with show date in memo'
                },
                'Church': {
                    'payment_method': 'flat_rate',
                    'amount': 700.00,
                    'instructions': 'Flat rate venue rental - contact venue for payment details'
                },
                'Citizen': {
                    'payment_method': 'none',
                    'instructions': 'No venue payment required'
                }
            }
        
        # Find matching venue configuration
        payment_info = None
        for venue_key in venue_payment_info:
            if venue_key.lower() in venue_name.lower():
                payment_info = venue_payment_info[venue_key]
                break
        
        if not payment_info:
            payment_info = {
                'payment_method': 'unknown',
                'instructions': 'Payment method not configured for this venue'
            }
        
        return jsonify({
            'venue': venue_name,
            'payment_info': payment_info
        })
        
    except Exception as e:
        logger.error(f"Error getting venue payment info: {e}")
        return jsonify({'error': str(e)}), 500

@venue_bp.route('/<venue_name>/payment', methods=['PUT'])
def update_venue_payment(venue_name):
    """Update venue payment status"""
    try:
        data = request.get_json()
        show_date = data.get('show_date')
        paid_status = data.get('paid', False)
        
        if not show_date:
            return jsonify({'error': 'show_date required'}), 400
        
        from ..utils.payment_utils import update_venue_payment_status
        success = update_venue_payment_status(venue_name, show_date, paid_status)
        
        if success:
            logger.info(f"Updated venue payment status for {venue_name} - {show_date}")
            return jsonify({'success': True, 'paid': paid_status})
        else:
            return jsonify({'error': 'Failed to update venue payment status'}), 500
            
    except Exception as e:
        logger.error(f"Error updating venue payment: {e}")
        return jsonify({'error': str(e)}), 500
