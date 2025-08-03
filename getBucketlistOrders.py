import json
import logging
import os
import requests
import time
import urllib.parse
import sys
from datetime import datetime, timedelta
from pymongo import MongoClient
from insertIntoGoogleSheet import insert_data_into_google_sheet
from addContactsToMongoDB import batch_add_contacts_to_mongodb
from addEmailToMailerLite import batch_add_contacts_to_mailerlite
from getVenueAndDate import get_city, append_year_to_show_date, get_venue, convert_date_from_any_format, format_time
from getBucketlistCookie import load_cookie, get_new_cookie
import uuid

# Configure logging
LOG_FILE = "/home/ec2-user/GuestListScripts/bucketlist_sales.log"
try:
    with open(LOG_FILE, 'a') as f:
        pass
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )
except IOError as e:
    print(f"Error: Cannot write to log file {LOG_FILE}: {str(e)}")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
logger = logging.getLogger(__name__)

def show_help():
    """Display help message for command line usage."""
    help_text = """
Bucketlist Orders Integration Script

USAGE:
    python getBucketlistOrders.py [OPTIONS]

OPTIONS:
    --mongo-only      Save data only to MongoDB, skip Google Sheets
    --force-refresh   Bypass duplicate checks and reimport all data
    --help           Show this help message

EXAMPLES:
    python getBucketlistOrders.py
    python getBucketlistOrders.py --mongo-only
    python getBucketlistOrders.py --force-refresh
    python getBucketlistOrders.py --mongo-only --force-refresh

DESCRIPTION:
    Fetches order data from Bucketlist API and processes guest information.
    
    --mongo-only: Saves data directly to MongoDB without updating Google Sheets.
                 Useful for bulk historical imports or when Google Sheets sync is not needed.
    
    --force-refresh: Ignores existing transaction records and processes all orders.
                    Useful for complete data refresh or fixing data inconsistencies.
                    Should be used with caution as it may create duplicates.

NOTES:
    - Requires valid Bucketlist authentication cookie
    - Uses MongoDB for duplicate detection and data storage
    - Automatically handles venue mapping and time formatting
    - Supports batch processing for improved performance
    """
    print(help_text)

def get_help_flag():
    """Check if help flag is provided."""
    return '--help' in sys.argv or '-h' in sys.argv

def batch_add_contacts_to_mongodb(batch_data):
    """
    Add contacts to MongoDB in batch format compatible with mongo-only mode.
    batch_data format: {"venue - date": [guest_arrays]}
    """
    try:
        from addContactsToMongoDB import batch_add_contacts_to_mongodb as mongo_batch_add
        
        # Convert the batch_data to the format expected by the MongoDB function
        # The MongoDB function expects: {"venue": [guest_arrays]}
        # But we have: {"venue - date": [guest_arrays]}
        
        # Since the MongoDB function groups by venue internally, we can convert our format
        mongo_batch_data = {}
        for show_key, guests in batch_data.items():
            # Extract venue from "venue - date" format
            venue = show_key.split(" - ")[0]
            if venue not in mongo_batch_data:
                mongo_batch_data[venue] = []
            mongo_batch_data[venue].extend(guests)
        
        logger.info(f"Converting {len(batch_data)} show groupings to {len(mongo_batch_data)} venue groupings")
        mongo_batch_add(mongo_batch_data)
        
    except ImportError as e:
        logger.error(f"Failed to import addContactsToMongoDB: {e}")
    except Exception as e:
        logger.error(f"Error in batch MongoDB operation: {e}")


def get_current_bucketlist_data():
    """Placeholder for current Bucketlist data retrieval"""
    pass

def check_mongo_only_flag():
    """Check if --mongo-only flag is present in command line arguments"""
    return '--mongo-only' in sys.argv

def check_force_refresh_flag():
    """Check if --force-refresh flag is present in command line arguments"""
    return '--force-refresh' in sys.argv

def show_help():
    """Display help information"""
    help_text = """
Bucketlist Orders Sync Script

Usage: python3 getBucketlistOrders.py [--mongo-only] [--force-refresh] [--help]

Options:
  --mongo-only      Skip Google Sheets integration, only save to MongoDB
  --force-refresh   Force refresh all data, bypass duplicate checks
                    (Use this for historical data import)
  --help, -h        Show this help message

Examples:
  python3 getBucketlistOrders.py                    # Normal sync (new data only)
  python3 getBucketlistOrders.py --mongo-only       # MongoDB only, new data
  python3 getBucketlistOrders.py --force-refresh    # Force refresh all data
  python3 getBucketlistOrders.py --mongo-only --force-refresh  # Historical import

For historical data import from beginning of year, use:
  python3 getBucketlistOrders.py --mongo-only --force-refresh
"""
    print(help_text)

