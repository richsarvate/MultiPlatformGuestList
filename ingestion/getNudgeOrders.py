#!/usr/bin/env python3
"""
Nudge Orders Sync - Fetch ticket purchases from Nudge API
"""
import requests
import csv
import logging
import os
import sys
from io import StringIO
from datetime import datetime
from pymongo import MongoClient
from insertIntoGoogleSheet import insert_guest_data_efficient
from getVenueAndDate import get_venue
from shared_config import get_mongo_config

# Ensure we're running from the correct directory
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
os.chdir(project_root)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/get_nudge_log.txt'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

PARTNER_ID = 15

def load_cookie():
    """Read Nudge session cookie from file"""
    try:
        with open('secrets/nudge-session-cookie.txt', 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.error("Cookie file not found: secrets/nudge-session-cookie.txt")
        return None

def get_existing_order_ids():
    """Fetch existing order_id values from Nudge collection for deduplication"""
    mongo_config = get_mongo_config()
    if not mongo_config:
        logger.warning("No MongoDB config - skipping deduplication")
        return set()
    
    try:
        client = MongoClient(mongo_config["mongo_uri"])
        db = client["guest_list_contacts"]
        collection = db["Nudge"]
        
        # Get all order_id values
        existing = collection.find({}, {"order_id": 1})
        order_ids = {doc["order_id"] for doc in existing if "order_id" in doc}
        
        logger.info(f"Found {len(order_ids)} existing Nudge orders in MongoDB")
        return order_ids
    except Exception as e:
        logger.error(f"Error fetching existing orders: {e}")
        return set()
    finally:
        if 'client' in locals():
            client.close()

def fetch_ticket_uuids(session, include_historical=False):
    """Get all ticket UUIDs from Nudge API with event metadata"""
    url = f"https://www.nudgetext.com/api/v2/tickets?partnerId={PARTNER_ID}"
    response = session.get(url)
    
    if response.status_code == 401:
        logger.error("Cookie expired - refresh at nudgetext.com/partners/dashboard")
        return None
    
    if response.status_code != 200:
        logger.error(f"Failed to fetch tickets: {response.status_code}")
        return None
    
    data = response.json()
    
    # Build metadata dict: {ticket_uuid: {eventDate, locationString, eventName}}
    ticket_metadata = {}
    for item in data.get('tickets', []):
        ticket = item.get('ticket', {})
        event = item.get('ticketedEvent', {})
        ticket_uuid = ticket.get('uuid')
        
        if ticket_uuid:
            ticket_metadata[ticket_uuid] = {
                'eventDate': ticket.get('eventDate'),  # ISO timestamp
                'locationString': event.get('locationString', ''),
                'eventName': event.get('name', ''),
                'eventUuid': event.get('uuid', '')
            }
    
    # Add historical tickets if requested
    if include_historical:
        import json
        import os
        historical_file = 'docs/NudgeInfo/all_nudge_tickets.json'
        if os.path.exists(historical_file):
            with open(historical_file, 'r') as f:
                historical_tickets = json.load(f)
                for ticket_uuid, ticket_info in historical_tickets.items():
                    if ticket_uuid not in ticket_metadata:
                        # Historical format has 'location' field
                        ticket_metadata[ticket_uuid] = {
                            'eventDate': None,  # Historical don't have dates in old format
                            'locationString': ticket_info.get('location', ''),
                            'eventName': ticket_info.get('name', ''),
                            'eventUuid': ''
                        }
                logger.info(f"Added {len(historical_tickets)} historical ticket UUIDs")
        else:
            logger.warning(f"Historical tickets file not found: {historical_file}")
    
    logger.info(f"Found {len(ticket_metadata)} total ticket types with metadata")
    return ticket_metadata

def fetch_purchases(session, ticket_metadata):
    """Fetch purchase data for each ticket UUID and attach event metadata"""
    all_purchases = []
    
    for ticket_uuid, metadata in ticket_metadata.items():
        url = "https://www.nudgetext.com/api/v2/tickets/report"
        payload = {"ticketUuids": [ticket_uuid]}
        
        response = session.post(url, json=payload)
        
        if response.status_code != 200:
            logger.warning(f"Failed to fetch purchases for {ticket_uuid}: {response.status_code}")
            continue
        
        # Parse CSV response and attach event metadata
        csv_reader = csv.DictReader(StringIO(response.text))
        
        for row in csv_reader:
            # Skip empty rows (unsold inventory)
            if not row.get('Email'):
                continue
            # Attach event metadata from API
            row['_event_date'] = metadata.get('eventDate')
            row['_location_string'] = metadata.get('locationString', '')
            row['_event_name'] = metadata.get('eventName', '')
            all_purchases.append(row)
    
    logger.info(f"Fetched {len(all_purchases)} total purchases with event metadata")
    return all_purchases

def transform_purchases(purchases, existing_order_ids, venue_filter=None):
    """Transform Nudge CSV data into guest_data format, filtering duplicates"""
    guest_data = []
    duplicates = 0
    
    for purchase in purchases:
        ticket_code = purchase['Ticket Code']
        
        # Skip duplicates
        if ticket_code in existing_order_ids:
            duplicates += 1
            logger.debug(f"Skipping duplicate: {ticket_code}")
            continue
        
        # Get venue from event metadata (set during fetch)
        location_string = purchase.get('_location_string', '')
        venue = get_venue(location_string) if location_string else None
        
        if not venue:
            logger.warning(f"No venue found for ticket {ticket_code}, location: {location_string}")
            continue
        
        # Apply venue filter if specified
        if venue_filter and venue.lower() != venue_filter.lower():
            continue
        
        # Parse event date from ISO timestamp (not purchase date!)
        event_date_iso = purchase.get('_event_date')
        if event_date_iso:
            try:
                # Parse ISO format: "2025-12-06T21:30:00.000-08:00"
                from dateutil import parser
                event_dt = parser.isoparse(event_date_iso)
                # Format: "Saturday December 6th 9pm 2025" with actual time
                day_name = event_dt.strftime("%A")
                month_name = event_dt.strftime("%B")
                day_num = event_dt.day
                # Add ordinal suffix (1st, 2nd, 3rd, 4th, etc.)
                if 10 <= day_num % 100 <= 20:
                    suffix = 'th'
                else:
                    suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day_num % 10, 'th')
                year = event_dt.year
                # Format hour as 7pm, 9pm, etc.
                hour = event_dt.hour
                if hour == 0:
                    time_str = "12am"
                elif hour < 12:
                    time_str = f"{hour}am"
                elif hour == 12:
                    time_str = "12pm"
                else:
                    time_str = f"{hour-12}pm"
                
                show_date_str = f"{day_name} {month_name} {day_num}{suffix} {time_str} {year}"
            except Exception as e:
                logger.warning(f"Failed to parse event date {event_date_iso}: {e}")
                # Fallback to purchase date if event date parsing fails
                try:
                    purchase_date = datetime.strptime(purchase['Purchase Date'], "%m/%d/%y")
                    show_date_str = purchase_date.strftime("%B %d, %Y 9pm")
                except ValueError:
                    logger.warning(f"Invalid date format for {ticket_code}: {purchase['Purchase Date']}")
                    continue
        else:
            # No event date in metadata (historical tickets), use purchase date
            try:
                purchase_date = datetime.strptime(purchase['Purchase Date'], "%m/%d/%y")
                show_date_str = purchase_date.strftime("%B %d, %Y 9pm")
            except ValueError:
                logger.warning(f"Invalid date format for {ticket_code}: {purchase['Purchase Date']}")
                continue
        
        # Clean price (remove $)
        try:
            total_price = float(purchase['Purchase Price'].replace('$', ''))
        except (ValueError, AttributeError):
            total_price = 0.0
        
        guest = {
            'venue': venue,
            'show_date': show_date_str,
            'email': purchase['Email'],
            'source': 'Nudge',
            'first_name': purchase['First Name'],
            'last_name': purchase['Last Name'],
            'tickets': 1,
            'ticket_type': purchase.get('Tag', ''),
            'phone': purchase['Phone Number'],
            'total_price': total_price,
            'order_id': ticket_code,
            'notes': f"Promo: {purchase['Promo Code']}" if purchase.get('Promo Code') else None
        }
        
        guest_data.append(guest)
        logger.debug(f"Inserted: {ticket_code} - {venue} - {show_date_str}")
    
    # Aggregate multiple tickets for same person at same show
    from collections import defaultdict
    aggregated = {}
    for guest in guest_data:
        key = (guest['email'], guest['show_date'], guest['venue'])
        
        if key not in aggregated:
            aggregated[key] = guest.copy()
        else:
            # Same person, same show - combine tickets
            aggregated[key]['tickets'] += guest['tickets']
            # Keep comma-separated order_ids
            aggregated[key]['order_id'] += f", {guest['order_id']}"
    
    guest_data = list(aggregated.values())
    logger.info(f"Summary: {len(guest_data)} unique guests (aggregated from {len(guest_data) + duplicates} total), {duplicates} duplicates skipped")
    return guest_data

