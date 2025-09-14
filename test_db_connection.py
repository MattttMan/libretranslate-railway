#!/usr/bin/env python3
"""
Test database connection and get food count
"""

import requests
import json

# Configuration
SUPABASE_URL = "https://jklyfpokjtqyrkkeehho.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImprbHlmcG9ranRxeXJra2VlaGhvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcxNTA3ODgsImV4cCI6MjA3MjcyNjc4OH0.s5RtIsu2FSWlt0W8spVZ-IvxdOScfzeR44IGYEoMbjk"

def test_connection():
    """Test Supabase connection"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/foods"
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
            "Content-Type": "application/json"
        }
        
        # Test with a simple query
        response = requests.get(url, headers=headers, params={"select": "id", "limit": "1"})
        
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Connection successful! Found {len(data)} foods in sample")
            
            # Get total count
            count_response = requests.get(url, headers=headers, params={"select": "id", "head": "true"})
            if count_response.status_code == 200:
                count = count_response.headers.get('content-range', '').split('/')[-1]
                print(f"📊 Total foods: {count}")
            else:
                print(f"❌ Failed to get count: {count_response.status_code}")
                
        else:
            print(f"❌ Connection failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_connection()
