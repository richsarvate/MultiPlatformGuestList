import json
import logging
import os
import time
import sys
import re
import pickle
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
from bs4 import BeautifulSoup
from base64 import urlsafe_b64decode
from pymongo import MongoClient
from insertIntoGoogleSheet import insert_data_into_google_sheet
from addContactsToMongoDB import batch_add_contacts_to_mongodb
from getVenueAndDate import get_venue, convert_date_from_any_format, format_time
import config

# Configure logging
LOG_FILE = "/home/ec2-user/GuestListScripts/fever_sales.log"
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

# Load configuration
try:
    CONFIG_FILE = "/home/ec2-user/GuestListScripts/bucketlistConfig.json"
    with open(CONFIG_FILE, 'r') as f:
        mongo_config = json.load(f)
    MONGO_URI = mongo_config["MONGO_URI"]
except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
    logger.warning(f"Could not load MongoDB config: {e}. MongoDB features will be disabled.")
    MONGO_URI = None

# MongoDB Configuration
MONGO_DB = "fever_events"
MONGO_COLLECTION = "email_tracking"
MONGO_SALES_COLLECTION = "fever_sales"

# Define the SCOPES. If modifying it, delete the token.pickle file.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def show_help():
    """Display help message for command line usage."""
    help_text = """
Fever Gmail Integration Script

USAGE:
    python getFeverFromGmail.py [OPTIONS]

OPTIONS:
    --mongo-only      Save data only to MongoDB, skip Google Sheets
    --force-refresh   Bypass duplicate checks and reimport all data
    --days=N          Process emails from last N days (e.g., --days=215)
    --help           Show this help message

EXAMPLES:
    python getFeverFromGmail.py
    python getFeverFromGmail.py --mongo-only
    python getFeverFromGmail.py --force-refresh
    python getFeverFromGmail.py --mongo-only --force-refresh --days=215

DESCRIPTION:
    Fetches Fever reservation emails from Gmail and processes guest information.
    
    --mongo-only: Saves data directly to MongoDB without updating Google Sheets.
                 Useful for bulk historical imports or when Google Sheets sync is not needed.
    
    --force-refresh: Reprocesses all emails and updates existing records.
                    Uses upsert operations to fix existing data (e.g., email fields)
                    without creating duplicates. Safe to run multiple times.
    
    --days=N: Process emails from last N days instead of default interval.
             For beginning of 2025, use --days=215 (as of August 1, 2025).

NOTES:
    - Uses upsert operations to prevent duplicates and fix existing records
    - Customer emails are empty (Fever doesn't provide customer email addresses)
    - Requires valid Gmail API credentials
    - Uses MongoDB for duplicate detection and data storage
    - Automatically handles venue mapping and time formatting
    - Supports batch processing for improved performance
    """
    print(help_text)

def get_help_flag():
    """Check if help flag is provided."""
    return '--help' in sys.argv or '-h' in sys.argv

def check_mongo_only_flag():
    """Check if --mongo-only flag is present in command line arguments"""
    return '--mongo-only' in sys.argv

def check_force_refresh_flag():
    """Check if --force-refresh flag is present in command line arguments"""
    return '--force-refresh' in sys.argv

def batch_add_contacts_to_mongodb(batch_data):
    """
    Add contacts to MongoDB in batch format compatible with mongo-only mode.
    batch_data format: {"venue - date": [guest_arrays]}
    """
    try:
        from addContactsToMongoDB import batch_add_contacts_to_mongodb as mongo_batch_add
        
        # Convert the batch_data to the format expected by the MongoDB function
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

def is_processed_email(message_id, force_refresh=False):
    """Check if email message has already been processed. If force_refresh=True, always return False to process all emails."""
    if force_refresh or not MONGO_URI:
        return False
    
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        collection = db[MONGO_COLLECTION]
        exists = collection.find_one({"messageId": message_id})
        return bool(exists)
    except Exception as e:
        logger.error(f"Error checking message ID: {str(e)}")
        return False
    finally:
        if 'client' in locals():
            client.close()

