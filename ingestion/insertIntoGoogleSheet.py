import gspread
from google.oauth2.service_account import Credentials
import sys
import os
from shared_config import load_project_config, get_google_service_account_path
from googleapiclient.discovery import build
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound
from datetime import datetime 
import re  # Add this line
import logging
import hashlib
from addContactsToMongoDB import batch_add_contacts_to_mongodb
from getVenueAndDate import get_city, append_year_to_show_date

# Setup logging
logger = logging.getLogger(__name__)

def _generate_row_hash(first_name, last_name, email, source, show_name):
    """Generate hash from key fields, skipping empty ones"""
    fields = [f for f in [first_name, last_name, email, source, show_name] if f]
    return hashlib.md5(''.join(str(f).lower().strip() for f in fields).encode()).hexdigest()[:12]

def _setup_google_sheets_client():
    """Initialize Google Sheets client and service"""
    logger.info("Setting up Google Sheets client")
    
    google_creds_file = get_google_service_account_path()
    if not google_creds_file or not os.path.exists(google_creds_file):
        raise FileNotFoundError(f"Google service account file not found: {google_creds_file}")
        
    creds = Credentials.from_service_account_file(
        google_creds_file, 
        scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    )
    gc = gspread.Client(auth=creds)
    service = build('sheets', 'v4', credentials=creds)
    logger.info("Google Sheets client initialized successfully")
    return gc, service

def _get_or_create_sheet(gc, venue):
    """Get existing sheet or create new one for venue"""
    sheet_title = get_city(venue) + "-" + venue
    logger.info(f"Processing sheet: {sheet_title}")
    
    try:
        sheet = gc.open(sheet_title)
        logger.info(f"Found existing sheet: {sheet_title}")
    except gspread.exceptions.SpreadsheetNotFound:
        logger.info(f"Creating new sheet: {sheet_title}")
        sheet = gc.create(sheet_title, folder_id=config.GUEST_LIST_FOLDER_ID)
        logger.info(f"Successfully created sheet: {sheet_title}")
    
    return sheet

def _get_or_create_worksheet(sheet, show_date):
    """Get existing worksheet or create new one for show date"""
    show_date_plus_year = append_year_to_show_date(show_date)
    logger.info(f"Processing worksheet for date: {show_date_plus_year}")
    
    try:
        worksheet = sheet.worksheet(show_date_plus_year)
        logger.info(f"Found existing worksheet: {show_date_plus_year}")
    except gspread.WorksheetNotFound:
        logger.info(f"Creating new worksheet: {show_date_plus_year}")
        worksheet = sheet.add_worksheet(show_date_plus_year, rows=100, cols=20)
        logger.info(f"Successfully created worksheet: {show_date_plus_year}")
    
    return worksheet

def _setup_worksheet_headers(worksheet):
    """Setup headers for the worksheet"""
    headers = ["venue", "date", "email", "source", "time", "type", "firstname", "lastname", "tickets", "total:"]
    
    if len(worksheet.get_all_values()) == 0:
        worksheet.append_row(headers, 1)
    else:
        if worksheet.row_values(1) != headers:
            worksheet.update('A1:J1', [headers])
    
    return headers

def _get_column_definitions(headers):
    """Define column variables for formulas"""
    return {
        'ticket_sales_column': chr(65 + headers.index("tickets")),
        'category_column': chr(65 + headers.index("source")),
        'checkbox_column': 'J',
        'total_tickets_column': 'K',
        'checked_in_column': 'L',
        'percentage_checked_in_column': 'M'
    }

