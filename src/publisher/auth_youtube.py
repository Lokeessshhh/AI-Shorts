"""One-Time Interactive Authentication for YouTube Data API v3.
Launches a local webserver to handle Google OAuth 2.0 authorization,
and saves permanent credentials (including refresh token) in credentials/youtube_token.json.
"""

import os
import sys
import json
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def authenticate_youtube():
    root_dir = Path(__file__).resolve().parent.parent.parent
    creds_dir = root_dir / "credentials"
    creds_dir.mkdir(parents=True, exist_ok=True)

    client_secrets_file = creds_dir / "client_secret.json"
    token_file = creds_dir / "youtube_token.json"

    if not client_secrets_file.exists():
        print("\n" + "=" * 60)
        print("[ERROR] client_secret.json not found in credentials/")
        print(f"Expected at: {client_secrets_file.resolve()}")
        print("Please place your downloaded Google Cloud OAuth client secret JSON file there.")
        print("=" * 60 + "\n")
        sys.exit(1)

    print("\n" + "=" * 65)
    print("[YOUTUBE] OAUTH 2.0 ONE-TIME AUTHENTICATION")
    print("=" * 65)
    print("1. A browser window will now open asking you to log in.")
    print("2. Choose the Google / YouTube account you want to upload to.")
    print("3. Click 'Continue' (or 'Advanced -> Go to AI Shorts (unsafe)' if unverified).")
    print("4. Click 'Allow' to grant upload permissions.")
    print("=" * 65 + "\n")

    prompt_msg = (
        "\n" + "=" * 65 + "\n"
        "GOOGLE AUTHENTICATION LINK:\n"
        "{url}\n"
        "=" * 65 + "\n"
        "Please click or copy the link above to log in and authorize.\n"
        "Waiting for browser authorization callback...\n"
    )

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_secrets_file),
            scopes=SCOPES,
        )
        print("[YouTube] Starting local authentication server...", flush=True)
        # Run local webserver on an available port
        credentials = flow.run_local_server(
            port=0,
            authorization_prompt_message=prompt_msg,
            success_message="Authentication successful! You can close this tab and return to the application.",
            open_browser=True,
        )

        # Save credentials to token file
        with open(token_file, "w", encoding="utf-8") as f:
            f.write(credentials.to_json())

        # Test API connection and get channel name
        youtube = build("youtube", "v3", credentials=credentials)
        channels_res = youtube.channels().list(mine=True, part="snippet").execute()

        channel_title = "Unknown Channel"
        if "items" in channels_res and len(channels_res["items"]) > 0:
            channel_title = channels_res["items"][0]["snippet"]["title"]

        print("\n" + "=" * 65)
        print("[SUCCESS] SUCCESSFULLY CONNECTED TO YOUTUBE!")
        print(f"    Connected Channel: {channel_title}")
        print(f"    Token saved to:    {token_file.resolve()}")
        print("    Future uploads will authenticate automatically in the background.")
        print("=" * 65 + "\n")

    except Exception as e:
        print(f"\n[ERROR] YouTube authentication failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    authenticate_youtube()
