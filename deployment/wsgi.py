#!/usr/bin/env python3
"""
WSGI entry point for Show Analytics Dashboard production deployment
"""

import sys
import os

# Add the parent directory to Python path (since we're in deployment/)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import our clean app
from app import create_app

# Create the application instance
app = create_app()

# Production configuration
app.config.update(
    DEBUG=False,
    TESTING=False
)

if __name__ == "__main__":
    app.run()