def mark_email_processed(message_data, force_refresh=False):
    """Mark email as processed in MongoDB using upsert to avoid duplicates."""
    if not MONGO_URI:
        return
        
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        collection = db[MONGO_COLLECTION]
        
        # Use upsert to replace existing records or insert new ones
        query = {"messageId": message_data["messageId"]}
        collection.replace_one(query, message_data, upsert=True)
        
        if force_refresh:
            logger.debug(f"Upserted email record for message {message_data['messageId']}")
    except Exception as e:
        logger.error(f"Error marking email as processed: {str(e)}")
    finally:
        if 'client' in locals():
            client.close()

def batch_add_contacts_to_mongodb_upsert(batch_data, force_refresh=False):
    """
    Batch adds contact data to MongoDB using upsert to prevent duplicates.
    Custom version for Fever that updates existing records.
    """
    if not MONGO_URI:
        logger.warning("MongoDB URI not available, skipping upsert batch operation")
        return
        
    try:
        # Import the original function as fallback for non-force-refresh mode
        from addContactsToMongoDB import batch_add_contacts_to_mongodb as original_batch_add
        
        if not force_refresh:
            # Use original function for normal operations
            original_batch_add(batch_data)
            return
            
        # Use upsert logic for force refresh
        client = MongoClient(MONGO_URI)
        db = client["guest_list_contacts"]
        collection = db["contacts"]
        
        upsert_count = 0
        for show_name, contact_list in batch_data.items():
            for contact in contact_list:
                if len(contact) >= 9:  # Ensure we have required fields
                    # Create unique identifier for upsert
                    query = {
                        "venue": contact[0],
                        "show_date": contact[1], 
                        "source": contact[3],
                        "first_name": contact[6],
                        "last_name": contact[7]
                    }
                    
                    # Create document to upsert
                    contact_doc = {
                        "venue": contact[0],
                        "show_date": contact[1],
                        "email": contact[2],  # Now empty string for Fever
                        "source": contact[3],
                        "show_time": contact[4],
                        "ticket_type": contact[5],
                        "first_name": contact[6],
                        "last_name": contact[7],
                        "tickets": contact[8],
                        "phone": contact[9] if len(contact) > 9 else "",
                        # Enhanced fields
                        "discount_code": contact[10] if len(contact) > 10 else None,
                        "total_price": contact[11] if len(contact) > 11 else None,
                        "order_id": contact[12] if len(contact) > 12 else None,
                        "transaction_id": contact[13] if len(contact) > 13 else None,
                        "customer_id": contact[14] if len(contact) > 14 else None,
                        "payment_method": contact[15] if len(contact) > 15 else None,
                        "entry_code": contact[16] if len(contact) > 16 else None,
                        "notes": contact[17] if len(contact) > 17 else None,
                        "timestamp": datetime.utcnow(),
                        "updated_timestamp": datetime.utcnow()
                    }
                    
                    # Perform upsert
                    result = collection.replace_one(query, contact_doc, upsert=True)
                    if result.upserted_id or result.modified_count > 0:
                        upsert_count += 1
        
        logger.info(f"Upserted {upsert_count} contact records in MongoDB")
        
    except ImportError as e:
        logger.error(f"Failed to import addContactsToMongoDB: {e}")
    except Exception as e:
        logger.error(f"Error in upsert batch MongoDB operation: {e}")
    finally:
        if 'client' in locals():
            client.close()

def store_fever_transaction(transaction_data, force_refresh=False):
    """Store transaction data for tracking using upsert to avoid duplicates."""
    if not MONGO_URI:
        return
        
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        collection = db[MONGO_SALES_COLLECTION]
        
        # Use upsert to replace existing records or insert new ones
        # Create unique identifier based on reservation details
        query = {
            "reservationNumber": transaction_data["reservationNumber"],
            "showName": transaction_data["showName"],
            "showDate": transaction_data["showDate"]
        }
        collection.replace_one(query, transaction_data, upsert=True)
        
        if force_refresh:
            logger.debug(f"Upserted transaction record for reservation {transaction_data['reservationNumber']}")
    except Exception as e:
        logger.error(f"Error storing transaction: {str(e)}")
    finally:
        if 'client' in locals():
            client.close()

