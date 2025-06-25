#!/usr/bin/env python3
"""
Generate a secure API token for the Vocal Extractor API
"""

import secrets

def generate_token(length=32):
    """Generate a secure URL-safe token"""
    return secrets.token_urlsafe(length)

if __name__ == "__main__":
    token = generate_token()
    print("🔐 Generated API Token:")
    print(f"\n{token}\n")
    print("Set this as your API_TOKEN environment variable:")
    print(f"export API_TOKEN=\"{token}\"")
    print("\nOr add it to your .env file:")
    print(f"API_TOKEN={token}") 