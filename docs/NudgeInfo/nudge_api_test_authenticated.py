#!/usr/bin/env python3
"""
Nudge API Test - Using Authentication Cookie
Testing with the partner-tooling-session cookie
"""

import requests
import json
from datetime import datetime

# Authentication
PARTNER_SESSION_COOKIE = "3FA6CE520583FEF4D4FFBD4E36458A618A3CC0D2-1794258998834-xpartnerId~15&ts~1762722998834&isInternal~false"
PARTNER_ID = "15"

# URLs
DASHBOARD_URL = "https://www.nudgetext.com/partners/dashboard"
API_BASE = "https://www.nudgetext.com/api/v2"

def test_authenticated_requests():
    """Test API requests with the authentication cookie"""
    print("\n" + "="*60)
    print("TESTING NUDGE API WITH AUTHENTICATION COOKIE")
    print("="*60)
    
    session = requests.Session()
    
    # Set the authentication cookie
    session.cookies.set(
        'partner-tooling-session',
        PARTNER_SESSION_COOKIE,
        domain='www.nudgetext.com',
        path='/'
    )
    
    # Test endpoints
    endpoints_to_test = [
        # Partner-specific endpoints
        (f"{API_BASE}/partners/{PARTNER_ID}", "GET", None, "Partner details"),
        (f"{API_BASE}/partners/{PARTNER_ID}/events", "GET", None, "Partner events"),
        (f"{API_BASE}/partners/{PARTNER_ID}/tickets", "GET", None, "Partner tickets"),
        (f"{API_BASE}/partners/{PARTNER_ID}/sales", "GET", None, "Partner sales"),
        (f"{API_BASE}/partners/{PARTNER_ID}/reports", "GET", None, "Partner reports"),
        
        # Event-specific (using known event UUIDs from the data)
        (f"{API_BASE}/partners/c", "GET", {"eventUuid": "jPBK0h"}, "Event data (Venice Townhouse)"),
        (f"{API_BASE}/partners/c", "GET", {"eventUuid": "42fYzd"}, "Event data (Lost Church SF)"),
        (f"{API_BASE}/partners/c", "GET", {"eventUuid": "3oQqKt"}, "Event data (Blind Barber Chicago)"),
        (f"{API_BASE}/partners/c", "GET", {"eventUuid": "OqzcT1"}, "Event data (Rabbit Box Seattle)"),
        
        # Ticket/sales endpoints
        (f"{API_BASE}/tickets/report", "GET", None, "Tickets report"),
        (f"{API_BASE}/partners/tickets", "GET", None, "All partner tickets"),
        (f"{API_BASE}/partners/orders", "GET", None, "Partner orders"),
        
        # Try with partnerId parameter
        (f"{API_BASE}/tickets", "GET", {"partnerId": PARTNER_ID}, "Tickets by partner ID"),
        (f"{API_BASE}/orders", "GET", {"partnerId": PARTNER_ID}, "Orders by partner ID"),
    ]
    
    successful_calls = []
    
    for url, method, params, description in endpoints_to_test:
        try:
            print(f"\n📍 Testing: {description}")
            print(f"   URL: {url}")
            if params:
                print(f"   Params: {params}")
            
            if method == "GET":
                response = session.get(url, params=params)
            else:
                response = session.post(url, json=params)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ SUCCESS!")
                try:
                    data = response.json()
                    print(f"   Response preview: {json.dumps(data, indent=2)[:300]}...")
                    
                    # Save successful responses
                    filename = f"response_{description.replace(' ', '_').replace('/', '_')}.json"
                    with open(filename, 'w') as f:
                        json.dump(data, f, indent=2)
                    print(f"   💾 Saved to: {filename}")
                    
                    successful_calls.append((description, url, data))
                except:
                    print(f"   Response (text): {response.text[:200]}")
                    
            elif response.status_code == 401:
                print(f"   ❌ Unauthorized (cookie may have expired)")
            elif response.status_code == 403:
                print(f"   ❌ Forbidden")
            elif response.status_code == 404:
                print(f"   ℹ️  Endpoint not found")
            else:
                print(f"   ⚠️  Status {response.status_code}: {response.text[:100]}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}")
    
    return successful_calls

def test_rsc_dashboard():
    """Test the React Server Components dashboard endpoint"""
    print("\n" + "="*60)
    print("TESTING RSC DASHBOARD ENDPOINT")
    print("="*60)
    
    session = requests.Session()
    session.cookies.set(
        'partner-tooling-session',
        PARTNER_SESSION_COOKIE,
        domain='www.nudgetext.com',
        path='/'
    )
    
    # The RSC endpoint from your notes
    rsc_url = "https://www.nudgetext.com/partners/dashboard?_rsc=6v6c2"
    
    print(f"\n📍 Fetching RSC dashboard data...")
    try:
        response = session.get(rsc_url)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ SUCCESS!")
            content = response.text
            
            # Save the full response
            with open('rsc_dashboard_response.txt', 'w') as f:
                f.write(content)
            print(f"   💾 Full response saved to: rsc_dashboard_response.txt")
            
            # Try to extract the events JSON from the RSC response
            print("\n   🔍 Searching for event data in response...")
            
            # The data appears to be in a specific format, let's parse it
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if '"events":[' in line or 'uuid' in line:
                    print(f"   Found potential event data at line {i}")
                    print(f"   {line[:200]}...")
            
            return content
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return None

def main():
    print("\n" + "="*70)
    print("NUDGE API AUTHENTICATED TEST")
    print(f"Partner ID: {PARTNER_ID}")
    print(f"Time: {datetime.now()}")
    print("="*70)
    
    # Test API endpoints
    successful_calls = test_authenticated_requests()
    
    # Test RSC dashboard
    rsc_data = test_rsc_dashboard()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"\n✅ Successful API calls: {len(successful_calls)}")
    for desc, url, _ in successful_calls:
        print(f"   • {desc}")
    
    if successful_calls:
        print("\n📋 Next steps:")
        print("   1. Review the saved JSON files to understand data structure")
        print("   2. Identify which endpoint provides ticket sales data")
        print("   3. Document the guest data fields available")
        print("   4. Build the ingestion script based on the working endpoint")
    else:
        print("\n⚠️  No successful API calls")
        print("   The cookie may have expired. Please:")
        print("   1. Log in to Nudge again in your browser")
        print("   2. Copy the new 'partner-tooling-session' cookie value")
        print("   3. Update the PARTNER_SESSION_COOKIE in this script")

if __name__ == "__main__":
    main()
