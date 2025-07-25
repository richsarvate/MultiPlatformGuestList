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

# Define the SCOPES. If modifying it, delete the token.pickle file.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def getEmails():
    creds = None

    print("attempting to get goldstar will call list from gmail")

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
    last_run = current_time_epoch - (config.GMAIL_SCRIPT_INTERVAL_HOURS * 60 * 60)  # hours * 60 minutes * 60 seconds

    # Compose the search query for messages sent after the specified time in epoch format
    search_query = f"after:{last_run} subject:'Will-Call List for'"

    result = service.users().messages().list(userId='me', q=search_query).execute()
    messages = result.get('messages')

    # Initialize a list to store subjects
    will_call_subjects = []

    if messages is not None:
        print("Total messages found:", len(messages))

    if messages:
        for msg in messages:
            txt = service.users().messages().get(userId='me', id=msg['id']).execute()
        
            subject = ""
            csv_data = None

            for header in txt['payload']['headers']:
                if header['name'] == 'Subject':
                    subject = header['value']

            for part in txt['payload']['parts']:
                if part['filename'] and part['filename'].endswith('.csv'):
                    #print(part['filename'])
                    #print(part['body'])

                    attachment_id = part['body']['attachmentId']
                    attachment = service.users().messages().attachments().get(userId='me', messageId=msg['id'], id=attachment_id).execute()
                    data = attachment['data']

                    csv_data = base64.urlsafe_b64decode(data.encode('UTF-8')).decode('UTF-8')
                    #print("Subject:", subject)
                    #print("CSV Data:")
                    #print(csv_data)

            if subject and csv_data:
                print("Subject:", subject)
                print("CSV Data:")
                #print(csv_data)

            # You can further process the CSV data if needed
            # For example, you can use the 'csv' module to parse and work with the data
            # Here's a basic example of parsing the CSV data:
            reader = csv.reader(csv_data.splitlines())

            batch_data = {}

            # Iterate through the order data and print customer details
            for row in reader:

                if 'First Name' in row:
                    continue  # Skip the row as it's a header

                if len(row) >= 4:
                    first_name = row[1]
                    last_name = row[0]
                    num_tickets = row[2]
                    show_name = subject
                    customer_email = "none"
                    venue_name = get_venue(subject)
                    showtime = convert_date_format(row[3])

                    row_data = [venue_name, showtime + " 8pm", customer_email,  "Goldstar", "GA", "8pm", first_name, last_name, num_tickets]
                    print(row_data)

                    if show_name not in batch_data:
                        batch_data[show_name] = []

                    batch_data[show_name].append(row_data)

            insert_data_into_google_sheet(batch_data)

    else:
        print(f"No emails with the subject 'Will-Call List for' found in the last {config.GMAIL_SCRIPT_INTERVAL_HOURS} hours.")

getEmails()

