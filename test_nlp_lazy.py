#!/usr/bin/env python3
"""Test lazy-loading implementation"""

import sys
sys.path.insert(0, '.')

try:
    print("Testing lazy-loading implementation...")
    
    from backend.nlp_pipeline import extract_issue, get_nlp_model
    print("[OK] Imports successful")
    
    # Test lazy loading
    print("Testing lazy loading...")
    nlp = get_nlp_model()
    print(f"[OK] get_nlp_model() returned: {type(nlp).__name__}")
    
    # Test extract_issue
    print("\nTesting extract_issue...")
    result = extract_issue("A man stole a car from Delhi")
    print(f"[OK] extract_issue works")
    print(f"  Summary: {result.get('issue_summary', '')[:50]}...")
    print(f"  Entities: {result.get('entities', [])}")
    
    print("\n[SUCCESS] All tests passed!")
    
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
