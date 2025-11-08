import json
import requests
import logging
from datetime import datetime, timedelta
from insertIntoGoogleSheet import insert_guest_data_efficient
from getVenueAndDate import get_venue, extract_venue_name, extract_date, extract_time, get_venue_filter, filter_guests_by_venue
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config.config as config

# Setup logging
logger = logging.getLogger(__name__)

def get_time_interval():
    """Get the time interval from command line argument or use default"""
    interval = config.SCRIPT_INTERVAL
    
    if len(sys.argv) > 1:
        try:
            interval = int(sys.argv[1])
            logger.info(f"Using command line interval: {interval} minutes")
        except ValueError:
            logger.warning(f"Invalid interval argument, using default: {interval} minutes")
    else:
        logger.info(f"Using default interval: {interval} minutes")
    
    return interval

def check_mongo_only_flag():
    """Check if --mongo-only flag is present in command line arguments"""
    return '--mongo-only' in sys.argv

def check_debug_only_flag():
    """Check if --debug-only flag is present in command line arguments"""
    return '--debug-only' in sys.argv

def calculate_time_range(interval_minutes):
    """Calculate the time range for API request"""
    current_time = datetime.utcnow().isoformat()[:-6] + "Z"
    last_run = (datetime.utcnow() - timedelta(minutes=interval_minutes)).isoformat()[:-6] + "Z"
    
    logger.info(f"Fetching orders from {last_run} to {current_time}")
    return last_run, current_time

def fetch_squarespace_orders(last_run, current_time):
    """Fetch orders from Squarespace API with pagination support"""
    from datetime import datetime
    import pytz
    
    # Convert date strings to datetime objects for comparison
    last_run_dt = datetime.fromisoformat(last_run.replace('Z', '+00:00'))
    current_time_dt = datetime.fromisoformat(current_time.replace('Z', '+00:00'))
    
    all_orders = []
    cursor = None
    page_count = 0
    
    headers = {
        "Authorization": f"Bearer {config.SQUARESPACE_API_KEY}",
        "User-Agent": "GuestListScripts_SquarespaceIntegration"
    }
    
    logger.info("Making API request to Squarespace")
    
    while True:
        # Build URL - use date filters only for first page, cursor only for subsequent pages
        if cursor:
            url = f"https://api.squarespace.com/1.0/commerce/orders?cursor={cursor}"
        else:
            url = f"https://api.squarespace.com/1.0/commerce/orders?modifiedAfter={last_run}&modifiedBefore={current_time}"
        
        logger.info(f"Fetching page {page_count + 1}" + (f" (cursor: {cursor[:20]}...)" if cursor else " (with date filters)"))
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            page_orders = data.get('result', [])
            
            # If using cursor (not first page), filter by date client-side
            if cursor:
                filtered_orders = []
                for order in page_orders:
                    modified_on = order.get('modifiedOn', '')
                    if modified_on:
                        try:
                            order_modified_dt = datetime.fromisoformat(modified_on.replace('Z', '+00:00'))
                            if last_run_dt <= order_modified_dt <= current_time_dt:
                                filtered_orders.append(order)
                        except ValueError:
                            # If date parsing fails, include the order to be safe
                            filtered_orders.append(order)
                
                # If no orders match our date range, we've gone too far back
                if not filtered_orders and page_orders:
                    logger.info("No orders in date range found on this page, stopping pagination")
                    break
                    
                page_orders = filtered_orders
            
            all_orders.extend(page_orders)
            page_count += 1
            
            logger.info(f"Page {page_count}: fetched {len(page_orders)} orders in date range (total so far: {len(all_orders)})")
            
            # Check if there are more pages
            pagination = data.get('pagination', {})
            if pagination.get('hasNextPage', False):
                cursor = pagination.get('nextPageCursor')
                if not cursor:
                    logger.warning("hasNextPage is True but no nextPageCursor found, stopping pagination")
                    break
            else:
                logger.info("No more pages to fetch")
                break
        else:
            logger.error(f"Failed to fetch data. Status code: {response.status_code}, Response: {response.text}")
            return None
    
    logger.info(f"Successfully fetched {len(all_orders)} total orders across {page_count} pages")
    return {"result": all_orders}

