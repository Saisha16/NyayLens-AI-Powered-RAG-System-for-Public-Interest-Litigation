#!/usr/bin/env python3
"""Test local backend"""

import requests
import time

time.sleep(3)

try:
    url = "http://127.0.0.1:8001/health"
    print(f"Testing: {url}")
    
    response = requests.get(url, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
except Exception as e:
    print(f"Error: {e}")