def main():
    # Parse flags
    mongo_only = '--mongo-only' in sys.argv
    debug_only = '--debug-only' in sys.argv
    historical = '--historical' in sys.argv
    venue_filter = None
    
    if '--venue' in sys.argv:
        idx = sys.argv.index('--venue')
        if idx + 1 < len(sys.argv):
            venue_filter = sys.argv[idx + 1]
            logger.info(f"Filtering for venue: {venue_filter}")
    
    if historical:
        logger.info("Including historical past event tickets")
    
    # Load cookie
    cookie = load_cookie()
    if not cookie:
        return
    
    # Setup session
    session = requests.Session()
    session.cookies.set('partner-tooling-session', cookie, 
                       domain='www.nudgetext.com', path='/')
    
    # Fetch data
    ticket_metadata = fetch_ticket_uuids(session, include_historical=historical)
    if not ticket_metadata:
        return
    
    purchases = fetch_purchases(session, ticket_metadata)
    if not purchases:
        return
    
    # Get existing orders for deduplication
    existing_order_ids = get_existing_order_ids()
    
    # Transform and filter
    guest_data = transform_purchases(purchases, existing_order_ids, venue_filter)
    
    if not guest_data:
        logger.info("No new purchases to process")
        return
    
    # Debug mode - just print
    if debug_only:
        logger.info(f"DEBUG: Would insert {len(guest_data)} guests")
        for guest in guest_data[:5]:
            logger.info(f"  {guest['first_name']} {guest['last_name']} - {guest['email']}")
        return
    
    # Insert into MongoDB (and Google Sheets unless mongo_only)
    if mongo_only:
        from insertIntoGoogleSheet import save_comprehensive_data_to_mongodb
        save_comprehensive_data_to_mongodb(guest_data)
        logger.info("Saved to MongoDB only")
    else:
        insert_guest_data_efficient(guest_data)
        logger.info("Saved to MongoDB and Google Sheets")

if __name__ == "__main__":
    logger.info(f"Nudge Orders Sync - {datetime.now().isoformat()}")
    main()
