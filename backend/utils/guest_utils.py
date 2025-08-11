"""
Guest Utilities - Format and process guest data
"""

import logging
from typing import List, Dict, Any
from .analytics_utils import safe_get, calculate_ticket_price

logger = logging.getLogger(__name__)

def format_guest_details(contacts: List[Dict], venue: str) -> List[Dict[str, Any]]:
    """Format guest details for display"""
    
    guest_details = []
    for contact in contacts:
        # Extract guest information
        first_name = safe_get(contact, 'first_name', 'Unknown')
        last_name = safe_get(contact, 'last_name', '')
        email = safe_get(contact, 'email', 'No email')
        tickets = safe_get(contact, 'tickets', 1)
        source = safe_get(contact, 'source', 'Unknown')
        ticket_type = safe_get(contact, 'ticket_type', 'GA')
        phone = safe_get(contact, 'phone', '')
        discount_code = safe_get(contact, 'discount_code', None)
        
        # Convert tickets to int safely
        try:
            tickets = int(tickets) if tickets else 1
        except (TypeError, ValueError):
            tickets = 1
        
        # Use centralized pricing logic
        total_price = calculate_ticket_price(contact, venue)
        
        guest_detail = {
            'name': f"{first_name} {last_name}".strip(),
            'email': email,
            'phone': phone,
            'tickets': tickets,
            'source': source,
            'ticket_type': ticket_type,
            'total_price': round(total_price, 2),
            'price_per_ticket': round(total_price / tickets, 2) if tickets > 0 else 0,
            'discount_code': discount_code if discount_code else 'None'
        }
        guest_details.append(guest_detail)
    
    # Sort by number of tickets (descending) then by name
    guest_details.sort(key=lambda x: (-x['tickets'], x['name']))
    
    return guest_details
