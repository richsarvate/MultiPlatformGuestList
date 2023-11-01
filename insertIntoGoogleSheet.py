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

        sum_formula = '=SUM(F2:F100)'
        try:
            cell = worksheet.find('total:')
            worksheet.update_cell(cell.row, cell.col + 1, sum_formula)
        except APIError as e:
            print(f"An error occurred: {e}")
            print("Tried to add the sum formula but could not find a cell to add it to")
            pass

        if len(worksheet.get_all_values()) == 0:
            worksheet.append_row(headers, 1)

        worksheet.append_rows(batch_data[show], 2)
