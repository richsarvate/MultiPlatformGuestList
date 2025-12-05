#!/usr/bin/env python3
"""
Test the /api/v2/tickets/report endpoint with ticket UUIDs
"""

import requests
import json

PARTNER_SESSION_COOKIE = "3FA6CE520583FEF4D4FFBD4E36458A618A3CC0D2-1794258998834-xpartnerId~15&ts~1762722998834&isInternal~false"

session = requests.Session()
session.cookies.set('partner-tooling-session', PARTNER_SESSION_COOKIE, domain='www.nudgetext.com', path='/')

# The endpoint you found!
url = "https://www.nudgetext.com/api/v2/tickets/report"

# Test with the Venice Townhouse ticket UUID (the one with $2,250 in sales)
ticket_uuid = "3b0xe5YsCKti"

print("\n🎯 TESTING TICKET REPORT ENDPOINT")
print("="*60)
print(f"URL: {url}")
print(f"Ticket UUID: {ticket_uuid}")
print(f"Expected: Venice Townhouse event with 90 purchases\n")

# Try POST with JSON body
payload = {"ticketUuids": [ticket_uuid]}
print(f"Payload: {json.dumps(payload, indent=2)}")

response = session.post(url, json=payload)
print(f"\nStatus: {response.status_code}")

if response.status_code == 200:
    print("✅ SUCCESS!\n")
    try:
        data = response.json()
        
        # Save the full response
        with open('ticket_report_venice.json', 'w') as f:
            json.dump(data, f, indent=2)
        print("💾 Saved full response to: ticket_report_venice.json\n")
        
        # Show structure
        print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'array'}\n")
        
        # Look for purchase/guest data
        if isinstance(data, dict):
            # Show first level keys
            for key in data.keys():
                value = data[key]
                if isinstance(value, list):
                    print(f"  {key}: array with {len(value)} items")
                    if len(value) > 0:
                        print(f"    First item keys: {list(value[0].keys()) if isinstance(value[0], dict) else type(value[0])}")
                elif isinstance(value, dict):
                    print(f"  {key}: dict with keys {list(value.keys())}")
                else:
                    print(f"  {key}: {value}")
        
        # Preview
        print(f"\nPreview (first 500 chars):")
        print(json.dumps(data, indent=2)[:500])
        print("...")
        
    except Exception as e:
        print(f"Error parsing response: {e}")
        print(f"Raw response: {response.text[:500]}")
else:
    print(f"❌ Failed with status {response.status_code}")
    print(f"Response: {response.text}")

# Now test with ALL ticket UUIDs to get all purchases
print("\n" + "="*60)
print("TESTING WITH ALL TICKET UUIDS")
print("="*60)

all_ticket_uuids = [
    "3b0xe5YsCKti",  # Venice Townhouse 11/2 - has 90 sales
    "ous2p72OFMcf",  # Venice 6/29 - no sales
    "K82WKKLKzkEy",  # Lost Church 12/6 9:30pm - no sales  
    "6fldoIG1rw58",  # Lost Church 12/6 7pm - no sales
]

payload_all = {"ticketUuids": all_ticket_uuids}
response_all = session.post(url, json=payload_all)

print(f"Status: {response_all.status_code}")
if response_all.status_code == 200:
    print("✅ SUCCESS!\n")
    try:
        data_all = response_all.json()
        with open('ticket_report_all.json', 'w') as f:
            json.dump(data_all, f, indent=2)
        print("💾 Saved to: ticket_report_all.json")
        
        # Check for purchase count
        if isinstance(data_all, dict):
            for key in data_all.keys():
                value = data_all[key]
                if isinstance(value, list):
                    print(f"  {key}: {len(value)} items")
    except:
        pass
