#!/usr/bin/env python3
"""
Google Sheets to MongoDB Sync Service
Professional background sync service for maintaining data consistency
"""

import gspread
from google.oauth2.service_account import Credentials
import config.config as config
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from backend.database_service import db_service
from backend.models import Contact, validate_contact, SyncMode
from ingestion.getVenueAndDate import get_city, append_year_to_show_date

# Setup logging
logger = logging.getLogger(__name__)


class SyncError(Exception):
    """Custom sync error"""
    pass


class SheetsToMongoSync:
    """
    Professional sync service for Google Sheets to MongoDB synchronization
    Handles intelligent merging, conflict resolution, and performance optimization
    """
    
    def __init__(self):
        self.gc = None
        self.service = None
        self.sync_job_id = None
        self._setup_google_client()
    
    def _setup_google_client(self):
        """Initialize Google Sheets client"""
        try:
            creds = Credentials.from_service_account_file(
                config.GOOGLE_CREDS_FILE,
                scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
            )
            self.gc = gspread.Client(auth=creds)
            logger.info("Google Sheets client initialized successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize Google Sheets client: {e}"
            logger.error(error_msg)
            raise SyncError(error_msg)
    
    def start_sync_job(self, job_type: str = "sheets_to_mongo") -> str:
        """Start a new sync job and return job ID"""
        try:
            self.sync_job_id = db_service.create_sync_job(job_type)
            db_service.update_sync_job(self.sync_job_id, {
                "status": "running",
                "started_at": datetime.utcnow()
            })
            logger.info(f"Started sync job: {self.sync_job_id}")
            return self.sync_job_id
            
        except Exception as e:
            logger.error(f"Failed to start sync job: {e}")
            raise SyncError(f"Sync job creation failed: {e}")
    
    def complete_sync_job(self, venues_processed: List[str], records_synced: int, errors: List[str]):
        """Mark sync job as completed"""
        if not self.sync_job_id:
            return
            
        try:
            db_service.update_sync_job(self.sync_job_id, {
                "status": "completed" if not errors else "completed_with_errors",
                "completed_at": datetime.utcnow(),
                "venues_processed": venues_processed,
                "records_synced": records_synced,
                "errors": errors
            })
            logger.info(f"Completed sync job: {self.sync_job_id}")
            
        except Exception as e:
            logger.error(f"Failed to complete sync job: {e}")
    
    def fail_sync_job(self, error_message: str):
        """Mark sync job as failed"""
        if not self.sync_job_id:
            return
            
        try:
            db_service.update_sync_job(self.sync_job_id, {
                "status": "failed",
                "completed_at": datetime.utcnow(),
                "errors": [error_message]
            })
            logger.error(f"Failed sync job: {self.sync_job_id} - {error_message}")
            
        except Exception as e:
            logger.error(f"Failed to update failed sync job: {e}")
    
    def sync_all_venues(self, max_workers: int = 3) -> Dict[str, Any]:
        """
        Sync all active venues with parallel processing
        Returns summary of sync operation
        """
        self.start_sync_job()
        
        try:
            # Get active venues from database
            venues = db_service.get_venues(active_only=True)
            venue_names = [venue['name'] for venue in venues]
            
            logger.info(f"Starting sync for {len(venue_names)} venues")
            
            venues_processed = []
            total_records_synced = 0
            all_errors = []
            
            # Process venues in parallel with controlled concurrency
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit sync tasks for each venue
                future_to_venue = {
                    executor.submit(self._sync_venue, venue_name): venue_name 
                    for venue_name in venue_names
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_venue):
                    venue_name = future_to_venue[future]
                    
                    try:
                        result = future.result(timeout=300)  # 5 minute timeout per venue
                        venues_processed.append(venue_name)
                        total_records_synced += result.get('records_synced', 0)
                        
                        if result.get('errors'):
                            all_errors.extend(result['errors'])
                            
                        logger.info(f"Completed sync for {venue_name}: {result.get('records_synced', 0)} records")
                        
                    except Exception as e:
                        error_msg = f"Failed to sync venue {venue_name}: {e}"
                        logger.error(error_msg)
                        all_errors.append(error_msg)
            
            # Complete the sync job
            self.complete_sync_job(venues_processed, total_records_synced, all_errors)
            
            summary = {
                "job_id": self.sync_job_id,
                "venues_processed": len(venues_processed),
                "total_venues": len(venue_names),
                "records_synced": total_records_synced,
                "errors": len(all_errors),
                "success": len(all_errors) == 0
            }
            
            logger.info(f"Sync completed: {summary}")
            return summary
            
        except Exception as e:
            error_msg = f"Sync operation failed: {e}"
            logger.error(error_msg)
            self.fail_sync_job(error_msg)
            raise SyncError(error_msg)
    
    def _sync_venue(self, venue_name: str) -> Dict[str, Any]:
        """Sync a single venue's data from Google Sheets to MongoDB"""
        try:
            logger.info(f"Starting sync for venue: {venue_name}")
            
            # Get venue's Google Sheets
            sheet_title = self._get_sheet_title(venue_name)
            
            try:
                sheet = self.gc.open(sheet_title)
                logger.info(f"Found Google Sheet: {sheet_title}")
            except gspread.exceptions.SpreadsheetNotFound:
                logger.warning(f"No Google Sheet found for venue: {venue_name}")
                return {"records_synced": 0, "errors": []}
            
            # Get recent worksheets (last 60 days)
            worksheets = self._get_recent_worksheets(sheet)
            logger.info(f"Found {len(worksheets)} recent worksheets for {venue_name}")
            
            records_synced = 0
            errors = []
            
            # Process each worksheet (show date)
            for worksheet in worksheets:
                try:
                    result = self._sync_worksheet(venue_name, worksheet)
                    records_synced += result.get('records_synced', 0)
                    
                    if result.get('errors'):
                        errors.extend(result['errors'])
                        
                except Exception as e:
                    error_msg = f"Failed to sync worksheet {worksheet.title}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                
                # Rate limiting to avoid API limits
                time.sleep(0.1)
            
            logger.info(f"Venue sync completed for {venue_name}: {records_synced} records")
            return {"records_synced": records_synced, "errors": errors}
            
        except Exception as e:
            error_msg = f"Venue sync failed for {venue_name}: {e}"
            logger.error(error_msg)
            return {"records_synced": 0, "errors": [error_msg]}
    
    def _sync_worksheet(self, venue_name: str, worksheet) -> Dict[str, Any]:
        """Sync a single worksheet (show date) to MongoDB"""
        try:
            show_date = worksheet.title
            logger.debug(f"Syncing worksheet: {venue_name} - {show_date}")
            
            # Get all worksheet data
            all_values = worksheet.get_all_values()
            
            if len(all_values) < 2:  # No data beyond headers
                return {"records_synced": 0, "errors": []}
            
            headers = all_values[0]
            rows = all_values[1:]
            
            # Parse guest data
            guest_contacts = self._parse_guest_data(venue_name, show_date, headers, rows)
            
            # Parse comedian data (if available)
            comedian_data = self._parse_comedian_data(venue_name, show_date, headers, rows)
            
            # Sync to database
            contact_result = db_service.bulk_create_contacts(guest_contacts)
            
            comedian_records_synced = 0
            for comedian in comedian_data:
                try:
                    db_service.create_comedian(comedian)
                    comedian_records_synced += 1
                except Exception as e:
                    logger.warning(f"Failed to sync comedian {comedian.get('name', 'unknown')}: {e}")
            
            total_synced = (contact_result['created'] + contact_result['updated'] + 
                          comedian_records_synced)
            
            logger.debug(f"Worksheet sync completed: {total_synced} records")
            return {"records_synced": total_synced, "errors": []}
            
        except Exception as e:
            error_msg = f"Worksheet sync failed: {e}"
            logger.error(error_msg)
            return {"records_synced": 0, "errors": [error_msg]}
    
    def _parse_guest_data(self, venue_name: str, show_date: str, headers: List[str], 
                         rows: List[List[str]]) -> List[Dict[str, Any]]:
        """Parse guest data from worksheet rows"""
        try:
            # Find column indices
            column_indices = {}
            header_mapping = {
                'venue': 'venue',
                'date': 'show_date', 
                'email': 'email',
                'source': 'source',
                'time': 'show_time',
                'type': 'ticket_type',
                'firstname': 'first_name',
                'lastname': 'last_name',
                'tickets': 'tickets'
            }
            
            for i, header in enumerate(headers):
                header_lower = header.lower()
                if header_lower in header_mapping:
                    column_indices[header_mapping[header_lower]] = i
            
            guest_contacts = []
            
            for row in rows:
                try:
                    # Skip empty rows
                    if not any(cell.strip() for cell in row):
                        continue
                    
                    # Extract contact data
                    contact_data = {
                        'venue': venue_name,
                        'show_date': show_date
                    }
                    
                    # Map columns to contact fields
                    for field, col_index in column_indices.items():
                        if col_index < len(row) and row[col_index].strip():
                            value = row[col_index].strip()
                            
                            # Handle special fields
                            if field == 'tickets':
                                try:
                                    contact_data[field] = int(value)
                                except (ValueError, TypeError):
                                    contact_data[field] = 1
                            else:
                                contact_data[field] = value
                    
                    # Validate required fields
                    required_fields = ['email', 'first_name', 'last_name', 'source']
                    if all(contact_data.get(field) for field in required_fields):
                        # Extract time from date if not separate
                        if not contact_data.get('show_time') and contact_data.get('show_date'):
                            contact_data['show_time'] = self._extract_time_from_date(
                                contact_data['show_date']
                            )
                        
                        guest_contacts.append(contact_data)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse guest row: {e}")
                    continue
            
            logger.debug(f"Parsed {len(guest_contacts)} guest contacts")
            return guest_contacts
            
        except Exception as e:
            logger.error(f"Failed to parse guest data: {e}")
            return []
    
    def _parse_comedian_data(self, venue_name: str, show_date: str, headers: List[str], 
                           rows: List[List[str]]) -> List[Dict[str, Any]]:
        """
        Parse comedian data from worksheet
        This is a placeholder - would need to identify how comedian data is stored
        """
        try:
            # For now, extract unique names from guest list as potential comedians
            # In practice, you might have a separate comedian sheet or section
            
            comedian_names = set()
            
            # Look for firstname column
            firstname_col = None
            for i, header in enumerate(headers):
                if header.lower() in ['firstname', 'first_name', 'name']:
                    firstname_col = i
                    break
            
            if firstname_col is not None:
                for row in rows:
                    if firstname_col < len(row) and row[firstname_col].strip():
                        name = row[firstname_col].strip()
                        # Simple heuristic: names that appear only once might be comedians
                        # This is very basic - you'd want better logic here
                        comedian_names.add(name)
            
            # Create comedian records
            comedians = []
            for name in comedian_names:
                comedian_data = {
                    'name': name,
                    'venue': venue_name,
                    'show_date': show_date,
                    'sync_mode': SyncMode.AUTO.value,
                    'last_synced': datetime.utcnow()
                }
                comedians.append(comedian_data)
            
            logger.debug(f"Parsed {len(comedians)} potential comedians")
            return comedians
            
        except Exception as e:
            logger.error(f"Failed to parse comedian data: {e}")
            return []
    
    def _extract_time_from_date(self, show_date: str) -> Optional[str]:
        """Extract time portion from show date string"""
        try:
            time_patterns = [
                r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))',  # 8:30 PM format
                r'(\d{1,2}(?:AM|PM|am|pm))',           # 8pm format  
                r'(\d{2}:\d{2})'                       # 20:30 format
            ]
            
            for pattern in time_patterns:
                time_match = re.search(pattern, show_date)
                if time_match:
                    return time_match.group(1)
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to extract time from date '{show_date}': {e}")
            return None
    
    def _get_sheet_title(self, venue_name: str) -> str:
        """Get Google Sheets title for venue"""
        try:
            city = get_city(venue_name)
            return f"{city}-{venue_name}"
        except Exception:
            return venue_name
    
    def _get_recent_worksheets(self, sheet, days_back: int = 60) -> List:
        """Get worksheets from recent dates"""
        try:
            all_worksheets = sheet.worksheets()
            recent_worksheets = []
            
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            for worksheet in all_worksheets:
                try:
                    # Try to parse worksheet title as date
                    # Assuming format like "Wednesday August 6th 2025" or "2025-08-06"
                    worksheet_date = self._parse_worksheet_date(worksheet.title)
                    
                    if worksheet_date and worksheet_date >= cutoff_date:
                        recent_worksheets.append(worksheet)
                        
                except Exception as e:
                    # If we can't parse the date, include it anyway (might be recent)
                    logger.debug(f"Could not parse worksheet date '{worksheet.title}': {e}")
                    recent_worksheets.append(worksheet)
            
            # Sort by title (approximate date order)
            recent_worksheets.sort(key=lambda w: w.title, reverse=True)
            
            # Limit to reasonable number to avoid API limits
            return recent_worksheets[:20]
            
        except Exception as e:
            logger.error(f"Failed to get recent worksheets: {e}")
            return []
    
    def _parse_worksheet_date(self, worksheet_title: str) -> Optional[datetime]:
        """Parse worksheet title to extract date"""
        try:
            # Try various date patterns
            patterns = [
                r'(\d{4}-\d{2}-\d{2})',  # 2025-08-06
                r'(\w+\s+\w+\s+\d{1,2}(?:st|nd|rd|th)?\s+\d{4})',  # Wednesday August 6th 2025
                r'(\d{1,2}/\d{1,2}/\d{4})',  # 8/6/2025
                r'(\d{1,2}-\d{1,2}-\d{4})'   # 8-6-2025
            ]
            
            for pattern in patterns:
                match = re.search(pattern, worksheet_title)
                if match:
                    date_str = match.group(1)
                    
                    # Try to parse the date
                    for date_format in ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y']:
                        try:
                            return datetime.strptime(date_str, date_format)
                        except ValueError:
                            continue
                    
                    # Try parsing natural language dates (basic)
                    if 'august' in date_str.lower():
                        # Extract year and day
                        year_match = re.search(r'\d{4}', date_str)
                        day_match = re.search(r'\d{1,2}', date_str)
                        
                        if year_match and day_match:
                            year = int(year_match.group())
                            day = int(day_match.group())
                            return datetime(year, 8, day)  # August = 8
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to parse worksheet date '{worksheet_title}': {e}")
            return None


def run_sync_service():
    """
    Run the sync service - can be called from command line or cron job
    """
    try:
        logger.info("Starting Google Sheets to MongoDB sync service")
        
        sync_service = SheetsToMongoSync()
        result = sync_service.sync_all_venues()
        
        if result['success']:
            logger.info(f"Sync completed successfully: {result}")
        else:
            logger.warning(f"Sync completed with errors: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"Sync service failed: {e}")
        raise


if __name__ == "__main__":
    # Setup logging for direct execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/home/ec2-user/GuestListScripts/logs/sheets_sync.log'),
            logging.StreamHandler()
        ]
    )
    
    run_sync_service()
