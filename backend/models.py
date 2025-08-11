#!/usr/bin/env python3
"""
Data Models for Guest List Management System
Professional data models with proper validation and typing
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class SyncMode(Enum):
    """Synchronization modes for comedian data"""
    AUTO = "auto"
    MANUAL = "manual"


class TicketSource(Enum):
    """Ticket sources enumeration"""
    SQUARESPACE = "squarespace"
    EVENTBRITE = "eventbrite"
    BUCKETLIST = "bucketlist"
    FEVER = "fever"
    DOMORE = "domore"
    MANUAL = "manual"
    GUEST_LIST = "guest_list"
    INDUSTRY = "industry"


@dataclass
class Contact:
    """Contact data model for guest list entries"""
    venue: str
    show_date: str
    email: str
    source: str
    first_name: str
    last_name: str
    tickets: int = 1
    
    # Optional fields
    show_time: Optional[str] = None
    ticket_type: Optional[str] = "GA"
    phone: Optional[str] = None
    show_name: Optional[str] = None
    
    # Enhanced fields for ticket platforms
    discount_code: Optional[str] = None
    total_price: Optional[float] = None
    order_id: Optional[str] = None
    transaction_id: Optional[str] = None
    customer_id: Optional[str] = None
    payment_method: Optional[str] = None
    entry_code: Optional[str] = None
    notes: Optional[str] = None
    
    # System fields
    added_to_mailerlite: bool = False
    mailerlite_added_date: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        result = {}
        for key, value in self.__dict__.items():
            if value is not None:
                result[key] = value
        return result


@dataclass
class Comedian:
    """Comedian data model for payment and booking information"""
    name: str
    venue: str
    show_date: str
    
    # Payment information
    venmo_handle: Optional[str] = None
    payment_rate: Optional[float] = None
    payment_notes: Optional[str] = None
    
    # Contact information
    email: Optional[str] = None
    phone: Optional[str] = None
    
    # Show information
    show_time: Optional[str] = None
    set_length: Optional[int] = None  # minutes
    is_headliner: bool = False
    is_host: bool = False
    
    # System fields
    sync_mode: str = SyncMode.AUTO.value
    last_synced: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        result = {}
        for key, value in self.__dict__.items():
            if value is not None:
                result[key] = value
        return result


@dataclass
class Venue:
    """Venue configuration data model"""
    name: str
    city: str
    
    # Google Sheets configuration
    sheets_folder_id: Optional[str] = None
    sheets_title_format: Optional[str] = None  # e.g., "{city}-{venue}"
    
    # Payment configuration
    default_payment_rates: Dict[str, float] = field(default_factory=dict)
    
    # System fields
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        result = {}
        for key, value in self.__dict__.items():
            if value is not None:
                result[key] = value
        return result


@dataclass
class SyncJob:
    """Sync job tracking for background processes"""
    job_id: str
    job_type: str  # "sheets_to_mongo", "mailerlite_sync", etc.
    status: str  # "pending", "running", "completed", "failed"
    
    # Job details
    venues_processed: List[str] = field(default_factory=list)
    records_synced: int = 0
    errors: List[str] = field(default_factory=list)
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        result = {}
        for key, value in self.__dict__.items():
            if value is not None:
                result[key] = value
        return result


class ValidationError(Exception):
    """Custom validation error for data models"""
    pass


def validate_contact(contact_data: Dict[str, Any]) -> Contact:
    """Validate and create Contact instance from dictionary"""
    required_fields = ['venue', 'show_date', 'email', 'source', 'first_name', 'last_name']
    
    for field in required_fields:
        if not contact_data.get(field):
            raise ValidationError(f"Required field '{field}' is missing or empty")
    
    # Validate email format (basic)
    email = contact_data.get('email', '')
    if '@' not in email or '.' not in email:
        raise ValidationError(f"Invalid email format: {email}")
    
    # Validate ticket count
    tickets = contact_data.get('tickets', 1)
    try:
        tickets = int(tickets)
        if tickets < 0:
            raise ValidationError("Ticket count cannot be negative")
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid ticket count: {tickets}")
    
    return Contact(**{k: v for k, v in contact_data.items() if v is not None})


def validate_comedian(comedian_data: Dict[str, Any]) -> Comedian:
    """Validate and create Comedian instance from dictionary"""
    required_fields = ['name', 'venue', 'show_date']
    
    for field in required_fields:
        if not comedian_data.get(field):
            raise ValidationError(f"Required field '{field}' is missing or empty")
    
    # Validate sync mode
    sync_mode = comedian_data.get('sync_mode', SyncMode.AUTO.value)
    if sync_mode not in [mode.value for mode in SyncMode]:
        raise ValidationError(f"Invalid sync mode: {sync_mode}")
    
    return Comedian(**{k: v for k, v in comedian_data.items() if v is not None})
