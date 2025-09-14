#!/usr/bin/env python3
"""
Simple test script for LibreTranslate Lite API
"""

import requests
import json

def test_simple():
    """Simple test function"""
    print("🧪 Simple LibreTranslate Lite Test")
    print("=" * 40)
    
    # Test URLs
    urls = [
        ("Local", "http://localhost:8080"),
        ("Railway", "https://cibus-translate-production.up.railway.app")
    ]
    
    for name, url in urls:
        print(f"\n📍 Testing {name} API: {url}")
        
        # Test health
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print("✅ API is running")
                
                # Test translation
                test_data = {
                    "q": "Hello world",
                    "source": "en",
                    "target": "es"
                }
                
                response = requests.post(f"{url}/translate", json=test_data, timeout=15)
                
                if response.status_code == 200:
                    result = response.json()
                    translated = result.get("translatedText", "No translation")
                    print(f"✅ Translation works: 'Hello world' → '{translated}'")
                else:
                    print(f"❌ Translation failed: HTTP {response.status_code}")
                    
            else:
                print(f"❌ API not responding: HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            print("⏰ Request timed out")
        except requests.exceptions.ConnectionError:
            print("❌ Connection failed - API not running")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_simple()
