import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import config
import re
from datetime import datetime
from datetime import timedelta
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

def hide_old_worksheets(folder_id):
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

    # Calculating the date one day before the current date
    one_day_old = current_date - timedelta(days=1)
    one_day_old_datetime = datetime.combine(one_day_old, datetime.min.time())

    # Get all spreadsheets in the specified folder
    response = drive_service.files().list(q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet'",
                                          spaces='drive',
                                          fields='files(id, name)').execute()

    for file in response.get('files', []):
        try:
            # Open the spreadsheet
            spreadsheet = gc.open_by_key(file['id'])

            # Iterate through each worksheet
            for worksheet in spreadsheet.worksheets():
                try:

                    sheet_properties = worksheet._properties
                    if sheet_properties.get('hidden', False):
                        print(f"Skipping hidden worksheet: {worksheet.title}")
                        continue

                    print(f"worksheet date is {worksheet.title}")
                    # Parse the worksheet name as a date
                    worksheet_date = parse_datetime_from_title(worksheet.title)

                    print(f"worksheet date is {worksheet_date}")
                    # Parse the worksheet name as a date
                    # Check if the worksheet date is older than the current date
                    if worksheet_date and worksheet_date < one_day_old_datetime:    
                        # Hide the worksheet
                        print(f"this worksheet is older than one day")

                        requests = [{
                            "updateSheetProperties": {
                                "properties": {
                                    "sheetId": worksheet.id,
                                    "hidden": True
                                },
                                "fields": "hidden"
                            }
                        }]

                        # Send the request to hide the worksheet
                        spreadsheet.batch_update({"requests": requests})

                except ValueError:
                    # If the worksheet name is not a valid date, ignore it
                    pass

        except (APIError, SpreadsheetNotFound, WorksheetNotFound) as e:
            print(f"An error occurred: {e}")

# Call the function with your folder ID
hide_old_worksheets(config.GUEST_LIST_FOLDER_ID)