# Load configuration from config.json
CONFIG_FILE = "/home/ec2-user/GuestListScripts/bucketlistConfig.json"
try:
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    PARTNER_ID = config["PARTNER_ID"]
    MONGO_URI = config["MONGO_URI"]
except FileNotFoundError:
    logger.error(f"Config file {CONFIG_FILE} not found.")
    raise
except json.JSONDecodeError:
    logger.error(f"Error parsing {CONFIG_FILE}. Ensure it is valid JSON.")
    raise
except KeyError as e:
    logger.error(f"Missing key {str(e)} in {CONFIG_FILE}.")
    raise

# Configuration
BASE_URL = "https://insights.bucketlisters.com"
MONGO_DB = "bucketlist_events"
MONGO_COLLECTION = "ticket_sales"
MONGO_SALES_COLLECTION = "event_sales"
EVENTS_DATA_PARAM = "routes/v2/$partnerId/experiences/$experienceId/sales-events"
GUEST_LIST_DATA_PARAM = "routes/v2/$partnerId/experiences/$experienceId/events/$eventId.guest-list"
EXPERIENCES_DATA_PARAM = "routes/v2/$partnerId/experiences/index"
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
}

def get_experience_ids(session, cookie):
    logger.info("Fetching active experience IDs")
    encoded_data = urllib.parse.quote(EXPERIENCES_DATA_PARAM)
    url = f"{BASE_URL}/v2/{PARTNER_ID}/experiences/?_data={encoded_data}"
    logger.info(f"Requesting URL: {url}")
    headers = HEADERS.copy()
    headers["Cookie"] = cookie
    try:
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        if "application/json" not in response.headers.get("Content-Type", ""):
            logger.error(f"Non-JSON response received for experiences. Attempting cookie refresh.")
            new_cookie = get_new_cookie()
            if not new_cookie:
                logger.error("Failed to refresh cookie")
                return [], cookie
            headers["Cookie"] = new_cookie
            response = session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            if "application/json" not in response.headers.get("Content-Type", ""):
                logger.error("Non-JSON response after refresh for experiences.")
                return [], new_cookie
            cookie = new_cookie
        data = response.json()
        experience_ids = [exp["experienceId"] for exp in data.get("experiences", [])]
        return experience_ids, cookie
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching experience IDs: {str(e)}")
        return [], cookie

def get_event_ids(session, experience_id, cookie):
    logger.info(f"Fetching events for experience {experience_id}")
    encoded_data = urllib.parse.quote(EVENTS_DATA_PARAM)
    url = f"{BASE_URL}/v2/{PARTNER_ID}/experiences/{experience_id}/sales-events?_data={encoded_data}"
    logger.info(f"Requesting URL: {url}")
    headers = HEADERS.copy()
    headers["Cookie"] = cookie
    try:
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        if "application/json" not in response.headers.get("Content-Type", ""):
            logger.error(f"Non-JSON response received. Attempting cookie refresh.")
            new_cookie = get_new_cookie()
            if not new_cookie:
                logger.error("Failed to refresh cookie")
                return [], cookie
            headers["Cookie"] = new_cookie
            response = session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            if "application/json" not in response.headers.get("Content-Type", ""):
                logger.error("Non-JSON after refresh.")
                return [], new_cookie
            cookie = new_cookie
        data = response.json()
        events = [{
            "eventId": event["eventId"],
            "ticketsSold": event["ticketStatistics"]["ticketsSold"],
            "name": event["name"],
            "startTime": event["startTime"],
            "ticketTypes": [{
                "name": tt["name"],
                "basePriceInCents": tt["basePriceInCents"],
                "ticketsSold": tt["ticketStatistics"]["ticketsSold"],
                "guestCount": tt["ticketStatistics"]["guestCount"]
            } for tt in event["eventTicketTypes"]]
        } for event in data.get("events", [])]
        return events, cookie
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching events: {str(e)}")
        return [], cookie

