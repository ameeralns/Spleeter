#!/usr/bin/env python3
"""
Test script for Vocal Extractor API
"""

import os
import sys
import requests
import json
from time import sleep

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
API_TOKEN = os.getenv("API_TOKEN")

# Test MP3 URL (royalty-free sample)
TEST_MP3_URL = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"

def test_health():
    """Test health endpoint"""
    print("🏥 Testing health endpoint...")
    try:
        response = requests.get(f"{API_URL}/health")
        response.raise_for_status()
        data = response.json()
        print(f"✅ Health check passed: {data}")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_auth():
    """Test authentication"""
    print("\n🔐 Testing authentication...")
    
    if not API_TOKEN:
        print("❌ No API_TOKEN found. Set it with: export API_TOKEN='your_token'")
        return False
    
    # Test with invalid token
    headers = {"Authorization": "Bearer invalid_token"}
    response = requests.post(
        f"{API_URL}/extract-vocals",
        json={"mp3_url": TEST_MP3_URL},
        headers=headers
    )
    
    if response.status_code == 401:
        print("✅ Invalid token correctly rejected")
        return True
    else:
        print(f"❌ Auth test failed: expected 401, got {response.status_code}")
        return False

def test_vocal_extraction():
    """Test vocal extraction endpoint"""
    print("\n🎵 Testing vocal extraction...")
    
    if not API_TOKEN:
        print("❌ No API_TOKEN found")
        return False
    
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print(f"   Using test MP3: {TEST_MP3_URL}")
    print("   This may take 10-30 seconds...")
    
    try:
        response = requests.post(
            f"{API_URL}/extract-vocals",
            json={"mp3_url": TEST_MP3_URL},
            headers=headers,
            timeout=60
        )
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Vocal extraction successful!")
        print(f"   Vocals URL: {data['vocals_url']}")
        print(f"   Processing time: {data['processing_time_seconds']:.2f} seconds")
        return True
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out (>60s)")
        return False
    except Exception as e:
        print(f"❌ Vocal extraction failed: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"   Response: {e.response.text}")
        return False

def main():
    print("🧪 Vocal Extractor API Test Suite")
    print("=================================")
    print(f"API URL: {API_URL}")
    print(f"API Token: {'***' + API_TOKEN[-8:] if API_TOKEN else 'NOT SET'}")
    
    # Run tests
    tests_passed = 0
    total_tests = 3
    
    if test_health():
        tests_passed += 1
    
    if test_auth():
        tests_passed += 1
    
    if test_vocal_extraction():
        tests_passed += 1
    
    # Summary
    print("\n📊 Test Summary")
    print("===============")
    print(f"Passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("✅ All tests passed! Your API is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 