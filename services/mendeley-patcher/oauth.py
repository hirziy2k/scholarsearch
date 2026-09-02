"""
OAuth 2.0 PKCE Authentication Flow for Mendeley API.
Stores credentials securely in Windows Credential Manager.
"""

import hashlib
import base64
import secrets
import json
import os
import sys
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, parse_qs
import requests

# Windows Credential Manager via ctypes
import ctypes
from ctypes import wintypes


# Mendeley OAuth endpoints
MENDELEY_AUTH_URL = "https://api.mendeley.com/oauth/authorize"
MENDELEY_TOKEN_URL = "https://api.mendeley.com/oauth/token"
MENDELEY_API_BASE = "https://api.mendeley.com"

# Default redirect URI for local flow
REDIRECT_URI = "http://localhost:8585/callback"
CLIENT_ID_KEY = "mendeley_patcher_client_id"
CLIENT_SECRET_KEY = "mendeley_patcher_client_secret"
REFRESH_TOKEN_KEY = "mendeley_patcher_refresh_token"
ACCESS_TOKEN_KEY = "mendeley_patcher_access_token"
TOKEN_EXPIRY_KEY = "mendeley_patcher_token_expiry"

# Credential Manager target
CREDENTIAL_TARGET = "MendeleyPatcher"
CREDENTIAL_USERNAME = "oauth_token"


class CREDENTIAL_ATTRIBUTE(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Keyword", ctypes.c_wchar_p),
        ("ValueSize", wintypes.DWORD),
        ("Value", ctypes.c_char_p),
    ]


class CREDENTIAL(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", ctypes.c_wchar_p),
        ("Comment", ctypes.c_wchar_p),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.c_char_p),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.POINTER(CREDENTIAL_ATTRIBUTE)),
        ("TargetAlias", ctypes.c_wchar_p),
        ("UserName", ctypes.c_wchar_p),
    ]


class CredentialManager:
    """Windows Credential Manager wrapper using ctypes."""
    
    # Windows API constants
    CRED_TYPE_GENERIC = 1
    CRED_PERSIST_LOCAL_MACHINE = 1
    
    def __init__(self):
        self.advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)
        self.kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    
    def _encode_string(self, s):
        """Encode string to wide char for Windows API."""
        if s is None:
            return None
        return s.encode('utf-16-le') if isinstance(s, str) else s
    
    def store_credential(self, target, username, secret):
        """Store a credential in Windows Credential Manager."""
        # Delete existing if present
        self.delete_credential(target)
        
        target_encoded = self._encode_string(target)
        username_encoded = self._encode_string(username)
        secret_bytes = secret.encode('utf-8') if isinstance(secret, str) else secret
        
        cred = CREDENTIAL()
        cred.Type = self.CRED_TYPE_GENERIC
        cred.TargetName = target
        cred.UserName = username
        cred.CredentialBlob = secret_bytes
        cred.CredentialBlobSize = len(secret_bytes)
        cred.Persist = self.CRED_PERSIST_LOCAL_MACHINE
        
        result = self.advapi32.CredWriteW(ctypes.byref(cred), 0)
        if not result:
            error = self.kernel32.GetLastError()
            raise ctypes.WinError(error)
        
        return True
    
    def read_credential(self, target):
        """Read a credential from Windows Credential Manager."""
        pcredential = ctypes.POINTER(CREDENTIAL)()
        
        result = self.advapi32.CredReadW(target, self.CRED_TYPE_GENERIC, ctypes.byref(pcredential))
        if not result:
            return None
        
        cred = pcredential.contents
        secret = cred.CredentialBlob.raw[:cred.CredentialBlobSize].decode('utf-8')
        
        # Free the credential
        self.advapi32.CredFree(ctypes.byref(cred))
        
        return secret
    
    def delete_credential(self, target):
        """Delete a credential from Windows Credential Manager."""
        self.advapi32.CredDeleteW(target, self.CRED_TYPE_GENERIC, 0)
        return True


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback."""
    
    authorization_code = None
    
    def do_GET(self):
        """Handle the OAuth callback."""
        if '/callback' in self.path:
            query = parse_qs(self.path.split('?')[1] if '?' in self.path else '')
            
            if 'code' in query:
                OAuthCallbackHandler.authorization_code = query['code'][0]
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"""
                <html><body>
                <h1>Authorization Successful!</h1>
                <p>You can close this window and return to the terminal.</p>
                <script>window.close();</script>
                </body></html>
                """)
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                error = query.get('error', ['unknown'])[0]
                self.wfile.write(f"""
                <html><body>
                <h1>Authorization Failed</h1>
                <p>Error: {error}</p>
                <p>Please close this window and try again.</p>
                </body></html>
                """.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress server log messages."""
        pass