def _create_formulas(columns):
    """Create all formula strings"""
    formulas = {}
    
    # Main formulas
    formulas['sum_formula'] = f'=ARRAYFORMULA(SUM(VALUE({columns["ticket_sales_column"]}2:{columns["ticket_sales_column"]}100)))'
    formulas['sum_formula_2'] = f'=SUM(ARRAYFORMULA(IF({columns["checkbox_column"]}2:{columns["checkbox_column"]}100=TRUE, VALUE({columns["ticket_sales_column"]}2:{columns["ticket_sales_column"]}100), 0)))'
    formulas['sum_formula_3'] = f'={columns["checked_in_column"]}1/{columns["total_tickets_column"]}1'
    formulas['sum_formula_4'] = 'Total Checked In'
    
    # Paid check-in formulas
    formulas['paid_checkin_formula_1'] = f'=SUM(ARRAYFORMULA(IF(({columns["category_column"]}2:{columns["category_column"]}99<>"Guest List")*({columns["category_column"]}2:{columns["category_column"]}99<>"Industry"), VALUE({columns["ticket_sales_column"]}2:{columns["ticket_sales_column"]}99), 0)))'
    formulas['paid_checkin_formula_2'] = f'=SUMPRODUCT(({columns["category_column"]}2:{columns["category_column"]}99<>"Guest List") * ({columns["category_column"]}2:{columns["category_column"]}99<>"Industry") * ({columns["checkbox_column"]}2:{columns["checkbox_column"]}99=TRUE) * VALUE({columns["ticket_sales_column"]}2:{columns["ticket_sales_column"]}99))'
    formulas['paid_checkin_percentage_formula'] = f'={columns["checked_in_column"]}2/{columns["total_tickets_column"]}2'
    formulas['paid_checkin_label'] = 'Paid Check In'
    
    # Free list check-in formulas
    formulas['freelist_checkin_formula_1'] = f'=SUM(ARRAYFORMULA(IF(({columns["category_column"]}2:{columns["category_column"]}99="Guest List")+({columns["category_column"]}2:{columns["category_column"]}99="Industry"), VALUE({columns["ticket_sales_column"]}2:{columns["ticket_sales_column"]}99), 0)))'
    formulas['freelist_checkin_formula_2'] = f'=SUMPRODUCT((({columns["category_column"]}2:{columns["category_column"]}99="Guest List") + ({columns["category_column"]}2:{columns["category_column"]}99="Industry")) * ({columns["checkbox_column"]}2:{columns["checkbox_column"]}99=TRUE) * VALUE({columns["ticket_sales_column"]}2:{columns["ticket_sales_column"]}99))'
    formulas['freelist_checkin_percentage_formula'] = f'={columns["checked_in_column"]}3/{columns["total_tickets_column"]}3'
    formulas['freelist_checkin_label'] = 'Free List Check In'
    
    return formulas

def _prepare_and_insert_data(worksheet, batch_data_for_show, headers):
    """Prepare data and insert into worksheet"""
    logger.info(f"Preparing to insert {len(batch_data_for_show)} rows")
    
    if len(worksheet.get_all_values()) == 0:
        worksheet.append_row(headers, 1)
        logger.info("Added headers to new worksheet")
    
    # Convert tickets column to integers
    ticket_sales_column_number = ord(headers.index("tickets") + 65) - ord('A')
    data_to_insert = batch_data_for_show
    
    for row in data_to_insert:
        row[ticket_sales_column_number] = int(row[ticket_sales_column_number]) if row[ticket_sales_column_number] else 0
    
    worksheet.append_rows(data_to_insert, 2)
    logger.info(f"Successfully inserted {len(data_to_insert)} rows")

def _sort_data_by_firstname(worksheet, headers):
    """Sort worksheet data by first name"""
    try:
        logger.info("Sorting data by first name")
        data_range = worksheet.get_all_values()
        firstname_column = headers.index("firstname") + 1
        
        def capitalize_name(name):
            return name.capitalize() if name else name
        
        # Capitalize first names and sort
        for row in data_range[1:]:
            row[firstname_column - 1] = capitalize_name(row[firstname_column - 1])
        
        data_range[1:] = sorted(data_range[1:], key=lambda row: row[firstname_column - 1])
        worksheet.update('A2', data_range[1:])
        logger.info(f"Successfully sorted {len(data_range) - 1} rows by first name")
        
    except Exception as e:
        logger.error(f"Error occurred while sorting: {e}")

