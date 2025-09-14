#!/usr/bin/env python3
"""
Fixed bulk translation script that properly saves to Supabase
"""

import requests
import time
import json
from typing import List, Dict, Any

# Configuration
RAILWAY_API_URL = "https://libretranslate-railway-production-ca6b.up.railway.app"
SUPABASE_URL = "https://jklyfpokjtqyrkkeehho.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImprbHlmcG9ranRxeXJra2VlaGhvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcxNTA3ODgsImV4cCI6MjA3MjcyNjc4OH0.s5RtIsu2FSWlt0W8spVZ-IvxdOScfzeR44IGYEoMbjk"

# Languages to translate to
LANGUAGES = ['es', 'de', 'it']

def translate_text(text: str, target_lang: str) -> str:
    """Translate text using Railway API"""
    try:
        payload = {
            "q": text,
            "source": "en",
            "target": target_lang
        }
        
        response = requests.post(f"{RAILWAY_API_URL}/translate", json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            return result.get("translatedText", text)
        else:
            print(f"❌ Translation failed: HTTP {response.status_code}")
            return text
    except Exception as e:
        print(f"❌ Translation error: {e}")
        return text

def save_translation(food_id: str, locale: str, translated_name: str) -> bool:
    """Save translation to ingredient_translations table"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/ingredient_translations"
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates"
        }
        
        data = {
            "ingredient_id": food_id,
            "locale": locale,
            "name": translated_name,
            "synonyms": []
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code in [200, 201]:
            return True
        else:
            print(f"❌ Save failed: HTTP {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error saving translation: {e}")
        return False

def check_existing_translation(food_id: str, locale: str) -> bool:
    """Check if translation already exists"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/ingredient_translations"
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
            "Content-Type": "application/json"
        }
        params = {
            "ingredient_id": f"eq.{food_id}",
            "locale": f"eq.{locale}",
            "select": "id"
        }
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            return len(data) > 0
        return False
    except Exception as e:
        print(f"❌ Error checking existing translation: {e}")
        return False

def get_foods_batch(offset: int, limit: int) -> List[Dict]:
    """Get a batch of foods"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/foods"
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
            "Content-Type": "application/json"
        }
        params = {
            "select": "id,name",
            "offset": offset,
            "limit": limit,
            "order": "name"
        }
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to fetch foods: HTTP {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error fetching foods: {e}")
        return []

def get_total_food_count() -> int:
    """Get total number of foods"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/foods"
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
            "Content-Type": "application/json"
        }
        params = {
            "select": "id",
            "head": "true"
        }
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            count = response.headers.get('content-range', '').split('/')[-1]
            return int(count) if count.isdigit() else 0
        return 0
    except Exception as e:
        print(f"❌ Error getting food count: {e}")
        return 0

def main():
    """Main function"""
    print("🚀 Starting bulk food translation...")
    print(f"🌍 Languages: {', '.join(LANGUAGES)}")
    
    # Test Railway API
    print("\n🧪 Testing Railway API...")
    try:
        response = requests.get(RAILWAY_API_URL, timeout=5)
        if response.status_code == 200:
            print("✅ Railway API is working")
        else:
            print(f"❌ Railway API error: HTTP {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Railway API test failed: {e}")
        return
    
    # Get total food count
    print("\n📊 Getting total food count...")
    total_foods = get_total_food_count()
    print(f"📊 Total foods: {total_foods:,}")
    
    if total_foods == 0:
        print("❌ No foods found in database")
        return
    
    # Calculate total translations needed
    total_translations = total_foods * len(LANGUAGES)
    print(f"🔄 Total translations needed: {total_translations:,}")
    
    # Estimate time
    estimated_time = (total_translations / 3) * 0.5  # ~0.5 seconds per translation, 3 concurrent
    print(f"⏱️  Estimated time: {estimated_time/60:.1f} minutes")
    
    # Process foods in batches
    batch_size = 50  # Process 50 foods at a time
    offset = 0
    translated_count = 0
    failed_count = 0
    skipped_count = 0
    
    print(f"\n📦 Processing foods in batches of {batch_size}...")
    
    while offset < total_foods:
        print(f"\n📦 Getting batch starting at offset {offset}...")
        foods = get_foods_batch(offset, batch_size)
        
        if not foods:
            print("✅ No more foods to process")
            break
        
        print(f"🔄 Processing {len(foods)} foods...")
        
        for food in foods:
            food_id = food['id']
            food_name = food['name']
            
            print(f"\n🍎 Processing: {food_name}")
            
            for lang in LANGUAGES:
                # Check if translation already exists
                if check_existing_translation(food_id, lang):
                    print(f"⏭️  Skipping {lang} (already exists)")
                    skipped_count += 1
                    continue
                
                # Translate
                print(f"🔄 Translating to {lang}...")
                translated_name = translate_text(food_name, lang)
                
                if translated_name != food_name:
                    # Save translation
                    success = save_translation(food_id, lang, translated_name)
                    if success:
                        translated_count += 1
                        print(f"✅ {food_name} -> {translated_name} ({lang})")
                    else:
                        failed_count += 1
                        print(f"❌ Failed to save: {food_name} -> {translated_name} ({lang})")
                else:
                    print(f"⚠️  No translation needed: {food_name} ({lang})")
                
                # Small delay to avoid overwhelming the API
                time.sleep(0.3)
        
        offset += batch_size
        
        # Show progress
        progress = (offset / total_foods) * 100
        print(f"\n📈 Progress: {progress:.1f}% ({offset:,}/{total_foods:,} foods)")
        print(f"✅ Translated: {translated_count:,}")
        print(f"⏭️  Skipped: {skipped_count:,}")
        print(f"❌ Failed: {failed_count:,}")
        
        # Ask user if they want to continue (for testing)
        if offset >= 200:  # Stop after 200 foods for testing
            print(f"\n🛑 Stopping after {offset} foods (testing mode)")
            break
        
        # Delay between batches
        if offset < total_foods:
            print(f"⏳ Waiting 2 seconds...")
            time.sleep(2)
    
    print(f"\n🎉 Bulk translation completed!")
    print(f"✅ Successfully translated: {translated_count:,}")
    print(f"⏭️  Skipped (already exists): {skipped_count:,}")
    print(f"❌ Failed translations: {failed_count:,}")
    if translated_count + skipped_count + failed_count > 0:
        print(f"📊 Success rate: {(translated_count/(translated_count+failed_count)*100):.1f}%")

if __name__ == "__main__":
    main()
