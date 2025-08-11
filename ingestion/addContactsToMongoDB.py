import json
import logging
import re
from datetime import datetime
from pymongo import MongoClient
from shared_config import get_mongo_config

# Set up logging
logger = logging.getLogger(__name__)

def parse_show_date_with_year(date_string: str) -> datetime:
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
            year = int(year_match.group(1))
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
    MONGO_COLLECTION = "contacts"
    
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        collection = db[MONGO_COLLECTION]
        
        contacts_to_insert = []
        
        # Process each show in batch_data
        for show_name, contact_list in batch_data.items():
            for contact in contact_list:
                # Extract data from the contact array
                # Array structure: [venue, date, email, source, time, type, firstname, lastname, tickets, phone, enhanced_fields...]
                if len(contact) >= 9:  # Ensure we have at least the required fields
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
                    
                    # Add enhanced fields if available (indices 10+)
                    enhanced_field_names = [
                        "discount_code", "total_price", "order_id", "transaction_id",
                        "customer_id", "payment_method", "entry_code", "notes"
                    ]
                    
                    for i, field_name in enumerate(enhanced_field_names, start=10):
                        if len(contact) > i and contact[i] is not None:
                            contact_doc[field_name] = contact[i]
                    
                    # Check if contact already exists to avoid duplicates
                    # Use transaction_id or order_id for better duplicate detection
                    duplicate_query = {}
                    
                    # Primary check: transaction_id (most reliable)
                    if len(contact) > 13 and contact[13]:  # transaction_id is at index 13
                        duplicate_query["transaction_id"] = contact[13]
                    # Secondary check: order_id (fallback)
                    elif len(contact) > 12 and contact[12]:  # order_id is at index 12
                        duplicate_query["order_id"] = contact[12]
                    # Fallback to old method for legacy data
                    else:
                        duplicate_query = {
                            "email": contact_doc["email"],
                            "show_date": contact_doc["show_date"],
                            "venue": contact_doc["venue"]
                        }
                    
                    existing_contact = collection.find_one(duplicate_query)
                    
                    if not existing_contact:
                        contacts_to_insert.append(contact_doc)
                        logger.debug(f"New contact: {contact_doc['email']} for {contact_doc['venue']} on {contact_doc['show_date']}")
                    else:
                        logger.debug(f"Updating existing contact: {contact_doc['email']} (found via {list(duplicate_query.keys())[0]})")
                        # Update existing contact with all fields including enhanced ones
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
                        
                        # Add enhanced fields if they exist (for new data structure)
                        enhanced_fields = ["discount_code", "total_price", "order_id", "transaction_id", 
                                         "customer_id", "payment_method", "entry_code", "notes"]
                        
                        for field in enhanced_fields:
                            if field in contact_doc and contact_doc[field] is not None:
                                update_fields[field] = contact_doc[field]
                        
                        collection.update_one(
                            duplicate_query,  # Use the same query that found the duplicate
                            {"$set": update_fields}
                        )
        
        # Insert new contacts in batch
        if contacts_to_insert:
            result = collection.insert_many(contacts_to_insert)
            print(f"Successfully inserted {len(result.inserted_ids)} new contacts to MongoDB")
        else:
            print("No new contacts to insert")
            
    except Exception as e:
        print(f"Error adding contacts to MongoDB: {str(e)}")
    finally:
        if 'client' in locals():
            client.close()
