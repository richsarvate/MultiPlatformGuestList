import json
import logging
import os
import time
import sys
import csv
import pickle
import base64
import requests
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from bs4 import BeautifulSoup
from pymongo import MongoClient
from insertIntoGoogleSheet import insert_data_into_google_sheet
from addContactsToMongoDB import batch_add_contacts_to_mongodb
from getVenueAndDate import get_venue, extract_time_from_subject, extract_date_from_subject, convert_date_from_any_format
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config.config as config

# Configure logging
LOG_FILE = "/home/ec2-user/GuestListScripts/logs/domore_sales.log"
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
    CONFIG_FILE = "config/bucketlistConfig.json"
    with open(CONFIG_FILE, 'r') as f:
        mongo_config = json.load(f)
    MONGO_URI = mongo_config["MONGO_URI"]
except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
    logger.warning(f"Could not load MongoDB config: {e}. MongoDB features will be disabled.")
    MONGO_URI = None

# MongoDB Configuration
MONGO_DB = "domore_events"
MONGO_COLLECTION = "email_tracking"
MONGO_SALES_COLLECTION = "domore_sales"

# Define the SCOPES. If modifying it, delete the token.pickle file.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def show_help():
    """Display help message for command line usage."""
    help_text = """
DoMORE Gmail Integration Script

USAGE:
    python getDoMoreFromGmail.py [OPTIONS]

OPTIONS:
    --mongo-only      Save data only to MongoDB, skip Google Sheets
    --force-refresh   Bypass duplicate checks and reimport all data
    --days=N          Search emails from last N days (for historical import)
    --help           Show this help message

EXAMPLES:
    python getDoMoreFromGmail.py                    # Normal sync (last 1 hour)
    python getDoMoreFromGmail.py --mongo-only       # MongoDB only, last 1 hour
    python getDoMoreFromGmail.py --days=365         # Search last year
    python getDoMoreFromGmail.py --mongo-only --force-refresh --days=365  # Historical import

DESCRIPTION:
    Processes DoMORE guest list emails from Gmail with CSV attachments.
    
    --mongo-only: Saves data directly to MongoDB without updating Google Sheets.
                 Useful for bulk historical imports or when Google Sheets sync is not needed.
    
    --force-refresh: Ignores existing email processing records.
                    Useful for reprocessing emails or fixing data inconsistencies.
    
    --days=N: Search emails from the last N days instead of default 1 hour interval.
             For beginning of year: use --days=365 or --days=250

NOTES:
    - Default behavior searches last 1 hour (for cronjob)
    - Requires Gmail API credentials and DoMORE email access
    - Automatically clicks "I RECEIVED THIS LIST" button in emails
    - Processes CSV attachments with guest names and ticket counts
    - All tickets are marked as free (price: 0.0)
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

def is_processed_email(message_id, csv_filename, force_refresh=False):
    """Check if email and CSV combination has already been processed."""
    if force_refresh or not MONGO_URI:
        return False
    
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        collection = db[MONGO_COLLECTION]
        exists = collection.find_one({
            "messageId": message_id,
            "csvFilename": csv_filename
        })
        return bool(exists)
    except Exception as e:
        logger.error(f"Error checking message processing status: {str(e)}")
        return False
    finally:
        if 'client' in locals():
            client.close()

def mark_email_processed(message_data):
    """Mark email as processed in MongoDB."""
    if not MONGO_URI:
        return
        
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        collection = db[MONGO_COLLECTION]
        collection.insert_one(message_data)
    except Exception as e:
        logger.error(f"Error marking email as processed: {str(e)}")
    finally:
        if 'client' in locals():
            client.close()

def store_domore_transaction(transaction_data):
    """Store transaction data for tracking."""
    if not MONGO_URI:
        return
        
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        collection = db[MONGO_SALES_COLLECTION]
        collection.insert_one(transaction_data)
    except Exception as e:
        logger.error(f"Error storing transaction: {str(e)}")
    finally:
        if 'client' in locals():
            client.close()

def extract_button_url(html_content):
    """Extract the 'I RECEIVED THIS LIST' button URL from email HTML."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        button = soup.find('a', string='I RECEIVED THIS LIST')  # Adjust text if necessary
        if button:
            return button['href']
        return None
    except Exception as e:
        logger.error(f"Error extracting button URL: {e}")
        return None

