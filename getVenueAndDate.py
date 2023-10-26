import re

def get_venue(string):
  """Takes a string and checks if it contains Valencia, Stowaway, Palace, or Citizen. Whichever one matches first, the function returns that name. The function ignores uppercase or lowercase when matching.

  Args:
    string: A string to check for the names.

  Returns:
    A string representing the name that was found in the input string, or None if no name was found.
  """

  # Create a regular expression that matches the names, ignoring uppercase or lowercase.
  name_regex = re.compile(r'(?i)(valencia|stowaway|palace|citizen)')

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