def _add_checkboxes(worksheet, service, sheet, columns):
    """Add checkboxes to the worksheet"""
    try:
        logger.info("Adding checkboxes to worksheet")
        all_values = worksheet.get_all_values()
        total_rows = len(all_values)
        checkbox_column_number = ord(columns['checkbox_column']) - ord('A')
        
        logger.debug(f"Checkbox column: {checkbox_column_number}, Total rows: {total_rows}")
        
        checkboxvalues = [row[checkbox_column_number] for row in all_values[1:]]
        
        requests = []
        for row_index in range(1, total_rows):
            bool_value = checkboxvalues[row_index - 1] == 'TRUE'
            requests.append({
                "updateCells": {
                    "range": {
                        "sheetId": worksheet.id,
                        "startRowIndex": row_index,
                        "endRowIndex": row_index + 1,
                        "startColumnIndex": checkbox_column_number,
                        "endColumnIndex": checkbox_column_number + 1,
                    },
                    "rows": [{
                        "values": [{
                            "userEnteredValue": {"boolValue": bool_value},
                            "dataValidation": {
                                "condition": {"type": "BOOLEAN"},
                                "showCustomUi": True
                            }
                        }]
                    }],
                    "fields": "userEnteredValue,dataValidation"
                }
            })
        
        if requests:
            body = {"requests": requests}
            service.spreadsheets().batchUpdate(spreadsheetId=sheet.id, body=body).execute()
            logger.info(f"Successfully added {len(requests)} checkboxes")
            
    except Exception as e:
        logger.error(f"Error occurred while adding checkboxes: {e}")

def _add_formulas(worksheet, formulas, columns):
    """Add calculation formulas to the worksheet"""
    try:
        logger.info("Adding calculation formulas")
        cell = worksheet.find('total:')
        logger.debug(f"Total cell location: row {cell.row}, col {cell.col}")
        
        # Add main formulas
        worksheet.update_cell(cell.row, cell.col + 1, formulas['sum_formula'])
        worksheet.update_cell(cell.row, cell.col + 2, formulas['sum_formula_2'])
        worksheet.update_cell(cell.row, cell.col + 3, formulas['sum_formula_3'])
        worksheet.update_cell(cell.row, cell.col + 4, formulas['sum_formula_4'])
        
        # Check if we have guest list data
        category_column_number = ord(columns['category_column']) - ord('A') + 1
        guest_list_values = worksheet.col_values(category_column_number)[1:]
        
        if any(value == "Guest List" for value in guest_list_values):
            logger.info("Guest List data detected - adding paid/free check-in formulas")
            # Add paid check-in formulas
            worksheet.update_cell(cell.row + 1, cell.col + 1, formulas['paid_checkin_formula_1'])
            worksheet.update_cell(cell.row + 1, cell.col + 2, formulas['paid_checkin_formula_2'])
            worksheet.update_cell(cell.row + 1, cell.col + 3, formulas['paid_checkin_percentage_formula'])
            worksheet.update_cell(cell.row + 1, cell.col + 4, formulas['paid_checkin_label'])
            
            # Add free list check-in formulas
            worksheet.update_cell(cell.row + 2, cell.col + 1, formulas['freelist_checkin_formula_1'])
            worksheet.update_cell(cell.row + 2, cell.col + 2, formulas['freelist_checkin_formula_2'])
            worksheet.update_cell(cell.row + 2, cell.col + 3, formulas['freelist_checkin_percentage_formula'])
            worksheet.update_cell(cell.row + 2, cell.col + 4, formulas['freelist_checkin_label'])
        else:
            logger.info("No Guest List data - skipping paid/free formulas")
            
        logger.info("Successfully added all formulas")
            
    except Exception as e:
        logger.error(f"Error occurred while adding formulas: {e}")

