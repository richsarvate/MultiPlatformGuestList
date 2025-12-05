#!/usr/bin/env python3
"""
Get ALL ticket UUIDs from ALL events across ALL metros
"""

import requests
import re
import json

COOKIE = '3FA6CE520583FEF4D4FFBD4E36458A618A3CC0D2-1794258998834-xpartnerId~15&ts~1762722998834&isInternal~false'
session = requests.Session()
session.cookies.set('partner-tooling-session', COOKIE, domain='www.nudgetext.com', path='/')

# All known event UUIDs from your browser data
events = {
    'jPBK0h': {'name': 'The Setup Speakeasy Comedy Show', 'location': 'Townhouse Venice', 'city': 'LA'},
    '42fYzd': {'name': 'The Setup Underground Comedy Show', 'location': 'The Lost Church', 'city': 'SF'},
    '3oQqKt': {'name': 'Nudge-Exclusive Comedy Show', 'location': 'Blind Barber', 'city': 'CHI'},
    'OqzcT1': {'name': 'The Setup at the Rabbit Box Seattle', 'location': 'The Rabbit Box', 'city': 'SEA'}
}

all_tickets = {}

print("\n🎫 EXTRACTING ALL TICKET UUIDS FROM ALL EVENTS")
print("="*80)

for event_uuid, event_info in events.items():
    print(f"\n📍 {event_info['name']}")
    print(f"   Location: {event_info['location']} ({event_info['city']})")
    print(f"   Event UUID: {event_uuid}")
    
    # Get the event's tickets page
    url = f'https://www.nudgetext.com/partners/events/{event_uuid}/tickets'
    response = session.get(url)
    
    if response.status_code == 200:
        html = response.text
        
        # Look for ticket data in the React Server Components payload
        # Pattern: "tickets":[{...ticket objects...}]
        tickets_pattern = r'\\"tickets\\":\[({[^\]]+})\]'
        
        # Find ticket UUIDs - they're 12 characters, mix of letters and numbers
        # Pattern: "uuid":"3b0xe5YsCKti"
        uuid_pattern = r'\\"uuid\\":\\"([a-zA-Z0-9]{12})\\"'
        ticketname_pattern = r'\\"ticketName\\":\\"([^"]+)\\"'
        
        ticket_uuids = re.findall(uuid_pattern, html)
        ticket_names = re.findall(ticketname_pattern, html)
        
        if ticket_uuids:
            print(f"   ✅ Found {len(ticket_uuids)} ticket UUID(s):")
            
            # Store tickets with their event info
            for i, uuid in enumerate(set(ticket_uuids)):
                name = ticket_names[i] if i < len(ticket_names) else "Unknown"
                print(f"      • {uuid} - {name}")
                
                all_tickets[uuid] = {
                    'event_uuid': event_uuid,
                    'event_name': event_info['name'],
                    'location': event_info['location'],
                    'city': event_info['city'],
                    'ticket_name': name
                }
        else:
            print(f"   ⚠️  No ticket UUIDs found (may be no active tickets)")
    else:
        print(f"   ❌ Error: {response.status_code}")

# Save the complete mapping
with open('all_nudge_tickets.json', 'w') as f:
    json.dump(all_tickets, f, indent=2)

print(f"\n" + "="*80)
print(f"📊 TOTAL: {len(all_tickets)} ticket UUID(s) across {len(events)} events")
print(f"💾 Saved to: all_nudge_tickets.json")

# Show summary by city
from collections import defaultdict
by_city = defaultdict(list)
for uuid, info in all_tickets.items():
    by_city[info['city']].append(uuid)

print(f"\n🌎 Tickets by Metro:")
for city, uuids in sorted(by_city.items()):
    print(f"   {city}: {len(uuids)} ticket(s)")
