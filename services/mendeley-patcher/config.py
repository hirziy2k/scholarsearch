"""
Configuration for Mendeley Patcher.
Register your app at: https://dev.mendeley.com/myapps.html
"""

import os
import sys

# Get base path (works for both script and PyInstaller .exe)
if getattr(sys, 'frozen', False):
    # Running as compiled .exe
    BASE_PATH = os.path.dirname(sys.executable)
else:
    # Running as Python script
    BASE_PATH = os.path.dirname(__file__)

# Mendeley OAuth 2.0 Credentials
# Set these as environment variables or fill in directly
# Note: When using OAuth PKCE flow, credentials are stored in Windows Credential Manager
MENDELEY_CLIENT_ID = os.environ.get("MENDELEY_CLIENT_ID", "24963")
MENDELEY_CLIENT_SECRET = os.environ.get("MENDELEY_CLIENT_SECRET", "")
MENDELEY_REFRESH_TOKEN = os.environ.get("MENDELEY_REFRESH_TOKEN", "")
MENDELEY_ACCESS_TOKEN = os.environ.get("MENDELEY_ACCESS_TOKEN", "")

# API Endpoints
MENDELEY_AUTH_URL = "https://api.elsevier.com/authenticate/v1/oauth"
MENDELEY_TOKEN_URL = "https://api.elsevier.com/authenticate/v1/oauth/token"
MENDELEY_API_BASE = "https://api.mendeley.com"
CROSSREF_API_BASE = "https://api.crossref.org"

# OAuth PKCE Settings
REDIRECT_URI = "http://localhost:8585/callback"
CREDENTIAL_TARGET = "MendeleyPatcher"

# Content Types
MENDELEY_DOC_CONTENT_TYPE = "application/vnd.mendeley-document.1+json"

# Rate Limiting (requests per minute)
MENDELEY_RATE_LIMIT = 100
CROSSREF_RATE_LIMIT = 50
REQUEST_DELAY_SECONDS = 0.6  # 60 seconds / 100 requests

# Database
DB_PATH = os.path.join(BASE_PATH, "patcher.db")

# Output
OUTPUT_DIR = os.path.join(BASE_PATH, "output")
REVIEW_HTML_PATH = os.path.join(OUTPUT_DIR, "review_dashboard.html")
REVIEW_CSV_PATH = os.path.join(OUTPUT_DIR, "review_grid.csv")  # Legacy support