def extract_guest_data_from_order(order):
    """
    Extract guest data from a single Squarespace order with all enhanced fields
    
    :param order: Single order object from Squarespace API
    :return: List of guest dictionaries (one per line item)
    """
    guests = []
    
    # Extract customer information
    billing_address = order.get("billingAddress", {})
    customer_email = order.get("customerEmail", "")
    order_number = order.get("orderNumber", "")
    order_id = order.get("id", "")
    created_on = order.get("createdOn", "")
    
    # Extract pricing and discount information
    grand_total = order.get("grandTotal", {}).get("value", "0.00")
    discount_total = order.get("discountTotal", {}).get("value", "0.00")
    discount_codes = []
    
    # Extract discount codes
    for discount_line in order.get("discountLines", []):
        discount_codes.append(discount_line.get("name", ""))
    
    # Process each line item (ticket)
    for item in order.get('lineItems', []):
        show_name = item.get("productName", "")
        venue_name = get_venue(show_name)
        show_date = extract_date(show_name)
        show_time = extract_time(show_name)
        
        # Create guest dictionary with enhanced fields
        guest = {
            "venue": venue_name,
            "show_date": f"{show_date} {show_time}",
            "email": customer_email,
            "source": "Squarespace",
            "first_name": billing_address.get("firstName", ""),
            "last_name": billing_address.get("lastName", ""),
            "tickets": item.get("quantity", 1),
            "ticket_type": "GA",  # Default, could be enhanced if variant info available
            "phone": billing_address.get("phone", ""),
            
            # Enhanced Squarespace-specific fields
            "discount_code": ", ".join(discount_codes) if discount_codes else None,
            "total_price": float(grand_total) if grand_total else None,
            "order_id": order_number,
            "transaction_id": order_id,
            "customer_id": customer_email,  # Using email as customer ID
            "payment_method": "Squarespace",
            "entry_code": item.get('sku', '') or f"SS_{order_number}_{item.get('variantId', '')}",  # Create consistent entry code
            "notes": f"Order created: {created_on}, SKU: {item.get('sku', '')}"
        }
        
        guests.append(guest)
        
        # Log the processed guest
        logger.debug(f"Processed guest: {guest['first_name']} {guest['last_name']} for {venue_name}")
    
    return guests

def process_squarespace_orders():
    """Main function to process Squarespace orders"""
    logger.info("Starting Squarespace order processing")
    
    # Check for mongo-only flag
    mongo_only = check_mongo_only_flag()
    if mongo_only:
        logger.info("Running in MONGO-ONLY mode - skipping Google Sheets integration")
    
    # Get time interval and calculate range
    interval = get_time_interval()
    last_run, current_time = calculate_time_range(interval)
    
    # Fetch orders from Squarespace
    data = fetch_squarespace_orders(last_run, current_time)
    
    if not data or not data.get("result"):
        logger.info("No orders found or API request failed")
        return
    
    # Process all orders into guest data
    all_guests = []
    
    for order in data["result"]:
        try:
            guests = extract_guest_data_from_order(order)
            all_guests.extend(guests)
        except Exception as e:
            logger.error(f"Error processing order {order.get('orderNumber', 'unknown')}: {e}")
            continue
    
    if all_guests:
        logger.info(f"Processing {len(all_guests)} guests total")
        
        # Apply venue filter if specified
        venue_filter = get_venue_filter()
        if venue_filter:
            all_guests = filter_guests_by_venue(all_guests, venue_filter)
        
        # Check for debug-only mode
        debug_only = check_debug_only_flag()
        
        if debug_only:
            logger.info("=== DEBUG-ONLY MODE: Showing guest data without insertion ===")
            for i, guest in enumerate(all_guests, 1):
                print(f"\n--- Guest {i} ---")
                print(f"Name: {guest.get('first_name')} {guest.get('last_name')}")
                print(f"Email: {guest.get('email')}")
                print(f"Venue: {guest.get('venue')}")
                print(f"Show Date: {guest.get('show_date')}")
                print(f"Source: {guest.get('source')}")
                print(f"Order ID: {guest.get('order_id')}")
                print(f"Tickets: {guest.get('tickets')}")
                print(f"Total Price: {guest.get('total_price')}")
                print(f"Phone: {guest.get('phone')}")
            logger.info("=== END DEBUG DATA ===")
            return
        
        if mongo_only:
            # Only save to MongoDB, skip Google Sheets
            from insertIntoGoogleSheet import _save_comprehensive_data_to_mongodb
            _save_comprehensive_data_to_mongodb(all_guests)
            logger.info("Successfully saved data to MongoDB only")
        else:
            # Use the full efficient insert function (MongoDB + Google Sheets)
            logger.info("=== DEBUG: Using Squarespace dual-path (Sheets + MongoDB) ===")
            logger.info(f"=== DEBUG: About to call insert_guest_data_efficient with {len(all_guests)} guests ===")
            insert_guest_data_efficient(all_guests)
            logger.info("Successfully processed all Squarespace orders")
    else:
        logger.info("No guests to process")

if __name__ == "__main__":
    print(f"Squarespace Orders Sync - {datetime.utcnow().isoformat()[:-6]}Z")
    if '--help' in sys.argv or '-h' in sys.argv:
        print("\nUsage: python3 getSquarespaceOrders.py [interval_minutes] [--mongo-only] [--debug-only] [--venue VENUE_NAME]")
        print("\nOptions:")
        print("  interval_minutes  Time interval to fetch orders (default: from config)")
        print("  --mongo-only      Save data only to MongoDB, skip Google Sheets")
        print("  --debug-only      Show order data without inserting to database or sheets")
        print("  --venue VENUE     Process only tickets from specified venue (case-insensitive)")
        print("\nExamples:")
        print("  python3 getSquarespaceOrders.py 60                    # Fetch last 60 minutes")
        print("  python3 getSquarespaceOrders.py 10080 --mongo-only    # Fetch last week, MongoDB only")
        print("  python3 getSquarespaceOrders.py 1440 --debug-only     # Show last 24 hours data without inserting")
        print("  python3 getSquarespaceOrders.py 180 --venue rabbitbox # Process only RabbitBox tickets from last 3 hours")
        print("  python3 getSquarespaceOrders.py 1440 --venue palace --debug-only # Debug Palace tickets from last 24 hours")
        sys.exit(0)
    
    process_squarespace_orders()
