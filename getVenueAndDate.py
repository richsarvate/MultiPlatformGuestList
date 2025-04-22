import re
from datetime import datetime, date
from dateutil import parser

def append_year_to_show_date(show_date):
    today = date.today()
    current_year = today.year
    
    # Parse the date string
    date_obj = parser.parse(show_date, fuzzy=True)
    show_month_day = date_obj.date().replace(year=current_year)
    
    # Compare with today
    year = current_year if show_month_day >= today else current_year + 1
    
    return f"{show_date} {year}"

def get_city(string):
    venue = get_venue(string)
    
    # Normalize the venue string to lowercase to make the comparison case-insensitive
    venue_lower = venue.lower()
    
    # Check if the venue matches the specified strings
    if venue_lower in ['valencia', 'palace', 'church']:
        city = 'SF'
    elif venue_lower in ['stowaway', 'citizen', 'barber','townhouse']:
        city = 'LA'
    elif venue_lower in ['blind barber fulton market']:
        city = 'CHI'
    else:
        city = 'Unknown'  # If the venue does not match any of the specified strings
    
    return city

def get_venue(string):
  """Takes a string and checks if it contains Valencia, Stowaway, Palace, or Citizen. Whichever one matches first, the function returns that name. The function ignores uppercase or lowercase when matching.

  Args:
    string: A string to check for the names.

  Returns:
    A string representing the name that was found in the input string, or None if no name was found.
  """

  # Create a regular expression that matches the names, ignoring uppercase or lowercase.
  name_regex = re.compile(r'(?i)(valencia|stowaway|palace|citizen|church|Blind Barber Fulton Market|townhouse)')

  # Find the first match in the input string.
  match = name_regex.search(string)

  # If there is a match, return the name that was found.
  if match:
    return capitalize_first_letter(match.group())

  # If there is no match, return None.
  else:
    return None

def capitalize_first_letter(response):
  return response[0].upper() + response[1:].lower()

def extract_venue_name(product_name):
  """Extracts the venue name from the product name.

  Args:
    product_name: The product name.

  Returns:
    The venue name, or None if the venue name cannot be extracted.
  """

  # Compile a regular expression to match the venue name.
  venue_name_regex = r"^([^ ]+-?)"

  # Match the regular expression against the product name.
  match = re.match(venue_name_regex, product_name)

  # If the regular expression matches, then the venue name is the first group in the match object.
  if match:
    venue_name = match.group(1)
    return venue_name
  else:
    return None

def extract_time_from_subject(email_subject):
    # Regular expression to match time in HH:MM AM/PM format
    time_pattern = r'\b\d{1,2}:\d{2}\s?[APMapm]{2}\b'
    
    # Search for the time in the email subject
    match = re.search(time_pattern, email_subject)
    
    if match:
        # Extracted time (e.g., '8:00 PM')
        extracted_time = match.group().strip().lower()
        
        # Remove minutes if it's ':00' and make 'am/pm' lowercase
        formatted_time = extracted_time.replace(':00', '').replace(' ', '')
        
        return formatted_time
    else:
        return None

def extract_date_from_subject(subject):
    """
    Extracts the date from the product name, assuming the date format is MM-DD-YYYY.

    Args:
    product_name: The product name containing a date.

    Returns:
    The date in MM-DD-YYYY format, or None if the date cannot be extracted.
    """
    # Compile a regular expression to match the date in MM-DD-YYYY format.
    date_regex = r"\d{2}-\d{2}-\d{4}"

    # Search the regular expression against the product name.
    match = re.search(date_regex, subject)

    # If the regular expression finds a match, return the matched date.
    if match:
        return match.group()
    else:
        return None


def extract_date(product_name):
  """Extracts the venue name from the product name.

  Args:
    product_name: The product name.

  Returns:
    The venue name, or None if the venue name cannot be extracted.
  """

  # Compile a regular expression to match the venue name.
  string_between_dashes_regex = r".*-(.*)-.*"

  # Match the regular expression against the product name.
  match = re.match(string_between_dashes_regex, product_name)

  # If the regular expression matches, then the venue name is the first group in the match object.
  if match:
      showtime = match.group(1)
      return showtime.strip()
  else:
      return None

def convert_date_from_any_format(date_str):
    if date_str == 'Date':
        return None  # Skip headers or non-date entries

    try:
        # Using dateutil.parser to parse the date string
        date_object = parser.parse(date_str)

        day = date_object.day
        month_names = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        month = date_object.month
        month_name = month_names[month - 1]

        day_of_week = date_object.strftime('%A')  # Get the name of the day

        # Add suffix to the day
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix = "th"
        else:
            suffix = ["st", "nd", "rd"][day % 10 - 1]

        formatted_date = f"{day_of_week} {month_name} {day}{suffix}"
        return formatted_date
    except ValueError:
        return None  # Skip non-date entries that cannot be parsed

def convert_date_format(date_str):
    if date_str == 'Date':
        return None  # Skip headers or non-date entries

    try:
        date_object = datetime.strptime(date_str, '%Y-%m-%d')
        day = date_object.day
        month_names = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        month = date_object.month
        month_name = month_names[month - 1]

        day_of_week = date_object.strftime('%A')  # Get the name of the day

        # Add suffix to the day
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix = "th"
        else:
            suffix = ["st", "nd", "rd"][day % 10 - 1]

        formatted_date = f"{day_of_week} {month_name} {day}{suffix}"
        return formatted_date
    except ValueError:
        return None  # Skip non-date entries that cannot be parsed

def extract_time(product_name):
    """Extracts the time from the product name and ensures the am/pm is lowercase.

    Args:
        product_name: The product name in the format 'Venue - Date - Time'.

    Returns:
        The time in lowercase (e.g., "8pm" or "7:30pm"), or None if the time cannot be extracted.
    """
    # Regular expression to capture time in the format "8pm", "7:30pm", etc.
    time_regex = r"(\d{1,2}(:\d{2})?(am|pm))$"

    # Match the regular expression against the product name.
    match = re.search(time_regex, product_name, re.IGNORECASE)

    # If the regular expression matches, return the captured time group in lowercase.
    if match:
        return match.group(0).strip().lower()
    else:
        return None
