import gspread
from google.oauth2.service_account import Credentials
import config
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound


GUEST_LIST_FOLDER_ID = "1dFTdMM97GwlnMvLpEfegyKUp39D6333i"

def insert_data_into_google_sheet(batch_data):
    
    # Replace with your Google Sheets credentials JSON file path
    credentials_file = "creds.json"  # Make sure the file path is correct

    # Authenticate using the credentials
    creds = Credentials.from_service_account_file(config.GOOGLE_CREDS_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])
    gc = gspread.Client(auth=creds)

    for show in batch_data:
        sheet_title = batch_data[show][0][0]

        print(sheet_title)
        try:
            sheet = gc.open(sheet_title)
        except gspread.exceptions.SpreadsheetNotFound:
            sheet = gc.create(sheet_title, folder_id=GUEST_LIST_FOLDER_ID)

        show_date = batch_data[show][0][1]
        print(show_date)
        try:
            worksheet = sheet.worksheet(show_date)
        except gspread.WorksheetNotFound:
            worksheet = sheet.add_worksheet(show_date, rows=100, cols=20)

        headers = ["venue", "date", "email", "firstname", "lastname", "tickets", "source", "total:"]

        if len(worksheet.get_all_values()) == 0:
            worksheet.append_row(headers, 1)
        else:
            if worksheet.row_values(1) != headers:
                # If the headers don't match, update the headers
                worksheet.update('A1:H1', [headers])

        sum_formula = '=ARRAYFORMULA(SUM(VALUE(F2:F100)))'
        try:
            cell = worksheet.find('total:')
            worksheet.update_cell(cell.row, cell.col + 1, sum_formula)
        except APIError as e:
            print(f"An error occurred: {e}")
            print("Tried to add the sum formula but could not find a cell to add it to")
            pass

        if len(worksheet.get_all_values()) == 0:
            worksheet.append_row(headers, 1)

        # Prepare the data by converting the 'tickets' column values to integers
        data_to_insert = batch_data[show]
        for row in data_to_insert:
            # Convert 'tickets' column to integers (assuming the 'tickets' column is at index 5 based on your headers)
            row[5] = int(row[5]) if row[5] else 0

        # Appending data with integer values for the 'tickets' column
        worksheet.append_rows(data_to_insert, 2)

        # Sort by firstname
        try:
            # Get the entire used range of the sheet
            data_range = worksheet.get_all_values()

            # Find the column index of 'firstname'
            firstname_column = headers.index("firstname") + 1  # Adding 1 as gspread uses 1-based indexing

            # Sort the data (excluding the header row)
            data_range[1:] = sorted(data_range[1:], key=lambda row: row[firstname_column - 1])  # Sort based on firstname

            # Update the entire range with sorted data
            worksheet.update('A2', data_range[1:])
        except Exception as e:
            print(f"An error occurred while sorting: {e}")
            # Handle the error as needed
