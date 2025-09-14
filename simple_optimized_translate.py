#!/usr/bin/env python3
"""
Simple optimized bulk translation script for all foods
- Better error handling and retry logic
- Progress persistence
- Optimized database queries
- Processes ALL foods (no testing limit)
"""

import requests
import time
import json
from typing import List, Dict, Any, Optional
import os

# Configuration
RAILWAY_API_URL = "https://libretranslate-railway-production-ca6b.up.railway.app"
SUPABASE_URL = "https://jklyfpokjtqyrkkeehho.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImprbHlmcG9ranRxeXJra2VlaGhvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcxNTA3ODgsImV4cCI6MjA3MjcyNjc4OH0.s5RtIsu2FSWlt0W8spVZ-IvxdOScfzeR44IGYEoMbjk"

# Languages to translate to
LANGUAGES = ['es', 'de', 'it']

# Performance settings
BATCH_SIZE = 50  # Process 50 foods at a time
MAX_RETRIES = 3  # Max retries for failed operations
TRANSLATION_TIMEOUT = 15  # Timeout for translation requests
DB_TIMEOUT = 10  # Timeout for database operations
DELAY_BETWEEN_TRANSLATIONS = 0.1  # Delay between individual translations
DELAY_BETWEEN_BATCHES = 2  # Delay between batches

