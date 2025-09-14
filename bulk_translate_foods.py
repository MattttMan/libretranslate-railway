#!/usr/bin/env python3
"""
Bulk translate all foods in the database to all supported languages
Uses the Railway LibreTranslate Lite API for translations
"""

import requests
import json
import time
import asyncio
import aiohttp
from typing import List, Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
RAILWAY_API_URL = "https://libretranslate-railway-production-ca6b.up.railway.app"
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://jklyfpokjtqyrkkeehho.supabase.co')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImprbHlmcG9ranRxeXJra2VlaGhvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcxNTA3ODgsImV4cCI6MjA3MjcyNjc4OH0.s5RtIsu2FSWlt0W8spVZ-IvxdOScfzeR44IGYEoMbjk')

# Languages to translate to (excluding English)
LANGUAGES = ['es', 'fr', 'de', 'it', 'pt', 'zh', 'ja', 'ko', 'ar']

# Batch settings
BATCH_SIZE = 50  # Process 50 foods at a time
MAX_CONCURRENT = 5  # Max concurrent translation requests
DELAY_BETWEEN_BATCHES = 2  # Seconds to wait between batches

class BulkTranslator:
    def __init__(self):
        self.session = None
        self.translated_count = 0
        self.failed_count = 0
        self.total_foods = 0
        
    async def translate_text(self, text: str, target_lang: str) -> str:
        """Translate a single text using Railway API"""
        try:
            payload = {
                "q": text,
                "source": "en",
                "target": target_lang
            }
            
            async with self.session.post(f"{RAILWAY_API_URL}/translate", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("translatedText", text)
                else:
                    print(f"❌ Translation failed: HTTP {response.status}")
                    return text
        except Exception as e:
            print(f"❌ Translation error: {e}")
            return text
    
    async def get_foods_batch(self, offset: int, limit: int) -> List[Dict]:
        """Get a batch of foods from Supabase"""
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
            
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"❌ Failed to fetch foods: HTTP {response.status}")
                    return []
        except Exception as e:
            print(f"❌ Error fetching foods: {e}")
            return []
    
    async def save_translation(self, food_id: str, locale: str, translated_name: str) -> bool:
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
            
            async with self.session.post(url, headers=headers, json=data) as response:
                return response.status in [200, 201]
        except Exception as e:
            print(f"❌ Error saving translation: {e}")
            return False
    
    async def check_existing_translation(self, food_id: str, locale: str) -> bool:
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
            
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return len(data) > 0
                return False
        except Exception as e:
            print(f"❌ Error checking existing translation: {e}")
            return False
    
    async def process_food_batch(self, foods: List[Dict]) -> None:
        """Process a batch of foods"""
        tasks = []
        
        for food in foods:
            food_id = food['id']
            food_name = food['name']
            
            # Create translation tasks for each language
            for lang in LANGUAGES:
                task = self.process_single_food(food_id, food_name, lang)
                tasks.append(task)
        
        # Process with concurrency limit
        semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        
        async def limited_task(task):
            async with semaphore:
                return await task
        
        await asyncio.gather(*[limited_task(task) for task in tasks])
    
    async def process_single_food(self, food_id: str, food_name: str, target_lang: str) -> None:
        """Process a single food translation"""
        try:
            # Check if translation already exists
            if await self.check_existing_translation(food_id, target_lang):
                print(f"⏭️  Skipping {food_name} -> {target_lang} (already exists)")
                return
            
            # Translate the food name
            translated_name = await self.translate_text(food_name, target_lang)
            
            if translated_name != food_name:  # Only save if translation is different
                success = await self.save_translation(food_id, target_lang, translated_name)
                if success:
                    self.translated_count += 1
                    print(f"✅ {food_name} -> {translated_name} ({target_lang})")
                else:
                    self.failed_count += 1
                    print(f"❌ Failed to save: {food_name} -> {translated_name} ({target_lang})")
            else:
                print(f"⚠️  No translation needed: {food_name} ({target_lang})")
                
        except Exception as e:
            self.failed_count += 1
            print(f"❌ Error processing {food_name} -> {target_lang}: {e}")
    
    async def get_total_food_count(self) -> int:
        """Get total number of foods in database"""
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
            
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    count = response.headers.get('content-range', '').split('/')[-1]
                    return int(count) if count.isdigit() else 0
                return 0
        except Exception as e:
            print(f"❌ Error getting food count: {e}")
            return 0
    
    async def run(self):
        """Main execution function"""
        print("🚀 Starting bulk food translation...")
        print(f"🌍 Languages: {', '.join(LANGUAGES)}")
        print(f"📦 Batch size: {BATCH_SIZE}")
        print(f"⚡ Max concurrent: {MAX_CONCURRENT}")
        
        # Test Railway API
        print("\n🧪 Testing Railway API...")
        try:
            async with aiohttp.ClientSession() as test_session:
                async with test_session.get(RAILWAY_API_URL) as response:
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
            estimated_time = (total_translations / MAX_CONCURRENT) * 0.5  # ~0.5 seconds per translation
            print(f"⏱️  Estimated time: {estimated_time/60:.1f} minutes")
            
            # Process in batches
            offset = 0
            batch_num = 1
            
            while offset < self.total_foods:
                print(f"\n📦 Processing batch {batch_num} (foods {offset+1}-{min(offset+BATCH_SIZE, self.total_foods)})")
                
                # Get batch of foods
                foods = await self.get_foods_batch(offset, BATCH_SIZE)
                
                if not foods:
                    print("❌ No more foods to process")
                    break
                
                # Process the batch
                await self.process_food_batch(foods)
                
                # Update progress
                progress = (offset + len(foods)) / self.total_foods * 100
                print(f"📈 Progress: {progress:.1f}% ({offset + len(foods):,}/{self.total_foods:,} foods)")
                print(f"✅ Translated: {self.translated_count:,}")
                print(f"❌ Failed: {self.failed_count:,}")
                
                offset += BATCH_SIZE
                batch_num += 1
                
                # Delay between batches
                if offset < self.total_foods:
                    print(f"⏳ Waiting {DELAY_BETWEEN_BATCHES} seconds...")
                    await asyncio.sleep(DELAY_BETWEEN_BATCHES)
        
        print(f"\n🎉 Bulk translation completed!")
        print(f"✅ Successfully translated: {self.translated_count:,}")
        print(f"❌ Failed translations: {self.failed_count:,}")
        print(f"📊 Success rate: {(self.translated_count/(self.translated_count+self.failed_count)*100):.1f}%")

async def main():
    """Main function"""
    translator = BulkTranslator()
    await translator.run()

if __name__ == "__main__":
    asyncio.run(main())