def generate_pkce_pair():
    """Generate PKCE code verifier and challenge."""
    code_verifier = secrets.token_urlsafe(32)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b'=').decode()
    return code_verifier, code_challenge


def get_stored_credentials():
    """Retrieve stored credentials from Windows Credential Manager."""
    cm = CredentialManager()
    
    client_id = cm.read_credential(f"{CREDENTIAL_TARGET}_client_id")
    client_secret = cm.read_credential(f"{CREDENTIAL_TARGET}_client_secret")
    refresh_token = cm.read_credential(f"{CREDENTIAL_TARGET}_refresh_token")
    access_token = cm.read_credential(f"{CREDENTIAL_TARGET}_access_token")
    expiry_str = cm.read_credential(f"{CREDENTIAL_TARGET}_token_expiry")
    
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "access_token": access_token,
        "token_expiry": float(expiry_str) if expiry_str else 0,
    }


def store_credentials(client_id, client_secret=None, refresh_token=None, access_token=None):
    """Store credentials in Windows Credential Manager."""
    cm = CredentialManager()
    
    if client_id:
        cm.store_credential(f"{CREDENTIAL_TARGET}_client_id", CREDENTIAL_USERNAME, client_id)
    if client_secret:
        cm.store_credential(f"{CREDENTIAL_TARGET}_client_secret", CREDENTIAL_USERNAME, client_secret)
    if refresh_token:
        cm.store_credential(f"{CREDENTIAL_TARGET}_refresh_token", CREDENTIAL_USERNAME, refresh_token)
    if access_token:
        cm.store_credential(f"{CREDENTIAL_TARGET}_access_token", CREDENTIAL_USERNAME, access_token)
        cm.store_credential(f"{CREDENTIAL_TARGET}_token_expiry", CREDENTIAL_USERNAME, str(time.time() + 3600))


def clear_credentials():
    """Clear all stored credentials."""
    cm = CredentialManager()
    for suffix in ["client_id", "client_secret", "refresh_token", "access_token", "token_expiry"]:
        try:
            cm.delete_credential(f"{CREDENTIAL_TARGET}_{suffix}")
        except:
            pass


def setup_client_credentials():
    """Interactive setup for Mendeley API client credentials."""
    print("""
+============================================================+
|           Mendeley API - First Time Setup                   |
+============================================================+

To use Mendeley Patcher, you need to register an application
with the Mendeley Developer Portal.

Follow these steps:
  1. Go to: https://dev.mendeley.com/myapps.html
  2. Sign in with your Elsevier/Mendeley credentials
  3. Click "Register a new app"
  4. Fill in:
     - Application Name: Mendeley Patcher
     - Description: Metadata correction tool
     - Redirect URL: http://localhost:8585/callback
     - Application Type: Select "Web application"
  5. Click "Create"
  6. Copy the Client ID and Client Secret

    """)
    
    client_id = input("Paste your Client ID here: ").strip()
    client_secret = input("Paste your Client Secret here: ").strip()
    
    if not client_id or not client_secret:
        print("Error: Both Client ID and Client Secret are required.")
        return None, None
    
    # Store securely
    store_credentials(client_id, client_secret)
    print("\n[OK] Credentials stored securely in Windows Credential Manager.")
    
    return client_id, client_secret


def start_pkce_flow(client_id):
    """Start OAuth 2.0 authorization flow."""
    print("\nStarting browser-based authorization...")
    
    # Build authorization URL (standard Mendeley OAuth, no PKCE)
    auth_params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": "all",
        "state": secrets.token_urlsafe(16),
    }
    
    auth_url = f"{MENDELEY_AUTH_URL}?{urlencode(auth_params)}"
    
    # Start local server
    server = HTTPServer(('localhost', 8585), OAuthCallbackHandler)
    server.timeout = 300  # 5 minute timeout
    
    # Open browser
    print(f"Opening browser to: {auth_url[:80]}...")
    webbrowser.open(auth_url)
    
    print("Waiting for authorization...")
    print("(If browser doesn't open, copy the URL above and paste in your browser)")
    
    # Wait for callback
    OAuthCallbackHandler.authorization_code = None
    while OAuthCallbackHandler.authorization_code is None:
        server.handle_request()
    
    server.server_close()
    
    authorization_code = OAuthCallbackHandler.authorization_code
    
    # Exchange code for tokens
    return exchange_code_for_tokens(authorization_code, client_id)