def click_button(url):
    """Click the confirmation button with robust error handling."""
    try:
        session = requests.Session()  # Using session to maintain context across requests
        response = session.get(url, allow_redirects=True, timeout=10)  # Ensure redirects are allowed
        final_url = response.url  # Get the final URL after redirection
        logger.info(f"Button clicked successfully. Final URL: {final_url}")
        return response.status_code, response.text
    except requests.exceptions.Timeout:
        logger.warning("Button click timed out after 10 seconds")
        return None, None
    except requests.exceptions.RequestException as e:
        logger.warning(f"Button click failed: {e}")
        return None, None
    except Exception as e:
        logger.warning(f"Unexpected error clicking button: {e}")
        return None, None


def getEmails(days=None, mongo_only=False, force_refresh=False):
    """Main function to fetch and process DoMORE emails from Gmail."""
    creds = None

    logger.info("Starting DoMORE guest list sync from Gmail")

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
        search_query = f"after:{days_ago} subject:'MORE Guest List'"
        logger.info(f"Searching emails from last {days} days")
    else:
        # Use default interval from config (for cronjob)
        current_time_epoch = int(time.time())
        last_run = current_time_epoch - (config.GMAIL_SCRIPT_INTERVAL_HOURS * 60 * 60)
        search_query = f"after:{last_run} subject:'MORE Guest List'"
        logger.info(f"Searching emails from last {config.GMAIL_SCRIPT_INTERVAL_HOURS} hours")

    try:
        result = service.users().messages().list(userId='me', q=search_query).execute()
        messages = result.get('messages', [])
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        return

    if not messages:
        logger.info(f"No DoMORE guest list emails found in the specified time range")
        return

    logger.info(f"Found {len(messages)} DoMORE guest list emails")

    batch_data = {}
    total_processed = 0
    total_skipped = 0

    for msg in messages:
        try:
            msg_id = msg['id']
            
            # Fetch the full message
            full_message = service.users().messages().get(userId='me', id=msg_id).execute()
            headers = full_message['payload']['headers']
            subject = next((header['value'] for header in headers if header['name'] == 'Subject'), "Subject not found")

            logger.info(f"Processing message: {subject}")

            # Process CSV attachments
            csv_data = None
            csv_filename = None
            
            if 'parts' in full_message['payload']:
                for part in full_message['payload']['parts']:
                    if part['filename'] and part['filename'].endswith('.csv'):
                        csv_filename = part['filename']
                        
                        # Check if already processed (unless force refresh)
                        if is_processed_email(msg_id, csv_filename, force_refresh):
                            total_skipped += 1
                            logger.debug(f"Skipping already processed CSV: {csv_filename}")
                            continue

                        try:
                            attachment_id = part['body']['attachmentId']
                            attachment = service.users().messages().attachments().get(
                                userId='me', messageId=msg_id, id=attachment_id
                            ).execute()
                            data = attachment['data']
                            csv_data = base64.urlsafe_b64decode(data.encode('UTF-8')).decode('UTF-8')
                            logger.info(f"Successfully extracted CSV: {csv_filename}")
                        except Exception as e:
                            logger.error(f"Error extracting CSV attachment {csv_filename}: {e}")
                            continue

            # Handle button clicking
            if 'parts' in full_message['payload']:
                for part in full_message['payload']['parts']:
                    if part['mimeType'] == 'text/html':
                        try:
                            html_data = base64.urlsafe_b64decode(part['body']['data'].encode('UTF-8')).decode('UTF-8')
                            button_url = extract_button_url(html_data)
                            if button_url:
                                logger.info(f"Found confirmation button, attempting to click...")
                                status_code, page_content = click_button(button_url)
                                if status_code:
                                    logger.info(f"Button clicked successfully. HTTP Status: {status_code}")
                                else:
                                    logger.warning("Button click failed, continuing with processing")
                        except Exception as e:
                            logger.warning(f"Error processing HTML for button clicking: {e}")

            # Process CSV data if found
            if csv_data and csv_filename:
                logger.info(f"Processing CSV data from {csv_filename}")
                
                try:
                    reader = csv.reader(csv_data.splitlines())
                    
                    # Extract venue and date information from subject
                    venue_name = get_venue(subject)
                    extracted_date = extract_date_from_subject(subject)
                    showtime = convert_date_from_any_format(extracted_date)
                    time_of_show = extract_time_from_subject(subject)
                    
                    # Fallback logic to prevent None dates
                    if showtime is None:
                        if extracted_date:
                            logger.warning(f"Could not parse date '{extracted_date}' from subject: {subject}")
                            # Use raw extracted date as fallback
                            showtime = extracted_date
                        else:
                            logger.warning(f"No date found in subject: {subject}")
                            # Use a generic fallback
                            showtime = "Date TBD"
                    
                    if time_of_show is None:
                        logger.warning(f"No time found in subject: {subject}")
                        time_of_show = "8pm"  # Default time fallback
                    
                    show_date_with_time = f"{showtime} {time_of_show}"
                    logger.info(f"Processed show date: {show_date_with_time}")

                    csv_guests_processed = 0
                    
                    for row in reader:
                        # Skip header rows
                        if 'First Name' in row or 'first_name' in row or not row:
                            continue
                        
                        if len(row) >= 3:
                            first_name = row[0].strip()
                            last_name = row[1].strip()
                            num_tickets = int(row[2]) if row[2].strip().isdigit() else 1
                            
                            # Create unique transaction ID
                            transaction_id = f"{msg_id}_{csv_filename}_{csv_guests_processed}"
                            
                            # Create 18-field guest data array
                            guest_array = [
                                venue_name,                     # 0: venue
                                show_date_with_time,           # 1: show_date_with_time
                                "",                            # 2: email (empty)
                                "DoMORE",                      # 3: source
                                time_of_show,                  # 4: show_time
                                "GA",                          # 5: ticket_type
                                first_name,                    # 6: first_name
                                last_name,                     # 7: last_name
                                num_tickets,                   # 8: quantity
                                "",                            # 9: phone (empty)
                                None,                          # 10: discount_code
                                0.0,                           # 11: total_price (free tickets)
                                None,                          # 12: order_id
                                transaction_id,                # 13: transaction_id
                                "",                            # 14: customer_id (empty)
                                "DoMORE",                      # 15: payment_method
                                transaction_id,                # 16: entry_code
                                f"DoMORE Guest List - {csv_filename}"  # 17: notes
                            ]

                            # Add to batch data
                            if mongo_only:
                                show_key = f"{venue_name} - {show_date_with_time}"
                                if show_key not in batch_data:
                                    batch_data[show_key] = []
                                batch_data[show_key].append(guest_array)
                            else:
                                # Original structure for Google Sheets
                                show_name = subject
                                if show_name not in batch_data:
                                    batch_data[show_name] = []
                                batch_data[show_name].append(guest_array)

                            csv_guests_processed += 1

                    logger.info(f"Processed {csv_guests_processed} guests from {csv_filename}")
                    total_processed += csv_guests_processed

                    # Mark email as processed and store transaction
                    if not force_refresh:
                        mark_email_processed({
                            "messageId": msg_id,
                            "csvFilename": csv_filename,
                            "subject": subject,
                            "venue": venue_name,
                            "showDate": show_date_with_time,
                            "guestsProcessed": csv_guests_processed,
                            "timestamp": datetime.utcnow()
                        })
                        
                        store_domore_transaction({
                            "messageId": msg_id,
                            "csvFilename": csv_filename,
                            "subject": subject,
                            "venue": venue_name,
                            "showDate": show_date_with_time,
                            "totalGuests": csv_guests_processed,
                            "timestamp": datetime.utcnow()
                        })

                except Exception as e:
                    logger.error(f"Error processing CSV data from {csv_filename}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error processing message {msg.get('id', 'unknown')}: {e}")
            continue

    # Process batch data
    if batch_data:
        logger.info(f"Processing {total_processed} total guests from {len(batch_data)} shows")
        
        if mongo_only:
            # Save directly to MongoDB
            batch_add_contacts_to_mongodb(batch_data)
            logger.info("Successfully saved data to MongoDB only")
        else:
            # Use original Google Sheets process
            insert_data_into_google_sheet(batch_data)
            logger.info("Successfully processed all DoMORE guest lists")
    else:
        logger.info("No new DoMORE guest lists to process")

    if total_skipped > 0:
        logger.info(f"Skipped {total_skipped} already processed emails")

def parse_days_parameter():
    """Parse --days=N parameter from command line arguments."""
    for arg in sys.argv:
        if arg.startswith('--days='):
            try:
                days = int(arg.split('=')[1])
                return days
            except (ValueError, IndexError):
                logger.error(f"Invalid days parameter: {arg}. Use --days=N where N is a number.")
                return None
    return None

def main():
    """Main entry point with command line argument handling."""
    # Check for help flag first
    if get_help_flag():
        show_help()
        return
    
    # Check flags
    mongo_only = check_mongo_only_flag()
    force_refresh = check_force_refresh_flag()
    days = parse_days_parameter()
    
    if mongo_only:
        logger.info("Running in MONGO-ONLY mode - skipping Google Sheets integration")
    if force_refresh:
        logger.info("Running in FORCE-REFRESH mode - bypassing duplicate checks")
    if days:
        logger.info(f"Using {days} days lookback period")
    
    # Get days parameter if specified (for backward compatibility)
    if not days:
        for i, arg in enumerate(sys.argv):
            if arg.isdigit():
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