def _cleanup_and_format(worksheet, service, sheet, columns):
    """Clean up old formulas and format columns"""
    try:
        # Remove old formulas
        end_column = chr(ord(columns['total_tickets_column']) + 3)
        range_to_clear = f'{columns["total_tickets_column"]}4:{end_column}'
        worksheet.batch_clear([range_to_clear])
        
        # Set percentage format
        worksheet.format(f'{columns["percentage_checked_in_column"]}:{columns["percentage_checked_in_column"]}', {
            "numberFormat": {
                "type": "PERCENT",
                "pattern": "0.00%"
            }
        })
        
        # Auto resize columns
        requests = []
        for col in range(worksheet.col_count):
            requests.append({
                'autoResizeDimensions': {
                    'dimensions': {
                        'sheetId': worksheet.id,
                        'dimension': 'COLUMNS',
                        'startIndex': col,
                        'endIndex': col + 1
                    }
                }
            })
        
        body = {'requests': requests}
        service.spreadsheets().batchUpdate(spreadsheetId=sheet.id, body=body).execute()
        
    except Exception as e:
        print(f"An error occurred during cleanup and formatting: {e}")

def insert_data_into_google_sheet(batch_data):
    """
    Legacy function that converts old batch_data format to new intuitive format
    and calls insert_guest_data_efficient.
    
    batch_data format: {
        "Show Name": [
            ["venue", "date", "email", "source", "time", "type", "firstname", "lastname", tickets],
            ...
        ]
    }
    """
    logger.info(f"Converting legacy batch_data format for {len(batch_data)} shows")
    
    # Convert legacy format to new intuitive format
    guest_data = []
    
    for show_name, guest_rows in batch_data.items():
        logger.debug(f"Converting {len(guest_rows)} guests from show: {show_name}")
        
        for row in guest_rows:
            # Convert array format to dictionary format
            # Expected array: [venue, date, email, source, time, type, firstname, lastname, tickets]
            if len(row) >= 9:
                guest_dict = {
                    "venue": row[0],
                    "show_date": row[1],
                    "email": row[2],
                    "source": row[3],
                    "first_name": row[6],
                    "last_name": row[7],
                    "tickets": int(row[8]) if row[8] else 1,
                    "ticket_type": row[5] if len(row) > 5 else "GA"
                }
                guest_data.append(guest_dict)
            else:
                logger.warning(f"Skipping malformed row with {len(row)} elements: {row}")
    
    logger.info(f"Converted {len(guest_data)} guests to new format")
    
    # Call the efficient function with converted data
    insert_guest_data_efficient(guest_data)

# ============================================================================
# NEW IMPROVED VERSION WITH INTUITIVE DATA STRUCTURE AND EFFICIENT OPERATIONS
# ============================================================================

def insert_guest_data_efficient(guest_data):
    """
    New improved function with intuitive data structure and efficient operations.
    
    :param guest_data: List of guest dictionaries with the following structure:
    [
        {
            "venue": "Palace",
            "show_date": "2025-08-15 8:30 PM", 
            "email": "john@example.com",
            "source": "Bucketlist",
            "first_name": "John",
            "last_name": "Doe", 
            "tickets": 2,
            "ticket_type": "GA",
            "phone": "+1234567890",
            # Optional enhanced fields
            "discount_code": "EARLY20",
            "total_price": 25.00,
            "order_id": "BL123456",
            "notes": "VIP guest"
        },
        # ... more guests
    ]
    """
    if not guest_data:
        logger.warning("No guest data provided")
        return
    
    logger.info(f"Starting efficient guest data insertion for {len(guest_data)} guests")
    
    # Convert to comprehensive format and save to MongoDB
    _save_comprehensive_data_to_mongodb(guest_data)
    
    # Group guests by venue and show date for efficient processing
    grouped_data = _group_guests_by_venue_and_date(guest_data)
    logger.info(f"Grouped data into {len(grouped_data)} venue/date combinations")
    
    # Setup Google Sheets client once
    gc, service = _setup_google_sheets_client()
    
    # Process each venue/date combination efficiently
    for venue_date_key, guests in grouped_data.items():
        venue, show_date = venue_date_key
        _process_venue_show_efficient(gc, service, venue, show_date, guests)
    
    logger.info("Efficient guest data insertion completed successfully")

