#!/usr/bin/env python3
"""
Get Nudge ticket purchases and save as CSV
"""

import requests
import csv
from io import StringIO

PARTNER_SESSION_COOKIE = "3FA6CE520583FEF4D4FFBD4E36458A618A3CC0D2-1794258998834-xpartnerId~15&ts~1762722998834&isInternal~false"

session = requests.Session()
session.cookies.set('partner-tooling-session', PARTNER_SESSION_COOKIE, domain='www.nudgetext.com', path='/')

url = "https://www.nudgetext.com/api/v2/tickets/report"

# Get all ticket UUIDs from the tickets endpoint first
tickets_response = session.get("https://www.nudgetext.com/api/v2/tickets?partnerId=15")
tickets_data = tickets_response.json()

all_ticket_uuids = []
for ticket_obj in tickets_data.get('tickets', []):
    ticket_uuid = ticket_obj['ticket']['uuid']
    ticket_name = ticket_obj['ticket']['ticketName']
    total_sales = ticket_obj['ticket']['totalSalesCents']
    
    all_ticket_uuids.append(ticket_uuid)
    print(f"  {ticket_uuid}: {ticket_name} (${total_sales/100:.2f} in sales)")

print(f"\n🎫 Found {len(all_ticket_uuids)} ticket types\n")
print(f"Fetching purchases...\n")

# Get the report for all tickets
payload = {"ticketUuids": all_ticket_uuids}
response = session.post(url, json=payload)

if response.status_code == 200:
    print(f"✅ Status: {response.status_code}\n")
    
    # The response is CSV
    csv_data = response.text
    
    # Save raw CSV
    with open('nudge_purchases_raw.csv', 'w') as f:
        f.write(csv_data)
    print("💾 Saved raw CSV to: nudge_purchases_raw.csv")
    
    # Parse and show summary
    csv_reader = csv.DictReader(StringIO(csv_data))
    purchases = list(csv_reader)
    
    print(f"\n📊 SUMMARY")
    print("="*60)
    print(f"Total purchases: {len(purchases)}")
    
    if len(purchases) > 0:
        print(f"\nCSV Columns: {', '.join(purchases[0].keys())}")
        
        print(f"\n📋 First 5 purchases:")
        for i, purchase in enumerate(purchases[:5]):
            print(f"\n{i+1}. {purchase['First Name']} {purchase['Last Name']}")
            print(f"   Email: {purchase['Email']}")
            print(f"   Phone: {purchase['Phone Number']}")
            print(f"   Code: {purchase['Ticket Code']}")
            print(f"   Date: {purchase['Purchase Date']}")
            print(f"   Price: {purchase['Purchase Price']}")
            print(f"   Tag: {purchase['Tag']}")
        
        # Group by event/tag
        from collections import Counter
        tags = Counter([p['Tag'] for p in purchases])
        
        print(f"\n📈 Purchases by Tag:")
        for tag, count in tags.most_common():
            print(f"   {tag}: {count} purchases")
    
    print("\n✅ Ready to build the ingestion script!")
    
else:
    print(f"❌ Status: {response.status_code}")
    print(response.text)
