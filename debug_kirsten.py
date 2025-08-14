#!/usr/bin/env python3
"""
Debug script to find Kirsten Wilmeth
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

# Search for Kirsten Wilmeth
print("=== Searching for Kirsten Wilmeth ===")
kirsten_records = list(collection.find(
    {"first_name": {"$regex": "Kirsten", "$options": "i"}},
    {"venue": 1, "show_date": 1, "show_datetime": 1, "source": 1, "first_name": 1, "last_name": 1, "email": 1, "order_id": 1, "transaction_id": 1, "created_at": 1}
))

print(f"Found {len(kirsten_records)} records for 'Kirsten':")
for i, record in enumerate(kirsten_records, 1):
    print(f"{i}. Name: {record.get('first_name')} {record.get('last_name')}")
    print(f"   Email: {record.get('email')}")
    print(f"   Venue: {record.get('venue')}, Date: {record.get('show_date')}")
    print(f"   Source: {record.get('source')}")
    print(f"   Order ID: {record.get('order_id')}")
    print(f"   Transaction ID: {record.get('transaction_id')}")
    print(f"   Created: {record.get('created_at')}")
    print()

# Also search by email
print("=== Searching for kirstenwilmeth@sbcglobal.net ===")
email_records = list(collection.find(
    {"email": "kirstenwilmeth@sbcglobal.net"},
    {"venue": 1, "show_date": 1, "source": 1, "first_name": 1, "last_name": 1, "email": 1, "order_id": 1, "created_at": 1}
))

print(f"Found {len(email_records)} records for this email:")
for i, record in enumerate(email_records, 1):
    print(f"{i}. Name: {record.get('first_name')} {record.get('last_name')}")
    print(f"   Venue: {record.get('venue')}, Date: {record.get('show_date')}")
    print(f"   Source: {record.get('source')}")
    print(f"   Created: {record.get('created_at')}")
    print()

# Search by order ID
print("=== Searching for order #151553847261 ===")
order_records = list(collection.find(
    {"order_id": {"$regex": "151553847261", "$options": "i"}},
    {"venue": 1, "show_date": 1, "source": 1, "first_name": 1, "last_name": 1, "email": 1, "order_id": 1, "created_at": 1}
))

print(f"Found {len(order_records)} records for this order ID:")
for i, record in enumerate(order_records, 1):
    print(f"{i}. Name: {record.get('first_name')} {record.get('last_name')}")
    print(f"   Email: {record.get('email')}")
    print(f"   Venue: {record.get('venue')}, Date: {record.get('show_date')}")
    print(f"   Source: {record.get('source')}")
    print(f"   Order ID: {record.get('order_id')}")
    print(f"   Created: {record.get('created_at')}")
    print()

client.close()
