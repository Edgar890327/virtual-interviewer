#!/usr/bin/env python3
"""
Simple API test script to verify interview app functionality without requiring
audio transcription or model downloads.
"""

import requests
import json
import base64
from urllib.parse import urljoin

BASE_URL = "http://127.0.0.1:8000"
USERNAME = "interviewer"
PASSWORD = "super-segura"

# Prepare auth header
auth_header = f"Basic {base64.b64encode(f'{USERNAME}:{PASSWORD}'.encode()).decode()}"
headers = {"Authorization": auth_header, "Content-Type": "application/json"}

def test_auth():
    """Test authentication endpoint."""
    print("\n[TEST] Auth Login")
    r = requests.get(urljoin(BASE_URL, "/api/auth/login"), headers=headers)
    print(f"  Status: {r.status_code}")
    print(f"  Response: {r.json()}")
    assert r.status_code == 200, "Auth failed"
    print("  ✓ Auth works")

def test_list_sessions():
    """Test listing sessions."""
    print("\n[TEST] List Sessions")
    r = requests.get(urljoin(BASE_URL, "/api/sessions"), headers=headers)
    print(f"  Status: {r.status_code}")
    print(f"  Response: {json.dumps(r.json(), indent=2)[:200]}...")
    assert r.status_code == 200, "List sessions failed"
    print("  ✓ Sessions endpoint works")
    return r.json()

def test_start_interview():
    """Test starting an interview (will fail if model not ready, but endpoint should work)."""
    print("\n[TEST] Start Interview")
    payload = {
        "candidate_name": "Test Candidate",
        "candidate_email": "test@example.com",
        "position": "Backend Engineer",
        "language": "en",
        "duration_minutes": 10
    }
    r = requests.post(urljoin(BASE_URL, "/api/interviews/start"), json=payload, headers=headers)
    print(f"  Status: {r.status_code}")
    print(f"  Response: {json.dumps(r.json(), indent=2)[:300]}...")
    
    if r.status_code == 200:
        print("  ✓ Interview started successfully")
        return r.json()["interview_id"]
    elif "Local LLM error" in str(r.json()):
        print("  ⚠ Interview endpoint works but model not ready (expected)")
        print(f"  Error: {r.json().get('detail', 'Unknown')[:100]}...")
        return None
    else:
        print(f"  ✗ Unexpected error: {r.status_code}")
        raise Exception(f"Start interview failed: {r.text}")

def test_get_session(session_id):
    """Test retrieving session details."""
    if not session_id:
        print("\n[TEST] Get Session - Skipped (no valid session)")
        return
    
    print(f"\n[TEST] Get Session ({session_id[:8]}...)")
    r = requests.get(urljoin(BASE_URL, f"/api/sessions/{session_id}"), headers=headers)
    print(f"  Status: {r.status_code}")
    print(f"  Response: {json.dumps(r.json(), indent=2)[:300]}...")
    assert r.status_code == 200, "Get session failed"
    print("  ✓ Session details retrieved")

def test_static_files():
    """Test static file serving."""
    print("\n[TEST] Static Files")
    r = requests.get(urljoin(BASE_URL, "/"))
    print(f"  Status: {r.status_code}")
    assert r.status_code == 200, "Static files not served"
    assert "AI Interview App" in r.text, "Expected title not found"
    print("  ✓ Frontend served correctly")

def test_exports(session_id):
    """Test export endpoints."""
    if not session_id:
        print("\n[TEST] Exports - Skipped (no valid session)")
        return
    
    print(f"\n[TEST] Export JSON ({session_id[:8]}...)")
    r = requests.get(urljoin(BASE_URL, f"/api/sessions/{session_id}/export/json"), headers=headers)
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        print("  ✓ JSON export works")
    else:
        print(f"  ⚠ JSON export returned {r.status_code}")
    
    print(f"\n[TEST] Export PDF ({session_id[:8]}...)")
    r = requests.get(urljoin(BASE_URL, f"/api/sessions/{session_id}/export/pdf"), headers=headers)
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        print("  ✓ PDF export works")
    else:
        print(f"  ⚠ PDF export returned {r.status_code}")

def main():
    print("=" * 60)
    print("API Test Suite - Interview App")
    print("=" * 60)
    
    try:
        test_static_files()
        test_auth()
        sessions = test_list_sessions()
        session_id = test_start_interview()
        
        # Use first existing session if available
        if not session_id and sessions:
            session_id = sessions[0]["interview_id"]
            print(f"\nUsing existing session: {session_id[:8]}...")
        
        test_get_session(session_id)
        test_exports(session_id)
        
        print("\n" + "=" * 60)
        print("✓ Test suite completed")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
