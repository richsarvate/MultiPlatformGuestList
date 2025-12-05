# getNudgeOrders.py - Design Document

## Overview
Fetch Nudge ticket purchases, check for duplicates in MongoDB, insert new tickets into MongoDB + Google Sheets.

## Data Flow
1. Read cookie from `secrets/nudge-session-cookie.txt`
2. Dynamically fetch all current/future ticket UUIDs via `GET /api/v2/tickets?partnerId=15`
3. For each ticket UUID:
   - POST to `/api/v2/tickets/report` with ticket UUID
   - Parse CSV response (First Name, Last Name, Email, Phone, Ticket Code, Purchase Date, Price)
   - For each purchase: check if Ticket Code exists in MongoDB, skip if duplicate, insert if new

## MongoDB Integration
- Database: `guest_list_contacts`
- Collection: **Nudge** (automatically created based on `source="Nudge"`)
- Follows standard pattern used by other platform scripts (Eventbrite, Bucketlist, Fever, DoMORE, Squarespace)
- Collection name determined by the `source` field in contact records

## Deduplication Strategy
- Pre-fetch all existing `order_id` values from the **Nudge** collection into a set
- Check `if ticket_code in existing_order_ids` before inserting
- Safe to run multiple times - only processes new tickets
- Query: `db['Nudge'].find({}, {"order_id": 1})`

## Data Transformation
Transform CSV data into format compatible with `insert_guest_data_efficient()`:
```python
{
    'venue': get_venue(location_string),       # Use existing function
    'show_date': f"{event_date} {event_time}", # Combined date/time string
    'email': email,
    'source': 'Nudge',                         # Creates "Nudge" collection in MongoDB
    'first_name': first_name,
    'last_name': last_name,
    'tickets': 1,                              # Each CSV row = 1 ticket
    'ticket_type': tag,                        # e.g., "General Admission"
    'phone': phone,
    'total_price': float(price.replace('$', '')),
    'order_id': ticket_code,                   # "Nudge1", "Nudge2" - UNIQUE ID for deduplication
    'notes': f"Promo: {promo_code}" if promo_code else None
}
```

## Reuse Existing Code
- `getVenueAndDate.py`: `get_venue()`, `get_city()`, `get_venue_filter()`, `filter_guests_by_venue()`
- `insertIntoGoogleSheet.py`: `insert_guest_data_efficient()` - handles both MongoDB + Google Sheets
- MongoDB will be saved via: `insert_guest_data_efficient()` → `save_comprehensive_data_to_mongodb()` → `batch_add_contacts_to_mongodb()`

## Command Line Flags
- `--mongo-only`: Skip Google Sheets
- `--debug-only`: Print data, don't insert
- `--venue VENUE_NAME`: Filter to specific venue

## Error Handling
- 401 response: Log "Cookie expired, refresh at nudgetext.com/partners/dashboard" and exit
- Parse errors: Log warning, skip row, continue
- API failures: Log error, continue with other tickets

## Logging
File: `logs/get_nudge_log.txt`
Key messages: "Found X tickets", "Skipping duplicate: NudgeX", "Inserted: NudgeX", "Summary: X new, Y duplicates"