def get_email_html(service, user_id, msg_id):
    """Get HTML content from email message."""
    try:
        # Fetch the email message by id
        message = service.users().messages().get(userId=user_id, id=msg_id).execute()

        # Get the payload and then get the HTML part of the email
        payload = message['payload']

        # Check if the email is multipart
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/html':
                    data = part['body']['data']
                    break
            else:
                # No HTML part found, try text/plain
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body']['data']
                        break
                else:
                    logger.warning(f"No suitable content type found for message {msg_id}")
                    return None
        else:
            # If not multipart, directly get the content
            data = payload['body']['data']

        # Decode the base64 encoded string
        html_content = urlsafe_b64decode(data).decode('utf-8')
        return html_content
    except HttpError as error:
        logger.error(f'An error occurred fetching email HTML: {error}')
        return None
    except Exception as e:
        logger.error(f'Unexpected error fetching email HTML: {e}')
        return None

def extract_email_from_message(service, user_id, msg_id):
    """Extract sender email from message headers. For Fever, return empty string as we don't have customer emails."""
    try:
        # For Fever integration, we don't have customer emails, only the company sender
        # Return empty string like DoMORE to indicate no customer email available
        return ""
    except Exception as e:
        logger.error(f"Error extracting email from message {msg_id}: {e}")
        return ""

