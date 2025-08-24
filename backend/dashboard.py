#!/usr/bin/env python3
"""
Show Analytics Dashboard - Clean and Simple
"""

import os
import sys
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, request

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Importing database service...")
from backend.database_service import db_service
print("Database service imported successfully")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app with correct paths
template_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'templates')
static_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'static')

print(f"Template path: {template_path}")
print(f"Static path: {static_path}")

app = Flask(__name__, template_folder=template_path, static_folder=static_path)

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/venues')
def get_venues():
    """Get all available venues"""
    try:
        venues_data = db_service.get_venues(active_only=True)
        venue_names = [venue['name'] for venue in venues_data]
        
        logger.info(f"Returned {len(venue_names)} venues")
        return jsonify({'venues': venue_names})
        
    except Exception as e:
        logger.error(f"Error fetching venues: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recent')
def get_most_recent():
    """Get the most recent venue and show combination"""
    try:
        venues_data = db_service.get_venues(active_only=True)
        recent_venue = None
        recent_show_datetime = None
        recent_show_display = None
        
        for venue_data in venues_data:
            venue_name = venue_data['name']
            shows = db_service.get_venue_shows(venue_name, days_back=30)
            
            if shows:
                # Get the most recent show (shows are sorted oldest first, so take the last one)
                latest_show = shows[-1]  # Last item = most recent
                show_datetime = latest_show['show_datetime']
                
                if not recent_show_datetime or show_datetime > recent_show_datetime:
                    recent_venue = venue_name
                    recent_show_datetime = show_datetime
                    recent_show_display = latest_show['show_date_original']  # Use original format for consistency
        
        result = {
            'recent_venue': recent_venue or '',
            'recent_show': recent_show_display or ''
        }
        
        logger.info(f"Recent show: {recent_venue} on {recent_show_display}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error fetching recent show: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/shows')
def get_shows():
    """Get shows for a specific venue"""
    try:
        venue = request.args.get('venue')
        if not venue:
            return jsonify({'error': 'Venue parameter required'}), 400
        
        shows = db_service.get_venue_shows(venue, days_back=60)
        
        result = {
            'venue': venue,
            'shows': shows
        }
        
        logger.info(f"Returned {len(shows)} shows for {venue}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error fetching shows: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/show-breakdown')
def get_show_breakdown():
    """Get detailed breakdown for a specific show"""
    try:
        venue = request.args.get('venue')
        show_date = request.args.get('show_date')
        
        if not venue or not show_date:
            return jsonify({'error': 'Venue and show_date parameters required'}), 400
        
        # Get show analytics
        analytics = db_service.get_show_analytics(venue, show_date)
        
        if not analytics['by_source']:
            return jsonify({'error': 'No data found for this show'}), 404
        
        # Get guests for processing fees calculation
        guests = db_service.get_guests_for_show(venue, show_date)
        
        # Calculate processing fees by source
        processing_fees = {}
        total_processing_fees = 0
        
        for guest in guests:
            source = guest.get('source', 'Manual')
            price = float(guest.get('total_price', 0))
            
            # Calculate fee based on source
            fee = 0
            if source.lower() in ['squarespace', 'ss']:
                fee = price * 0.029 + 0.30  # Stripe: 2.9% + $0.30
            elif source.lower() in ['eventbrite', 'eb']:
                fee = price * 0.037 + 1.79  # Eventbrite: 3.7% + $1.79
            elif source.lower() in ['bucketlist', 'bl', 'fever']:
                fee = price * 0.25  # 25% commission
            
            if fee > 0:
                if source not in processing_fees:
                    processing_fees[source] = 0
                processing_fees[source] += fee
                total_processing_fees += fee
        
        # Round fees
        for source in processing_fees:
            processing_fees[source] = round(processing_fees[source], 2)
        total_processing_fees = round(total_processing_fees, 2)
        
        # Build response
        breakdown = {
            'venue': venue,
            'show_date': show_date,
            'total_tickets': analytics['total_tickets'],
            'total_attendees': analytics['total_attendees'], 
            'total_revenue': analytics['total_revenue'],
            'processing_fees': total_processing_fees,
            'net_revenue': analytics['total_revenue'] - total_processing_fees,
            'venue_cost': 0,  # Simplified for now
            'by_source': {item['_id']: {
                'tickets': item['total_tickets'],
                'attendees': item['total_attendees'],
                'revenue': item['total_revenue']
            } for item in analytics['by_source']},
            'revenue_breakdown': {
                'gross_revenue': analytics['total_revenue'],
                'processing_fees': total_processing_fees,
                'net_revenue': analytics['total_revenue'] - total_processing_fees
            },
            'processing_fees_by_source': processing_fees
        }
        
        logger.info(f"Breakdown for {venue} - {show_date}: ${analytics['total_revenue']} gross, ${total_processing_fees} fees")
        return jsonify(breakdown)
        
    except Exception as e:
        logger.error(f"Error getting show breakdown: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/guest-details')
def get_guest_details():
    """Get guest details for a specific venue and show date"""
    try:
        venue = request.args.get('venue')
        show_date = request.args.get('show_date')
        
        if not venue or not show_date:
            return jsonify({'error': 'Venue and show_date parameters required'}), 400
        
        guests = db_service.get_guests_for_show(venue, show_date)
        
        logger.info(f"Returned {len(guests)} guests for {venue} - {show_date}")
        return jsonify({'guests': guests})
        
    except Exception as e:
        logger.error(f"Error getting guest details: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    try:
        health_result = db_service.health_check()
        
        # Return the full health check result from the database service
        return jsonify(health_result)
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    print("Starting Show Analytics Dashboard...")
    print("Dashboard will be available at: http://localhost:8080")
    print("Checking database connection...")
    
    # Test database connection
    try:
        print("Testing database connection...")
        health_result = db_service.health_check()
        print(f"Database health check result: {health_result}")
        
        if health_result['status'] == 'healthy':
            print(f"✅ MongoDB connected successfully - {health_result['total_records']} total records")
        else:
            print(f"❌ MongoDB connection failed: {health_result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        import traceback
        traceback.print_exc()
    
    print("Starting Flask application...")
    app.run(host='0.0.0.0', port=8080, debug=True)
