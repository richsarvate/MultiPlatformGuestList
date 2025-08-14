#!/usr/bin/env python3
# Check records for Citizen with 2025-08-13 date
print("=== Searching for Citizen 2025-08-13 records ===")
records = list(collection.find(
    {"venue": "Citizen", "show_date": {"$regex": "2025-08-13"}},
    {"venue": 1, "show_date": 1, "show_datetime": 1, "date": 1, "source": 1, "first_name": 1, "last_name": 1, "transaction_id": 1}
))

print(f"Found {len(records)} records:")
for i, record in enumerate(records, 1):
    show_date = record.get('show_date')
    show_datetime = record.get('show_datetime') 
    date_field = record.get('date')
    source = record.get('source')
    name = f"{record.get('first_name')} {record.get('last_name')}"
    print(f"{i}. show_date: '{show_date}', show_datetime: '{show_datetime}', date: '{date_field}', Source: {source}, Name: {name}")script to debug MongoDB data
"""

import json
from pymongo import MongoClient
from datetime import datetime

# Load configuration
CONFIG_FILE = "config/bucketlistConfig.json"
with open(CONFIG_FILE, 'r') as f:
    mongo_config = json.load(f)
MONGO_URI = mongo_config["MONGO_URI"]

client = MongoClient(MONGO_URI)
db = client.guest_list_contacts
collection = db.contacts

# Check total count first
total_count = collection.count_documents({})
print(f"=== Total documents in guest_list_contacts.contacts: {total_count} ===")

# Check records for Citizen with 2025-08-13 date
print("\n=== Searching for Citizen 2025-08-13 records ===")
records = list(collection.find(
    {"venue": "Citizen", "date": {"$regex": "2025-08-13"}},
    {"venue": 1, "date": 1, "source": 1, "first_name": 1, "last_name": 1, "transaction_id": 1}
))

print(f"Found {len(records)} records:")
for i, record in enumerate(records, 1):
    print(f"{i}. Date: {record.get('date')}, Source: {record.get('source')}, Name: {record.get('first_name')} {record.get('last_name')}")

# Show unique date formats for Citizen
print("\n=== All Citizen records ===")
all_citizen = list(collection.find(
    {"venue": "Citizen"},
    {"venue": 1, "date": 1, "source": 1, "first_name": 1, "last_name": 1, "transaction_id": 1}
).limit(10))
print(f"Found {len(all_citizen)} Citizen records (showing first 10):")
for i, record in enumerate(all_citizen, 1):
    print(f"{i}. Date: {record.get('date')}, Source: {record.get('source')}, Name: {record.get('first_name')} {record.get('last_name')}")

# Show unique date formats
print("\n=== Unique date formats for Citizen ===")
dates = collection.distinct("date", {"venue": "Citizen"})
citizen_dates = [d for d in dates if d]
for date in sorted(citizen_dates):
    print(f"Date format: {date} (type: {type(date)})")

client.close()