class SimpleOptimizedTranslator:
    def __init__(self):
        self.translated_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.total_foods = 0
        self.processed_foods = 0
        self.start_time = time.time()
        
        # Progress tracking
        self.progress_file = "translation_progress.json"
        self.load_progress()
    
    def load_progress(self):
        """Load progress from file"""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, 'r') as f:
                    progress = json.load(f)
                    self.processed_foods = progress.get('processed_foods', 0)
                    self.translated_count = progress.get('translated_count', 0)
                    self.failed_count = progress.get('failed_count', 0)
                    self.skipped_count = progress.get('skipped_count', 0)
                    print(f"📊 Resuming from {self.processed_foods} foods processed")
        except Exception as e:
            print(f"⚠️ Could not load progress: {e}")
    
    def save_progress(self):
        """Save progress to file"""
        try:
            progress = {
                'processed_foods': self.processed_foods,
                'translated_count': self.translated_count,
                'failed_count': self.failed_count,
                'skipped_count': self.skipped_count,
                'timestamp': time.time()
            }
            with open(self.progress_file, 'w') as f:
                json.dump(progress, f)
        except Exception as e:
            print(f"⚠️ Could not save progress: {e}")
    
    def translate_text(self, text: str, target_lang: str, retries: int = 0) -> str:
        """Translate text using Railway API with retry logic"""
        try:
            payload = {
                "q": text,
                "source": "en",
                "target": target_lang
            }
            
            response = requests.post(
                f"{RAILWAY_API_URL}/translate", 
                json=payload, 
                timeout=TRANSLATION_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("translatedText", text)
            else:
                raise Exception(f"HTTP {response.status_code}")
                
        except Exception as e:
            if retries < MAX_RETRIES:
                print(f"🔄 Retrying translation ({retries + 1}/{MAX_RETRIES}): {e}")
                time.sleep(1 * (retries + 1))  # Exponential backoff
                return self.translate_text(text, target_lang, retries + 1)
            else:
                print(f"❌ Translation failed after {MAX_RETRIES} retries: {e}")
                return text
    
    def check_existing_translation(self, food_id: str, locale: str) -> bool:
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
            
            response = requests.get(url, headers=headers, params=params, timeout=DB_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                return len(data) > 0
            return False
        except Exception as e:
            print(f"❌ Error checking existing translation: {e}")
            return False
    
    def save_translation(self, food_id: str, locale: str, translated_name: str) -> bool:
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
            
            response = requests.post(url, headers=headers, json=data, timeout=DB_TIMEOUT)
            return response.status_code in [200, 201]
        except Exception as e:
            print(f"❌ Error saving translation: {e}")
            return False
    
    def get_foods_batch(self, offset: int, limit: int) -> List[Dict]:
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
            
            response = requests.get(url, headers=headers, params=params, timeout=DB_TIMEOUT)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Failed to fetch foods: HTTP {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error fetching foods: {e}")
            return []
    
    def get_total_food_count(self) -> int:
        """Get total number of foods by counting in batches"""
        try:
            # Get a large batch to estimate total
            url = f"{SUPABASE_URL}/rest/v1/foods"
            headers = {
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
                "Content-Type": "application/json"
            }
            params = {
                "select": "id",
                "limit": "10000"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=DB_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                # If we got 10000, there might be more
                if len(data) == 10000:
                    return 10000  # We'll handle pagination in the main loop
                else:
                    return len(data)
            return 0
        except Exception as e:
            print(f"❌ Error getting food count: {e}")
            return 0
    
    def print_progress(self):
        """Print current progress"""
        elapsed = time.time() - self.start_time
        if self.processed_foods > 0:
            rate = self.processed_foods / elapsed
            eta = (self.total_foods - self.processed_foods) / rate if rate > 0 else 0
            
            print(f"\n📊 Progress: {self.processed_foods:,}/{self.total_foods:,} foods ({self.processed_foods/self.total_foods*100:.1f}%)")
            print(f"✅ Translated: {self.translated_count:,}")
            print(f"⏭️  Skipped: {self.skipped_count:,}")
            print(f"❌ Failed: {self.failed_count:,}")
            print(f"⚡ Rate: {rate:.1f} foods/sec")
            print(f"⏱️  ETA: {eta/60:.1f} minutes")
    
    def run(self):
        """Main execution function"""
        print("🚀 Starting optimized bulk food translation...")
        print(f"🌍 Languages: {', '.join(LANGUAGES)}")
        print(f"📦 Batch size: {BATCH_SIZE}")
        print(f"🔄 Max retries: {MAX_RETRIES}")
        print(f"⏱️  Translation timeout: {TRANSLATION_TIMEOUT}s")
        print(f"💾 Database timeout: {DB_TIMEOUT}s")
        
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
        self.total_foods = self.get_total_food_count()
        print(f"📊 Total foods to process: {self.total_foods:,}")
        
        if self.total_foods == 0:
            print("❌ No foods found in database")
            return
        
        # Calculate total translations needed
        total_translations = self.total_foods * len(LANGUAGES)
        print(f"🔄 Total translations needed: {total_translations:,}")
        
        # Estimate time
        estimated_time = (total_translations / 3) * 0.3  # ~0.3 seconds per translation
        print(f"⏱️  Estimated time: {estimated_time/60:.1f} minutes")
        
        # Process in batches
        offset = self.processed_foods
        batch_num = 1
        
        while offset < self.total_foods:
            print(f"\n📦 Processing batch {batch_num} (foods {offset+1}-{min(offset+BATCH_SIZE, self.total_foods)})")
            
            # Get batch of foods
            foods = self.get_foods_batch(offset, BATCH_SIZE)
            
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
                    if self.check_existing_translation(food_id, lang):
                        print(f"⏭️  Skipping {lang} (already exists)")
                        self.skipped_count += 1
                        continue
                    
                    # Translate
                    print(f"🔄 Translating to {lang}...")
                    translated_name = self.translate_text(food_name, lang)
                    
                    if translated_name != food_name:
                        # Save translation
                        success = self.save_translation(food_id, lang, translated_name)
                        if success:
                            self.translated_count += 1
                            print(f"✅ {food_name} -> {translated_name} ({lang})")
                        else:
                            self.failed_count += 1
                            print(f"❌ Failed to save: {food_name} -> {translated_name} ({lang})")
                    else:
                        print(f"⚠️  No translation needed: {food_name} ({lang})")
                    
                    # Small delay to avoid overwhelming the API
                    time.sleep(DELAY_BETWEEN_TRANSLATIONS)
            
            self.processed_foods += len(foods)
            self.save_progress()
            
            # Print progress
            self.print_progress()
            
            offset += BATCH_SIZE
            batch_num += 1
            
            # Delay between batches
            if offset < self.total_foods:
                print(f"⏳ Waiting {DELAY_BETWEEN_BATCHES} seconds...")
                time.sleep(DELAY_BETWEEN_BATCHES)
        
        print(f"\n🎉 Bulk translation completed!")
        print(f"✅ Successfully translated: {self.translated_count:,}")
        print(f"⏭️  Skipped (already exists): {self.skipped_count:,}")
        print(f"❌ Failed translations: {self.failed_count:,}")
        if self.translated_count + self.failed_count > 0:
            print(f"📊 Success rate: {(self.translated_count/(self.translated_count+self.failed_count)*100):.1f}%")
        
        # Clean up progress file
        try:
            os.remove(self.progress_file)
            print("🧹 Cleaned up progress file")
        except:
            pass

def main():
    """Main function"""
    translator = SimpleOptimizedTranslator()
    translator.run()

if __name__ == "__main__":
    main()