def get_guest_list(session, experience_id, event_id, cookie):
    logger.info(f"Fetching guest list for event {event_id}")
    encoded_data = urllib.parse.quote(GUEST_LIST_DATA_PARAM)
    url = f"{BASE_URL}/v2/{PARTNER_ID}/experiences/{experience_id}/events/{event_id}/guest-list?_data={encoded_data}"
    headers = HEADERS.copy()
    headers["Cookie"] = cookie
    try:
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        if "application/json" not in response.headers.get("Content-Type", ""):
            logger.error(f"Non-JSON guest list response. Attempting cookie refresh.")
            new_cookie = get_new_cookie()
            if not new_cookie:
                logger.error("Failed to refresh cookie")
                return [], cookie
            headers["Cookie"] = new_cookie
            response = session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            if "application/json" not in response.headers.get("Content-Type", ""):
                logger.error("Non-JSON guest list after refresh.")
                return [], new_cookie
            cookie = new_cookie
        data = response.json()
        guests = [{
            "customerName": order["customerName"],
            "customerEmail": order["customerEmail"],
            "customerPhone": order["customerPhone"],
            "ticketType": ticket["ticketType"],
            "entryCode": ticket["entryCode"],
            "quantity": sum(li["quantity"] for li in order["lineItems"] if li["type"] == "ITEM")
        } for order in data.get("orders", []) for ticket in order["tickets"]]
        return guests, cookie
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching guest list: {str(e)}")
        return [], cookie

def is_new_transaction(event_id, transaction_id, customer_email):
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        collection = db[MONGO_SALES_COLLECTION]
        exists = collection.find_one({
            "eventId": event_id,
            "transactionId": transaction_id,
            "customerEmail": customer_email
        })
        return not exists
    except Exception as e:
        logger.error(f"Error checking transactionId: {str(e)}")
        return False
    finally:
        client.close()

def store_transaction(transaction_data):
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        collection = db[MONGO_SALES_COLLECTION]
        collection.insert_one(transaction_data)
    except Exception as e:
        logger.error(f"Error inserting transaction: {str(e)}")
    finally:
        client.close()

def check_mongo_db(event_id, tickets_sold, force_refresh=False):
    """Check MongoDB for event changes. If force_refresh=True, always return True to process all events."""
    if force_refresh:
        logger.info(f"Force refresh mode: processing event {event_id} with {tickets_sold} tickets")
        return True, tickets_sold
    
    logger.info(f"Checking MongoDB for event {event_id}")
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        collection = db[MONGO_COLLECTION]
        event_record = collection.find_one({"eventId": event_id})
        if not event_record:
            collection.insert_one({"eventId": event_id, "ticketsSold": tickets_sold})
            return True, tickets_sold
        elif event_record["ticketsSold"] != tickets_sold:
            collection.update_one(
                {"eventId": event_id},
                {"$set": {"ticketsSold": tickets_sold}}
            )
            return True, tickets_sold - event_record["ticketsSold"]
        return False, 0
    except Exception as e:
        logger.error(f"Error checking MongoDB for event {event_id}: {str(e)}")
        return False, 0
    finally:
        client.close()

def is_new_transaction(event_id, transaction_id, customer_email, force_refresh=False):
    """Check if transaction is new. If force_refresh=True, always return True to process all transactions."""
    if force_refresh:
        return True
    
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        collection = db[MONGO_SALES_COLLECTION]
        exists = collection.find_one({
            "eventId": event_id,
            "transactionId": transaction_id,
            "customerEmail": customer_email
        })
        return not exists
    except Exception as e:
        logger.error(f"Error checking transactionId: {str(e)}")
        return False
    finally:
        client.close()

