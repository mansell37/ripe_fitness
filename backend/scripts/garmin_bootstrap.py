"""Run this ONCE on your local PC to generate Garmin auth tokens.

Usage:
    cd backend
    uv run python scripts/garmin_bootstrap.py

It will log into Garmin Connect from your trusted home IP, save the OAuth
tokens, then print a base64-encoded string to paste into Railway as the
GARMIN_TOKENS_B64 environment variable.
"""

import base64
import getpass
import sys

TOKEN_DIR = ".garmin_tokens"


def main():
    try:
        from garminconnect import Garmin
    except ImportError:
        print("ERROR: garminconnect not installed. Run: uv sync")
        sys.exit(1)

    email = input("Garmin email: ").strip()
    password = getpass.getpass("Garmin password: ")

    def prompt_mfa():
        return input("Enter the one-time code Garmin emailed you: ").strip()

    print("\nLogging into Garmin Connect...")
    try:
        client = Garmin(email, password, prompt_mfa=prompt_mfa)
        client.login()
    except Exception as e:
        print(f"\nERROR: Login failed — {e}")
        print("\nIf you see a 429 rate-limit error, wait 15–30 minutes and try again.")
        sys.exit(1)

    # Serialize tokens to a JSON string using the internal client.
    try:
        token_json = client.client.dumps()
    except Exception as e:
        print(f"\nERROR: Could not serialize tokens — {e}")
        sys.exit(1)

    # Also save locally so dev sync works without the env var.
    try:
        client.client.dump(TOKEN_DIR)
        print(f"Tokens also saved locally to ./{TOKEN_DIR}/")
    except Exception:
        pass

    encoded = base64.b64encode(token_json.encode()).decode()

    print("\n" + "=" * 60)
    print("SUCCESS! In the app, open the Goals tab and paste the string")
    print("below into the 'Garmin token' field, then Save:")
    print("=" * 60)
    print(encoded)
    print("=" * 60)
    print("\nAfter saving, hit 'Sync now' on the Progress tab.\n")


if __name__ == "__main__":
    main()
