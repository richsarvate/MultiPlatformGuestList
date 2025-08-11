#!/usr/bin/env python3
"""
Daily MailerLite Sync Script

This script runs as a daily cron job to:
1. Query MongoDB for contacts from completed shows (show_date < today)
2. Find contacts that haven't been added to MailerLite yet
3. Add them to MailerLite using the existing batch logic
4. Mark them as processed in MongoDB

Run this script once daily via cron job.
"""

import json
import logging
from datetime import datetime, date
from pymongo import MongoClient
import requests
import re

# Configure logging
LOG_FILE = "/home/ec2-user/GuestListScripts/logs/mailerlite_sync.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# MailerLite API Configuration (from addEmailToMailerLite.py)
API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI0IiwianRpIjoiOWU1ZjkzMDRiN2QxYWY1ZWM2ZDNjNmFlODM0YmYyNjM5YjhjYTU5ZDdhYWUyNmM0ZmQ0YTYxZmEyMmM1YzIxZDYxZjM4Y2FhYmNhZTg0ODciLCJpYXQiOjE3MzY5MTY1MTQuMzI3NTY5LCJuYmYiOjE3MzY5MTY1MTQuMzI3NTcxLCJleHAiOjQ4OTI1OTAxMTQuMzIzOTg1LCJzdWIiOiIxMjkwMjEyIiwic2NvcGVzIjpbXX0.RZpywLR4PD5LvI4ef1XshSbEr4ab7AcnjQC8V6EqrY4kqV-8i0RrGO57nkyhW46VtT0KzbLxnsEMEsszFH0rJH12-fN7afM7-GRPXyZSPvfNpk0Z6yWTJHlMy9oS8keTJvGcuCHRilkR694XfoAofsNbWhfJFtPx6yRKOb8LdJScyC7gwobdhuIcteor7jkFskaRCYRW8wo2MHPE7z3_EdahPyYZc1FXzbaonrjhNoUT0Zx_KeUZwajXht39RcM-V6zwBFFBF6XKXx-67NCOMLTjzCk8N2RgiBV2sTMoIMB0WRmdgnkTsBlq4zacGm-29Q3Mnp_gtu7QEQlRDzEMGjKTTlPqVuTT4vclWySUq1NGQdT6X-XGuIbuA3syLFNd3lDq0DpE1nF2x4NwUbcIuzyFKr-w2bHcg_Pr4XDrlv5llSPKR19Bf66jPDqdPWPLy3u4MSQXZtdW3RKPwSSyVdUFFzICQp1KhtxrYLxms6Mweq3TW9nkfZCM7nogI8l8S7uprTk11XK0q1SSnp65fPGNPRiR4yZ446plS1i1fDskcTJxLfoX6RkybBTofNDWjg33Gio9NkuzzTDCoM1OSTFC-ufw184tzbN8a2i29JUDd2Yqep7riyY6qY3Oc0yvNFDpRzb3zAZcwJSdvdBhkMFhLRyIY32aSAalShiskWo"

# Venue to MailerLite Group Mapping (from addEmailToMailerLite.py)
GROUPS = {
    "townhouse": "143572270449690387",
    "stowaway": "143572260771333843",
    "citizen": "143572251965392675",
    "church": "143572232163034114",
    "palace": "143571926962407099",
    "blind barber fulton market": "148048384759956607",
    "uncategorized": "143572290783675542"
}

def load_mongo_config():
    """Load MongoDB configuration from config file"""
    CONFIG_FILE = "config/bucketlistConfig.json"
    try:
        with open(CONFIG_FILE, 'r') as f:
            config_data = json.load(f)
        return config_data["MONGO_URI"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error loading MongoDB config: {str(e)}")
        return None

def is_valid_email(email):
    """Validate email address format"""
    if not email or email.lower() in ['', 'none', 'null']:
        return False
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email) is not None

