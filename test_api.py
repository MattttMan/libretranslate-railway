#!/usr/bin/env python3
"""
Test script for LibreTranslate Lite API
Tests both local and deployed versions
"""

import requests
import json
import time

# Configuration
LOCAL_URL = "http://localhost:8080"
RAILWAY_URL = "https://cibus-translate-production.up.railway.app"

# Test cases
TEST_CASES = [
    {
        "text": "Hello world",
        "source": "en",
        "target": "es",
        "expected": "Hola mundo"
    },
    {
        "text": "Good morning",
        "source": "en", 
        "target": "fr",
        "expected": "Bonjour"
    },
    {
        "text": "Thank you",
        "source": "en",
        "target": "de",
        "expected": "Danke"
    },
    {
        "text": "Chicken breast",
        "source": "en",
        "target": "it",
        "expected": "Petto di pollo"
    }
]

def test_translation(url, test_case):
    """Test a single translation"""
    try:
        payload = {
            "q": test_case["text"],
            "source": test_case["source"],
            "target": test_case["target"]
        }
        
        print(f"🔄 Testing: '{test_case['text']}' ({test_case['source']} → {test_case['target']})")
        
        response = requests.post(f"{url}/translate", json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            translated_text = result.get("translatedText", "")
            
            print(f"✅ Success: '{translated_text}'")
            return True, translated_text
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return False, None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection Error: {e}")
        return False, None
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return False, None

def test_health(url):
    """Test if the API is healthy"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Health Check: {result.get('message', 'OK')}")
            return True
        else:
            print(f"❌ Health Check Failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health Check Error: {e}")
        return False

def run_tests(url, name):
    """Run all tests for a given URL"""
    print(f"\n{'='*50}")
    print(f"🧪 Testing {name}")
    print(f"📍 URL: {url}")
    print(f"{'='*50}")
    
    # Test health first
    if not test_health(url):
        print(f"❌ {name} is not responding. Skipping translation tests.")
        return False
    
    print(f"\n📝 Running Translation Tests:")
    success_count = 0
    total_tests = len(TEST_CASES)
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n[{i}/{total_tests}]", end=" ")
        success, result = test_translation(url, test_case)
        if success:
            success_count += 1
        time.sleep(0.5)  # Small delay between requests
    
    print(f"\n📊 Results for {name}:")
    print(f"   ✅ Successful: {success_count}/{total_tests}")
    print(f"   ❌ Failed: {total_tests - success_count}/{total_tests}")
    print(f"   📈 Success Rate: {(success_count/total_tests)*100:.1f}%")
    
    return success_count == total_tests

def main():
    """Main test function"""
    print("🚀 LibreTranslate Lite API Test Suite")
    print("=" * 50)
    
    # Test local version
    local_success = run_tests(LOCAL_URL, "Local API")
    
    # Test Railway version
    railway_success = run_tests(RAILWAY_URL, "Railway API")
    
    # Summary
    print(f"\n{'='*50}")
    print("📋 FINAL SUMMARY")
    print(f"{'='*50}")
    print(f"🏠 Local API: {'✅ PASS' if local_success else '❌ FAIL'}")
    print(f"☁️  Railway API: {'✅ PASS' if railway_success else '❌ FAIL'}")
    
    if local_success and railway_success:
        print(f"\n🎉 All tests passed! Your LibreTranslate Lite is working perfectly!")
    elif local_success:
        print(f"\n⚠️  Local API works, but Railway deployment needs attention.")
    elif railway_success:
        print(f"\n⚠️  Railway API works, but local setup needs attention.")
    else:
        print(f"\n❌ Both APIs failed. Check your setup.")
    
    print(f"\n💡 Usage Examples:")
    print(f"   curl -X POST {LOCAL_URL}/translate \\")
    print(f"     -H 'Content-Type: application/json' \\")
    print(f"     -d '{{\"q\": \"Hello\", \"source\": \"en\", \"target\": \"es\"}}'")

if __name__ == "__main__":
    main()
