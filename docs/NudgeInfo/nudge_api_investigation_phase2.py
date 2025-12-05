#!/usr/bin/env python3
"""
Nudge API Deep Investigation - Phase 2
Extract authentication tokens and explore authenticated endpoints
"""

import requests
import json
import re
from datetime import datetime
from http.cookies import SimpleCookie

LOGIN_URL = "https://www.nudgetext.com/partners/login"
DASHBOARD_URL = "https://www.nudgetext.com/partners/dashboard"
API_BASE = "https://www.nudgetext.com/api/v2"
PASSWORD = "the-setup-nudge"

def perform_login():
    """
    Perform login and extract all authentication details
    """
    print("\n" + "="*60)
    print("PERFORMING LOGIN AND EXTRACTING AUTH TOKENS")
    print("="*60)
    
    session = requests.Session()
    
    # First, visit the login page to get initial cookies
    print("\n1. Getting initial session from login page...")
    response = session.get(LOGIN_URL)
    print(f"   Initial cookies: {dict(session.cookies)}")
    
    # Perform the login
    print("\n2. Submitting login credentials...")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Referer": LOGIN_URL,
        "Origin": "https://www.nudgetext.com"
    }
    
    login_response = session.post(
        LOGIN_URL,
        json={"code": PASSWORD},
        headers=headers,
        allow_redirects=True
    )
    
    print(f"   Login Status: {login_response.status_code}")
    print(f"   Cookies after login: {dict(session.cookies)}")
    print(f"   Response headers: {dict(login_response.headers)}")
    
    # Check if we got redirected or got a token
    if 'Set-Cookie' in login_response.headers:
        print(f"\n   Set-Cookie header: {login_response.headers['Set-Cookie']}")
    
    # Now try to access the dashboard
    print("\n3. Accessing dashboard with authenticated session...")
    dashboard_response = session.get(DASHBOARD_URL, allow_redirects=True)
    print(f"   Dashboard Status: {dashboard_response.status_code}")
    print(f"   Final URL: {dashboard_response.url}")
    print(f"   All cookies: {dict(session.cookies)}")
    
    # Extract any tokens from the dashboard HTML
    if dashboard_response.status_code == 200:
        print("\n4. Searching for API tokens in dashboard content...")
        content = dashboard_response.text
        
        # Look for common token patterns
        token_patterns = [
            (r'token["\']?\s*[:=]\s*["\']([^"\']+)["\']', 'token'),
            (r'apiKey["\']?\s*[:=]\s*["\']([^"\']+)["\']', 'apiKey'),
            (r'authorization["\']?\s*[:=]\s*["\']([^"\']+)["\']', 'authorization'),
            (r'Bearer\s+([A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.?[A-Za-z0-9\-_=]*)', 'JWT'),
            (r'"accessToken":\s*"([^"]+)"', 'accessToken'),
            (r'"sessionId":\s*"([^"]+)"', 'sessionId'),
        ]
        
        found_tokens = {}
        for pattern, name in token_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                found_tokens[name] = matches[0] if len(matches) == 1 else matches
                print(f"   Found {name}: {matches[0][:50]}...")
        
        # Look for Next.js data
        print("\n5. Searching for Next.js data...")
        nextdata_pattern = r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>'
        nextdata_matches = re.findall(nextdata_pattern, content, re.DOTALL)
        
        if nextdata_matches:
            try:
                nextdata = json.loads(nextdata_matches[0])
                print("   Found __NEXT_DATA__!")
                
                # Pretty print relevant sections
                if 'props' in nextdata:
                    print("\n   Props structure:")
                    print(f"   {json.dumps(nextdata['props'], indent=2)[:500]}...")
                    
                    # Save full Next.js data for analysis
                    with open('/home/ec2-user/GuestListScripts/docs/NudgeInfo/nextdata.json', 'w') as f:
                        json.dump(nextdata, f, indent=2)
                    print("\n   Full Next.js data saved to nextdata.json")
                
            except json.JSONDecodeError as e:
                print(f"   Error parsing Next.js data: {e}")
        
        # Look for API endpoints in the page
        print("\n6. Searching for API endpoints in dashboard...")
        api_patterns = [
            r'["\']/(api/v\d+/[^"\']+)["\']',
            r'https://www\.nudgetext\.com/(api/[^"\']+)["\']',
            r'fetch\(["\']([^"\']+api[^"\']+)["\']',
        ]
        
        found_endpoints = set()
        for pattern in api_patterns:
            matches = re.findall(pattern, content)
            found_endpoints.update(matches)
        
        if found_endpoints:
            print("   Found API endpoints:")
            for endpoint in sorted(found_endpoints)[:20]:  # Limit output
                print(f"      {endpoint}")
    
    return session, found_tokens