def parse_show_date(show_date_str):
    """
    Parse show date string to date object.
    Handles various date formats that might be in the database.
    """
    try:
        # Try common date formats
        for fmt in ["%Y-%m-%d %I:%M %p", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y %I:%M %p"]:
            try:
                parsed = datetime.strptime(show_date_str, fmt)
                return parsed.date()
            except ValueError:
                continue
        
        # If all formats fail, log and return None
        logger.warning(f"Could not parse date: {show_date_str}")
        return None
    except Exception as e:
        logger.warning(f"Error parsing date '{show_date_str}': {str(e)}")
        return None

def get_contacts_to_process():
    """
    Query MongoDB for contacts from completed shows that haven't been added to MailerLite
    """
    MONGO_URI = load_mongo_config()
    if not MONGO_URI:
        return []
    
    MONGO_DB = "guest_list_contacts"
    MONGO_COLLECTION = "contacts"
    
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        collection = db[MONGO_COLLECTION]
        
        # Find contacts that haven't been added to MailerLite
        query = {
            "added_to_mailerlite": {"$ne": True},
            "email": {"$exists": True, "$ne": "", "$nin": [None, "none", "null"]}
        }
        
        contacts = list(collection.find(query))
        
        # Filter by show date (only completed shows)
        today = date.today()
        valid_contacts = []
        
        for contact in contacts:
            show_date = parse_show_date(contact.get('show_date', ''))
            if show_date and show_date < today:
                valid_contacts.append(contact)
            elif show_date is None:
                logger.warning(f"Skipping contact with unparseable date: {contact.get('show_date')} for {contact.get('email')}")
        
        logger.info(f"Found {len(valid_contacts)} contacts from completed shows to process")
        return valid_contacts
        
    except Exception as e:
        logger.error(f"Error querying MongoDB: {str(e)}")
        return []
    finally:
        if 'client' in locals():
            client.close()

def convert_to_mailerlite_format(contacts):
    """
    Convert MongoDB contacts to the format expected by MailerLite batch function
    Returns dictionary in format: {venue: [[contact_array], ...]}
    """
    mailerlite_data = {}
    
    for contact in contacts:
        # Skip invalid emails
        if not is_valid_email(contact.get('email')):
            logger.warning(f"Skipping invalid email: {contact.get('email')}")
            continue
            
        venue = contact.get('venue', 'uncategorized')
        
        # Create contact array in expected format
        # [venue, date, email, source, time, type, firstname, lastname, tickets, phone(optional)]
        contact_array = [
            contact.get('venue', ''),
            contact.get('show_date', ''),
            contact.get('email', ''),
            contact.get('source', ''),
            contact.get('show_time', ''),
            contact.get('ticket_type', ''),
            contact.get('first_name', ''),
            contact.get('last_name', ''),
            contact.get('tickets', 1),
            contact.get('phone', '')
        ]
        
        if venue not in mailerlite_data:
            mailerlite_data[venue] = []
        
        mailerlite_data[venue].append(contact_array)
    
    return mailerlite_data

def batch_add_contacts_to_mailerlite(emailsToAdd):
    """
    Add contacts to MailerLite using batch API (adapted from addEmailToMailerLite.py)
    """
    logger.info("Starting MailerLite batch upload")
    
    # API Endpoint for batch requests
    batch_url = "https://connect.mailerlite.com/api/batch"
    
    # Request Headers
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    # Collect requests for batch processing
    requests_list = []
    processed_emails = []
    
    for show, contacts in emailsToAdd.items():
        for contact in contacts:
            email = contact[2]
            group_id = GROUPS.get(contact[0].lower(), GROUPS["uncategorized"])
            
            # Skip if email is not valid
            if not is_valid_email(email):
                logger.warning(f"Invalid email skipped: {email}")
                continue
            
            first_name = contact[6]
            last_name = contact[7]
            name = f"{first_name} {last_name}".strip()
            
            # Prepare individual request body
            body = {
                "email": email,
                "fields": {"name": name},
                "groups": [group_id]
            }
            
            requests_list.append({
                "method": "POST",
                "path": "/api/subscribers",
                "body": body
            })
            
            processed_emails.append(email)
    
    if not requests_list:
        logger.info("No valid contacts to process")
        return []
    
    # Split requests into batches of 50
    successful_emails = []
    failed_emails = []
    
    for i in range(0, len(requests_list), 50):
        batch_payload = {"requests": requests_list[i:i+50]}
        
        # Make the batch request
        try:
            response = requests.post(batch_url, json=batch_payload, headers=headers)
            
            # Handle response
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Batch Process Completed: {result['successful']} successful, {result['failed']} failed.")
                
                # Track successful emails for this batch
                batch_start = i
                for idx, res in enumerate(result['responses']):
                    email_idx = batch_start + idx
                    if email_idx < len(processed_emails):
                        if res.get('code') in [200, 201]:  # Success codes
                            successful_emails.append(processed_emails[email_idx])
                        else:
                            failed_emails.append(processed_emails[email_idx])
                            logger.warning(f"Failed to add {processed_emails[email_idx]}: {res}")
            else:
                logger.error(f"Failed to process batch: {response.status_code} - {response.text}")
                # Mark all emails in this batch as failed
                batch_emails = processed_emails[i:i+50]
                failed_emails.extend(batch_emails)
                
        except Exception as e:
            logger.error(f"Error processing batch: {str(e)}")
            batch_emails = processed_emails[i:i+50]
            failed_emails.extend(batch_emails)
    
    logger.info(f"MailerLite upload complete: {len(successful_emails)} successful, {len(failed_emails)} failed")
    return successful_emails

def mark_contacts_as_processed(successful_emails):
    """
    Mark successfully processed contacts as added to MailerLite in MongoDB
    """
    if not successful_emails:
        return
        
    MONGO_URI = load_mongo_config()
    if not MONGO_URI:
        return
    
    MONGO_DB = "guest_list_contacts"
    MONGO_COLLECTION = "contacts"
    
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        collection = db[MONGO_COLLECTION]
        
        # Update all successfully processed contacts
        result = collection.update_many(
            {"email": {"$in": successful_emails}},
            {
                "$set": {
                    "added_to_mailerlite": True,
                    "mailerlite_added_date": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"Marked {result.modified_count} contacts as processed in MongoDB")
        
    except Exception as e:
        logger.error(f"Error updating MongoDB: {str(e)}")
    finally:
        if 'client' in locals():
            client.close()

def main():
    """Main function to run the daily sync process"""
    logger.info("Starting daily MailerLite sync process")
    
    try:
        # Step 1: Get contacts to process
        contacts = get_contacts_to_process()
        
        if not contacts:
            logger.info("No contacts to process today")
            return
        
        # Step 2: Convert to MailerLite format
        mailerlite_data = convert_to_mailerlite_format(contacts)
        
        if not mailerlite_data:
            logger.info("No valid contacts after filtering")
            return
        
        # Step 3: Add to MailerLite
        successful_emails = batch_add_contacts_to_mailerlite(mailerlite_data)
        
        # Step 4: Mark as processed in MongoDB
        mark_contacts_as_processed(successful_emails)
        
        logger.info(f"Daily sync complete: processed {len(successful_emails)} contacts")
        
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")

if __name__ == "__main__":
    main()
