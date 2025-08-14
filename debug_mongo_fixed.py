#!/usr/bin/env python3
"""
Quick script to debug MongoDB data
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

# Check records for Citizen with August 13th date
print("=== Searching for Citizen August 13 records by show_date ===")
records = list(collection.find(
    {"venue": "Citizen", "show_date": {"$regex": "August 13"}},
    {"venue": 1, "show_date": 1, "show_datetime": 1, "date": 1, "source": 1, "first_name": 1, "last_name": 1, "transaction_id": 1}
))

print(f"Found {len(records)} records:")
for i, record in enumerate(records, 1):
    print(f"{i}. show_date: {record.get('show_date')}")
    print(f"   show_datetime: {record.get('show_datetime')}")
    print(f"   date: {record.get('date')}")
    print(f"   Source: {record.get('source')}, Name: {record.get('first_name')} {record.get('last_name')}")
    print()

client.close()
