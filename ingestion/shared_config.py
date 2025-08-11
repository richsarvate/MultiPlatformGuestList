#!/usr/bin/env python3
"""
Shared Configuration Utility for Ingestion Scripts
Provides fool-proof configuration loading from environment variables
"""

import os
import sys
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

def get_project_root():
    """Get absolute path to project root directory"""
    # Get the directory containing this file (ingestion/)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to get project root
    project_root = os.path.dirname(current_dir)
    return project_root

def load_project_config():
    """
    Load configuration from .env file in project root
    Returns dict with all configuration values
    """
    try:
        project_root = get_project_root()
        env_path = os.path.join(project_root, '.env')
        
        if not os.path.exists(env_path):
            logger.error(f"Environment file not found: {env_path}")
            return None
            
        load_dotenv(env_path)
        
        config = {
            # MongoDB Configuration
            'mongo_uri': os.getenv('MONGO_URI'),
            'partner_id': os.getenv('PARTNER_ID'),
            
            # Google Configuration
            'google_service_account_file': os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE'),
            'gmail_oauth_credentials_file': os.getenv('GMAIL_OAUTH_CREDENTIALS_FILE'),
            'gmail_token_path': os.getenv('GMAIL_TOKEN_PATH'),
            'guest_list_folder_id': os.getenv('GUEST_LIST_FOLDER_ID'),
            
            # API Keys
            'eventbrite_org_id': os.getenv('EVENTBRITE_ORGANIZATION_ID'),
            'eventbrite_token': os.getenv('EVENTBRITE_PRIVATE_TOKEN'),
            'squarespace_api_key': os.getenv('SQUARESPACE_API_KEY'),
            
            # Script Configuration
            'script_interval': int(os.getenv('SCRIPT_INTERVAL', 10)),
            'gmail_script_interval_hours': int(os.getenv('GMAIL_SCRIPT_INTERVAL_HOURS', 1)),
            'gmail_script_interval_hours_test': int(os.getenv('GMAIL_SCRIPT_INTERVAL_HOURS_TEST', 70)),
            'gmail_script_interval_minutes_fever': int(os.getenv('GMAIL_SCRIPT_INTERVAL_MINUTES_FEVER', 60)),
            
            # Legacy config file path
            'bucketlist_config_file': os.getenv('BUCKETLIST_CONFIG_FILE'),
            
            # Project paths
            'project_root': project_root,
            'secrets_dir': os.path.join(project_root, 'secrets'),
            'config_dir': os.path.join(project_root, 'config'),
            'logs_dir': os.path.join(project_root, 'logs'),
        }
        
        logger.info(f"Configuration loaded successfully from {env_path}")
        return config
        
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return None

def get_mongo_config():
    """Get MongoDB configuration for backward compatibility"""
    config = load_project_config()
    if not config:
        return None
        
    return {
        'mongo_uri': config['mongo_uri'],
        'partner_id': config['partner_id'],
    }

def get_google_service_account_path():
    """Get absolute path to Google service account file"""
    config = load_project_config()
    if not config:
        return None
    return config['google_service_account_file']

def get_gmail_credentials_path():
    """Get absolute path to Gmail OAuth credentials file"""
    config = load_project_config()
    if not config:
        return None
    return config['gmail_oauth_credentials_file']

def ensure_project_root_in_path():
    """Add project root to Python path for imports"""
    project_root = get_project_root()
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        
# Auto-add project root to path when module is imported
ensure_project_root_in_path()
