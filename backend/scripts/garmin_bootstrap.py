"""Run this ONCE on your local PC to generate Garmin auth tokens.

Usage:
    cd backend
    uv run python scripts/garmin_bootstrap.py

It will log into Garmin Connect from your trusted home IP, save the OAuth
tokens locally, then print a base64-encoded string to paste into Railway as
the GARMIN_TOKENS_B64 environment variable.
"""

import base64
import getpass
import io
import os
import sys
import tarfile

TOKEN_DIR = ".garmin_tokens"


def main():
    try:
        from garminconnect import Garmin
    except ImportError:
        print("ERROR: garminconnect not installed. Run: uv sync")
        sys.exit(1)

    email = input("Garmin email: ").strip()
    password = getpass.getpass("Garmin password: ")

    print("\nLogging into Garmin Connect...")
    try:
        client = Garmin(email, password)
        client.login()
    except Exception as e:
        print(f"\nERROR: Login failed — {e}")
        print("\nGarmin may have sent a verification email. Check your inbox,")
        print("click the link to approve this login, then run this script again.")
        sys.exit(1)

    os.makedirs(TOKEN_DIR, exist_ok=True)
    client.garth.dump(TOKEN_DIR)
    print(f"\nTokens saved to ./{TOKEN_DIR}/")

    # Pack the token directory into a base64 string for Railway.
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(TOKEN_DIR)
    encoded = base64.b64encode(buf.getvalue()).decode()

    print("\n" + "=" * 60)
    print("SUCCESS! Copy the value below and add it to Railway as:")
    print("  Variable name:  GARMIN_TOKENS_B64")
    print("  Variable value: (the long string on the next line)")
    print("=" * 60)
    print(encoded)
    print("=" * 60)
    print("\nAfter adding it to Railway, redeploy responsible-cat.")
    print("The Sync Garmin button should then work.\n")


if __name__ == "__main__":
    main()
