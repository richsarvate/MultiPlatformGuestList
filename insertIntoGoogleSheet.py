import gspread
from google.oauth2.service_account import Credentials
import config
from googleapiclient.discovery import build
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound
from datetime import datetime 
import re  # Add this line
from addEmailToMailerLite import batch_add_contacts_to_mailerlite

#batch_data example:
#batch_data = {
#    "Townhouse": [
#        ["Townhouse", "2025-01-15", "janedoe@example.com", "Guest List", "7:00 PM", "GA", "Jane", "Doe", 2],
#        ["Townhouse", "2025-01-15", "johndoe@example.com", "Eventbrite", "8:00 PM", "GA", "John", "Doe", 3]
#    ],
#    "Speakeasy": [
#        ["Speakeasy", "2025-01-16", "alice@example.com", "Squarespace", "7:30 PM", "GA", "Alice", "Smith", 1],
#        ["Speakeasy", "2025-01-16", "bob@example.com", "Squarespace", "9:00 PM", "VIP", "Bob", "Johnson", 4]
#    ]
#}

def insert_data_into_google_sheet(batch_data):

    batch_add_contacts_to_mailerlite(emailsToAdd=batch_data)
    
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

        headers = ["venue", "date", "email", "source", "time", "type", "firstname", "lastname", "tickets", "total:"]

        if len(worksheet.get_all_values()) == 0:
            worksheet.append_row(headers, 1)
        else:
            if worksheet.row_values(1) != headers:
                # If the headers don't match, update the headers
                worksheet.update('A1:J1', [headers])

        # Define variables for each column
        ticket_sales_column = chr(65 + headers.index("tickets")) # Column for ticket sales
        category_column = chr(65 + headers.index("source"))  # Column for categories like 'Eventbrite' or 'Guest List' or 'Industry'
        checkbox_column = 'J'  # Column for the checkbox
        total_tickets_column = 'K'  # Column for total number of tickets
        checked_in_column = 'L'  # Column for people checked in
        percentage_checked_in_column = 'M'

        # Create formulas using the defined variables
        sum_formula = f'=ARRAYFORMULA(SUM(VALUE({ticket_sales_column}2:{ticket_sales_column}100)))'
        sum_formula_2 = f'=SUM(ARRAYFORMULA(IF({checkbox_column}2:{checkbox_column}100=TRUE, VALUE({ticket_sales_column}2:{ticket_sales_column}100), 0)))'
        sum_formula_3 = f'={checked_in_column}1/{total_tickets_column}1'
        sum_formula_4 = 'Total Checked In'

        # New formulas for Paid Check-ins and Free List Check-ins using variables
        paid_checkin_formula_1 = f'=SUM(ARRAYFORMULA(IF(({category_column}2:{category_column}99<>"Guest List")*({category_column}2:{category_column}99<>"Industry"), VALUE({ticket_sales_column}2:{ticket_sales_column}99), 0)))'
        paid_checkin_formula_2 = f'=SUMPRODUCT(({category_column}2:{category_column}99<>"Guest List") * ({category_column}2:{category_column}99<>"Industry") * ({checkbox_column}2:{checkbox_column}99=TRUE) * VALUE({ticket_sales_column}2:{ticket_sales_column}99))'
        paid_checkin_percentage_formula = f'={checked_in_column}2/{total_tickets_column}2'
        paid_checkin_label = 'Paid Check In'

        freelist_checkin_formula_1 = f'=SUM(ARRAYFORMULA(IF(({category_column}2:{category_column}99="Guest List")+({category_column}2:{category_column}99="Industry"), VALUE({ticket_sales_column}2:{ticket_sales_column}99), 0)))'
        freelist_checkin_formula_2 = f'=SUMPRODUCT((({category_column}2:{category_column}99="Guest List") + ({category_column}2:{category_column}99="Industry")) * ({checkbox_column}2:{checkbox_column}99=TRUE) * VALUE({ticket_sales_column}2:{ticket_sales_column}99))'
        freelist_checkin_percentage_formula = f'={checked_in_column}3/{total_tickets_column}3'
        freelist_checkin_label = 'Free List Check In'

        if len(worksheet.get_all_values()) == 0:
            worksheet.append_row(headers, 1)

        # Prepare the data by converting the 'tickets' column values to integers
        ticket_sales_column_number = ord(ticket_sales_column) - ord('A')
        data_to_insert = batch_data[show]
        for row in data_to_insert:
            # Convert 'tickets' column to integers (assuming the 'tickets' column is at index 5 based on your headers)
            row[ticket_sales_column_number] = int(row[ticket_sales_column_number]) if row[ticket_sales_column_number] else 0

        # Appending data with integer values for the 'tickets' column
        worksheet.append_rows(data_to_insert, 2)

        # Sort by firstname
        try:
            # Get the entire used range of the sheet
            data_range = worksheet.get_all_values()

            # Find the column index of 'firstname'
            firstname_column = headers.index("firstname") + 1  # Adding 1 as gspread uses 1-based indexing

            # Function to capitalize the first letter and lowercase the rest
            def capitalize_name(name):
                return name.capitalize() if name else name

            # Capitalize first names and sort the data (excluding the header row)
            for row in data_range[1:]:
                row[firstname_column - 1] = capitalize_name(row[firstname_column - 1])  # Capitalize first name

            # Sort the data (excluding the header row)
            data_range[1:] = sorted(data_range[1:], key=lambda row: row[firstname_column - 1])  # Sort based on firstname

            # Update the entire range with sorted data
            worksheet.update('A2', data_range[1:])
        except Exception as e:
            print(f"An error occurred while sorting: {e}")
            # Handle the error as needed

        # Add checkboxes
        try:
            all_values = worksheet.get_all_values()

            total_rows = len(all_values)  # Including header row

            checkbox_column_number = ord(checkbox_column) - ord('A')

            print(f"checkbox column is : {checkbox_column_number}")

            checkboxvalues = [row[checkbox_column_number] for row in all_values[1:]]  # Skip header row

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
                            "startColumnIndex": checkbox_column_number,
                            "endColumnIndex": checkbox_column_number+1,
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
            print(f"location of total is {cell.row} and {cell.col}")
            worksheet.update_cell(cell.row, cell.col + 1, "" + sum_formula)
            worksheet.update_cell(cell.row, cell.col + 2, "" + sum_formula_2)
            worksheet.update_cell(cell.row, cell.col + 3, "" + sum_formula_3)
            worksheet.update_cell(cell.row, cell.col + 4, "" + sum_formula_4)

            category_column_number = ord(category_column) - ord('A') + 1

            guest_list_values = worksheet.col_values(category_column_number)[1:]  # Skip header
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
        end_column = chr(ord(total_tickets_column) + 3) 
        range_to_clear = f'{total_tickets_column}4:{end_column}'
        worksheet.batch_clear([range_to_clear])

        # Set the format for the percentage checked in column to percentage
        worksheet.format(f'{percentage_checked_in_column}:{percentage_checked_in_column}', {
            "numberFormat": {
                "type": "PERCENT",
                "pattern": "0.00%"  # Two decimal places
            }
        })

        # Prepare the requests to auto resize each column
        requests = []
        for col in range(worksheet.col_count):
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
