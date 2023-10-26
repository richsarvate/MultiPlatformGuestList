import requests
import datetime 
from datetime import datetime, timedelta
from insertIntoGoogleSheet import insert_data_into_google_sheet
from getVenueAndDate import get_venue
import config

# Get the current date
current_date = datetime.now()

# Calculate the date that is 14 days from now
last_run = current_date - timedelta(minutes=config.SCRIPT_INTERVAL)

changed_since = last_run.strftime("%Y-%m-%dT%H:%M:%SZ")

# Make the API call
response = requests.get(
    "https://www.eventbriteapi.com/v3/organizations/{}/orders?changed_since={}&token={}".format(
        config.EVENTBRITE_ORGANIZATION_ID, changed_since, config.EVENTBRITE_PRIVATE_TOKEN
    )
)

def format_date(input_date):
    try:
        # Parse the input date string into a datetime object
        date_obj = datetime.strptime(input_date, "%Y-%m-%dT%H:%M:%S")

        # Extract the day, month, and year
        day = date_obj.strftime("%d").lstrip("0")  # Remove leading zeros
        month = date_obj.strftime("%B")
        year = date_obj.strftime("%Y")

        # Get the day suffix (e.g., "st", "nd", "rd", "th")
        day_suffix = "th" if 11 <= int(day) <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(int(day) % 10, "th")

        # Format the date and return it
        formatted_date = f"{date_obj.strftime('%A')} {month} {day}{day_suffix}"
        return formatted_date
    except ValueError:
        return "Invalid date format"

def count_objects_with_email(json_data, email):
  count = 0
  for attendee in json_data["attendees"]:
    if attendee["profile"]["email"] == email:
      count += 1

  return count

def iterate_through_orders(orders):
  """Iterates through a list of Eventbrite orders and prints the order ID, first and last name,
  email, show name, and number of tickets purchased for each order.

  Args:
    orders: A list of Eventbrite orders in JSON format.
  """

  batch_data = {}

  for order in orders:
      
    #print(order)

    # Get the first and last name of the customer.
    first_name = order["first_name"]
    last_name = order["last_name"]

    # Get the customer's email address.
    email = order["email"]

    # Get the show name.
    event_id = order["event_id"]

    eventResponse = requests.get(
        "https://www.eventbriteapi.com/v3/events/{}?token={}".format(
            event_id, config.EVENTBRITE_PRIVATE_TOKEN
        )
    )

    event_name = ""

    # Check the status code of the response
    if eventResponse.status_code == 200:
        eventData = eventResponse.json()

        #print(eventData)

        # Get the name of the show
        event_name = eventData["name"]["text"]
        venue = get_venue(event_name)
        #event_date = convert_date_format(eventData["start"]["local"])
        event_date=format_date(eventData["start"]["local"])

    else:
        # Handle the error
        print("Error: {} - {}".format(response.status_code, response.content))

    eventAttendees = requests.get(
        "https://www.eventbriteapi.com/v3/events/{}/attendees/?token={}".format(
            event_id, config.EVENTBRITE_PRIVATE_TOKEN
        )
    )

    # Check the status code of the response
    if eventAttendees.status_code == 200:
        attendees = eventAttendees.json()
    else:
        # Handle the error
        print("Error: {} - {}".format(eventAttendees.status_code, response.content))

    tickets = count_objects_with_email(attendees, email)

    row_data = [venue, event_date, email, first_name, last_name, tickets, "EventBrite"]

    if event_name not in batch_data:
        batch_data[event_name] = []

    batch_data[event_name].append(row_data)

  insert_data_into_google_sheet(batch_data)

# Check the status code of the response
if response.status_code == 200:
    # Get the list of orders
    orders = response.json()["orders"]
    # Iterate through the orders and print the order information
    iterate_through_orders(orders)
else:
    # Handle the error
    print("Error: {} - {}".format(response.status_code, response.content))
