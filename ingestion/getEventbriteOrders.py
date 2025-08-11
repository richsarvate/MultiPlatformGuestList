import requests
import logging
from datetime import datetime, timedelta
from insertIntoGoogleSheet import insert_guest_data_efficient
from addContactsToMongoDB import batch_add_contacts_to_mongodb
from getVenueAndDate import get_venue
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config.config as config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_mongo_only_flag():
    """Check if --mongo-only flag is present in command line arguments"""
    return '--mongo-only' in sys.argv

def get_help_flag():
    """Check if help flag is present"""
    return '--help' in sys.argv or '-h' in sys.argv

def show_help():
    """Display help information"""
    help_text = """
Eventbrite Orders Sync Script

Usage: python3 getEventbriteOrders.py [MINUTES] [--mongo-only] [--help]

Arguments:
  MINUTES       Number of minutes to look back for changed orders
                Default: Value from config.SCRIPT_INTERVAL
                
Options:
  --mongo-only  Skip Google Sheets integration, only save to MongoDB
  --help, -h    Show this help message

Examples:
  python3 getEventbriteOrders.py 60              # Last hour
  python3 getEventbriteOrders.py 1440            # Last 24 hours  
  python3 getEventbriteOrders.py 306720          # From beginning of year (approx)
  python3 getEventbriteOrders.py 60 --mongo-only # Last hour, MongoDB only

For historical data import from beginning of year, use:
  python3 getEventbriteOrders.py 306720 --mongo-only
"""
    print(help_text)

def get_time_interval():
    """Get the time interval from command line argument or use default"""
    interval = config.SCRIPT_INTERVAL
    
    # Filter out non-numeric arguments (like --mongo-only)
    numeric_args = []
    for arg in sys.argv[1:]:
        if not arg.startswith('--') and not arg.startswith('-'):
            try:
                numeric_args.append(int(arg))
            except ValueError:
                continue
    
    if numeric_args:
        interval = numeric_args[0]
        logger.info(f"Using command line interval: {interval} minutes")
    else:
        logger.info(f"Using default interval: {interval} minutes")
    
    return interval

def calculate_time_range(interval_minutes):
    """Calculate the time range for API request"""
    current_date = datetime.now()
    last_run = current_date - timedelta(minutes=interval_minutes)
    changed_since = last_run.strftime("%Y-%m-%dT%H:%M:%SZ")
    current_time = current_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    logger.info(f"Fetching Eventbrite orders changed from {changed_since} to {current_time}")
    return changed_since

def fetch_eventbrite_orders(changed_since):
    """Fetch orders from Eventbrite API with pagination support"""
    all_orders = []
    page = 1
    has_more_items = True
    
    headers = {
        'Authorization': f'Bearer {config.EVENTBRITE_PRIVATE_TOKEN}'
    }
    
    logger.info("Making API request to Eventbrite")
    
    while has_more_items:
        url = f"https://www.eventbriteapi.com/v3/organizations/{config.EVENTBRITE_ORGANIZATION_ID}/orders"
        params = {
            'changed_since': changed_since,
            'page': page
        }
        
        logger.info(f"Fetching page {page}")
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            page_orders = data.get('orders', [])
            pagination = data.get('pagination', {})
            
            all_orders.extend(page_orders)
            logger.info(f"Page {page}: fetched {len(page_orders)} orders (total so far: {len(all_orders)})")
            
            # Check if there are more pages
            has_more_items = pagination.get('has_more_items', False)
            if has_more_items:
                page += 1
            else:
                logger.info("No more pages to fetch")
                break
        else:
            logger.error(f"Failed to fetch Eventbrite orders. Status code: {response.status_code}, Response: {response.text}")
            return None
    
    logger.info(f"Successfully fetched {len(all_orders)} total orders across {page} pages")
    return {"orders": all_orders}

