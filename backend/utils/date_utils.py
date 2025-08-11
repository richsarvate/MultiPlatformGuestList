"""
Date Utilities - Parse and handle show dates properly
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

def parse_show_date(date_string: str) -> Optional[datetime]:
    """
    Parse show date from format like 'Wednesday May 7th 8pm' to datetime
    Assumes current year if not specified
    """
    try:
        if not date_string:
            return None
        
        # Month mapping
        month_map = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4, 
            'may': 5, 'june': 6, 'july': 7, 'august': 8, 
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        
        # Extract month and day using regex
        date_match = re.search(r'(\w+)\s+(\d+)', date_string.lower())
        time_match = re.search(r'(\d+(?:\:\d+)?)\s*(pm|am)', date_string.lower())
        
        if not date_match:
            logger.warning(f"Could not parse date from: {date_string}")
            return None
            
        month_name = date_match.group(1)
        day_num = int(date_match.group(2))
        
        if month_name not in month_map:
            logger.warning(f"Unknown month: {month_name}")
            return None
        
        # Parse time (default to 9pm if no time found)
        hour = 21  # 9pm default
        minute = 0
        
        if time_match:
            time_part = time_match.group(1)
            am_pm = time_match.group(2)
            
            if ':' in time_part:
                time_hours, time_minutes = time_part.split(':')
                hour = int(time_hours)
                minute = int(time_minutes)
            else:
                hour = int(time_part)
                minute = 0
            
            # Convert to 24-hour format
            if am_pm == 'pm' and hour != 12:
                hour += 12
            elif am_pm == 'am' and hour == 12:
                hour = 0
        
        # Use current year or guess based on context
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # If the month has passed this year, might be next year
        if month_map[month_name] < current_month - 1:  # Give some leeway
            year = current_year + 1
        else:
            year = current_year
        
        # Create datetime object
        show_datetime = datetime(year, month_map[month_name], day_num, hour, minute)
        return show_datetime
        
    except Exception as e:
        logger.error(f"Error parsing date '{date_string}': {e}")
        return None

def sort_show_dates_chronologically(show_dates, reverse: bool = True):
    """
    Sort show dates chronologically
    
    Args:
        show_dates: List of show date strings or show objects with datetime
        reverse: If True, most recent first
    
    Returns:
        List of show dates sorted chronologically
    """
    try:
        # Create list of (parsed_date, original_item) tuples
        date_tuples = []
        for item in show_dates:
            if isinstance(item, dict) and 'show_datetime' in item:
                # New format: dictionary with show_datetime field
                parsed_date = item['show_datetime']
                date_tuples.append((parsed_date, item))
            elif isinstance(item, str):
                # Legacy format: string that needs parsing
                parsed_date = parse_show_date(item)
                if parsed_date:
                    date_tuples.append((parsed_date, item))
                else:
                    # Keep unparseable dates at the end
                    date_tuples.append((datetime.min if reverse else datetime.max, item))
            else:
                logger.warning(f"Unknown show date format: {type(item)} - {item}")
                continue
        
        # Sort by parsed date
        date_tuples.sort(key=lambda x: x[0], reverse=reverse)
        
        # Return just the original items
        return [item for _, item in date_tuples]
        
    except Exception as e:
        logger.error(f"Error sorting show dates: {e}")
        return show_dates  # Return original order if sorting fails

def get_most_recent_show_date(show_dates):
    """Get the most recent show date from a list"""
    if not show_dates:
        return None
    
    sorted_dates = sort_show_dates_chronologically(show_dates, reverse=True)
    return sorted_dates[0] if sorted_dates else None

def is_show_date_recent(date_string: str, days_back: int = 30) -> bool:
    """Check if a show date is within the specified number of days"""
    try:
        parsed_date = parse_show_date(date_string)
        if not parsed_date:
            return False
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        return parsed_date >= cutoff_date
        
    except Exception as e:
        logger.error(f"Error checking if date is recent: {e}")
        return False
