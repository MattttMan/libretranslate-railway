#!/usr/bin/env python3
"""
Enhanced bulk translation script with visual progress bar and persistent time tracking
- Visual progress bar with percentage
- Persistent time tracking across restarts
- ETA calculations that work even after interruption
- Total compute time tracking
"""

import requests
import time
import json
import os
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

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

class ProgressBar:
    """Visual progress bar for terminal"""
    
    def __init__(self, total: int, width: int = 50):
        self.total = total
        self.width = width
        self.current = 0
        self.start_time = time.time()
    
    def update(self, current: int):
        """Update progress bar"""
        self.current = current
        percentage = (current / self.total) * 100 if self.total > 0 else 0
        
        # Calculate progress bar
        filled = int((current / self.total) * self.width) if self.total > 0 else 0
        bar = '█' * filled + '░' * (self.width - filled)
        
        # Calculate ETA
        elapsed = time.time() - self.start_time
        if current > 0:
            rate = current / elapsed
            remaining = (self.total - current) / rate if rate > 0 else 0
            eta = timedelta(seconds=int(remaining))
        else:
            eta = timedelta(seconds=0)
        
        # Print progress bar
        print(f"\r🔄 Progress: [{bar}] {percentage:.1f}% ({current:,}/{self.total:,}) | ETA: {eta} | Rate: {rate:.1f}/sec", end='', flush=True)
    
    def finish(self):
        """Finish progress bar"""
        elapsed = time.time() - self.start_time
        print(f"\n✅ Completed in {timedelta(seconds=int(elapsed))}")

