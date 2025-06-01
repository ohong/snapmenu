#!/usr/bin/env python3
"""
Test script to debug Pixtral API endpoints
Run with: python test_endpoints.py
"""

import os
import asyncio
import aiohttp
import base64
from dotenv import load_dotenv

load_dotenv()

async def test_pixtral_endpoints():
    """Test different Pixtral endpoint routes"""
    
    base_endpoint = os.getenv('PIXTRAL_ENDPOINT')
    api_key = os.getenv('KOYEB_API_KEY')
    
    if not base_endpoint or not api_key:
        print("❌ Missing PIXTRAL_ENDPOINT or KOYEB_API_KEY in .env")
        return
    
    print(f"🔍 Testing base endpoint: {base_endpoint}")
    print(f"🔑 API Key: {api_key[:10]}...")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Test different possible routes
    test_routes = [
        "",  # base endpoint
        "/generate",
        "/chat", 
        "/vision",
        "/v1/chat/completions",
        "/v1/generate"
    ]
    
    timeout = aiohttp.ClientTimeout(total=10)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for route in test_routes:
            endpoint = base_endpoint.rstrip('/') + route
            
            # Simple text test payload
            payload = {
                "prompt": "Hello, can you respond?",
                "max_tokens": 50,
                "temperature": 0.3
            }
            
            print(f"\n🧪 Testing: {endpoint}")
            
            try:
                async with session.post(endpoint, json=payload, headers=headers) as response:
                    print(f"   Status: {response.status}")
                    
                    if response.status == 200:
                        result = await response.json()
                        print(f"   ✅ Success! Response keys: {list(result.keys())}")
                        return endpoint  # Found working endpoint
                    elif response.status == 404:
                        print(f"   ❌ Not found")
                    elif response.status == 401:
                        print(f"   ❌ Unauthorized - check API key")
                    else:
                        error_text = await response.text()
                        print(f"   ❌ Error: {error_text[:100]}...")
                        
            except asyncio.TimeoutError:
                print(f"   ⏰ Timeout")
            except Exception as e:
                print(f"   💥 Exception: {str(e)}")
    
    print(f"\n❌ No working endpoint found. Check your Pixtral service deployment.")

if __name__ == "__main__":
    asyncio.run(test_pixtral_endpoints())