def main():
    # Check for help flag first
    if get_help_flag():
        show_help()
        return
    
    # Check flags
    mongo_only = check_mongo_only_flag()
    force_refresh = check_force_refresh_flag()
    
    if mongo_only:
        logger.info("Running in MONGO-ONLY mode - skipping Google Sheets integration")
    if force_refresh:
        logger.info("Running in FORCE-REFRESH mode - bypassing duplicate checks")
    
    logger.info("Starting Bucketlist sales sync")
    cookie = load_cookie()
    if not cookie:
        logger.error("Failed to load cookie.")
        return
    session = requests.Session()
    batch_data = {}

    # Fetch active experience IDs
    active_experiences, cookie = get_experience_ids(session, cookie)
    if not active_experiences:
        logger.error("No active experiences found.")
        return

    logger.info(f"Found {len(active_experiences)} active experiences")
    total_events_processed = 0
    total_guests_processed = 0

    for exp_id in active_experiences:
        events, cookie = get_event_ids(session, exp_id, cookie)
        if not events:
            continue
        
        logger.info(f"Experience {exp_id}: found {len(events)} events")
        
        for event in events:
            event_id = event["eventId"]
            tickets_sold = event["ticketsSold"]
            event_name = event["name"]
            start_time = datetime.strptime(event["startTime"], "%Y-%m-%dT%H:%M:%S%z")
            show_date = start_time.strftime("%Y-%m-%d")
            show_date_readable = convert_date_from_any_format(show_date)
            show_time = format_time(start_time.strftime("%I:%M %p"))

            if show_time.strip().lower() == "8:30pm" and get_venue(event_name).strip().lower() == "palace":
                show_time = "9pm"

            show_date_with_time = f"{show_date_readable} {show_time}"
            has_new_sales, new_tickets = check_mongo_db(event_id, tickets_sold, force_refresh)

            logger.debug(f"Event {event_id} ({event_name}): {tickets_sold} tickets, new_sales: {has_new_sales}, new_tickets: {new_tickets}")

            if has_new_sales and (new_tickets > 0 or force_refresh):
                guests, cookie = get_guest_list(session, exp_id, event_id, cookie)
                if not guests:
                    continue
                    
                venue = get_venue(event_name)
                logger.info(f"Processing {event_name} at {venue} on {show_date_with_time} - {len(guests)} guests")
                
                # Initialize batch_data structure for MongoDB-only mode
                if mongo_only:
                    show_key = f"{venue} - {show_date_with_time}"
                    if show_key not in batch_data:
                        batch_data[show_key] = []
                else:
                    # Original structure for Google Sheets
                    if venue not in batch_data:
                        batch_data[venue] = {}
                    if show_date_with_time not in batch_data[venue]:
                        batch_data[venue][show_date_with_time] = []

                event_guests_processed = 0
                for guest in guests:
                    transaction_id = guest["entryCode"]
                    if not is_new_transaction(event_id, transaction_id, guest["customerEmail"], force_refresh):
                        continue
                        
                    name_parts = guest["customerName"].split(" ", 1)
                    first_name = name_parts[0]
                    last_name = name_parts[1] if len(name_parts) > 1 else ""
                    ticket_quantity = guest["quantity"]
                    if "pair" in guest["ticketType"].lower():
                        ticket_quantity *= 2

                    # Create guest data array
                    guest_array = [
                        venue,
                        show_date_with_time,
                        guest["customerEmail"],
                        "Bucketlist",
                        show_time,
                        guest["ticketType"],
                        first_name,
                        last_name,
                        ticket_quantity,
                        guest.get("customerPhone", ""),
                        # Enhanced fields for MongoDB consistency
                        None,  # discount_code
                        None,  # total_price
                        None,  # order_id
                        transaction_id,  # transaction_id
                        guest["customerEmail"],  # customer_id
                        "Bucketlist",  # payment_method
                        transaction_id,  # entry_code
                        f"Ticket Type: {guest['ticketType']}"  # notes
                    ]

                    if mongo_only:
                        batch_data[show_key].append(guest_array)
                    else:
                        batch_data[venue][show_date_with_time].append(guest_array)
                    
                    # Store transaction data for tracking
                    if not force_refresh:  # Only store if not in force refresh mode to avoid duplicates
                        store_transaction({
                            "transactionId": transaction_id,
                            "customerName": guest["customerName"],
                            "customerEmail": guest["customerEmail"],
                            "customerPhone": guest["customerPhone"],
                            "quantity": ticket_quantity,
                            "eventId": event_id,
                            "experienceId": exp_id,
                            "showName": event_name,
                            "showDate": show_date_with_time,
                            "timestamp": datetime.utcnow()
                        })
                    
                    event_guests_processed += 1
                
                total_events_processed += 1
                total_guests_processed += event_guests_processed
                logger.info(f"Event {event_name}: processed {event_guests_processed} guests")

    if batch_data:
        logger.info(f"Processing {total_guests_processed} total guests from {total_events_processed} events")
        
        if mongo_only:
            # Save directly to MongoDB using the consolidated structure
            batch_add_contacts_to_mongodb(batch_data)
            logger.info("Successfully saved data to MongoDB only")
        else:
            # Use original Google Sheets process
            for venue in batch_data:
                for date in batch_data[venue]:
                    insert_data_into_google_sheet({venue: batch_data[venue][date]})
            logger.info("Successfully processed all Bucketlist orders")
    else:
        logger.info("No new sales to update.")

if __name__ == "__main__":
    main()