class EnhancedBulkTranslator:
    def __init__(self):
        self.translated_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.total_foods = 0
        self.processed_foods = 0
        self.start_time = time.time()
        self.session_start_time = time.time()
        
        # Progress tracking
        self.progress_file = "translation_progress.json"
        self.load_progress()
        
        # Progress bar
        self.progress_bar = None
    
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
                    
                    # Load session start time
                    self.session_start_time = progress.get('session_start_time', time.time())
                    
                    # Calculate total compute time
                    total_compute_time = progress.get('total_compute_time', 0)
                    if self.processed_foods > 0:
                        print(f"📊 Resuming from {self.processed_foods} foods processed")
                        print(f"⏱️  Previous compute time: {timedelta(seconds=int(total_compute_time))}")
                        print(f"🔄 Session started: {datetime.fromtimestamp(self.session_start_time).strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"⚠️ Could not load progress: {e}")
    
    def save_progress(self):
        """Save progress to file"""
        try:
            # Calculate total compute time
            current_session_time = time.time() - self.session_start_time
            total_compute_time = current_session_time
            
            # Load previous compute time if exists
            if os.path.exists(self.progress_file):
                try:
                    with open(self.progress_file, 'r') as f:
                        prev_progress = json.load(f)
                        total_compute_time += prev_progress.get('total_compute_time', 0)
                except:
                    pass
            
            progress = {
                'processed_foods': self.processed_foods,
                'translated_count': self.translated_count,
                'failed_count': self.failed_count,
                'skipped_count': self.skipped_count,
                'session_start_time': self.session_start_time,
                'total_compute_time': total_compute_time,
                'timestamp': time.time(),
                'last_update': datetime.now().isoformat()
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
                time.sleep(1 * (retries + 1))  # Exponential backoff
                return self.translate_text(text, target_lang, retries + 1)
            else:
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
                return []
        except Exception as e:
            return []
    
    def get_total_food_count(self) -> int:
        """Get total number of foods by counting in batches"""
        try:
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
                if len(data) == 10000:
                    return 10000  # We'll handle pagination
                else:
                    return len(data)
            return 0
        except Exception as e:
            return 0
    
    def print_detailed_progress(self):
        """Print detailed progress information"""
        elapsed = time.time() - self.start_time
        total_compute_time = time.time() - self.session_start_time
        
        if self.processed_foods > 0:
            rate = self.processed_foods / elapsed
            eta = (self.total_foods - self.processed_foods) / rate if rate > 0 else 0
            
            print(f"\n📊 Detailed Progress:")
            print(f"   Foods: {self.processed_foods:,}/{self.total_foods:,} ({self.processed_foods/self.total_foods*100:.1f}%)")
            print(f"   ✅ Translated: {self.translated_count:,}")
            print(f"   ⏭️  Skipped: {self.skipped_count:,}")
            print(f"   ❌ Failed: {self.failed_count:,}")
            print(f"   ⚡ Rate: {rate:.1f} foods/sec")
            print(f"   ⏱️  ETA: {timedelta(seconds=int(eta))}")
            print(f"   🕐 Total compute time: {timedelta(seconds=int(total_compute_time))}")
            print(f"   📅 Started: {datetime.fromtimestamp(self.session_start_time).strftime('%Y-%m-%d %H:%M:%S')}")
    
    def run(self):
        """Main execution function"""
        print("🚀 Starting Enhanced Bulk Food Translation...")
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
        
        # Initialize progress bar
        self.progress_bar = ProgressBar(self.total_foods)
        
        # Calculate total translations needed
        total_translations = self.total_foods * len(LANGUAGES)
        print(f"🔄 Total translations needed: {total_translations:,}")
        
        # Estimate time
        estimated_time = (total_translations / 3) * 0.3  # ~0.3 seconds per translation
        print(f"⏱️  Estimated time: {timedelta(seconds=int(estimated_time))}")
        
        # Process in batches
        offset = self.processed_foods
        batch_num = 1
        
        try:
            while offset < self.total_foods:
                # Get batch of foods
                foods = self.get_foods_batch(offset, BATCH_SIZE)
                
                if not foods:
                    print("\n✅ No more foods to process")
                    break
                
                # Process each food in the batch
                for food in foods:
                    food_id = food['id']
                    food_name = food['name']
                    
                    for lang in LANGUAGES:
                        # Check if translation already exists
                        if self.check_existing_translation(food_id, lang):
                            self.skipped_count += 1
                            continue
                        
                        # Translate
                        translated_name = self.translate_text(food_name, lang)
                        
                        if translated_name != food_name:
                            # Save translation
                            success = self.save_translation(food_id, lang, translated_name)
                            if success:
                                self.translated_count += 1
                            else:
                                self.failed_count += 1
                        else:
                            self.skipped_count += 1
                        
                        # Small delay to avoid overwhelming the API
                        time.sleep(DELAY_BETWEEN_TRANSLATIONS)
                
                self.processed_foods += len(foods)
                
                # Update progress bar
                self.progress_bar.update(self.processed_foods)
                
                # Save progress every batch
                self.save_progress()
                
                offset += BATCH_SIZE
                batch_num += 1
                
                # Delay between batches
                if offset < self.total_foods:
                    time.sleep(DELAY_BETWEEN_BATCHES)
        
        except KeyboardInterrupt:
            print(f"\n\n⚠️ Translation interrupted by user")
            print(f"📊 Progress saved - you can resume by running the script again")
            self.print_detailed_progress()
            return
        
        except Exception as e:
            print(f"\n\n❌ Unexpected error: {e}")
            print(f"📊 Progress saved - you can resume by running the script again")
            self.print_detailed_progress()
            return
        
        # Finish progress bar
        self.progress_bar.finish()
        
        # Final statistics
        total_time = time.time() - self.session_start_time
        print(f"\n🎉 Bulk translation completed!")
        print(f"✅ Successfully translated: {self.translated_count:,}")
        print(f"⏭️  Skipped (already exists): {self.skipped_count:,}")
        print(f"❌ Failed translations: {self.failed_count:,}")
        if self.translated_count + self.failed_count > 0:
            print(f"📊 Success rate: {(self.translated_count/(self.translated_count+self.failed_count)*100):.1f}%")
        print(f"🕐 Total compute time: {timedelta(seconds=int(total_time))}")
        
        # Clean up progress file
        try:
            os.remove(self.progress_file)
            print("🧹 Cleaned up progress file")
        except:
            pass

def main():
    """Main function"""
    translator = EnhancedBulkTranslator()
    translator.run()

if __name__ == "__main__":
    main()