def parse_price_from_html(html_content):
    """Extract price from email HTML content."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for price patterns in the HTML
        price_patterns = [
            r'(\d+\.?\d*)\s*(USD|usd|\$)',
            r'\$(\d+\.?\d*)',
            r'Total[:\s]*(\d+\.?\d*)',
            r'Price[:\s]*(\d+\.?\d*)'
        ]
        
        text_content = soup.get_text()
        for pattern in price_patterns:
            match = re.search(pattern, text_content)
            if match:
                price_str = match.group(1)
                try:
                    return float(price_str)
                except ValueError:
                    continue
        
        logger.debug("No price found in email HTML")
        return None
    except Exception as e:
        logger.error(f"Error parsing price from HTML: {e}")
        return None

def format_time(time_str):
    """Format time string properly."""
    # Remove whitespace and format the time properly
    time_str = time_str.strip().lower()
    
    # If the time ends with ":00", remove the minutes part
    formatted_time = re.sub(r'(\d+):00\s*(am|pm)', r'\1\2', time_str)
    
    # Otherwise, return the original time string with any necessary cleanup
    return formatted_time if formatted_time else time_str

def get_email_body(service, user_id, msg_id):
    """Extract comprehensive guest data from Fever email."""
    html_content = get_email_html(service, user_id, msg_id)
    if not html_content:
        return None, None, None, None, None, None

    # Parse the HTML content
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find and extract customer name
    name_img_tag = soup.find('img', alt="Name")
    if name_img_tag:
        full_name = name_img_tag.find_parent('td').find_next_sibling('td').get_text(strip=True)
        name_parts = full_name.split()  # Splits the name into a list of words
        if len(name_parts) >= 2:  # Check if there are at least two parts
            first_name = name_parts[0]
            last_name = ' '.join(name_parts[1:])  # Handles cases where the last name might be multi-part
        else:  # Handle cases where there might only be one part to the name
            first_name = full_name
            last_name = ""
    else:
        first_name, last_name = "Name", "Not found"

    # Find the <img> tag with alt="Tickets" and get the ticket number from the next <p> tag
    tickets_img_tag = soup.find('img', alt="Tickets")
    if tickets_img_tag:
        tickets_text = tickets_img_tag.find_parent('td').find_next_sibling('td').get_text(strip=True)
        match = re.search(r'\d+', tickets_text)  # Search for any sequence of digits in the text
        if match:
            ticket_number = int(match.group())  # Convert to int
        else:
            ticket_number = 1  # Default to 1 if no number is found
    else:
        ticket_number = 1

    # Find the <img> tag with alt="Date" and get the date of the show from the next <p> tag
    date_img_tag = soup.find('img', alt="Date")
    if date_img_tag:
        show_date = date_img_tag.find_parent('td').find_next_sibling('td').get_text(strip=True)
    else:
        show_date = "Date not found"

    # Find the <img> tag with alt="Hour" and get the time of the show from the next <p> tag
    time_img_tag = soup.find('img', alt="Hour")
    if time_img_tag:
        show_time = time_img_tag.find_parent('td').find_next_sibling('td').get_text(strip=True)
    else:
        show_time = "Time not found"

    # Extract price from HTML
    price = parse_price_from_html(html_content)

    return first_name, last_name, ticket_number, show_date, format_time(show_time), price

def getEmails(days=None, mongo_only=False, force_refresh=False):
    """Main function to fetch and process Fever emails from Gmail."""
    creds = None

    logger.info("Starting Fever sales sync from Gmail")

    # Gmail authentication
    if os.path.exists(config.GMAIL_TOKEN_PATH):
        with open(config.GMAIL_TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                config.GMAIL_CREDS_FILE,
                scopes=SCOPES,
                redirect_uri='http://ec2-3-17-25-171.us-east-2.compute.amazonaws.com:8080/'
            )
            creds = flow.run_local_server(port=8080, host="ec2-3-17-25-171.us-east-2.compute.amazonaws.com", open_browser=False)

        with open(config.GMAIL_TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)

    # Calculate time range for search
    if days:
        # Use specified days
        days_ago = int(time.time()) - (days * 24 * 60 * 60)
        search_query = f"after:{days_ago} subject:'New reservation with Fever'"
        logger.info(f"Searching emails from last {days} days")
    else:
        # Use default interval from config
        current_time_epoch = int(time.time())
        last_run = current_time_epoch - (config.GMAIL_SCRIPT_INTERVAL_MINUTES_FEVER * 60)
        search_query = f"after:{last_run} subject:'New reservation with Fever'"
        logger.info(f"Searching emails from last {config.GMAIL_SCRIPT_INTERVAL_MINUTES_FEVER} minutes")

    try:
        result = service.users().messages().list(userId='me', q=search_query).execute()
        messages = result.get('messages', [])
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        return

    if not messages:
        logger.info(f"No Fever reservation emails found in the specified time range")
        return

    logger.info(f"Found {len(messages)} Fever reservation emails")

    batch_data = {}
    total_processed = 0
    total_skipped = 0

    for msg in messages:
        try:
            msg_id = msg['id']
            
            # Check if already processed (unless force refresh)
            if is_processed_email(msg_id, force_refresh):
                total_skipped += 1
                logger.debug(f"Skipping already processed message {msg_id}")
                continue

            # Fetch the full message for subject extraction
            full_message = service.users().messages().get(userId='me', id=msg_id).execute()
            headers = full_message['payload']['headers']
            subject = next((header['value'] for header in headers if header['name'] == 'Subject'), "Subject not found")

            # Extract guest data from email
            first_name, last_name, number_of_tickets, show_date, show_time, price = get_email_body(service, 'me', msg_id)
            
            if not first_name or first_name == "Name":
                logger.warning(f"Could not extract guest data from message {msg_id}")
                continue

            # Extract customer email
            customer_email = extract_email_from_message(service, 'me', msg_id)
            
            # Get venue from subject
            venue = get_venue(subject)
            
            # Convert and format date
            show_date_formatted = convert_date_from_any_format(show_date)
            show_date_with_time = f"{show_date_formatted} {show_time}"

            # Use message ID as reservation number for uniqueness
            reservation_number = msg_id

            logger.info(f"Processing: {first_name} {last_name} - {venue} on {show_date_with_time} - {number_of_tickets} tickets")

            # Create 18-field guest data array matching Bucketlist structure
            guest_array = [
                venue,                              # 0: venue
                show_date_with_time,               # 1: show_date_with_time
                customer_email,                    # 2: email
                "Fever",                           # 3: source
                show_time,                         # 4: show_time
                "GA",                              # 5: ticket_type (General Admission default)
                first_name,                        # 6: first_name
                last_name,                         # 7: last_name
                number_of_tickets,                 # 8: quantity
                "",                                # 9: phone (not available from Fever)
                None,                              # 10: discount_code
                price,                             # 11: total_price
                None,                              # 12: order_id
                msg_id,                            # 13: transaction_id (using message ID)
                customer_email,                    # 14: customer_id
                "Fever",                           # 15: payment_method
                msg_id,                            # 16: entry_code (using message ID)
                f"Fever reservation - {subject}"   # 17: notes
            ]

            # Add to batch data
            if mongo_only:
                show_key = f"{venue} - {show_date_with_time}"
                if show_key not in batch_data:
                    batch_data[show_key] = []
                batch_data[show_key].append(guest_array)
            else:
                # Original structure for Google Sheets
                if venue not in batch_data:
                    batch_data[venue] = {}
                if show_date_with_time not in batch_data[venue]:
                    batch_data[venue][show_date_with_time] = []
                batch_data[venue][show_date_with_time].append(guest_array)

            # Always mark email as processed and store transaction (using upsert)
            mark_email_processed({
                "messageId": msg_id,
                "subject": subject,
                "customerEmail": customer_email,
                "customerName": f"{first_name} {last_name}",
                "venue": venue,
                "showDate": show_date_with_time,
                "timestamp": datetime.utcnow()
            }, force_refresh)
            
            store_fever_transaction({
                "messageId": msg_id,
                "customerName": f"{first_name} {last_name}",
                "customerEmail": customer_email,
                "quantity": number_of_tickets,
                "price": price,
                "venue": venue,
                "showDate": show_date_with_time,
                "reservationNumber": reservation_number,  # Add for upsert uniqueness
                "showName": f"{venue} Show",  # Add for upsert uniqueness
                "timestamp": datetime.utcnow()
            }, force_refresh)

            total_processed += 1

        except Exception as e:
            logger.error(f"Error processing message {msg.get('id', 'unknown')}: {e}")
            continue

    # Process batch data
    if batch_data:
        logger.info(f"Processing {total_processed} guests from {len(batch_data)} shows")
        
        if mongo_only:
            # Save directly to MongoDB using upsert for force_refresh
            batch_add_contacts_to_mongodb_upsert(batch_data, force_refresh)
            logger.info("Successfully saved data to MongoDB only")
        else:
            # Use original Google Sheets process
            for venue in batch_data:
                for date in batch_data[venue]:
                    insert_data_into_google_sheet({venue: batch_data[venue][date]})
            logger.info("Successfully processed all Fever reservations")
    else:
        logger.info("No new Fever reservations to process")

    if total_skipped > 0:
        logger.info(f"Skipped {total_skipped} already processed emails")

def main():
    """Main entry point with command line argument handling."""
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
    
    # Parse days parameter
    days = None
    for arg in sys.argv:
        if arg.startswith('--days='):
            try:
                days = int(arg.split('=')[1])
                logger.info(f"Using {days} days lookback period")
                break
            except (ValueError, IndexError):
                logger.error(f"Invalid days parameter: {arg}")
                sys.exit(1)
        elif arg.isdigit():
            # Backward compatibility with plain digit format
            days = int(arg)
            logger.info(f"Using {days} days lookback period (legacy format)")
            break
    
    try:
        getEmails(days=days, mongo_only=mongo_only, force_refresh=force_refresh)
    except Exception as e:
        logger.error(f"Fatal error in main execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

