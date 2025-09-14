#!/usr/bin/env python3
"""
Optimized bulk translation script for all foods
- Concurrent processing with asyncio
- Better error handling and retry logic
- Progress persistence
- Optimized database queries
"""

import asyncio
import aiohttp
import time
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import os

# Configuration
RAILWAY_API_URL = "https://libretranslate-railway-production-ca6b.up.railway.app"
SUPABASE_URL = "https://jklyfpokjtqyrkkeehho.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImprbHlmcG9ranRxeXJra2VlaGhvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcxNTA3ODgsImV4cCI6MjA3MjcyNjc4OH0.s5RtIsu2FSWlt0W8spVZ-IvxdOScfzeR44IGYEoMbjk"

# Languages to translate to
LANGUAGES = ['es', 'de', 'it']

# Performance settings
BATCH_SIZE = 100  # Process 100 foods at a time
MAX_CONCURRENT_TRANSLATIONS = 10  # Max concurrent translation requests
MAX_CONCURRENT_DB_OPERATIONS = 20  # Max concurrent database operations
DELAY_BETWEEN_BATCHES = 1  # Seconds to wait between batches
MAX_RETRIES = 3  # Max retries for failed operations
TRANSLATION_TIMEOUT = 15  # Timeout for translation requests
DB_TIMEOUT = 10  # Timeout for database operations

@dataclass
class TranslationResult:
    food_id: str
    food_name: str
    locale: str
    translated_name: str
    success: bool
    error: Optional[str] = None

