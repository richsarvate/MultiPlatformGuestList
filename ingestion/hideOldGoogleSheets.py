import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config.config as config
import logging
import re
from datetime import datetime
from datetime import timedelta
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound

def parse_datetime_from_title(title):
    # Remove the day of the week (e.g., "Wednesday")
    parts = title.split(" ", 1)
    if len(parts) < 2:
        return None  # Invalid format
    
    # The date and time part (e.g., "October 9th 8pm 2025")
    datetime_str = parts[1]

    # Remove ordinal suffixes (st, nd, rd, th) from the day part
    datetime_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', datetime_str)

    # Try to parse the string with or without a year
    try:
        # First, try parsing with a year (e.g., "October 9 8pm 2025")
        try:
            parsed_datetime = datetime.strptime(datetime_str, '%B %d %I:%M%p %Y')
            return parsed_datetime
        except ValueError:
            try:
                parsed_datetime = datetime.strptime(datetime_str, '%B %d %I%p %Y')
                return parsed_datetime
            except ValueError:
                parsed_datetime = datetime.strptime(datetime_str, '%B %d %I%p')
                parsed_datetime = parsed_datetime.replace(year=datetime.now().year)
                return parsed_datetime

#        try:
#            parsed_datetime = datetime.strptime(datetime_str, '%B %d %I%p %Y')
#            return parsed_datetime
#        except ValueError:
#            # If parsing with year fails, try without (e.g., "October 9 8pm")
#            parsed_datetime = datetime.strptime(datetime_str, '%B %d %I%p')
#            # Add the current year to the parsed datetime
#            parsed_datetime = parsed_datetime.replace(year=datetime.now().year)
#            return parsed_datetime
    except ValueError:
        return None  # Return None if parsing fails

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

