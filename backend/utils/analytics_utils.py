"""
Analytics Utilities - Calculate show analytics and revenue breakdowns
"""

import logging
from collections import defaultdict
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def safe_get(obj, key, default=None):
    """Safely get value from dictionary with fallback"""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default

def normalize_source_name(source):
    """Normalize source names to handle variations"""
    if not source:
        return 'Manual'
    
    source_lower = source.lower()
    if source_lower in ['ss', 'squarespace']:
        return 'Squarespace'
    elif source_lower in ['eb', 'eventbrite']:
        return 'Eventbrite'
    elif source_lower in ['bl', 'bucketlist']:
        return 'Bucketlist'
    elif source_lower == 'fever':
        return 'Fever'
    elif source_lower in ['domore', 'do more']:
        return 'DoMORE'
    else:
        return source.title()

def get_default_ticket_price(venue_name):
    """Get default ticket price based on venue"""
    venue_defaults = {
        'Palace': 35.00,
        'Church': 30.00,
        'Citizen': 15.00
    }
    
    for venue_key in venue_defaults:
        if venue_key.lower() in venue_name.lower():
            return venue_defaults[venue_key]
    
    return 25.00

def calculate_ticket_price(guest, venue):
    """Calculate the correct price for a ticket based on guest data and venue"""
    # Check source first - DoMORE tickets are always free
    source = safe_get(guest, 'source', '').lower()
    if source in ['domore', 'do more']:
        return 0.0
    
    # Get the stored price
    price = safe_get(guest, 'total_price', 0)
    tickets = safe_get(guest, 'tickets', 1)
    discount_code = safe_get(guest, 'discount_code', None)
    
    # Convert price to float safely
    try:
        price = float(price) if price else 0
    except (TypeError, ValueError):
        price = 0
    
    # Convert tickets to int safely
    try:
        tickets = int(tickets) if tickets else 1
    except (TypeError, ValueError):
        tickets = 1
    
    # Apply smart pricing logic if price is 0
    if price == 0:
        # Check if this is legitimately free
        has_discount = discount_code and discount_code.strip()
        is_intentionally_free = (
            has_discount or
            safe_get(guest, 'is_free', False) or
            safe_get(guest, 'ticket_type', '').lower() in ['free', 'comp', 'complimentary']
        )
        
        if not is_intentionally_free:
            # Apply default pricing for missing data
            default_price = get_default_ticket_price(venue)
            price = default_price * tickets
        else:
            price = 0
    
    return price

def calculate_processing_fees(guest_price, source):
    """Calculate payment processing fees for a single transaction"""
    if guest_price <= 0:
        return {'total_fee': 0.0, 'percentage_fee': 0.0, 'fixed_fee': 0.0}
    
    source_lower = source.lower() if source else ''
    
    # Fee structures by platform
    if source_lower in ['squarespace', 'ss']:
        percentage_rate = 0.029  # 2.9%
        fixed_fee = 0.30
    elif source_lower in ['eventbrite', 'eb']:
        percentage_rate = 0.037  # 3.7%
        fixed_fee = 1.79
    elif source_lower in ['bucketlist', 'bl']:
        percentage_rate = 0.25  # 25%
        fixed_fee = 0.00
    elif source_lower in ['fever']:
        percentage_rate = 0.25  # 25%
        fixed_fee = 0.00
    else:
        # DoMORE and Manual entries typically have no processing fees
        return {'total_fee': 0.0, 'percentage_fee': 0.0, 'fixed_fee': 0.0}
    
    percentage_fee = guest_price * percentage_rate
    total_fee = percentage_fee + fixed_fee
    
    return {
        'total_fee': round(total_fee, 2),
        'percentage_fee': round(percentage_fee, 2),
        'fixed_fee': fixed_fee
    }