class OptimizedBulkTranslator:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
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
    
    async def translate_text(self, text: str, target_lang: str, retries: int = 0) -> str:
        """Translate text using Railway API with retry logic"""
        try:
            payload = {
                "q": text,
                "source": "en",
                "target": target_lang
            }
            
            timeout = aiohttp.ClientTimeout(total=TRANSLATION_TIMEOUT)
            async with self.session.post(
                f"{RAILWAY_API_URL}/translate", 
                json=payload, 
                timeout=timeout
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("translatedText", text)
                else:
                    raise Exception(f"HTTP {response.status}")
                    
        except Exception as e:
            if retries < MAX_RETRIES:
                print(f"🔄 Retrying translation ({retries + 1}/{MAX_RETRIES}): {e}")
                await asyncio.sleep(1 * (retries + 1))  # Exponential backoff
                return await self.translate_text(text, target_lang, retries + 1)
            else:
                print(f"❌ Translation failed after {MAX_RETRIES} retries: {e}")
                return text
    
    async def check_existing_translations(self, food_ids: List[str]) -> Dict[str, List[str]]:
        """Check existing translations for multiple foods at once"""
        try:
            url = f"{SUPABASE_URL}/rest/v1/ingredient_translations"
            headers = {
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
                "Content-Type": "application/json"
            }
            
            # Create a query for all food IDs
            food_id_filter = ",".join([f"eq.{food_id}" for food_id in food_ids])
            params = {
                "ingredient_id": f"in.({food_id_filter})",
                "select": "ingredient_id,locale"
            }
            
            timeout = aiohttp.ClientTimeout(total=DB_TIMEOUT)
            async with self.session.get(url, headers=headers, params=params, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    # Group by food_id
                    existing = {}
                    for item in data:
                        food_id = item['ingredient_id']
                        locale = item['locale']
                        if food_id not in existing:
                            existing[food_id] = []
                        existing[food_id].append(locale)
                    return existing
                else:
                    print(f"❌ Failed to check existing translations: HTTP {response.status}")
                    return {}
        except Exception as e:
            print(f"❌ Error checking existing translations: {e}")
            return {}
    
    async def save_translations_batch(self, translations: List[TranslationResult]) -> int:
        """Save multiple translations in a single batch"""
        if not translations:
            return 0
            
        try:
            url = f"{SUPABASE_URL}/rest/v1/ingredient_translations"
            headers = {
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates"
            }
            
            # Prepare batch data
            batch_data = []
            for trans in translations:
                if trans.success and trans.translated_name != trans.food_name:
                    batch_data.append({
                        "ingredient_id": trans.food_id,
                        "locale": trans.locale,
                        "name": trans.translated_name,
                        "synonyms": []
                    })
            
            if not batch_data:
                return 0
            
            timeout = aiohttp.ClientTimeout(total=DB_TIMEOUT)
            async with self.session.post(url, headers=headers, json=batch_data, timeout=timeout) as response:
                if response.status in [200, 201]:
                    return len(batch_data)
                else:
                    print(f"❌ Batch save failed: HTTP {response.status}")
                    return 0
        except Exception as e:
            print(f"❌ Error saving batch: {e}")
            return 0
    
    async def get_foods_batch(self, offset: int, limit: int) -> List[Dict]:
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
            
            timeout = aiohttp.ClientTimeout(total=DB_TIMEOUT)
            async with self.session.get(url, headers=headers, params=params, timeout=timeout) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"❌ Failed to fetch foods: HTTP {response.status}")
                    return []
        except Exception as e:
            print(f"❌ Error fetching foods: {e}")
            return []
    
    async def get_total_food_count(self) -> int:
        """Get total number of foods"""
        try:
            # Get a large sample to estimate total
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
            
            timeout = aiohttp.ClientTimeout(total=DB_TIMEOUT)
            async with self.session.get(url, headers=headers, params=params, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    # If we got 10000, there are likely more
                    if len(data) == 10000:
                        return 10000  # We'll handle pagination
                    else:
                        return len(data)
                return 0
        except Exception as e:
            print(f"❌ Error getting food count: {e}")
            return 0
    
    async def process_food_translations(self, food: Dict, existing_translations: List[str]) -> List[TranslationResult]:
        """Process translations for a single food"""
        food_id = food['id']
        food_name = food['name']
        results = []
        
        # Create semaphore for concurrent translations
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_TRANSLATIONS)
        
        async def translate_single(food_id: str, food_name: str, lang: str) -> TranslationResult:
            async with semaphore:
                if lang in existing_translations:
                    return TranslationResult(food_id, food_name, lang, food_name, True)
                
                translated_name = await self.translate_text(food_name, lang)
                success = translated_name != food_name
                
                return TranslationResult(food_id, food_name, lang, translated_name, success)
        
        # Create tasks for all languages
        tasks = [translate_single(food_id, food_name, lang) for lang in LANGUAGES]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                print(f"❌ Translation error: {result}")
                processed_results.append(TranslationResult(food_id, food_name, "unknown", food_name, False, str(result)))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def process_batch(self, foods: List[Dict]) -> None:
        """Process a batch of foods"""
        if not foods:
            return
        
        food_ids = [food['id'] for food in foods]
        
        # Check existing translations for all foods in batch
        existing_translations = await self.check_existing_translations(food_ids)
        
        # Process all foods concurrently
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_DB_OPERATIONS)
        
        async def process_single_food(food: Dict) -> List[TranslationResult]:
            async with semaphore:
                existing = existing_translations.get(food['id'], [])
                return await self.process_food_translations(food, existing)
        
        # Create tasks for all foods
        tasks = [process_single_food(food) for food in foods]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results and count
        translations_to_save = []
        for results in all_results:
            if isinstance(results, Exception):
                print(f"❌ Batch processing error: {results}")
                continue
            
            for result in results:
                if result.success:
                    if result.translated_name != result.food_name:
                        self.translated_count += 1
                        translations_to_save.append(result)
                    else:
                        self.skipped_count += 1
                else:
                    self.failed_count += 1
        
        # Save all translations in batch
        if translations_to_save:
            saved_count = await self.save_translations_batch(translations_to_save)
            print(f"💾 Saved {saved_count} translations to database")
        
        self.processed_foods += len(foods)
        self.save_progress()
    
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
    
    async def run(self):
        """Main execution function"""
        print("🚀 Starting optimized bulk food translation...")
        print(f"🌍 Languages: {', '.join(LANGUAGES)}")
        print(f"📦 Batch size: {BATCH_SIZE}")
        print(f"⚡ Max concurrent translations: {MAX_CONCURRENT_TRANSLATIONS}")
        print(f"💾 Max concurrent DB operations: {MAX_CONCURRENT_DB_OPERATIONS}")
        
        # Test Railway API
        print("\n🧪 Testing Railway API...")
        try:
            async with aiohttp.ClientSession() as test_session:
                async with test_session.get(RAILWAY_API_URL, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        print("✅ Railway API is working")
                    else:
                        print(f"❌ Railway API error: HTTP {response.status}")
                        return
        except Exception as e:
            print(f"❌ Railway API test failed: {e}")
            return
        
        # Get total food count
        async with aiohttp.ClientSession() as session:
            self.session = session
            self.total_foods = await self.get_total_food_count()
            print(f"📊 Total foods to process: {self.total_foods:,}")
            
            if self.total_foods == 0:
                print("❌ No foods found in database")
                return
            
            # Calculate total translations needed
            total_translations = self.total_foods * len(LANGUAGES)
            print(f"🔄 Total translations needed: {total_translations:,}")
            
            # Estimate time
            estimated_time = (total_translations / MAX_CONCURRENT_TRANSLATIONS) * 0.3  # ~0.3 seconds per translation
            print(f"⏱️  Estimated time: {estimated_time/60:.1f} minutes")
            
            # Process in batches
            offset = self.processed_foods
            batch_num = 1
            
            while offset < self.total_foods:
                print(f"\n📦 Processing batch {batch_num} (foods {offset+1}-{min(offset+BATCH_SIZE, self.total_foods)})")
                
                # Get batch of foods
                foods = await self.get_foods_batch(offset, BATCH_SIZE)
                
                if not foods:
                    print("✅ No more foods to process")
                    break
                
                # Process the batch
                await self.process_batch(foods)
                
                # Print progress
                self.print_progress()
                
                offset += BATCH_SIZE
                batch_num += 1
                
                # Delay between batches
                if offset < self.total_foods:
                    await asyncio.sleep(DELAY_BETWEEN_BATCHES)
        
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

async def main():
    """Main function"""
    translator = OptimizedBulkTranslator()
    await translator.run()

if __name__ == "__main__":
    asyncio.run(main())