def _save_comprehensive_data_to_mongodb(guest_data):
    """Save comprehensive guest data to MongoDB"""
    logger.info(f"=== DEBUG: Starting MongoDB save for {len(guest_data)} guests ===")
    
    try:
        # Convert intuitive format to the array format expected by batch_add_contacts_to_mongodb
        batch_data = {}
        
        for guest in guest_data:
            venue = guest.get('venue', '')
            show_date = guest.get('show_date', '')
            
            # Create a show key (venue + date for grouping)
            show_key = f"{venue} - {show_date}"
            
            if show_key not in batch_data:
                batch_data[show_key] = []
            
            # Convert to array format that MongoDB function expects
            # Array structure: [venue, date, email, source, time, type, firstname, lastname, tickets, phone, ...]
            guest_array = [
                venue,
                show_date,
                guest.get('email', ''),
                guest.get('source', ''),
                _extract_time_from_date(show_date),
                guest.get('ticket_type', 'GA'),
                guest.get('first_name', ''),
                guest.get('last_name', ''),
                guest.get('tickets', 1),
                guest.get('phone', ''),
                # Enhanced fields as additional array elements
                guest.get('discount_code'),
                guest.get('total_price'),
                guest.get('order_id'),
                guest.get('transaction_id'),
                guest.get('customer_id'),
                guest.get('payment_method'),
                guest.get('entry_code'),
                guest.get('notes')
            ]
            
            batch_data[show_key].append(guest_array)
        
        logger.info(f"Converted to {len(batch_data)} show groupings")
        
        # Use existing MongoDB function with array format
        logger.info("=== DEBUG: About to call batch_add_contacts_to_mongodb ===")
        logger.info(f"=== DEBUG: batch_data keys: {list(batch_data.keys())} ===")
        
        batch_add_contacts_to_mongodb(batch_data)
        logger.info("=== DEBUG: batch_add_contacts_to_mongodb completed successfully ===")
        
    except Exception as e:
        logger.error(f"=== DEBUG: MongoDB save operation FAILED: {e} ===")
        logger.error(f"=== DEBUG: Exception type: {type(e).__name__} ===")
        import traceback
        logger.error(f"=== DEBUG: Full traceback: {traceback.format_exc()} ===")
        raise

def _extract_time_from_date(show_date):
    """Extract time portion from show date string"""
    import re
    # Try to extract time patterns:
    # - "8:30 PM" or "8:30 AM" (with colon and minutes)
    # - "8pm" or "8am" (without colon)
    # - "20:30" (24-hour format)
    time_patterns = [
        r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))',  # 8:30 PM format
        r'(\d{1,2}(?:AM|PM|am|pm))',           # 8pm format
        r'(\d{2}:\d{2})'                       # 20:30 format
    ]
    
    for pattern in time_patterns:
        time_match = re.search(pattern, show_date)
        if time_match:
            return time_match.group(1)
    
    return ''

def _group_guests_by_venue_and_date(guest_data):
    """Group guests by venue and show date for efficient processing"""
    grouped = {}
    
    for guest in guest_data:
        venue = guest.get('venue', '')
        show_date = guest.get('show_date', '')
        
        # Clean up the show date to extract just the date part for grouping
        date_part = _extract_date_part(show_date)
        key = (venue, date_part)
        
        if key not in grouped:
            grouped[key] = []
        
        grouped[key].append(guest)
    
    return grouped