def fetch_event_details(event_id):
    """Fetch event details from Eventbrite API"""
    url = f"https://www.eventbriteapi.com/v3/events/{event_id}"
    headers = {
        'Authorization': f'Bearer {config.EVENTBRITE_PRIVATE_TOKEN}'
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Failed to fetch event {event_id}. Status code: {response.status_code}")
        return None

def fetch_event_attendees(event_id):
    """Fetch attendees for an event from Eventbrite API"""
    url = f"https://www.eventbriteapi.com/v3/events/{event_id}/attendees/"
    headers = {
        'Authorization': f'Bearer {config.EVENTBRITE_PRIVATE_TOKEN}'
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Failed to fetch attendees for event {event_id}. Status code: {response.status_code}")
        return None

def format_time(date_string):
    """Convert datetime string to formatted time (e.g., '8pm')"""
    try:
        date_obj = datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S')
        formatted_time = date_obj.strftime('%I%p').lstrip('0').lower()
        return formatted_time
    except ValueError:
        return "Time Not Found"

def format_date(date_string):
    """Convert datetime string to formatted date (e.g., 'Wednesday July 30th')"""
    try:
        date_obj = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S")
        day = date_obj.strftime("%d").lstrip("0")
        month = date_obj.strftime("%B")
        
        # Get day suffix
        day_suffix = "th" if 11 <= int(day) <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(int(day) % 10, "th")
        
        formatted_date = f"{date_obj.strftime('%A')} {month} {day}{day_suffix}"
        return formatted_date
    except ValueError:
        return "Invalid date format"

def extract_guest_data_from_order(order, event_details, attendees_data):
    """
    Extract guest data from an Eventbrite order with all enhanced fields
    
    :param order: Single order object from Eventbrite API
    :param event_details: Event details from Eventbrite API
    :param attendees_data: Attendees data from Eventbrite API
    :return: Guest dictionary with enhanced fields
    """
    order_id = order.get('id', '')
    event_id = order.get('event_id', '')
    
    # Extract basic customer info
    first_name = order.get('first_name', '')
    last_name = order.get('last_name', '')
    email = order.get('email', '')
    
    # Extract event details
    event_name = event_details.get('name', {}).get('text', '') if event_details else ''
    venue_name = get_venue(event_name)
    
    event_start = event_details.get('start', {}).get('local', '') if event_details else ''
    event_date = format_date(event_start)
    event_time = format_time(event_start)
    
    # Find attendee details for this order
    ticket_class = "General Admission"
    total_tickets = 0
    attendee_info = []
    
    if attendees_data:
        for attendee in attendees_data.get('attendees', []):
            if attendee.get('order_id') == order_id:
                ticket_class = attendee.get('ticket_class_name', 'General Admission')
                total_tickets += attendee.get('quantity', 1)
                attendee_info.append({
                    'barcode': attendee.get('barcodes', [{}])[0].get('barcode', ''),
                    'status': attendee.get('status', ''),
                    'checked_in': attendee.get('checked_in', False)
                })
    
    # Handle special ticket types (e.g., pairs)
    if "pair" in ticket_class.lower():
        total_tickets *= 2
    
    # Extract cost information
    costs = order.get('costs', {})
    base_price = costs.get('base_price', {}).get('major_value', '0.00')
    eventbrite_fee = costs.get('eventbrite_fee', {}).get('major_value', '0.00')
    payment_fee = costs.get('payment_fee', {}).get('major_value', '0.00')
    gross_total = costs.get('gross', {}).get('major_value', '0.00')
    
    # Extract discount information (for consistency with Squarespace)
    discount_code = None
    if float(base_price) > float(gross_total):
        # There's a discount applied
        discount_amount = float(base_price) - float(gross_total) + float(eventbrite_fee) + float(payment_fee)
        discount_code = f"DISCOUNT_${discount_amount:.2f}"
    
    # Create entry code from first barcode (for consistency with Squarespace)
    entry_code = attendee_info[0].get('barcode', '') if attendee_info else None
    
    # Create guest dictionary with enhanced fields
    guest = {
        "venue": venue_name,
        "show_date": f"{event_date} {event_time}",
        "email": email,
        "source": "Eventbrite",
        "first_name": first_name,
        "last_name": last_name,
        "tickets": total_tickets,
        "ticket_type": ticket_class,
        "phone": "",  # Eventbrite doesn't typically provide phone in order data
        
        # Enhanced Eventbrite-specific fields (consistent with Squarespace)
        "discount_code": discount_code,
        "total_price": float(gross_total) if gross_total else None,
        "order_id": order_id,
        "transaction_id": order.get('resource_uri', '').split('/')[-2] if order.get('resource_uri') else order_id,
        "customer_id": email,  # Using email as customer ID
        "payment_method": "Eventbrite",
        "entry_code": entry_code,
        "notes": f"Base: ${base_price}, EB Fee: ${eventbrite_fee}, Payment Fee: ${payment_fee}, Status: {order.get('status', '')}"
    }
    
    logger.debug(f"Processed Eventbrite guest: {first_name} {last_name} for {venue_name} - {total_tickets} tickets")
    return guest

def process_eventbrite_orders():
    """Main function to process Eventbrite orders"""
    # Check for help flag first
    if get_help_flag():
        show_help()
        return
    
    # Check if running in mongo-only mode
    mongo_only = check_mongo_only_flag()
    if mongo_only:
        logger.info("Running in MONGO-ONLY mode - skipping Google Sheets integration")
    
    logger.info("Starting Eventbrite order processing")
    
    # Get time interval and fetch orders
    interval = get_time_interval()
    changed_since = calculate_time_range(interval)
    
    # Fetch orders from Eventbrite
    data = fetch_eventbrite_orders(changed_since)
    
    if not data or not data.get("orders"):
        logger.info("No orders found or API request failed")
        return
    
    orders = data["orders"]
    all_guests = []
    
    # Process each order
    for order in orders:
        try:
            order_id = order.get('id', 'unknown')
            event_id = order.get('event_id', '')
            
            logger.debug(f"Processing order {order_id} for event {event_id}")
            
            # Fetch event details
            event_details = fetch_event_details(event_id)
            if not event_details:
                logger.warning(f"Skipping order {order_id} - could not fetch event details")
                continue
            
            # Fetch attendees
            attendees_data = fetch_event_attendees(event_id)
            if not attendees_data:
                logger.warning(f"Could not fetch attendees for order {order_id}")
            
            # Extract guest data
            guest = extract_guest_data_from_order(order, event_details, attendees_data)
            all_guests.append(guest)
            
        except Exception as e:
            logger.error(f"Error processing order {order.get('id', 'unknown')}: {e}")
            continue
    
    if all_guests:
        logger.info(f"Processing {len(all_guests)} guests total from Eventbrite")
        
        if mongo_only:
            # Convert guest dictionaries to the array format expected by MongoDB
            batch_data = {}
            
            for guest in all_guests:
                venue = guest.get('venue', '')
                show_date = guest.get('show_date', '')
                
                # Create a show key (venue + date for grouping)
                show_key = f"{venue} - {show_date}"
                
                if show_key not in batch_data:
                    batch_data[show_key] = []
                
                # Convert to array format that MongoDB function expects
                # Array structure: [venue, date, email, source, time, type, firstname, lastname, tickets, phone, ...]
                guest_array = [
                    venue,
                    show_date,
                    guest.get('email', ''),
                    guest.get('source', ''),
                    guest.get('show_time', ''),  # Use show_time directly from guest dict
                    guest.get('ticket_type', 'GA'),
                    guest.get('first_name', ''),
                    guest.get('last_name', ''),
                    guest.get('tickets', 1),
                    guest.get('phone', ''),
                    # Enhanced fields as additional array elements
                    guest.get('discount_code'),
                    guest.get('total_price'),
                    guest.get('order_id'),
                    guest.get('transaction_id'),
                    guest.get('customer_id'),
                    guest.get('payment_method'),
                    guest.get('entry_code'),
                    guest.get('notes')
                ]
                
                batch_data[show_key].append(guest_array)
            
            # Save directly to MongoDB
            batch_add_contacts_to_mongodb(batch_data)
            logger.info("Successfully saved data to MongoDB only")
        else:
            # Use the normal process with Google Sheets
            insert_guest_data_efficient(all_guests)
            logger.info("Successfully processed all Eventbrite orders")
    else:
        logger.info("No guests to process")

if __name__ == "__main__":
    print(f"Eventbrite Orders Sync - {datetime.now().isoformat()}")
    process_eventbrite_orders()
