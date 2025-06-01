#!/usr/bin/env python3
"""
Test script to debug FLUX API endpoints
Run with: python test_flux.py
"""

import os
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

async def test_flux_endpoints():
    """Test different FLUX endpoint routes"""
    
    flux_endpoint = os.getenv('FLUX_ENDPOINT')
    api_key = os.getenv('KOYEB_API_KEY')
    
    if not flux_endpoint or not api_key:
        print("❌ Missing FLUX_ENDPOINT or KOYEB_API_KEY in .env")
        return
    
    print(f"🔍 Testing FLUX endpoint: {flux_endpoint}")
    print(f"🔑 API Key: {api_key[:10]}...")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Extract base URL from current endpoint
    base_url = flux_endpoint.replace('/generate', '').replace('/v1/images/generations', '').replace('/create', '').rstrip('/')
    
    # Test different possible routes
    test_routes = [
        "/generate",
        "/v1/images/generations", 
        "/create",
        "/text-to-image",
        "",  # base endpoint
    ]
    
    timeout = aiohttp.ClientTimeout(total=10)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for route in test_routes:
            endpoint = base_url + route
            
            # Test payload for image generation
            payload = {
                "prompt": "A simple test image of a red apple",
                "num_inference_steps": 20,
                "guidance_scale": 7.5,
                "width": 512,
                "height": 512
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
                    elif response.status == 422:
                        error_text = await response.text()
                        print(f"   ⚠️  Validation error (but endpoint exists): {error_text[:100]}...")
                    else:
                        error_text = await response.text()
                        print(f"   ❌ Error: {error_text[:100]}...")
                        
            except asyncio.TimeoutError:
                print(f"   ⏰ Timeout")
            except Exception as e:
                print(f"   💥 Exception: {str(e)}")
    
    print(f"\n❌ No working endpoint found. Check your FLUX service deployment.")

if __name__ == "__main__":
    asyncio.run(test_flux_endpoints())