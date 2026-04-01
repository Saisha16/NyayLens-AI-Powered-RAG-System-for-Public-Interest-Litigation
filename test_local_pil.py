#!/usr/bin/env python3
"""Test generate-pil endpoint"""

import requests
import json

try:
    url = "http://127.0.0.1:8001/generate-pil?idx=0"
    print(f"Testing: {url}\n")
    
    response = requests.get(url, timeout=30)
    print(f"Status: {response.status_code}")
    
    data = response.json()
    
    print(f"\nResponse keys: {list(data.keys())}\n")
    
    # Show each field
    for key in data:
        value = data[key]
        if isinstance(value, (list, dict)):
            print(f"{key}: {str(value)[:100]}...")
        else:
            print(f"{key}: {value}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
