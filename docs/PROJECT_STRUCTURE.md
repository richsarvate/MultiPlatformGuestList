# 📁 CLEAN DIRECTORY STRUCTURE

## 🎯 **Organized Project Layout**

```
GuestListScripts/
├── app.py                                    # Main Flask application entry point
│
├── 🎨 frontend/                              # ALL FRONTEND FILES
│   ├── static/js/
│   │   ├── main-dashboard.js                 # Main app controller
│   │   └── modules/                          # Modular JavaScript
│   │       ├── api-client.js                 # Clean API calls
│   │       ├── chart-manager.js              # Data visualization
│   │       ├── comedian-manager.js           # Comedian UI (MongoDB only)
│   │       └── venmo-manager.js              # Venmo payments
│   └── templates/
│       └── dashboard.html                    # Clean HTML template
│
├── ⚙️ backend/                               # ALL BACKEND FILES
│   ├── routes/                               # API endpoints by feature
│   │   ├── api_routes.py                     # Health & utility endpoints
│   │   ├── venue_routes.py                   # Venue operations
│   │   ├── show_routes.py                    # Show analytics & breakdowns
│   │   └── comedian_routes.py                # Comedian management
│   ├── utils/                                # Business logic utilities
│   │   ├── analytics_utils.py                # Revenue calculations
│   │   ├── guest_utils.py                    # Guest data formatting
│   │   ├── payment_utils.py                  # Payment operations
│   │   └── [other utility files]               # Various utilities
│   └── services/                             # Core backend services
│       ├── database_service.py               # MongoDB operations
│       ├── auth.py                           # Authentication (disabled)
│       └── models.py                         # Data models
│
├── 📊 DATA INGESTION SCRIPTS (unchanged for crontab)
│   ├── getBucketlistOrders.py               # Bucketlist API harvesting
│   ├── getEventbriteOrders.py               # Eventbrite order sync
│   ├── getSquarespaceOrders.py              # Squarespace order processing
│   ├── getDoMoreFromGmail.py                # DoMORE email parsing
│   ├── getFeverFromGmail.py                 # Fever HTML email extraction
│   ├── getGoldstarFromGmail.py              # Goldstar CSV processing
│   ├── getVenmoFromGmail.py                 # Venmo payment tracking
│   ├── addContactsToMongoDB.py              # MongoDB contact insertion
│   ├── addEmailToMailerLite.py              # MailerLite API integration
│   ├── dailyMailerLiteSync.py               # Daily email marketing sync
│   ├── googleSheetsComedianIntegration.py   # Google Sheets comedian sync
│   ├── sortGoogleWorksheets.py              # Sheet organization
│   ├── hideOldGoogleSheets.py               # Sheet archiving
│   ├── comedianProfiles.py                  # Comedian profile management
│   ├── [other scripts]                      # Various utility scripts
│   └── ... (all other ingestion scripts)
│
├── 🔧 config/                                # Configuration files
│   ├── config.py                        # Python configuration constants
│   ├── bucketlistConfig.json               # Bucketlist API settings
│   ├── payment_config.json                 # Venue payment configurations
│   ├── gunicorn.conf.py                    # Production WSGI settings
│   └── nginx_*.conf                        # Nginx proxy configurations
│
├── 🚀 deployment/                            # Deployment & service files
│   ├── setup-analytics.service             # Systemd service definition
│   ├── sheets-sync.service                 # Background sync service
│   ├── wsgi.py                             # Production WSGI entry point
│   ├── start_analytics.sh                  # Service start script
│   ├── stop_analytics.sh                   # Service stop script
│   ├── restart_dashboard.sh                # Service restart script
│   └── sync_cron.sh                        # Cron job helper script
│
├── 📚 docs/                                  # Documentation
│   ├── README.md                           # Main project documentation
│   ├── README_MongoDB_Architecture.md     # Database design docs
│   ├── CLEANUP_SUMMARY.md                 # What we accomplished today
│   └── OAUTH_SETUP.md                     # Authentication setup guide
│
├── 📁 logs/                                  # Application logs
│   ├── analytics.pid                       # Process ID tracking
│   ├── auto_restart.log                    # Service restart logs
│   ├── dashboard.log                       # Dashboard application logs
│   └── ... (other log files)
│
└── 🔐 credentials/                           # Sensitive files (existing)
    ├── .env                                # Environment variables
    ├── creds.json                          # MongoDB credentials
    ├── gmailApiCreds.json                  # Gmail API credentials
    ├── gsheetcreds                         # Google Sheets credentials
    ├── PersonalAccessToken                 # GitHub token
    └── token.pickle                        # OAuth tokens
```

## ✅ **Benefits of New Structure**

### **🎯 Clear Separation of Concerns**
- **Frontend**: All UI code in one place
- **Backend**: Clean API architecture  
- **Data Ingestion**: Scripts stay where crontab expects them
- **Configuration**: All settings centralized
- **Documentation**: Easy to find and maintain

### **📈 Maintainability Improvements**
- **Modular JavaScript**: Easy to debug and extend
- **Organized Routes**: Each feature has its own API file
- **Business Logic Utilities**: Reusable functions
- **Clean Dependencies**: No more circular imports

### **🔄 Crontab Compatibility Preserved**
- All data ingestion scripts remain in root directory
- Existing cron jobs continue to work unchanged
- No need to update production schedules

### **🚀 Development Benefits**
- **Easy Navigation**: Find any file quickly
- **Logical Grouping**: Related files are together
- **Clean Imports**: Clear dependency structure
- **Future Growth**: Easy to add new features

---

**📊 Result**: From cluttered mess to professional, maintainable codebase! 🎉

## 🧹 **Recently Completed Cleanup**

## 🧹 **Recently Completed Cleanup**

### **Test File Removal & Config Organization (Just Completed)**
- ✅ **Removed 6 test scripts**: `test*.py`, `testGoogleSheetsAccess.py`, `testWorkingGoogleSheets.py`
- ✅ **Removed 3 temporary files**: `get-pip.py` (2.6MB), `cleanup_none_dates.py`, `comedianProfiles.py` (empty)
- ✅ **Removed 4 one-time setup scripts**: `dedupe_mongodb_contacts.py`, `fix_mongo_duplicates.py`, `system_setup.py`, `setup_oauth.py`
- ✅ **Moved config.py to config/ folder**: Updated 10 files with proper import paths (`import config.config as config`)
- ✅ **Total cleanup**: 13 unnecessary files removed (~2.6MB+ freed)
- ✅ **Professional directory**: Only production code remains (42 files from original 55)
