#!/usr/bin/env python3
"""
Nudge API Investigation Script
Testing authentication and API endpoints for ticket sales data
"""

import requests
import json
from datetime import datetime

# Known information
LOGIN_URL = "https://www.nudgetext.com/partners/login"
API_BASE = "https://www.nudgetext.com/api/v2"
PASSWORD = "the-setup-nudge"

# API endpoints discovered
TICKETS_REPORT_ENDPOINT = f"{API_BASE}/tickets/report"
PARTNERS_ENDPOINT = f"{API_BASE}/partners/c"

def test_login_authentication():
    """
    Test the login authentication mechanism
    Based on the form structure, it appears to use a simple code-based login
    """
    print("\n" + "="*60)
    print("TESTING NUDGE LOGIN AUTHENTICATION")
    print("="*60)
    
    session = requests.Session()
    
    # Try to understand the login flow
    print("\n1. Testing GET request to login page...")
    try:
        response = session.get(LOGIN_URL)
        print(f"   Status: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        
        # Check for any session cookies
        if session.cookies:
            print(f"   Cookies received: {dict(session.cookies)}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Try POST login with the password
    print("\n2. Testing POST login with password...")
    login_data = {
        "code": PASSWORD,
        "password": PASSWORD,
        "secretCode": PASSWORD
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "SetupComedyGuestList/1.0"
    }
    
    for key, value in login_data.items():
        print(f"\n   Trying with field '{key}'...")
        try:
            response = session.post(
                LOGIN_URL,
                json={key: value},
                headers=headers
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            
            if response.status_code == 200:
                print(f"   SUCCESS! Authentication key: {key}")
                print(f"   Session cookies: {dict(session.cookies)}")
                return session
        except Exception as e:
            print(f"   Error: {e}")
    
    # Try form-encoded POST
    print("\n3. Testing form-encoded POST...")
    try:
        response = session.post(
            LOGIN_URL,
            data={"code": PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"   Error: {e}")
    
    return session

def test_api_endpoints(session):
    """
    Test the discovered API endpoints
    """
    print("\n" + "="*60)
    print("TESTING API ENDPOINTS")
    print("="*60)
    
    # Test tickets report endpoint
    print("\n1. Testing /api/v2/tickets/report endpoint...")
    try:
        # Try GET request
        response = session.get(TICKETS_REPORT_ENDPOINT)
        print(f"   GET Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {json.dumps(response.json(), indent=2)[:500]}")
        else:
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Try with parameters
    print("\n2. Testing tickets report with date parameters...")
    params = {
        "startDate": "2025-10-01",
        "endDate": "2025-11-09"
    }
    try:
        response = session.get(TICKETS_REPORT_ENDPOINT, params=params)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {json.dumps(response.json(), indent=2)[:500]}")
        else:
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test partners endpoint
    print("\n3. Testing /api/v2/partners/c endpoint...")
    event_uuid = "jPBK0h"  # From your notes
    try:
        response = session.get(f"{PARTNERS_ENDPOINT}?eventUuid={event_uuid}")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {json.dumps(response.json(), indent=2)[:500]}")
        else:
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Try to discover more endpoints
    print("\n4. Testing potential partner dashboard endpoints...")
    potential_endpoints = [
        f"{API_BASE}/partners/events",
        f"{API_BASE}/partners/tickets",
        f"{API_BASE}/partners/orders",
        f"{API_BASE}/partners/dashboard",
        f"{API_BASE}/partners/sales",
        f"{API_BASE}/events",
        f"{API_BASE}/orders",
    ]
    
    for endpoint in potential_endpoints:
        try:
            response = session.get(endpoint)
            if response.status_code in [200, 401, 403]:  # These indicate the endpoint exists
                print(f"   {endpoint}: Status {response.status_code}")
                if response.status_code == 200:
                    print(f"      Response: {response.text[:100]}")
        except:
            pass

def test_dashboard_inspection(session):
    """
    Try to access the dashboard and inspect what data is available
    """
    print("\n" + "="*60)
    print("TESTING DASHBOARD ACCESS")
    print("="*60)
    
    dashboard_url = "https://www.nudgetext.com/partners/dashboard"
    
    print("\n1. Accessing partner dashboard...")
    try:
        response = session.get(dashboard_url)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            # Look for API calls in the response
            content = response.text
            
            # Search for API endpoints in the HTML/JS
            import re
            api_patterns = [
                r'/api/v[0-9]/[a-zA-Z0-9/_-]+',
                r'https://www\.nudgetext\.com/api/[a-zA-Z0-9/_-]+',
            ]
            
            found_endpoints = set()
            for pattern in api_patterns:
                matches = re.findall(pattern, content)
                found_endpoints.update(matches)
            
            if found_endpoints:
                print("\n   Found potential API endpoints in dashboard:")
                for endpoint in sorted(found_endpoints):
                    print(f"      {endpoint}")
    except Exception as e:
        print(f"   Error: {e}")

def main():
    print("\n" + "="*60)
    print("NUDGE API INVESTIGATION")
    print(f"Time: {datetime.now()}")
    print("="*60)
    
    # Step 1: Test authentication
    session = test_login_authentication()
    
    # Step 2: Test API endpoints
    test_api_endpoints(session)
    
    # Step 3: Inspect dashboard
    test_dashboard_inspection(session)
    
    print("\n" + "="*60)
    print("INVESTIGATION COMPLETE")
    print("="*60)
    print("\nNext steps:")
    print("1. Review the output above for successful authentication methods")
    print("2. Note any working API endpoints")
    print("3. Check if there are authentication tokens in cookies/headers")
    print("4. Document the data structure of any successful responses")

if __name__ == "__main__":
    main()
