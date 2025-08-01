import json
import requests
import logging
from datetime import datetime, timedelta
from insertIntoGoogleSheet import insert_guest_data_efficient
from getVenueAndDate import get_venue, extract_venue_name, extract_date, extract_time
import config
import sys

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

def calculate_time_range(interval_minutes):
    """Calculate the time range for API request"""
    current_time = datetime.utcnow().isoformat()[:-6] + "Z"
    last_run = (datetime.utcnow() - timedelta(minutes=interval_minutes)).isoformat()[:-6] + "Z"
    
    logger.info(f"Fetching orders from {last_run} to {current_time}")
    return last_run, current_time

def fetch_squarespace_orders(last_run, current_time):
    """Fetch orders from Squarespace API"""
    url = f"https://api.squarespace.com/1.0/commerce/orders?modifiedAfter={last_run}&modifiedBefore={current_time}"
    
    headers = {
        "Authorization": f"Bearer {config.SQUARESPACE_API_KEY}",
        "User-Agent": "GuestListScripts_SquarespaceIntegration"
    }
    
    logger.info("Making API request to Squarespace")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        logger.info(f"Successfully fetched {len(data.get('result', []))} orders")
        return data
    else:
        logger.error(f"Failed to fetch data. Status code: {response.status_code}")
        return None

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
            "entry_code": None,  # Could be added if available
            "notes": f"Order created: {created_on}, SKU: {item.get('sku', '')}"
        }
        
        guests.append(guest)
        
        # Log the processed guest
        logger.debug(f"Processed guest: {guest['first_name']} {guest['last_name']} for {venue_name}")
    
    return guests

def process_squarespace_orders():
    """Main function to process Squarespace orders"""
    logger.info("Starting Squarespace order processing")
    
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
        
        # Use the new efficient insert function
        insert_guest_data_efficient(all_guests)
        
        logger.info("Successfully processed all Squarespace orders")
    else:
        logger.info("No guests to process")

if __name__ == "__main__":
    print(f"Squarespace Orders Sync - {datetime.utcnow().isoformat()[:-6]}Z")
    process_squarespace_orders()