def _extract_date_part(show_date):
    """Extract date part from show date string"""
    import re
    # Try to extract date pattern like "2025-08-15" or "August 15, 2025"
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', show_date)
    if date_match:
        return date_match.group(1)
    
    # If no standard format found, return the original
    return show_date

def _process_venue_show_efficient(gc, service, venue, show_date, guests):
    """Process a single venue/show combination efficiently"""
    try:
        # Get or create sheet and worksheet
        sheet = _get_or_create_sheet(gc, venue)
        worksheet = _get_or_create_worksheet(sheet, show_date)
        
        # Setup headers and definitions
        headers = _setup_worksheet_headers(worksheet)
        columns = _get_column_definitions(headers)
        formulas = _create_formulas(columns)
        
        # Convert guests to row format for Google Sheets
        guest_rows = _convert_guests_to_rows(guests)
        
        # Batch insert all data at once (more efficient)
        _batch_insert_guest_data(worksheet, guest_rows, headers)
        
        # Sort and format data
        _sort_data_by_firstname(worksheet, headers)
        
        # Add interactive elements and formulas
        _add_checkboxes(worksheet, service, sheet, columns)
        _add_formulas(worksheet, formulas, columns)
        
        # Final cleanup and formatting
        _cleanup_and_format(worksheet, service, sheet, columns)
        
        print(f"Successfully processed {len(guests)} guests for {venue} on {show_date}")
        
    except Exception as e:
        print(f"Error processing {venue} on {show_date}: {e}")

def _convert_guests_to_rows(guests):
    """Convert guest dictionaries to row arrays for Google Sheets"""
    rows = []
    
    for guest in guests:
        # Convert to the expected array format for Google Sheets
        # [venue, date, email, source, time, type, firstname, lastname, tickets]
        row = [
            guest.get('venue', ''),
            guest.get('show_date', ''),
            guest.get('email', ''),
            guest.get('source', ''),
            _extract_time_from_date(guest.get('show_date', '')),
            guest.get('ticket_type', 'GA'),
            guest.get('first_name', ''),
            guest.get('last_name', ''),
            int(guest.get('tickets', 1))
        ]
        rows.append(row)
    
    return rows

def _batch_insert_guest_data(worksheet, guest_rows, headers):
    """Efficiently insert guest data in batch with deduplication"""
    if not guest_rows:
        return
    
    # Ensure headers exist
    all_values = worksheet.get_all_values()
    if len(all_values) == 0:
        worksheet.append_row(headers, 1)
        existing_rows = []
    else:
        existing_rows = all_values[1:]  # Skip header
    
    # Create hash set from existing rows
    existing_hashes = set()
    for row in existing_rows:
        if len(row) >= 7:  # Ensure row has enough columns
            show_name = f"{row[0]} - {row[1]}" if len(row) > 1 else ""
            row_hash = _generate_row_hash(row[6] if len(row) > 6 else "", row[7] if len(row) > 7 else "", row[2] if len(row) > 2 else "", row[3] if len(row) > 3 else "", show_name)
            existing_hashes.add(row_hash)
    
    # Filter out duplicates
    unique_rows = []
    for row in guest_rows:
        if len(row) >= 7:
            show_name = f"{row[0]} - {row[1]}" if len(row) > 1 else ""
            row_hash = _generate_row_hash(row[6] if len(row) > 6 else "", row[7] if len(row) > 7 else "", row[2] if len(row) > 2 else "", row[3] if len(row) > 3 else "", show_name)
            if row_hash not in existing_hashes:
                unique_rows.append(row)
                existing_hashes.add(row_hash)
    
    # Insert only unique rows
    if unique_rows:
        worksheet.append_rows(unique_rows)
        print(f"Inserted {len(unique_rows)} unique guests (skipped {len(guest_rows) - len(unique_rows)} duplicates)")
    else:
        print("No new guests to insert (all were duplicates)")
