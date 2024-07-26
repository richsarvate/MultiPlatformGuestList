import gspread
from google.oauth2.service_account import Credentials
import config
from googleapiclient.discovery import build
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound
from datetime import datetime 
import re  # Add this line

def insert_data_into_google_sheet(batch_data):
    
    # Replace with your Google Sheets credentials JSON file path
    credentials_file = "creds.json"  # Make sure the file path is correct

    # Authenticate using the credentials
    creds = Credentials.from_service_account_file(config.GOOGLE_CREDS_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])
    gc = gspread.Client(auth=creds)

    # Build the service for Google Sheets API
    service = build('sheets', 'v4', credentials=creds)

    for show in batch_data:
        sheet_title = batch_data[show][0][0]

        print(sheet_title)
        try:
            sheet = gc.open(sheet_title)
        except gspread.exceptions.SpreadsheetNotFound:
            sheet = gc.create(sheet_title, folder_id=config.GUEST_LIST_FOLDER_ID)

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
        sum_formula_2 = '=SUM(ARRAYFORMULA(IF(H2:H100=TRUE, VALUE(F2:F100), 0)))'
        sum_formula_3 = '=J1/I1'
        sum_formula_4 = 'Total Checked In'

		# New formulas for Paid Check-ins and Free List Check-ins
        paid_checkin_formula_1 = '=SUM(ARRAYFORMULA(IF((G2:G99<>"Guest List")*(G2:G99<>"Industry"), VALUE(F2:F99), 0)))'
        paid_checkin_formula_2 = '=SUMPRODUCT((G2:G99<>"Guest List") * (G2:G99<>"Industry") * (H2:H99=TRUE) * VALUE(F2:F99))'
        paid_checkin_percentage_formula = '=J2/I2'
        paid_checkin_label = 'Paid Check In'

        freelist_checkin_formula_1 = '=SUM(ARRAYFORMULA(IF((G2:G99="Guest List")+(G2:G99="Industry"), VALUE(F2:F99), 0)))'
        freelist_checkin_formula_2 = '=SUMPRODUCT(((G2:G99="Guest List") + (G2:G99="Industry")) * (H2:H99=TRUE) * VALUE(F2:F99))'
        freelist_checkin_percentage_formula = '=J3/I3'
        freelist_checkin_label = 'Free List Check In'

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

        # Add checkboxes in column H
        try:
            checkbox_range = f'H2:H{len(data_to_insert) + 1}'

            all_values = worksheet.get_all_values()

            total_rows = len(all_values)  # Including header row

            checkboxvalues = [row[7] for row in all_values[1:]]  # Skip header row

            # Create a request to add checkboxes individually
            requests = []
            for row_index in range(1, total_rows):  # Skip the header row
                bool_value = checkboxvalues[row_index - 1] == 'TRUE'  # Determine the boolean value based on the array
                requests.append({
                    "updateCells": {
                        "range": {
                            "sheetId": worksheet.id,
                            "startRowIndex": row_index,
                            "endRowIndex": row_index + 1,
                            "startColumnIndex": 7,
                            "endColumnIndex": 8,
                        },
                        "rows": [{
                            "values": [{
                                "userEnteredValue": {
                                    "boolValue": bool_value
                                },
                                "dataValidation": {
                                    "condition": {
                                        "type": "BOOLEAN"
                                    },
                                    "showCustomUi": True
                                }
                            }]
                        }],
                        "fields": "userEnteredValue,dataValidation"
                    }
                })

            # Execute the request to add checkboxes
            try:
                body = {
                    "requests": requests
                }
                service.spreadsheets().batchUpdate(spreadsheetId=sheet.id, body=body).execute()
                print("Checkboxes added successfully.")
            except Exception as e:
                print(f"An error occurred while adding checkboxes: {e}")
        except Exception as e:
            print(f"An error occurred while adding checkboxes: {e}")

        #add formulas to calculate how many free and paid customers have checked in
        try:
            cell = worksheet.find('total:')
            worksheet.update_cell(cell.row, cell.col + 1, "" + sum_formula)
            worksheet.update_cell(cell.row, cell.col + 2, "" + sum_formula_2)
            worksheet.update_cell(cell.row, cell.col + 3, "" + sum_formula_3)
            worksheet.update_cell(cell.row, cell.col + 4, "" + sum_formula_4)

            guest_list_values = worksheet.col_values(cell.col -1)[1:]  # Skip header
            if any(value == "Guest List" for value in guest_list_values):

                # Update cells with the new formulas for Paid Check-ins
                worksheet.update_cell(cell.row + 1, cell.col + 1, paid_checkin_formula_1)
                worksheet.update_cell(cell.row + 1, cell.col + 2, paid_checkin_formula_2)
                worksheet.update_cell(cell.row + 1, cell.col + 3, paid_checkin_percentage_formula)
                worksheet.update_cell(cell.row + 1, cell.col + 4, paid_checkin_label)

                # Update cells with the new formulas for Free List Check-ins
                worksheet.update_cell(cell.row + 2, cell.col + 1, freelist_checkin_formula_1)
                worksheet.update_cell(cell.row + 2, cell.col + 2, freelist_checkin_formula_2)
                worksheet.update_cell(cell.row + 2, cell.col + 3, freelist_checkin_percentage_formula)
                worksheet.update_cell(cell.row + 2, cell.col + 4, freelist_checkin_label)

        except Exception as e:
            print(f"An error occurred: {e}")

        # Remove any old formulas that may be remaining because of the sorting.
        # Define the range to clear (columns I, J, K, L from row 4 downwards)
        range_to_clear = 'I4:L'

        # Clear the content in the specified range
        worksheet.batch_clear([range_to_clear])

        #Change column K to percentage so that it can display the percent of people who've checked in
        # Define the range for column K (11th column)
        column_k_range = 'K:K'
        
        # Set the format for the column to percentage
        worksheet.format(column_k_range, {
            "numberFormat": {
                "type": "PERCENT",
                "pattern": "0.00%"  # Two decimal places
            }
        })

        #resize all the columns to be the length of the max value in that column
        num_columns = 12

        # Prepare the requests to auto resize each column
        requests = []
        for col in range(num_columns):
            requests.append({
                'autoResizeDimensions': {
                    'dimensions': {
                        'sheetId': worksheet.id,  # You'll need to get the sheet ID
                        'dimension': 'COLUMNS',
                        'startIndex': col,
                        'endIndex': col + 1
                    }
                }
            })

        # Send the batch update request
        body = {
            'requests': requests
        }
        service.spreadsheets().batchUpdate(spreadsheetId=sheet.id, body=body).execute()
