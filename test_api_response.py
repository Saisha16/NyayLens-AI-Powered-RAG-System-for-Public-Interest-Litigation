#!/usr/bin/env python3
"""Test what the API returns"""

import requests
import json

try:
    url = "https://nyaylens-backend.onrender.com/generate-pil?idx=0"
    print(f"Testing: {url}")
    
    response = requests.get(url, timeout=30)
    print(f"Status: {response.status_code}")
    
    data = response.json()
    print(f"\nResponse keys: {list(data.keys())}")
    print(f"\nFull response (first 2000 chars):")
    print(json.dumps(data, indent=2)[:2000])
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
