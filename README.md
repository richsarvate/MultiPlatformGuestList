# MultiPlatformGuestList

**MultiPlatformGuestList** is a Python automation suite for managing ticketing data and guest lists across multiple platforms for a nationwide live event business. It centralizes ticket orders, parses email-based sales, and updates clean, organized Google Sheets—automatically and reliably.

---

## 📌 Overview

This tool automates the full guest list workflow for comedy shows across seven U.S. cities. It connects to platforms like Eventbrite, Squarespace, Goldstar, and Fever, and scrapes email data when APIs aren't available. Output is a dynamically managed Google Sheet with checkboxes, totals, and clean formatting—ready to use at the venue.

---

## 🔑 Features

- Retrieves orders from:
  - ✅ **Eventbrite** (via API)
  - ✅ **Squarespace** (via API)
  - ✅ **BucketListers** (via cookie authentication)
  - ✅ **Goldstar**, **Fever**, **DoMORE** (via Gmail parsing)
- Consolidates guest lists into Google Sheets with:
  - Totals, checkboxes, and summaries
  - Separate sheets by city and date
  - Automatic hiding of old worksheets
- Adds ticket buyers to **MailerLite** mailing segments
- Runs hourly via **cron** on an **AWS EC2** instance

---

## 🛠️ Tech Stack

- **Python 3**
- **APIs**: Google Sheets, Gmail, Eventbrite, Squarespace, MailerLite
- **Libraries**: `requests`, `gspread`, `google-api-python-client`, `oauth2client`, `beautifulsoup4`
- **Infra**: AWS EC2, Linux cron jobs

---

## ⚙️ Setup Guide

### Requirements

Install dependencies:
```bash
pip install requests gspread google-auth-oauthlib google-auth-httplib2 google-api-python-client beautifulsoup4
```

### Configuration Steps

1. Create a `config.py` file:
```python
EVENTBRITE_ORGANIZATION_ID = "[YOUR_ORG_ID]"
EVENTBRITE_PRIVATE_TOKEN = "[YOUR_TOKEN]"
SQUARESPACE_API_KEY = "[YOUR_KEY]"
GUEST_LIST_FOLDER_ID = "[GOOGLE_DRIVE_FOLDER_ID]"
```

2. Add credentials to your working directory:
- `creds.json` — Google Service Account for Sheets/Drive
- `gmailApiCreds.json` — OAuth for Gmail access
- `token.pickle` — Gmail session token

3. Upload everything to your EC2 instance:
```
/home/ec2-user/GuestListScripts/
```

4. Add a crontab entry to run the Eventbrite sync hourly:
```bash
0 * * * * /usr/bin/python3 /home/ec2-user/GuestListScripts/getEventbriteOrders.py
```

---

## 🧪 Script Reference

| Script | Description |
|--------|-------------|
| `getEventbriteOrders.py` | Pulls Eventbrite orders |
| `getSquarespaceOrders.py` | Grabs Squarespace orders and logs to Sheets |
| `getDoMoreFromGmail.py` | Parses DoMORE confirmation emails |
| `getFeverFromGmail.py` | Extracts HTML email data from Fever |
| `getGoldstarFromGmail.py` | Processes Goldstar CSV attachments |
| `addEmailToMailerLite.py` | Adds buyers to MailerLite segments |
| `insertIntoGoogleSheet.py` | Adds and formats guest info in Sheets |
| `hideOldGoogleSheets.py` | Hides sheets older than 1 day |
| `sortGoogleWorksheets.py` | Sorts worksheets by date |

---

## 🧠 Notes

- Logging is handled via `log.txt` (with rotation) on the EC2 instance.
- Parsing and workflow logic was prototyped using ChatGPT and refined for production.
- Future improvement ideas:
  - Event-to-ad-spend analytics integration
  - Frontend dashboard for status and triggers

---

## 👤 Author

**Richard Sarvate**  
[LinkedIn](https://www.linkedin.com/in/richardsarvate/)  
[GitHub](https://github.com/richsarvate)

---

> Built for event producers who don’t have time to manage seven spreadsheets and refresh Eventbrite all day.