def calculate_venue_cost(venue_name, total_revenue):
    """Calculate venue cost based on venue type"""
    venue_costs = {
        'Palace': {'type': 'percentage', 'rate': 0.30},  # 30% door split
        'Church': {'type': 'flat', 'rate': 700.00},      # $700 rental
        'Citizen': {'type': 'flat', 'rate': 0.00}        # No cost
    }
    
    for venue_key in venue_costs:
        if venue_key.lower() in venue_name.lower():
            cost_info = venue_costs[venue_key]
            if cost_info['type'] == 'percentage':
                cost = total_revenue * cost_info['rate']
                return {
                    'amount': cost,
                    'type': 'percentage',
                    'rate': cost_info['rate'] * 100,
                    'description': f"{cost_info['rate'] * 100:.0f}% door split"
                }
            else:  # flat rate
                return {
                    'amount': cost_info['rate'],
                    'type': 'flat',
                    'rate': cost_info['rate'],
                    'description': f"${cost_info['rate']:.0f} venue rental"
                }
    
    # Default case
    return {
        'amount': 0.00,
        'type': 'unknown',
        'rate': 0,
        'description': 'Venue cost not configured'
    }

def calculate_show_analytics(contacts: List[Dict], venue: str, show_date: str) -> Dict[str, Any]:
    """Calculate comprehensive show analytics from contact data"""
    
    # Initialize counters
    total_tickets = 0
    total_revenue = 0.0
    source_breakdown = defaultdict(lambda: {'tickets': 0, 'revenue': 0.0})
    processing_fees_total = 0.0
    fees_by_source = defaultdict(lambda: {'total': 0.0, 'count': 0, 'percentage': 0.0, 'fixed': 0.0})
    
    # Process each contact
    for contact in contacts:
        # Calculate ticket price
        price = calculate_ticket_price(contact, venue)
        tickets = safe_get(contact, 'tickets', 1)
        source = normalize_source_name(safe_get(contact, 'source', 'Manual'))
        
        # Convert tickets to int safely
        try:
            tickets = int(tickets) if tickets else 1
        except (TypeError, ValueError):
            tickets = 1
        
        # Update totals
        total_tickets += tickets
        total_revenue += price
        source_breakdown[source]['tickets'] += tickets
        source_breakdown[source]['revenue'] += price
        
        # Calculate processing fees
        fees = calculate_processing_fees(price, source)
        processing_fees_total += fees['total_fee']
        fees_by_source[source]['total'] += fees['total_fee']
        fees_by_source[source]['percentage'] += fees['percentage_fee']
        fees_by_source[source]['fixed'] += fees['fixed_fee']
        fees_by_source[source]['count'] += 1
    
    # Calculate venue cost and net revenue
    net_revenue_after_fees = total_revenue - processing_fees_total
    venue_cost = calculate_venue_cost(venue, net_revenue_after_fees)
    net_revenue = net_revenue_after_fees - venue_cost['amount']
    
    # Format response
    return {
        'venue': venue,
        'show_date': show_date,
        'total_tickets': total_tickets,
        'total_revenue': round(total_revenue, 2),
        'gross_revenue': round(total_revenue, 2),
        'processing_fees': round(processing_fees_total, 2),
        'venue_cost': venue_cost,
        'net_revenue': round(net_revenue, 2),
        'by_source': {k: {'revenue': round(v['revenue'], 2), 'tickets': v['tickets']} for k, v in source_breakdown.items()},  # Frontend compatibility
        'source_breakdown': {
            'by_tickets': {k: v['tickets'] for k, v in source_breakdown.items()},
            'by_revenue': {k: round(v['revenue'], 2) for k, v in source_breakdown.items()}
        },
        'revenue_breakdown': {
            'total_revenue': round(total_revenue, 2),
            'gross_revenue': round(total_revenue, 2),
            'processing_fees': round(processing_fees_total, 2),
            'source_breakdown': {k: round(v['revenue'], 2) for k, v in source_breakdown.items()}
        },
        'processing_fees': {
            'total_fees': round(processing_fees_total, 2),
            'fees_by_source': {k: {
                'total': round(v['total'], 2),
                'count': v['count'],
                'percentage': round(v['percentage'], 2),
                'fixed': round(v['fixed'], 2)
            } for k, v in fees_by_source.items()}
        }
    }
