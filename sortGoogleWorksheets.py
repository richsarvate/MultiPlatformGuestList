import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import config
import re
from datetime import datetime
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound

def parse_datetime_from_title(title):
    # Remove the day of the week (e.g., "Wednesday")
    parts = title.split(" ", 1)
    if len(parts) < 2:
        return None  # Invalid format
    
    # The date and time part (e.g., "October 9th 8pm")
    datetime_str = parts[1]

    # Remove ordinal suffixes (st, nd, rd, th) from the day part
    datetime_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', datetime_str)

    # Try to parse the string with the date and time
    try:
        # Parse the string with the format "Month Day Time" (e.g., "October 9 8pm")
        parsed_datetime = datetime.strptime(datetime_str, '%B %d %I%p')
        # Add the current year to the parsed datetime
        parsed_datetime = parsed_datetime.replace(year=datetime.now().year)
        return parsed_datetime
    except ValueError:
        return None  # Return None if parsing fails

def parse_date_from_title(title):
    # Split the title to remove the day name
    parts = title.split(" ", 1)
    if len(parts) < 2:
        return None  # Invalid format

    date_str = parts[1]

    # Remove ordinal suffixes (st, nd, rd, th) from the day part
    date_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)


    # Parse the date
    try:
        parsed_date =  datetime.strptime(date_str, '%B %d').date()
        current_year = datetime.now().year
        parsed_date = parsed_date.replace(year=current_year)
        return parsed_date
    except ValueError:
        return None

def arrange_worksheets_in_ascending_order(spreadsheet):
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(config.GOOGLE_CREDS_FILE, scopes=scopes)
    gc = gspread.Client(auth=creds)

    try:

        worksheets = spreadsheet.worksheets()
        # Create a list of tuples (worksheet, date) and sort it by date
        sorted_worksheets = sorted(
            [(ws, parse_datetime_from_title(ws.title) or datetime.min) for ws in worksheets],
            key=lambda x: x[1]
        )
        # Iterate over the sorted worksheets and update their index
        for index, (worksheet, _) in enumerate(sorted_worksheets):
            requests = {
                "requests": [
                    {
                        "updateSheetProperties": {
                            "properties": {
                                "sheetId": worksheet.id,
                                "index": index
                            },
                            "fields": "index"
                        }
                    }
                ]
            }
            spreadsheet.batch_update(requests)

    except (APIError, SpreadsheetNotFound, WorksheetNotFound) as e:
        print(f"An error occurred: {e}")

def sort_worksheets(folder_id):
    # Google Drive and Sheets scopes
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    # Authorize and create a client
    creds = Credentials.from_service_account_file(config.GOOGLE_CREDS_FILE, scopes=scopes)
    gc = gspread.Client(auth=creds)
    drive_service = build('drive', 'v3', credentials=creds)

    # Get current date
    current_date = datetime.now().date()

    # Get all spreadsheets in the specified folder
    response = drive_service.files().list(q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet'",
                                          spaces='drive',
                                          fields='files(id, name)').execute()

    for file in response.get('files', []):
        try:
            # Open the spreadsheet
            spreadsheet = gc.open_by_key(file['id'])

            arrange_worksheets_in_ascending_order(spreadsheet) 

        except (APIError, SpreadsheetNotFound, WorksheetNotFound) as e:
            print(f"An error occurred: {e}")

# Call the function with your folder ID
sort_worksheets(config.GUEST_LIST_FOLDER_ID)

