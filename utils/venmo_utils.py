"""
Venmo Utilities - Handle Venmo handle lookups and storage
"""

import logging

logger = logging.getLogger(__name__)

def find_comedian_venmo_handle(comedian_name: str, min_confidence: float = 0.8):
    """Find Venmo handle for a comedian by name"""
    try:
        # Import the existing venmo lookup function
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from venmoHandleLookup import find_venmo_handle
        
        result = find_venmo_handle(comedian_name, min_confidence=min_confidence)
        
        if result:
            logger.info(f"Found Venmo handle for {comedian_name}: @{result.get('handle', 'unknown')}")
            return result
        else:
            logger.info(f"No Venmo handle found for {comedian_name}")
            return None
            
    except Exception as e:
        logger.error(f"Error finding Venmo handle for {comedian_name}: {e}")
        return None

def save_comedian_venmo_handle(comedian_name: str, venmo_handle: str) -> bool:
    """Save Venmo handle for a comedian"""
    try:
        # Import the existing venmo storage function
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from venmoHandleLookup import save_comedian_venmo_handle as save_handle
        
        success = save_handle(comedian_name, venmo_handle)
        
        if success:
            logger.info(f"Saved Venmo handle @{venmo_handle} for {comedian_name}")
        else:
            logger.warning(f"Failed to save Venmo handle for {comedian_name}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error saving Venmo handle for {comedian_name}: {e}")
        return False
