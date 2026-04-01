#!/usr/bin/env python3
"""Test Render production API"""

import requests
import json
import sys

urls_to_test = [
    ("Health", "https://nyaylens-backend.onrender.com/health"),
    ("Generate PIL", "https://nyaylens-backend.onrender.com/generate-pil?idx=0"),
]

print("=" * 80)
print("Testing Render Production API")
print("=" * 80)

for name, url in urls_to_test:
    print(f"\n[TEST] {name}")
    print(f"URL: {url}")
    print("-" * 80)
    
    try:
        resp = requests.get(url, timeout=30)
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                print("Response (first 1500 chars):")
                print(json.dumps(data, indent=2)[:1500])
            except:
                print("Response (raw):")
                print(resp.text[:1500])
        else:
            print(f"Error Response:")
            print(resp.text[:500])
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
