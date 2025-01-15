import requests

# MailerLite API Key
API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI0IiwianRpIjoiOWU1ZjkzMDRiN2QxYWY1ZWM2ZDNjNmFlODM0YmYyNjM5YjhjYTU5ZDdhYWUyNmM0ZmQ0YTYxZmEyMmM1YzIxZDYxZjM4Y2FhYmNhZTg0ODciLCJpYXQiOjE3MzY5MTY1MTQuMzI3NTY5LCJuYmYiOjE3MzY5MTY1MTQuMzI3NTcxLCJleHAiOjQ4OTI1OTAxMTQuMzIzOTg1LCJzdWIiOiIxMjkwMjEyIiwic2NvcGVzIjpbXX0.RZpywLR4PD5LvI4ef1XshSbEr4ab7AcnjQC8V6EqrY4kqV-8i0RrGO57nkyhW46VtT0KzbLxnsEMEsszFH0rJH12-fN7afM7-GRPXyZSPvfNpk0Z6yWTJHlMy9oS8keTJvGcuCHRilkR694XfoAofsNbWhfJFtPx6yRKOb8LdJScyC7gwobdhuIcteor7jkFskaRCYRW8wo2MHPE7z3_EdahPyYZc1FXzbaonrjhNoUT0Zx_KeUZwajXht39RcM-V6zwBFFBF6XKXx-67NCOMLTjzCk8N2RgiBV2sTMoIMB0WRmdgnkTsBlq4zacGm-29Q3Mnp_gtu7QEQlRDzEMGjKTTlPqVuTT4vclWySUq1NGQdT6X-XGuIbuA3syLFNd3lDq0DpE1nF2x4NwUbcIuzyFKr-w2bHcg_Pr4XDrlv5llSPKR19Bf66jPDqdPWPLy3u4MSQXZtdW3RKPwSSyVdUFFzICQp1KhtxrYLxms6Mweq3TW9nkfZCM7nogI8l8S7uprTk11XK0q1SSnp65fPGNPRiR4yZ446plS1i1fDskcTJxLfoX6RkybBTofNDWjg33Gio9NkuzzTDCoM1OSTFC-ufw184tzbN8a2i29JUDd2Yqep7riyY6qY3Oc0yvNFDpRzb3zAZcwJSdvdBhkMFhLRyIY32aSAalShiskWo"

# Segment Mapping
SEGMENTS = {
    "Townhouse": "143572270449690387",
    "Stowaway": "143572260771333843",
    "Citizen": "143572251965392675",
    "Church": "143572232163034114",
    "Speakeasy": "143571926962407099",
    "Uncategorized": "143572290783675542"
}

# Function to Add Contact to Segment
def add_contact_to_mailerlite_segment(email, name=None, show=None):
    """
    Add a contact to a specific MailerLite segment based on the show name.
    Defaults to 'Uncategorized' if the show is not found.

    :param email: Email address of the contact (required)
    :param name: Name of the contact (optional)
    :param show: Name of the show to determine the segment ID (optional)
    :return: Response from the API
    """
    # Use "Uncategorized" if the show is not found
    if show not in SEGMENTS:
        print(f"Show '{show}' not found. Defaulting to 'Uncategorized'.")
        show = "Uncategorized"

    # Get the Segment ID
    segment_id = SEGMENTS[show]

    # API Endpoint
    api_url = f"https://connect.mailerlite.com/api/subscribers"

    # Request Headers
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    # Payload
    payload = {
        "email": email,
        "fields": {"name": name} if name else {},
        "groups": [segment_id]
    }

    # Make the POST request
    response = requests.post(api_url, json=payload, headers=headers)

    # Check the response
    if response.status_code in [200, 201]:
        print(f"Contact added to '{show}' segment successfully:", response.json())
    else:
        print(f"Failed to add contact to '{show}' segment:", response.status_code, response.json())


# Example Usage
add_contact_to_mailerlite_segment(
    email="janedoe@example.com",
    name="Jane Doe",
    show="LA - Unknown"  # Invalid show name will default to "Uncategorized"
)
