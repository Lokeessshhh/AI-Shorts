"""One-Time Interactive Authentication for Instagram.
Logs in via instagrapi, handles 2FA / verification challenges,
and permanently saves the session cookie to credentials/instagram_session.json.
"""

import os
import sys
import getpass
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
from instagrapi import Client
from instagrapi.exceptions import (
    BadPassword,
    TwoFactorRequired,
    ChallengeRequired,
    PleaseWaitFewMinutes,
)


def authenticate_instagram():
    root_dir = Path(__file__).resolve().parent.parent.parent
    load_dotenv(root_dir / ".env")

    creds_dir = root_dir / "credentials"
    creds_dir.mkdir(parents=True, exist_ok=True)
    session_file = creds_dir / "instagram_session.json"

    print("\n" + "=" * 65)
    print("[INSTAGRAM] ONE-TIME AUTHENTICATION")
    print("=" * 65)

    cl = Client()
    # Configure client settings for stability
    cl.delay_range = [2, 5]

    # Check for existing session
    if session_file.exists():
        try:
            print("[Instagram] Testing existing session file...")
            cl.load_settings(session_file)
            cl.get_timeline_feed()
            print("✅ Existing Instagram session is valid! No login needed.")
            return
        except Exception:
            print("[Instagram] Saved session expired. Proceeding to fresh login...")

    username = os.getenv("INSTAGRAM_USERNAME")
    password = os.getenv("INSTAGRAM_PASSWORD")

    if not username:
        username = input("Enter your Instagram username: ").strip()
    if not password:
        password = getpass.getpass("Enter your Instagram password: ").strip()

    try:
        print(f"\n[Instagram] Logging in as @{username}...")
        cl.login(username, password)
    except TwoFactorRequired:
        code = input("Enter the 2FA 6-digit security code (from SMS or Authenticator App): ").strip()
        cl.login(username, password, verification_code=code)
    except ChallengeRequired:
        print("[Instagram] Security challenge required by Instagram.")
        cl.challenge_resolve(cl.last_json)
    except BadPassword:
        print("\n[ERROR] Incorrect password. Please verify your credentials.")
        sys.exit(1)
    except PleaseWaitFewMinutes:
        print("\n[ERROR] Instagram rate-limit: Please wait a few minutes before trying again.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Instagram login failed: {e}")
        sys.exit(1)

    # Save session settings
    cl.dump_settings(session_file)

    try:
        user_info = cl.user_info_by_username(username)
        print("\n" + "=" * 65)
        print("[SUCCESS] SUCCESSFULLY CONNECTED TO INSTAGRAM!")
        print(f"    Account:        @{user_info.username} ({user_info.full_name})")
        print(f"    Session file:   {session_file.resolve()}")
        print("    Future uploads will run automatically in the background.")
        print("=" * 65 + "\n")
    except Exception:
        print("\n[SUCCESS] Logged in and saved session to credentials/instagram_session.json!")


if __name__ == "__main__":
    authenticate_instagram()