def test_authenticated_endpoints(session):
    """
    Test various endpoints with the authenticated session
    """
    print("\n" + "="*60)
    print("TESTING AUTHENTICATED API ENDPOINTS")
    print("="*60)
    
    # Test various partner endpoints
    endpoints_to_test = [
        ("/api/v2/partners/events", {}),
        ("/api/v2/partners/tickets", {}),
        ("/api/v2/partners/orders", {}),
        ("/api/v2/partners/sales", {}),
        ("/api/v2/partners/dashboard", {}),
        ("/api/v2/partners/c", {"eventUuid": "jPBK0h"}),
        ("/api/v2/tickets/report", {}),
        ("/api/v2/events", {}),
        ("/api/v2/orders", {}),
        ("/api/v2/partners/me", {}),
        ("/api/v2/partners/profile", {}),
    ]
    
    successful_endpoints = []
    
    for endpoint, params in endpoints_to_test:
        try:
            full_url = f"https://www.nudgetext.com{endpoint}" if endpoint.startswith('/') else endpoint
            response = session.get(full_url, params=params)
            
            status = response.status_code
            if status in [200, 201]:
                print(f"\n✓ SUCCESS: {endpoint}")
                print(f"   Status: {status}")
                print(f"   Response preview: {response.text[:200]}")
                successful_endpoints.append((endpoint, response))
                
                # Save full response
                safe_name = endpoint.replace('/', '_').replace('?', '_')
                with open(f'/home/ec2-user/GuestListScripts/docs/NudgeInfo/response_{safe_name}.json', 'w') as f:
                    try:
                        json.dump(response.json(), f, indent=2)
                    except:
                        f.write(response.text)
                
            elif status in [401, 403]:
                print(f"\n✗ AUTH REQUIRED: {endpoint} (Status: {status})")
            elif status == 404:
                pass  # Skip 404s to reduce noise
            else:
                print(f"\n? {endpoint}: Status {status}")
                
        except Exception as e:
            print(f"\n✗ ERROR {endpoint}: {str(e)[:100]}")
    
    return successful_endpoints

def main():
    print("\n" + "="*60)
    print("NUDGE API DEEP INVESTIGATION - PHASE 2")
    print(f"Time: {datetime.now()}")
    print("="*60)
    
    # Perform login and extract tokens
    session, tokens = perform_login()
    
    # Test authenticated endpoints
    successful_endpoints = test_authenticated_endpoints(session)
    
    # Summary
    print("\n" + "="*60)
    print("INVESTIGATION SUMMARY")
    print("="*60)
    
    print(f"\nAuthentication tokens found: {len(tokens)}")
    for name, value in tokens.items():
        print(f"  - {name}: {str(value)[:50]}...")
    
    print(f"\nSuccessful endpoints: {len(successful_endpoints)}")
    for endpoint, _ in successful_endpoints:
        print(f"  - {endpoint}")
    
    print("\n" + "="*60)
    print("FILES CREATED:")
    print("  - nextdata.json (if found)")
    print("  - response_*.json (for successful endpoints)")
    print("="*60)

if __name__ == "__main__":
    main()
