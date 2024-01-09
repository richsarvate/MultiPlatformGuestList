from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os.path
import base64
import email
import time
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import base64
import csv
from getVenueAndDate import get_venue,extract_venue_name, extract_date,convert_date_format
from insertIntoGoogleSheet import insert_data_into_google_sheet
import config
from email import message_from_bytes
import re
from base64 import urlsafe_b64decode
from googleapiclient.errors import HttpError
from getVenueAndDate import get_venue,extract_venue_name, extract_date,convert_date_from_any_format

# Define the SCOPES. If modifying it, delete the token.pickle file.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_email_html(service, user_id, msg_id):
    try:
        # Fetch the email message by id
        message = service.users().messages().get(userId=user_id, id=msg_id).execute()

        # Get the payload and then get the HTML part of the email
        payload = message['payload']

        # Check if the email is multipart
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/html':
                    data = part['body']['data']
                    break
        else:
            # If not multipart, directly get the HTML content
            data = payload['body']['data']

        # Decode the base64 encoded string
        html_content = urlsafe_b64decode(data).decode('utf-8')
        return html_content
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def get_email_body(service, user_id, msg_id):
    html_content = get_email_html(service, user_id, msg_id)

    # Parse the HTML content
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find and extract customer name
    name_img_tag = soup.find('img', alt="Name")
    if name_img_tag:
        full_name = name_img_tag.find_parent('td').find_next_sibling('td').get_text(strip=True)
        name_parts = full_name.split()  # Splits the name into a list of words
        if len(name_parts) >= 2:  # Check if there are at least two parts
            first_name = name_parts[0]
            last_name = ' '.join(name_parts[1:])  # Handles cases where the last name might be multi-part
        else:  # Handle cases where there might only be one part to the name
            first_name = full_name
            last_name = ""
    else:
        first_name, last_name = "Name", "Not found"

    # Find the <img> tag with alt="Tickets" and get the ticket number from the next <p> tag
    tickets_img_tag = soup.find('img', alt="Tickets")
    if tickets_img_tag:
        tickets_text = tickets_img_tag.find_parent('td').find_next_sibling('td').get_text(strip=True)
        match = re.search(r'\d+', tickets_text)  # Search for any sequence of digits in the text
        if match:
            ticket_number = match.group()  # This will be the first (and in this case, only) sequence of digits found
        else:
            ticket_number = "0"  # Default to 0 if no number is found
    else:
        ticket_number = "Number of tickets not found"

    # Find the <img> tag with alt="Date" and get the date of the show from the next <p> tag
    date_img_tag = soup.find('img', alt="Date")
    if date_img_tag:
        show_date = date_img_tag.find_parent('td').find_next_sibling('td').get_text(strip=True)
    else:
        show_date = "Date not found"

    return first_name, last_name, ticket_number, show_date

def getEmails():
    creds = None

    print("attempting to get fever sales from gmail")

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
    result = service.users().messages().list(userId='me').execute()
    messages = result.get('messages')

    # Get the current time in epoch format
    current_time_epoch = int(time.time())

    # Calculate the time 1 hours ago in epoch format
    last_run = current_time_epoch - (config.GMAIL_SCRIPT_INTERVAL_MINUTES_FEVER * 60)  # minutes * 60 seconds

    # Compose the search query for messages sent after the specified time in epoch format
    search_query = f"after:{last_run} subject:'New reservation with Fever'"

    result = service.users().messages().list(userId='me', q=search_query).execute()
    messages = result.get('messages')

    # Initialize a list to store subjects
    will_call_subjects = []

    if messages is not None:
        print("Total messages found:", len(messages))

    if messages:
        
        batch_data = {}

        for msg in messages:

            # Fetch the full message
            full_message = service.users().messages().get(userId='me', id=msg['id']).execute()

            # Extract the subject from the email headers
            headers = full_message['payload']['headers']
            subject = next((header['value'] for header in headers if header['name'] == 'Subject'), "Subject not found")

            txt = service.users().messages().get(userId='me', id=msg['id']).execute()
        
            first_name, last_name, number_of_tickets, show_date = get_email_body(service, 'me', msg['id'])

            venue = get_venue(subject)
            showtime = convert_date_from_any_format(show_date)

            print(f"Customer Name: {first_name}")
            print(f"Last Name: {last_name}")
            print(f"Tickets: {number_of_tickets}")
            print(f"Date: {show_date}")
            print(f"Converted Date: {showtime}")
            print(f"Venue: {venue}")

            row_data = [venue, showtime, "none", first_name, last_name, number_of_tickets, "Fever"]

            show_name = venue + " " + showtime

            if show_name not in batch_data:
                batch_data[show_name] = []
            
            batch_data[show_name].append(row_data)

        insert_data_into_google_sheet(batch_data)

    else:
        print(f"No emails with the subject 'New reservation with Fever' found in the last {config.GMAIL_SCRIPT_INTERVAL_MINUTES_FEVER} minutes.")

getEmails()

