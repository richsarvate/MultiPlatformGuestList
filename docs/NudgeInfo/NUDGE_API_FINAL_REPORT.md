# Nudge API Investigation - Final Report

## Date: November 9, 2025

## SUCCESS: Authentication Working ✅

The `partner-tooling-session` cookie successfully authenticates API requests!

## Working Endpoints Discovered

### 1. **Partner Overview** ✅
```
GET https://www.nudgetext.com/api/v2/partners/c?eventUuid={eventUuid}
```
Returns partner summary with:
- Partner ID: 15
- Partner Name: "The Setup"
- Event Count: 11
- Sold Ticket Count: 610

### 2. **Ticket Details** ✅
```
GET https://www.nudgetext.com/api/v2/tickets?partnerId=15
```
Returns all ticket types for the partner with:
- Ticket configuration (price, service fees, dates)
- Total sales per ticket (`totalSalesCents`)
- Remaining capacity
- Event details (name, location, description)

**Example Response:**
```json
{
  "tickets": [
    {
      "ticket": {
        "uuid": "3b0xe5YsCKti",
        "ticketName": "The Setup Speakeasy Comedy Show Venice 11/2",
        "unitPriceCents": 2500,
        "serviceFeeCents": 399,
        "totalSalesCents": 225000,  // $2,250 in sales!
        "totalCount": 150,
        "remainingCount": 60,
        "eventDate": "2025-11-02T19:30:00.000-08:00"
      },
      "ticketedEvent": {
        "uuid": "jPBK0h",
        "name": "The Setup Speakeasy Comedy Show",
        "locationString": "Townhouse Venice",
        "supportEmail": "info@setupcomedy.com"
      }
    }
  ]
}
```

### 3. **Tickets Page** ✅
```
GET https://www.nudgetext.com/partners/events/{eventUuid}/tickets
```
Returns HTML page with React Server Components data embedded.

## ✅ FOUND: Purchase/Guest Data Endpoint!

**THE SOLUTION:**
```
POST https://www.nudgetext.com/api/v2/tickets/report
Content-Type: application/json

{
  "ticketUuids": ["3b0xe5YsCKti", "other_uuid", ...]
}
```

**Returns:** CSV data with guest information!

**CSV Format:**
```
First Name,Last Name,Email,Phone Number,Ticket Code,Purchase Date,Purchase Price,Promo Code,Tag
Doreen,A,doreenabargel@yahoo.com,18184660212,Nudge1,10/28/25,$28.99,,General Admission
Yene,Alamerew,yenea2020@gmail.com,19089302458,Nudge62,10/29/25,$28.99,,General Admission
```

**Example: Venice Townhouse event returned 150 purchase records with full guest details!**

## Possible Solutions

### Option 1: Browser Network Inspection (RECOMMENDED)
The dashboard likely loads purchase data via API when you click on a ticket/event.

**Steps:**
1. Open Chrome DevTools (F12) → Network tab
2. Log into https://www.nudgetext.com/partners/dashboard
3. Click on one of your events (e.g., Venice Townhouse)
4. Click on "View Purchases" or "Guest List" (if available)
5. Look for API calls in Network tab that return guest data
6. Copy the endpoint URL and parameters

### Option 2: Check for Export Functionality
Some partner dashboards have an "Export" or "Download CSV" button.

**Steps:**
1. Log into the partner dashboard
2. Navigate to an event's details or tickets page
3. Look for:
   - "Export Guest List"
   - "Download CSV"
   - "Download Attendees"
   - "Export to Excel"
4. If found, capture the Network request when clicking export

### Option 3: Contact Nudge Support
Email `info@setupcomedy.com` or Nudge support asking:
- "How do I export my guest list / purchase data?"
- "Is there an API endpoint to retrieve purchase information?"
- "Can I get a CSV of all ticket purchasers for my events?"

### Option 4: Selenium/Browser Automation
If the data is only accessible through the web interface:
- Use Selenium to automate logging in
- Navigate to the guest list/purchases page
- Scrape the table/data from the rendered page

## Current Event Inventory

| Event UUID | Event Name | Venue | Sales Status |
|------------|------------|-------|--------------|
| `jPBK0h` | The Setup Speakeasy Comedy Show | Townhouse Venice | $2,250 in sales (90 tickets sold) |
| `42fYzd` | The Setup Underground Comedy Show | The Lost Church SF | No current sales |
| `3oQqKt` | Nudge-Exclusive Comedy Show | Blind Barber Chicago | No current sales |
| `OqzcT1` | The Setup at the Rabbit Box Seattle | The Rabbit Box SEA | No current sales |

## Next Actions

**IMMEDIATE (Do this now):**
1. Log into Nudge partner dashboard with browser DevTools open
2. Navigate to the Venice Townhouse event (has 90 ticket sales)
3. Look for ANY way to view individual purchases/guests
4. Capture the API endpoint that loads that data

**THEN:**
1. Share the endpoint URL and parameters with me
2. I'll integrate it into a `getNudgeOrders.py` script
3. Test the ingestion with Venice Townhouse event (90 purchases)
4. Deploy to production

## Authentication Details

**Cookie to use:**
```
partner-tooling-session: 3FA6CE520583FEF4D4FFBD4E36458A618A3CC0D2-1794258998834-xpartnerId~15&ts~1762722998834&isInternal~false
```

**Partner ID:** 15

**Cookie may expire.** If API calls start returning 401:
1. Log in to Nudge again
2. Copy new `partner-tooling-session` cookie from browser
3. Update the script

## Files Created

- `nudge_api_test_authenticated.py` - Tests authentication with cookie
- `nudge_find_purchases.py` - Attempts to find purchase endpoints
- `nudge_tickets_pages.py` - Downloads ticket page HTML
- `response_*.json` - API response samples
- `tickets_page_*.html` - Ticket pages for each event
- `NUDGE_API_FINAL_REPORT.md` - This file

## Summary

✅ **Authentication:** Working  
✅ **Partner Data:** Accessible  
✅ **Ticket Inventory:** Accessible  
✅ **Purchase/Guest Data:** FOUND! `/api/v2/tickets/report` endpoint returns CSV with all guest details

**We're 100% there!** Ready to build the ingestion script.
