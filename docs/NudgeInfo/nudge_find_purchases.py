#!/usr/bin/env python3
"""
Find the endpoint that returns actual guest purchases
"""

import requests
import json

PARTNER_SESSION_COOKIE = "3FA6CE520583FEF4D4FFBD4E36458A618A3CC0D2-1794258998834-xpartnerId~15&ts~1762722998834&isInternal~false"
PARTNER_ID = "15"
API_BASE = "https://www.nudgetext.com/api/v2"

# Known event UUIDs
EVENT_UUIDS = ["jPBK0h", "42fYzd", "3oQqKt", "OqzcT1"]
# Known ticket UUID from the tickets response
TICKET_UUID = "K82WKKLKzkEy"

session = requests.Session()
session.cookies.set('partner-tooling-session', PARTNER_SESSION_COOKIE, domain='www.nudgetext.com', path='/')

print("\n🔍 SEARCHING FOR PURCHASE/ORDER ENDPOINTS\n" + "="*60)

# Try various endpoint patterns to find purchase data
endpoints = [
    # Purchase/Order patterns
    (f"{API_BASE}/purchases", {"partnerId": PARTNER_ID}, "All purchases by partner"),
    (f"{API_BASE}/purchases", {"eventUuid": EVENT_UUIDS[0]}, "Purchases by event"),
    (f"{API_BASE}/purchases", {"ticketUuid": TICKET_UUID}, "Purchases by ticket"),
    (f"{API_BASE}/orders", {"eventUuid": EVENT_UUIDS[0]}, "Orders by event"),
    (f"{API_BASE}/sales", {"partnerId": PARTNER_ID}, "Sales by partner"),
    (f"{API_BASE}/sales", {"eventUuid": EVENT_UUIDS[0]}, "Sales by event"),
    
    # Event-specific purchase endpoints
    (f"{API_BASE}/events/{EVENT_UUIDS[0]}/purchases", None, "Event purchases (path)"),
    (f"{API_BASE}/events/{EVENT_UUIDS[0]}/orders", None, "Event orders (path)"),
    (f"{API_BASE}/events/{EVENT_UUIDS[0]}/tickets", None, "Event tickets (path)"),
    
    # Ticket-specific
    (f"{API_BASE}/tickets/{TICKET_UUID}/purchases", None, "Ticket purchases"),
    (f"{API_BASE}/tickets/{TICKET_UUID}/orders", None, "Ticket orders"),
    
    # Partner admin endpoints
    (f"{API_BASE}/partners/{PARTNER_ID}/purchases", None, "Partner purchases"),
    (f"{API_BASE}/partners/purchases", {"partnerId": PARTNER_ID}, "Partner purchases (query)"),
    (f"{API_BASE}/partners/sales", {"partnerId": PARTNER_ID}, "Partner sales"),
    
    # Guests/attendees
    (f"{API_BASE}/guests", {"eventUuid": EVENT_UUIDS[0]}, "Guests by event"),
    (f"{API_BASE}/attendees", {"eventUuid": EVENT_UUIDS[0]}, "Attendees by event"),
    (f"{API_BASE}/events/{EVENT_UUIDS[0]}/guests", None, "Event guests (path)"),
    (f"{API_BASE}/events/{EVENT_UUIDS[0]}/attendees", None, "Event attendees (path)"),
    
    # Reports
    (f"{API_BASE}/reports/sales", {"partnerId": PARTNER_ID}, "Sales report"),
    (f"{API_BASE}/reports/purchases", {"partnerId": PARTNER_ID}, "Purchases report"),
    (f"{API_BASE}/reports/tickets", {"partnerId": PARTNER_ID}, "Tickets report"),
    
    # Web tickets endpoint (from confirmation message)
    (f"{API_BASE}/webtickets", {"eventUuid": EVENT_UUIDS[0]}, "Web tickets by event"),
    (f"{API_BASE}/webtickets", {"partnerId": PARTNER_ID}, "Web tickets by partner"),
]

successful = []

for url, params, description in endpoints:
    try:
        print(f"\n📍 {description}")
        print(f"   {url}")
        if params:
            print(f"   Params: {params}")
        
        response = session.get(url, params=params)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ SUCCESS!")
            try:
                data = response.json()
                print(f"   Keys: {list(data.keys()) if isinstance(data, dict) else 'array'}")
                
                # Look for guest/purchase data
                if isinstance(data, dict):
                    if 'purchases' in data or 'orders' in data or 'guests' in data:
                        print(f"   🎯 FOUND PURCHASE DATA!")
                        filename = f"purchases_{description.replace(' ', '_').replace('/', '_')}.json"
                        with open(filename, 'w') as f:
                            json.dump(data, f, indent=2)
                        print(f"   💾 Saved to: {filename}")
                        successful.append((description, url, params))
                        
                        # Show sample of the data
                        print(f"   Preview: {json.dumps(data, indent=2)[:400]}...")
                
            except Exception as e:
                print(f"   Response (text): {response.text[:200]}")
        
        elif response.status_code == 404:
            print(f"   ℹ️  Not found")
        elif response.status_code == 401:
            print(f"   ❌ Unauthorized")
        else:
            print(f"   Status {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

print("\n" + "="*60)
print(f"✅ Found {len(successful)} endpoint(s) with purchase data:")
for desc, url, params in successful:
    print(f"   • {desc}")
    print(f"     {url}")
    if params:
        print(f"     Params: {params}")
