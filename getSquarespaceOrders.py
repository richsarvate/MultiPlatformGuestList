import json
import requests
import gspread
from datetime import datetime, timedelta
from insertIntoGoogleSheet import insert_data_into_google_sheet
from getVenueAndDate import get_venue,extract_venue_name, extract_date, extract_time
import config

print(datetime.utcnow().isoformat()[:-6] + "Z");

# Calculate the timestamp for the current time
current_time = datetime.utcnow().isoformat()[:-6] + "Z"

# Calculate the timestamp for 5 minutes ago
last_run = (datetime.utcnow() - timedelta(minutes=config.SCRIPT_INTERVAL)).isoformat()[:-6] + "Z"

# Define the URL for the API request with the "modifiedAfter" argument set to 5 minutes ago
url = f"https://api.squarespace.com/1.0/commerce/orders?modifiedAfter={last_run}&modifiedBefore={current_time}"

# Define the headers for the request
headers = {
    "Authorization": f"Bearer {config.SQUARESPACE_API_KEY}",
    "User-Agent": "YOUR_CUSTOM_APP_DESCRIPTION"
}

# Make the API request
response = requests.get(url, headers=headers)

# Check if the request was successful
if response.status_code == 200:
    # Parse the JSON response
    data = response.json()

    print(data)

    #batch_data = {"date1":[], "date2":[]}
    batch_data = {}

    # Iterate through the order data and print customer details
    for order in data["result"]:
        
        first_name = order["billingAddress"]["firstName"]
        last_name = order["billingAddress"]["lastName"]
        customer_email = order["customerEmail"]
        time = "Not Found"

        for item in order['lineItems']:
       
            num_tickets = item["quantity"]
            show_name = item["productName"]
            showtime = extract_date(show_name)
            venue_name = get_venue(show_name)
            time = extract_time(show_name)

            row_data = [venue_name, showtime + " " + time, customer_email, first_name, last_name, num_tickets, "Squarespace", time, "GA"]
            print(row_data)

            if show_name not in batch_data:
                batch_data[show_name] = []
        
            batch_data[show_name].append(row_data)

    insert_data_into_google_sheet(batch_data)
    
else:
    print(f"Failed to fetch data. Status code: {response.status_code}")

