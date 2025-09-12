import json
import logging
import re
from datetime import datetime
from pymongo import MongoClient
from shared_config import get_mongo_config

# Set up logging
logger = logging.getLogger(__name__)

from typing import Optional

def parse_show_date_with_year(date_string: str) -> Optional[datetime]:
    """
    Parse show date string into datetime object.
    If year is present, use it. If not, apply future-show logic.
    """
    try:
        if not date_string:
            return None
        
        # Month mapping
        month_map = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4, 
            'may': 5, 'june': 6, 'july': 7, 'august': 8, 
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        
        # Check if year is already present using regex
        if re.search(r'\b\d{4}\b', date_string):
            # Year is present, extract year, month, and day
            year_match = re.search(r'\b(\d{4})\b', date_string)
            if year_match:
                year = int(year_match.group(1))
            else:
                logger.warning(f"Could not extract year from: {date_string}")
                return None
        else:
            # No year present, assume current year (2025) for all existing data
            # This is simpler and more reliable than trying to guess future vs past
            year = datetime.now().year
        
        # Extract month and day using regex
        date_match = re.search(r'(\w+)\s+(\d+)', date_string.lower())
        time_match = re.search(r'(\d+(?:\:\d+)?)\s*(pm|am)', date_string.lower())
        
        if not date_match:
            logger.warning(f"Could not parse date from: {date_string}")
            return None
            
        month_name = date_match.group(1)
        day_num = int(date_match.group(2))
        
        if month_name not in month_map:
            logger.warning(f"Unknown month: {month_name}")
            return None
        
        # Parse time (default to 9pm if no time found)
        hour = 21  # 9pm default
        minute = 0
        
        if time_match:
            time_part = time_match.group(1)
            am_pm = time_match.group(2)
            
            if ':' in time_part:
                time_hours, time_minutes = time_part.split(':')
                hour = int(time_hours)
                minute = int(time_minutes)
            else:
                hour = int(time_part)
                minute = 0
            
            # Convert to 24-hour format
            if am_pm == 'pm' and hour != 12:
                hour += 12
            elif am_pm == 'am' and hour == 12:
                hour = 0
        
        # Create datetime object
        show_datetime = datetime(year, month_map[month_name], day_num, hour, minute)
        return show_datetime
        
    except Exception as e:
        logger.error(f"Error parsing date '{date_string}': {e}")
        return None

def batch_add_contacts_to_mongodb(batch_data):
    """
    Batch adds contact data to MongoDB instead of MailerLite.
    
    :param batch_data: Dictionary with show names as keys and contact lists as values
    """
    # Load MongoDB configuration
    mongo_config = get_mongo_config()
    if not mongo_config:
        print("Error: Could not load MongoDB configuration from environment")
        return
        
    MONGO_URI = mongo_config["mongo_uri"]
    if not MONGO_URI:
        print("Error: MONGO_URI not found in configuration")
        return
    
    # MongoDB configuration
    MONGO_DB = "guest_list_contacts"
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB]

        # Group contacts by source
        contacts_by_source = {}

        # Process each show in batch_data
        for show_name, contact_list in batch_data.items():
            for contact in contact_list:
                if len(contact) >= 9:
                    contact_doc = {
                        "venue": contact[0],
                        "show_date": contact[1],
                        "show_datetime": parse_show_date_with_year(contact[1]),
                        "email": contact[2],
                        "source": contact[3],
                        "show_time": contact[4],
                        "ticket_type": contact[5],
                        "first_name": contact[6],
                        "last_name": contact[7],
                        "tickets": contact[8],
                        "phone": contact[9] if len(contact) > 9 else None,
                        "show_name": show_name,
                        "added_to_mailerlite": False,
                        "mailerlite_added_date": None,
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }

                    enhanced_field_names = [
                        "discount_code", "total_price", "order_id", "transaction_id",
                        "customer_id", "payment_method", "entry_code", "notes"
                    ]
                    for i, field_name in enumerate(enhanced_field_names, start=10):
                        if len(contact) > i and contact[i] is not None:
                            contact_doc[field_name] = contact[i]

                    # Determine collection name
                    source_name = contact_doc["source"] if contact_doc["source"] else "contacts"
                    if not isinstance(source_name, str) or not source_name.strip():
                        source_name = "contacts"
                    source_name = source_name.strip()

                    if source_name not in contacts_by_source:
                        contacts_by_source[source_name] = []
                    contacts_by_source[source_name].append(contact_doc)

        # Insert contacts by source
        for source_name, contacts_to_insert in contacts_by_source.items():
            collection = db[source_name]
            inserted_count = 0
            for contact_doc in contacts_to_insert:
                # Build duplicate query
                duplicate_query = {}
                if "transaction_id" in contact_doc and contact_doc["transaction_id"]:
                    duplicate_query["transaction_id"] = contact_doc["transaction_id"]
                elif "order_id" in contact_doc and contact_doc["order_id"]:
                    duplicate_query["order_id"] = contact_doc["order_id"]
                else:
                    duplicate_query = {
                        "email": contact_doc["email"],
                        "show_date": contact_doc["show_date"],
                        "venue": contact_doc["venue"],
                        "first_name": contact_doc["first_name"],
                        "last_name": contact_doc["last_name"]
                    }
                existing_contact = collection.find_one(duplicate_query)
                if not existing_contact:
                    collection.insert_one(contact_doc)
                    inserted_count += 1
                    logger.debug(f"New contact: {contact_doc['email']} for {contact_doc['venue']} on {contact_doc['show_date']} in collection {source_name}")
                else:
                    logger.debug(f"Updating existing contact: {contact_doc['email']} (found via {list(duplicate_query.keys())[0]}) in collection {source_name}")
                    update_fields = {
                        "updated_at": datetime.utcnow(),
                        "show_datetime": parse_show_date_with_year(contact_doc["show_date"]),
                        "tickets": contact_doc["tickets"],
                        "phone": contact_doc["phone"],
                        "source": contact_doc["source"],
                        "show_time": contact_doc["show_time"],
                        "ticket_type": contact_doc["ticket_type"],
                        "first_name": contact_doc["first_name"],
                        "last_name": contact_doc["last_name"]
                    }
                    enhanced_fields = ["discount_code", "total_price", "order_id", "transaction_id", 
                                     "customer_id", "payment_method", "entry_code", "notes"]
                    for field in enhanced_fields:
                        if field in contact_doc and contact_doc[field] is not None:
                            update_fields[field] = contact_doc[field]
                    collection.update_one(
                        duplicate_query,
                        {"$set": update_fields}
                    )
            if inserted_count:
                print(f"Successfully inserted {inserted_count} new contacts to MongoDB collection '{source_name}'")
            else:
                print(f"No new contacts to insert for collection '{source_name}'")
    except Exception as e:
        print(f"Error adding contacts to MongoDB: {str(e)}")
    finally:
        if 'client' in locals():
            client.close()
