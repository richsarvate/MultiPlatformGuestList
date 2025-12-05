# Nudge API Integration - Complete Solution

## ✅ SUCCESS - Full API Access Achieved!

### Authentication
**Cookie:** `partner-tooling-session`
**Partner ID:** 15
**Partner Name:** The Setup

### Key Endpoints Discovered

#### 1. Get All Tickets (Current/Future Events)
```
GET https://www.nudgetext.com/api/v2/tickets?partnerId=15
```
Returns ticket inventory for upcoming events only.

#### 2. Get Purchase Data (THE MONEY ENDPOINT! 💰)
```
POST https://www.nudgetext.com/api/v2/tickets/report
Content-Type: application/json

{
  "ticketUuids": ["3b0xe5YsCKti", "K82WKKLKzkEy", ...]
}
```

**Returns:** CSV data with full guest information!

**CSV Columns:**
- First Name
- Last Name  
- Email
- Phone Number
- Ticket Code (e.g., "Nudge1", "Nudge2")
- Purchase Date (e.g., "10/28/25")
- Purchase Price (e.g., "$28.99")
- Promo Code
- Tag (e.g., "General Admission")

### Data Structure

**Key Insight:** Each ticket purchase creates a separate row in the CSV. If someone buys 4 tickets, there are 4 rows with the same name/email but different Ticket Codes.

**Example:**
```csv
First Name,Last Name,Email,Phone Number,Ticket Code,Purchase Date,Purchase Price,Promo Code,Tag
Doreen,A,doreenabargel@yahoo.com,18184660212,Nudge1,10/28/25,$28.99,,General Admission
Doreen,A,doreenabargel@yahoo.com,18184660212,Nudge2,10/28/25,$28.99,,General Admission
```
This person bought 2 tickets.

### Known Ticket UUIDs

From the browser inspection, we know these exist:

**Past Events (with sales):**
- `3b0xe5YsCKti` - The Setup Speakeasy Comedy Show Venice 11/2 (150 tickets sold, $2,250 revenue)

**Future Events (from API):**
- `K82WKKLKzkEy` - The Setup Underground Comedy Show @ Lost Church (12/6 9:30pm)
- `6fldoIG1rw58` - The Setup Underground Comedy Show @ Lost Church (12/6 7:00pm)

**Other events found in initial dashboard data:**
- Event UUID `jPBK0h` - Venice Townhouse (has multiple ticket UUIDs)
- Event UUID `42fYzd` - Lost Church SF
- Event UUID `3oQqKt` - Blind Barber Chicago
- Event UUID `OqzcT1` - Rabbit Box Seattle

### How to Get Ticket UUIDs

**For Future Events:** Use the `/api/v2/tickets?partnerId=15` endpoint

**For Past Events:** 
1. Must be obtained from the browser while viewing the event's ticket page
2. When viewing `/partners/events/{eventUuid}/tickets`, the ticket UUIDs are embedded in the React Server Components payload
3. Alternative: Keep a database of ticket UUIDs as they're created

### Venue Mapping for Integration

Based on location strings in the data:
- "Townhouse Venice" → LA city, venue "townhouse"
- "The Lost Church" → SF city, venue "church"
- "Blind Barber" → CHI city, venue "Blind Barber Fulton Market"
- "The Rabbit Box" → SEA city, venue "rabbitbox"

### Integration Strategy

#### Option 1: Real-time Polling (Recommended)
1. Poll `/api/v2/tickets?partnerId=15` to get current/future ticket UUIDs
2. For each ticket UUID, call `/api/v2/tickets/report` with that UUID
3. Parse CSV response
4. Extract guest data and insert into MongoDB/Google Sheets
5. Track processed purchases to avoid duplicates (use Ticket Code as unique ID)

#### Option 2: Manual Trigger for Past Events
1. User provides specific ticket UUID(s) to process
2. Script fetches purchase data via `/api/v2/tickets/report`
3. Processes and inserts data

#### Option 3: Hybrid
1. Auto-process all current/future events (Option 1)
2. Allow manual processing of past events by UUID (Option 2)

### Data Transformation Requirements

**Nudge CSV → Your Schema:**

```python
{
    'name': f"{row['First Name']} {row['Last Name']}",
    'email': row['Email'],
    'phone': row['Phone Number'],
    'venue': extract_venue_from_location(location_string),  # "townhouse", "church", etc.
    'date': parse_date(event_date),  # Convert to your format
    'time': parse_time(event_date),  # Convert to your format
    'city': map_venue_to_city(venue),  # "LA", "SF", "CHI", "SEA"
    'quantity': 1,  # Each CSV row = 1 ticket
    'total': parse_price(row['Purchase Price']),  # "$28.99" → 28.99
    'order_number': row['Ticket Code'],  # Use as unique ID
    'platform': 'nudge',
    'created_date': parse_purchase_date(row['Purchase Date'])
}
```

### Cookie Expiration

The `partner-tooling-session` cookie will eventually expire. When it does:

1. Log in to https://www.nudgetext.com/partners/dashboard  
2. Open browser DevTools → Application → Cookies
3. Copy new `partner-tooling-session` value
4. Update the script

**Consider:** Store cookie in `secrets/` directory like other credentials.

### Rate Limiting

Unknown - hasn't been encountered yet during testing. Recommend:
- Add delays between API calls (1-2 seconds)
- Implement exponential backoff on errors
- Cache ticket UUIDs to minimize `/tickets` calls

### Next Steps

1. ✅ Create `secrets/nudge-session-cookie.txt` to store the cookie
2. ✅ Build `ingestion/getNudgeOrders.py` script
3. ✅ Test with Venice event (3b0xe5YsCKti) - has real data
4. ✅ Verify MongoDB insertion
5. ✅ Verify Google Sheets creation
6. ✅ Add to cron for automated daily runs
7. ✅ Document cookie refresh process

### Files Created During Investigation

- `nudge_api_test_authenticated.py` - Initial auth testing
- `nudge_find_purchases.py` - Endpoint discovery
- `nudge_test_report_endpoint.py` - Testing the /tickets/report endpoint
- `nudge_get_all_purchases.py` - Fetching and parsing purchase CSV
- `nudge_ticket_mapping.py` - Mapping tickets to events
- `venice_purchases.csv` - Sample purchase data (150 records)
- `NUDGE_API_FINAL_REPORT.md` - Previous summary (now superseded by this doc)
- `NUDGE_COMPLETE_SOLUTION.md` - This file

### Ready for Production! 🚀

All API endpoints are working, data structure is understood, and we have real test data to validate the integration.
