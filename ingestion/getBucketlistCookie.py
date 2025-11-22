import requests
import time
import pickle
import os.path
import base64
import re
import logging
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from urllib.parse import urlparse, parse_qs, urljoin
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config.config as config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/blt_cookie.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "https://insights.bucketlisters.com"
EMAIL = "info@setupcomedy.com"
COOKIE_FILE = "blt_cookie.txt"
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Referer": f"{BASE_URL}/login/email"
}
EMAIL_DELAY_SECONDS = 5  # Initial delay for email delivery
MAX_EMAIL_RETRIES = 3  # Number of retries to fetch email

def is_cookie_valid(cookie):
    """Check if the provided cookie is valid by making a test API call."""
    logger.info("Checking cookie validity")
    headers = HEADERS.copy()
    headers["Cookie"] = cookie
    try:
        # Use the _data parameter to get JSON response instead of HTML
        import urllib.parse
        data_param = urllib.parse.quote("routes/v2/$partnerId/experiences/index")
        response = requests.get(f"{BASE_URL}/v2/152/experiences/?_data={data_param}", headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Verify we got JSON, not HTML
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                # Double-check the response has expected structure
                try:
                    data = response.json()
                    if "experiences" in data:
                        logger.info("Cookie is valid")
                        return True
                    else:
                        logger.warning("Cookie returned JSON but missing 'experiences' key")
                        return False
                except ValueError:
                    logger.warning("Cookie validation: Failed to parse JSON response")
                    return False
            else:
                logger.warning(f"Cookie validation: Got {content_type} instead of JSON")
                return False
        else:
            logger.warning(f"Cookie invalid: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error checking cookie: {str(e)}")
        return False

def fetch_verification_code():
    """Fetch the latest verification code from Gmail using the Gmail API."""
    logger.info("Fetching verification code from Gmail")
    creds = None
    if os.path.exists(config.GMAIL_TOKEN_PATH):
        logger.info(f"Loading Gmail token from {config.GMAIL_TOKEN_PATH}")
        with open(config.GMAIL_TOKEN_PATH, 'rb') as token:
            try:
                creds = pickle.load(token)
            except Exception as e:
                logger.error(f"Error loading Gmail token: {str(e)}")
                return None

    if not creds or not creds.valid:
        logger.info("Gmail credentials invalid or expired")
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing Gmail token")
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Failed to refresh Gmail token: {str(e)}")
                return None
        else:
            logger.info("Running OAuth flow for new Gmail credentials")
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    config.GMAIL_CREDS_FILE,
                    scopes=SCOPES,
                    redirect_uri='http://ec2-3-17-25-171.us-east-2.compute.amazonaws.com:8080/'
                )
                creds = flow.run_local_server(
                    port=8080,
                    host="ec2-3-17-25-171.us-east-2.compute.amazonaws.com",
                    open_browser=False
                )
                with open(config.GMAIL_TOKEN_PATH, 'wb') as token:
                    logger.info(f"Saving new Gmail token to {config.GMAIL_TOKEN_PATH}")
                    pickle.dump(creds, token)
            except Exception as e:
                logger.error(f"Failed to run OAuth flow: {str(e)}")
                return None

    service = build('gmail', 'v1', credentials=creds)
    
    # Search for emails from noreply@bucketlisters.com
    query = 'from:noreply@bucketlisters.com "Here is your verification code"'
    for attempt in range(1, MAX_EMAIL_RETRIES + 1):
        try:
            logger.info(f"Attempt {attempt}/{MAX_EMAIL_RETRIES} - Searching Gmail with query: {query}")
            result = service.users().messages().list(userId='me', q=query).execute()
            messages = result.get('messages', [])
            
            if not messages:
                logger.warning(f"Attempt {attempt}/{MAX_EMAIL_RETRIES} - No verification email found")
                if attempt < MAX_EMAIL_RETRIES:
                    logger.info(f"Waiting {EMAIL_DELAY_SECONDS} seconds before retry")
                    time.sleep(EMAIL_DELAY_SECONDS)
                continue

            # Get the latest email
            latest_msg_id = messages[0]['id']
            logger.info(f"Fetching email with ID: {latest_msg_id}")
            message = service.users().messages().get(userId='me', id=latest_msg_id).execute()
            
            # Extract email body
            payload = message['payload']
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body']['data']
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        code = re.search(r'\b\d{6}\b', body)
                        if code:
                            logger.info(f"Found verification code: {code.group()}")
                            return code.group()
            else:
                data = payload['body']['data']
                body = base64.urlsafe_b64decode(data).decode('utf-8')
                code = re.search(r'\b\d{6}\b', body)
                if code:
                    logger.info(f"Found verification code: {code.group()}")
                    return code.group()
            
            logger.warning(f"Attempt {attempt}/{MAX_EMAIL_RETRIES} - No verification code found in email")
            if attempt < MAX_EMAIL_RETRIES:
                logger.info(f"Waiting {EMAIL_DELAY_SECONDS} seconds before retry")
                time.sleep(EMAIL_DELAY_SECONDS)
        except Exception as e:
            logger.error(f"Attempt {attempt}/{MAX_EMAIL_RETRIES} - Error fetching email: {str(e)}")
            if attempt < MAX_EMAIL_RETRIES:
                logger.info(f"Waiting {EMAIL_DELAY_SECONDS} seconds before retry")
                time.sleep(EMAIL_DELAY_SECONDS)
    
    logger.error("Failed to fetch verification code after all retries")
    return None

