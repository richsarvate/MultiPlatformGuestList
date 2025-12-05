#!/usr/bin/env python3
"""
Try the tickets page endpoint for each event
"""

import requests
import json

PARTNER_SESSION_COOKIE = "3FA6CE520583FEF4D4FFBD4E36458A618A3CC0D2-1794258998834-xpartnerId~15&ts~1762722998834&isInternal~false"
EVENT_UUIDS = ["jPBK0h", "42fYzd", "3oQqKt", "OqzcT1"]
EVENT_NAMES = ["Venice Townhouse", "Lost Church SF", "Blind Barber Chicago", "Rabbit Box Seattle"]

session = requests.Session()
session.cookies.set('partner-tooling-session', PARTNER_SESSION_COOKIE, domain='www.nudgetext.com', path='/')

print("\n🎫 TESTING TICKETS PAGE ENDPOINTS\n" + "="*60)

for uuid, name in zip(EVENT_UUIDS, EVENT_NAMES):
    print(f"\n📍 {name} (UUID: {uuid})")
    
    # Try the tickets page URL
    url = f"https://www.nudgetext.com/partners/events/{uuid}/tickets"
    print(f"   URL: {url}")
    
    response = session.get(url)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        # Save the HTML/data
        filename = f"tickets_page_{name.replace(' ', '_')}.html"
        with open(filename, 'w') as f:
            f.write(response.text)
        print(f"   💾 Saved to: {filename}")
        
        # Check if there's any JSON data in the response
        if 'soldTicketCount' in response.text or 'purchases' in response.text or 'orders' in response.text:
            print(f"   🎯 FOUND TICKET DATA IN PAGE!")
            
    # Also try an API version
    api_url = f"https://www.nudgetext.com/api/v2/partners/events/{uuid}/tickets"
    response2 = session.get(api_url)
    print(f"   API Status: {response2.status_code}")
    
    if response2.status_code == 200:
        try:
            data = response2.json()
            filename = f"tickets_api_{name.replace(' ', '_')}.json"
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"   ✅ API SUCCESS! Saved to: {filename}")
            print(f"   Keys: {list(data.keys() if isinstance(data, dict) else 'array')}")
        except:
            pass
