import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import config
import re
from datetime import datetime
from time import sleep
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound
import logging

# Configure logging to console and file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('script.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def parse_datetime_from_title(title):
    logger.debug(f"Parsing title: {title}")
    parts = title.split(" ", 1)
    if len(parts) < 2:
        logger.warning(f"Invalid title format: {title}")
        return None
    
    datetime_str = parts[1]
    datetime_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', datetime_str)
    
    try:
        # Try parsing with year (e.g., "August 1 9pm 2025")
        parsed_datetime = datetime.strptime(datetime_str, '%B %d %I%p %Y')
        logger.debug(f"Parsed datetime: {parsed_datetime}")
        return parsed_datetime
    except ValueError:
        try:
            # Fallback to no year (assume current year)
            parsed_datetime = datetime.strptime(datetime_str, '%B %d %I%p')
            parsed_datetime = parsed_datetime.replace(year=datetime.now().year)
            logger.debug(f"Parsed datetime (no year): {parsed_datetime}")
            return parsed_datetime
        except ValueError:
            logger.warning(f"Failed to parse datetime from title: {title}")
            return None

def parse_date_from_title(title):
    logger.debug(f"Parsing date from title: {title}")
    parts = title.split(" ", 1)
    if len(parts) < 2:
        logger.warning(f"Invalid title format: {title}")
        return None

    date_str = parts[1]
    date_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)

    try:
        # Try parsing with year (e.g., "August 1 2025")
        parsed_date = datetime.strptime(date_str, '%B %d %Y').date()
        logger.debug(f"Parsed date: {parsed_date}")
        return parsed_date
    except ValueError:
        try:
            # Fallback to no year
            parsed_date = datetime.strptime(date_str, '%B %d').date()
            current_year = datetime.now().year
            parsed_date = parsed_date.replace(year=current_year)
            logger.debug(f"Parsed date (no year): {parsed_date}")
            return parsed_date
        except ValueError:
            logger.warning(f"Failed to parse date from title: {title}")
            return None

def arrange_worksheets_in_ascending_order(spreadsheet):
    logger.info(f"Processing spreadsheet: {spreadsheet.title}")
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(config.GOOGLE_CREDS_FILE, scopes=scopes)
    gc = gspread.Client(auth=creds)
    
    try:
        worksheets = [ws for ws in spreadsheet.worksheets() if not ws.isSheetHidden]
        logger.info(f"Found {len(worksheets)} unhidden worksheets: {[ws.title for ws in worksheets]}")
        
        # Create sorted list of worksheets by date
        sorted_worksheets = sorted(
            [(ws, parse_datetime_from_title(ws.title) or datetime.min) for ws in worksheets],
            key=lambda x: x[1]
        )
        logger.info(f"Sorted worksheets: {[ws.title for ws, _ in sorted_worksheets]}")
        
        # Check if reordering is needed
        current_order = [ws.title for ws in worksheets]
        sorted_order = [ws.title for ws, _ in sorted_worksheets]
        if current_order == sorted_order:
            logger.info("Worksheets already in correct order, skipping update")
            return

        # Prepare batch update
        requests = [
            {
                "updateSheetProperties": {
                    "properties": {"sheetId": ws.id, "index": idx},
                    "fields": "index"
                }
            } for idx, (ws, _) in enumerate(sorted_worksheets)
        ]
        
        if requests:
            logger.info(f"Submitting batch update for {len(requests)} worksheets")
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    spreadsheet.batch_update({"requests": requests})
                    logger.info("Successfully updated worksheet order")
                    break
                except APIError as e:
                    if 'rate limit' in str(e).lower() and attempt < max_retries - 1:
                        logger.warning(f"Rate limit hit, retrying after {2 ** attempt}s")
                        sleep(2 ** attempt)
                    else:
                        logger.error(f"API error: {e}")
                        raise e
        else:
            logger.info("No updates needed for worksheets")
            
    except (APIError, SpreadsheetNotFound, WorksheetNotFound) as e:
        logger.error(f"Error processing spreadsheet {spreadsheet.title}: {e}")

def sort_worksheets(folder_id):
    logger.info(f"Starting sort_worksheets for folder ID: {folder_id}")
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = Credentials.from_service_account_file(config.GOOGLE_CREDS_FILE, scopes=scopes)
    gc = gspread.Client(auth=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    
    try:
        response = drive_service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet'",
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        files = response.get('files', [])
        logger.info(f"Found {len(files)} spreadsheets in folder")
        
        for file in files:
            try:
                logger.info(f"Opening spreadsheet: {file['name']} (ID: {file['id']})")
                spreadsheet = gc.open_by_key(file['id'])
                arrange_worksheets_in_ascending_order(spreadsheet)
                sleep(1)  # Delay to avoid rate limits
            except (APIError, SpreadsheetNotFound, WorksheetNotFound) as e:
                logger.error(f"Error processing file {file['name']}: {e}")
                
    except Exception as e:
        logger.error(f"Error listing files in folder {folder_id}: {e}")

if __name__ == "__main__":
    logger.info("Script started")
    sort_worksheets(config.GUEST_LIST_FOLDER_ID)
    logger.info("Script completed")