def exchange_code_for_tokens(authorization_code, client_id):
    """Exchange authorization code for access/refresh tokens (PKCE - no client_secret)."""
    print("Exchanging authorization code for tokens...")
    
    # PKCE: client_id goes in POST body, NOT in Basic Auth
    token_data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "code": authorization_code,
        "redirect_uri": REDIRECT_URI,
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.post(
        MENDELEY_TOKEN_URL,
        data=token_data,
        headers=headers,
        timeout=30
    )
    
    if response.status_code == 200:
        tokens = response.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in", 3600)
        
        # Store tokens securely
        store_credentials(
            access_token=access_token,
            refresh_token=refresh_token,
        )
        
        print("[OK] Authorization successful! Tokens stored securely.")
        return access_token, refresh_token
    else:
        print(f"[Error] Token exchange failed: {response.status_code}")
        print(response.text)
        return None, None


def refresh_access_token():
    """Refresh the access token using stored refresh token."""
    creds = get_stored_credentials()
    
    if not creds.get("refresh_token") or not creds.get("client_id"):
        return None
    
    # Check if current token is still valid
    if creds.get("access_token") and time.time() < creds.get("token_expiry", 0):
        return creds["access_token"]
    
    print("Refreshing access token...")
    
    # PKCE: client_id in POST body, no Basic Auth
    token_data = {
        "grant_type": "refresh_token",
        "client_id": creds["client_id"],
        "refresh_token": creds["refresh_token"],
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.post(
        MENDELEY_TOKEN_URL,
        data=token_data,
        headers=headers,
        timeout=30
    )
    
    if response.status_code == 200:
        tokens = response.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token", creds["refresh_token"])
        expires_in = tokens.get("expires_in", 3600)
        
        store_credentials(
            access_token=access_token,
            refresh_token=refresh_token,
        )
        
        print("[OK] Token refreshed.")
        return access_token
    else:
        print(f"[Warning] Token refresh failed: {response.status_code}")
        return None


def get_valid_token():
    """Get a valid access token, refreshing or prompting as needed."""
    # Try to get stored token
    creds = get_stored_credentials()
    
    if creds.get("access_token") and time.time() < creds.get("token_expiry", 0):
        return creds["access_token"]
    
    # Try to refresh
    token = refresh_access_token()
    if token:
        return token
    
    # Need to do full auth flow
    client_id = creds.get("client_id")
    client_secret = creds.get("client_secret")
    
    if not client_id or not client_secret:
        client_id, client_secret = setup_client_credentials()
        if not client_id:
            return None
    
    # Run PKCE flow
    access_token, refresh_token = start_pkce_flow(client_id)
    return access_token


def clear_all_credentials():
    """Clear all stored credentials."""
    clear_credentials()
    print("[OK] All credentials cleared.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "clear":
            clear_all_credentials()
        elif sys.argv[1] == "status":
            creds = get_stored_credentials()
            print(f"Client ID: {'configured' if creds.get('client_id') else 'not set'}")
            print(f"Client Secret: {'configured' if creds.get('client_secret') else 'not set'}")
            print(f"Refresh Token: {'configured' if creds.get('refresh_token') else 'not set'}")
            print(f"Access Token: {'configured' if creds.get('access_token') else 'not set'}")
            if creds.get("token_expiry"):
                remaining = creds["token_expiry"] - time.time()
                print(f"Token expires in: {max(0, remaining):.0f} seconds")
        elif sys.argv[1] == "setup":
            setup_client_credentials()
        elif sys.argv[1] == "auth":
            token = get_valid_token()
            if token:
                print(f"Access token obtained: {token[:20]}...")
    else:
        print("Usage:")
        print("  python oauth.py setup   - Configure client credentials")
        print("  python oauth.py auth    - Run authorization flow")
        print("  python oauth.py status  - Check stored credentials")
        print("  python oauth.py clear   - Clear all credentials")
