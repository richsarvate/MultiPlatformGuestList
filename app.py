#!/usr/bin/env python3
"""
Show Analytics Dashboard - Main Application
Clean Flask app without authentication, focused on MongoDB data only
"""

from flask import Flask, render_template
import logging
import os
from datetime import datetime

# Import our route modules
from backend.routes.api_routes import api_bp
from backend.routes.venue_routes import venue_bp
from backend.routes.show_routes import show_bp
from backend.routes.comedian_routes import comedian_bp

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/ec2-user/GuestListScripts/logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure Flask app"""
    app = Flask(__name__, 
                template_folder='frontend/templates',
                static_folder='frontend/static')
    
    # Basic config - no auth needed for now
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-key-change-in-production')
    
    # Register blueprints
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(venue_bp, url_prefix='/api/venues')
    app.register_blueprint(show_bp, url_prefix='/api/shows')
    app.register_blueprint(comedian_bp)  # Already has /api/comedians prefix
    
    @app.route('/')
    def dashboard():
        """Main dashboard page - no auth required for now"""
        return render_template('dashboard.html')
    
    @app.route('/health')
    def health():
        """Simple health check"""
        return {'status': 'ok', 'timestamp': datetime.utcnow().isoformat()}
    
    return app

# Create app instance for gunicorn
app = create_app()

if __name__ == '__main__':
    app = create_app()
    
    print("🚀 Starting Show Analytics Dashboard...")
    print("📊 Dashboard available at: http://localhost:8080")
    print("🔧 No authentication required (dev mode)")
    
    app.run(host='0.0.0.0', port=8080, debug=True)
