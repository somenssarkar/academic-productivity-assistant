"""One-time script to get a Google OAuth2 refresh token for a new account.

Usage:
    python scripts/get_oauth_token.py

Opens a browser for Google login. Sign in as eduflowlearn@gmail.com.
Prints the refresh token — paste it into eduflow_agents/.env as GOOGLE_OAUTH_REFRESH_TOKEN.
"""

import os
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv("eduflow_agents/.env")

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]

client_config = {
    "installed": {
        "client_id": os.environ["GOOGLE_OAUTH_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }
}

flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
creds = flow.run_local_server(port=0)

print("\n" + "=" * 60)
print("SUCCESS — paste this into eduflow_agents/.env:")
print("=" * 60)
print(f"GOOGLE_OAUTH_REFRESH_TOKEN={creds.refresh_token}")
print("=" * 60)
