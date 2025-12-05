# Nudge API Investigation Report
**Date:** November 9, 2025  
**Status:** In Progress

## Overview
Nudge (nudgetext.com) is a ticketing/event platform. We need to extract ticket sales data for guest list integration.

## Known Information

### Login Details
- **Login URL:** `https://www.nudgetext.com/partners/login`
- **Password/Code:** `the-setup-nudge`
- **Login Field:** Single input field that accepts a "code"

### Discovered API Endpoints
- `/api/v2/partners/c?eventUuid={uuid}` - Event/partner data (requires auth)
- `/api/v2/tickets/report` - Ticket sales report (existence unconfirmed)
- `/api/v2/events` - Events listing (requires auth)
- `/api/v2/partners/*` - Various partner endpoints (all require auth)

## Investigation Findings

### Authentication Mechanism
1. **Login Flow:** 
   - POST to `/partners/login` with `{"code": "the-setup-nudge"}` returns 200
   - However, no authentication cookies are set in the response
   - The site appears to redirect back to login page even after "successful" login

2. **Likely Architecture:**
   - Next.js application (confirmed by `X-Powered-By: Next.js` header)
   - Authentication may be **client-side only** (JavaScript-based)
   - Tokens might be stored in:
     - localStorage
     - sessionStorage  
     - Cookies set via JavaScript (not HTTP-only)
   
3. **Issue:** Python requests library cannot execute JavaScript, so we cannot:
   - Trigger client-side authentication flows
   - Access browser storage (localStorage/sessionStorage)
   - Capture JavaScript-set cookies

### Current Status
- ✅ Can POST to login endpoint (returns 200)
- ❌ Cannot maintain authenticated session
- ❌ Cannot access protected API endpoints (all return 401)
- ❌ No authentication tokens captured

## Recommended Next Steps

### Option 1: Browser Automation (Recommended)
Use Selenium or Playwright to:
1. Launch a real browser
2. Navigate to login page
3. Fill in the code and submit
4. Wait for JavaScript authentication to complete
5. Extract cookies/tokens from browser storage
6. Use those tokens for API requests

**Pros:** Can handle JavaScript-based auth, closest to real user flow  
**Cons:** Requires browser automation dependencies, slightly slower

### Option 2: Manual Token Extraction
1. Manually log in to Nudge via Chrome/Firefox
2. Open DevTools → Network tab
3. Find authenticated API requests
4. Extract the authentication header/cookie values
5. Hard-code them in the script (or store in .env)
6. Use those credentials for API requests

**Pros:** Fast to test, simple implementation  
**Cons:** Tokens may expire, manual process, not automated

### Option 3: Reverse Engineer Client-Side Auth
1. Inspect the Next.js JavaScript bundles
2. Find the authentication logic
3. Replicate it in Python
4. Generate valid tokens programmatically

**Pros:** Fully automated, no browser needed  
**Cons:** Very time-consuming, complex, may break with site updates

### Option 4: Contact Nudge for API Access
1. Reach out to Nudge support/tech team
2. Request official API documentation
3. Get proper API credentials

**Pros:** Official, supported, stable  
**Cons:** May take time, may not be available

## Immediate Action Items

### To complete investigation, you should:

1. **Manual browser inspection (Quick test):**
   ```
   - Open Chrome DevTools
   - Go to https://www.nudgetext.com/partners/login
   - Enter code: the-setup-nudge
   - Click Login
   - Go to Application → Cookies/Storage
   - Document any tokens/cookies you see
   - Go to Network tab
   - Look for API calls after login
   - Document the headers (especially Authorization or Cookie headers)
   ```

2. **Check for API calls in browser:**
   ```
   - While logged in, open DevTools → Network tab
   - Filter by "Fetch/XHR"
   - Navigate through the dashboard
   - Look for API calls to /api/v2/*
   - Document the request headers and response structure
   ```

3. **Look for event-specific data:**
   ```
   - Find where ticket sales are displayed in the UI
   - Check what API endpoint loads that data
   - Document the data structure
   ```

## Technical Details for Implementation

Once we understand the authentication mechanism, the script should:

1. **Authenticate:** Obtain valid session/token
2. **Fetch Events:** Get list of active events  
3. **Fetch Tickets:** Get ticket sales for each event
4. **Parse Data:** Extract guest information (name, email, ticket type, etc.)
5. **Transform:** Convert to standard guest data format
6. **Integrate:** Send to MongoDB and Google Sheets (like other ingestion scripts)

## Questions to Answer

- [ ] What authentication header/cookie is required for API calls?
- [ ] What is the format of authentication tokens?
- [ ] Do tokens expire? If so, how long?
- [ ] What API endpoint returns ticket sales data?
- [ ] What is the structure of the ticket sales response?
- [ ] How are events identified (UUID, ID, slug)?
- [ ] What guest information is available (name, email, phone, etc.)?

## Files Created

- `nudge_api_investigation.py` - Initial authentication testing
- `nudge_api_investigation_phase2.py` - Token extraction attempt
- This report: `NUDGE_INVESTIGATION_REPORT.md`

## Next Investigation Session

**Recommended approach:** Use browser automation (Selenium) to:
1. Log in with code
2. Extract authentication state
3. Test API endpoints with real authentication
4. Document working data flow

Would you like me to:
- [ ] Create a Selenium-based investigation script?
- [ ] Create a manual token extraction guide?
- [ ] Wait for you to provide authentication details from browser inspection?