def get_new_cookie():
    """Fetch a new BLT_partner_session cookie and save to file."""
    logger.info("Starting process to fetch new BLT cookie")
    
    # Submit email to get login code and capture redirect URL
    login_url = f"{BASE_URL}/login/email"
    data = {"email": EMAIL, "redirectTo": "/"}
    try:
        logger.info(f"Submitting email {EMAIL} to {login_url}")
        response = requests.post(login_url, headers=HEADERS, data=data, allow_redirects=False, timeout=10)
        if response.status_code in (301, 302, 303, 307, 308):
            redirect_url = response.headers.get("Location")
            full_redirect_url = urljoin(BASE_URL, redirect_url)
            logger.info(f"Redirected to: {full_redirect_url}")
        else:
            logger.error(f"Expected redirect, got HTTP {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error submitting email: {str(e)}")
        return None

    # Parse redirect URL for parameters
    try:
        parsed_url = urlparse(full_redirect_url)
        query_params = parse_qs(parsed_url.query)
        otp_request_id = query_params.get('otp', [None])[0]
        contact_info = query_params.get('contactInfo', [None])[0]
        method = query_params.get('method', [None])[0]
        redirect_to = query_params.get('redirectTo', [None])[0]
        
        if not all([otp_request_id, contact_info, method, redirect_to]):
            logger.error(f"Missing required parameters in redirect URL: otp={otp_request_id}, contactInfo={contact_info}, method={method}, redirectTo={redirect_to}")
            return None
        logger.info(f"Extracted parameters: otpRequestId={otp_request_id}, contactInfo={contact_info}, method={method}, redirectTo={redirect_to}")
    except Exception as e:
        logger.error(f"Error parsing redirect URL {full_redirect_url}: {str(e)}")
        return None

    # Fetch verification code
    logger.info(f"Waiting {EMAIL_DELAY_SECONDS} seconds for email delivery")
    time.sleep(EMAIL_DELAY_SECONDS)
    code = fetch_verification_code()
    if not code:
        logger.error("Failed to retrieve verification code")
        return None

    # Submit verification code to login/verify
    verify_url = f"{BASE_URL}/login/verify?otp={otp_request_id}&redirectTo={redirect_to}&contactInfo={contact_info}&method={method}"
    data = {
        "contactInfo": contact_info,
        "method": method,
        "redirectTo": redirect_to,
        "otpRequestId": otp_request_id,
        "verificationCode": code
    }
    try:
        logger.info(f"Submitting verification code {code} to {verify_url}")
        session = requests.Session()
        
        # Try JSON first (new API format)
        headers_json = HEADERS.copy()
        headers_json["Content-Type"] = "application/json"
        response = session.post(verify_url, headers=headers_json, json=data, allow_redirects=True, timeout=10)
        
        # If JSON fails with 400, try form data (old API format)
        if response.status_code == 400:
            logger.warning("JSON submission failed with 400, trying form data")
            headers_form = HEADERS.copy()
            headers_form["Content-Type"] = "application/x-www-form-urlencoded"
            response = session.post(verify_url, headers=headers_form, data=data, allow_redirects=True, timeout=10)
        
        response.raise_for_status()
        
        cookie = session.cookies.get("BLT_partner_session")
        if cookie:
            try:
                with open(COOKIE_FILE, "w") as f:
                    f.write(f"BLT_partner_session={cookie}")
                logger.info(f"New cookie saved to {COOKIE_FILE}")
                return f"BLT_partner_session={cookie}"
            except IOError as e:
                logger.error(f"Error saving cookie to {COOKIE_FILE}: {str(e)}")
                return None
        else:
            logger.error(f"No BLT_partner_session cookie found in response. Headers: {response.headers}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error submitting verification code: {str(e)}")
        return None

def load_cookie():
    """Load the BLT_partner_session cookie from file, fetching a new one if invalid or missing."""
    logger.info("Loading BLT cookie")
    try:
        with open(COOKIE_FILE, "r") as f:
            current_cookie = f.read().strip()
            logger.info(f"Loaded existing cookie from {COOKIE_FILE}")
    except FileNotFoundError:
        current_cookie = None
        logger.warning(f"No existing cookie found at {COOKIE_FILE}")

    if current_cookie and is_cookie_valid(current_cookie):
        logger.info("Current cookie is valid")
        return current_cookie
    else:
        logger.info("Current cookie is invalid or not found. Fetching new cookie...")
        new_cookie = get_new_cookie()
        if new_cookie:
            logger.info(f"Using new cookie: {new_cookie}")
            return new_cookie
        else:
            logger.error("Failed to obtain a valid cookie")
            return None

if __name__ == "__main__":
    cookie = load_cookie()
    if cookie:
        logger.info(f"Successfully retrieved cookie: {cookie}")
    else:
        logger.error("Failed to retrieve a valid cookie")
