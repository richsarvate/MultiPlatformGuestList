import json
import logging
import os
import requests
import time
import urllib.parse
from datetime import datetime, timedelta
from pymongo import MongoClient
from insertIntoGoogleSheet import insert_data_into_google_sheet
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
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )
except IOError as e:
    print(f"Error: Cannot write to log file {LOG_FILE}: {str(e)}")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
logger = logging.getLogger(__name__)

# Load configuration from config.json
CONFIG_FILE = "bucketlistConfig.json"
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

def check_mongo_db(event_id, tickets_sold):
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

def main():
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

    for exp_id in active_experiences:
        events, cookie = get_event_ids(session, exp_id, cookie)
        if not events:
            continue
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
            has_new_sales, new_tickets = check_mongo_db(event_id, tickets_sold)

            if has_new_sales and new_tickets > 0:
                guests, cookie = get_guest_list(session, exp_id, event_id, cookie)
                if not guests:
                    continue
                venue = get_venue(event_name)
                if venue not in batch_data:
                    batch_data[venue] = {}
                if show_date_with_time not in batch_data[venue]:
                    batch_data[venue][show_date_with_time] = []

                for guest in guests:
                    transaction_id = guest["entryCode"]
                    if not is_new_transaction(event_id, transaction_id, guest["customerEmail"]):
                        continue
                    name_parts = guest["customerName"].split(" ", 1)
                    first_name = name_parts[0]
                    last_name = name_parts[1] if len(name_parts) > 1 else ""
                    ticket_quantity = guest["quantity"]
                    if "pair" in guest["ticketType"].lower():
                        ticket_quantity *= 2

                    batch_data[venue][show_date_with_time].append([
                        venue,
                        show_date_with_time,
                        guest["customerEmail"],
                        "Bucketlist",
                        show_time,
                        guest["ticketType"],
                        first_name,
                        last_name,
                        ticket_quantity,
                        ""
                    ])
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

    if batch_data:
        for venue in batch_data:
            for date in batch_data[venue]:
                insert_data_into_google_sheet({venue: batch_data[venue][date]})
    else:
        logger.info("No new sales to update.")

if __name__ == "__main__":
    main()
