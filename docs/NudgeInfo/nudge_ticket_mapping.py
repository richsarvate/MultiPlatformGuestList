#!/usr/bin/env python3
"""
Map ticket UUIDs to events for Nudge ingestion
"""

import requests
import json

PARTNER_SESSION_COOKIE = "3FA6CE520583FEF4D4FFBD4E36458A618A3CC0D2-1794258998834-xpartnerId~15&ts~1762722998834&isInternal~false"

session = requests.Session()
session.cookies.set('partner-tooling-session', PARTNER_SESSION_COOKIE, domain='www.nudgetext.com', path='/')

# Get all tickets
tickets_response = session.get("https://www.nudgetext.com/api/v2/tickets?partnerId=15")
tickets_data = tickets_response.json()

print("\n📋 NUDGE TICKET MAPPING")
print("="*80)

ticket_map = {}

for ticket_obj in tickets_data.get('tickets', []):
    ticket = ticket_obj['ticket']
    event = ticket_obj['ticketedEvent']
    
    ticket_uuid = ticket['uuid']
    ticket_name = ticket['ticketName']
    event_name = event['name']
    event_uuid = event['uuid']
    location = event['locationString']
    event_date = ticket.get('eventDate', 'N/A')
    total_sales = ticket['totalSalesCents']
    sold_count = ticket['totalCount'] - ticket['remainingCount']
    
    ticket_map[ticket_uuid] = {
        'ticket_name': ticket_name,
        'event_name': event_name,
        'event_uuid': event_uuid,
        'location': location,
        'event_date': event_date,
        'total_sales_cents': total_sales,
        'sold_count': sold_count
    }
    
    print(f"\nTicket UUID: {ticket_uuid}")
    print(f"  Ticket Name: {ticket_name}")
    print(f"  Event: {event_name}")
    print(f"  Event UUID: {event_uuid}")
    print(f"  Location: {location}")
    print(f"  Date: {event_date}")
    print(f"  Sales: ${total_sales/100:.2f} ({sold_count} tickets sold)")

# Save the mapping
with open('nudge_ticket_mapping.json', 'w') as f:
    json.dump(ticket_map, f, indent=2)

print(f"\n💾 Saved ticket mapping to: nudge_ticket_mapping.json")
print(f"📊 Total tickets: {len(ticket_map)}")
