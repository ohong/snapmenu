#!/usr/bin/env python3
"""
Test Pixtral service health and responsiveness
Run with: python test_pixtral_health.py
"""

import os
import asyncio
import time
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

async def test_pixtral_health():
    """Test if Pixtral service is responsive"""
    
    base_endpoint = os.getenv('PIXTRAL_ENDPOINT')
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not base_endpoint or not api_key:
        print("❌ Missing PIXTRAL_ENDPOINT or OPENAI_API_KEY in .env")
        return False
    
    print(f"🏥 Health Check: Testing Pixtral at {base_endpoint}")
    
    try:
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=f"{base_endpoint.rstrip('/')}/v1",
            timeout=10.0
        )
        
        # Simple text-only request to test responsiveness
        print("📋 Testing basic text completion...")
        start_time = time.time()
        
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model="mistralai/Pixtral-12B-2409",
                messages=[
                    {
                        "role": "user",
                        "content": "Respond with exactly: 'Service is healthy'"
                    }
                ],
                max_tokens=10,
                temperature=0.0
            ),
            timeout=8.0
        )
        
        elapsed = time.time() - start_time
        result = response.choices[0].message.content.strip()
        
        print(f"✅ Text test completed in {elapsed:.2f}s")
        print(f"📝 Response: '{result}'")
        
        if "healthy" in result.lower():
            print("🎉 Pixtral service is healthy and responsive!")
            return True
        else:
            print("⚠️  Service responded but with unexpected content")
            return False
            
    except asyncio.TimeoutError:
        print("⏰ Health check timed out - service may be slow or unresponsive")
        return False
    except Exception as e:
        error_type = type(e).__name__
        print(f"❌ Health check failed ({error_type}): {str(e)}")
        
        if "timeout" in str(e).lower():
            print("   → Service appears to be timing out")
        elif "connection" in str(e).lower():
            print("   → Cannot connect to service")
        elif "401" in str(e) or "unauthorized" in str(e).lower():
            print("   → Authentication issue")
        elif "500" in str(e) or "502" in str(e) or "503" in str(e):
            print("   → Server error")
        
        return False

async def test_simple_vision():
    """Test vision capabilities with a minimal request"""
    
    base_endpoint = os.getenv('PIXTRAL_ENDPOINT')
    api_key = os.getenv('OPENAI_API_KEY')
    
    print(f"\n👁️  Vision Test: Testing image analysis...")
    
    try:
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=f"{base_endpoint.rstrip('/')}/v1",
            timeout=15.0
        )
        
        # Test with a simple data URL (1x1 red pixel)
        red_pixel_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        
        start_time = time.time()
        
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model="mistralai/Pixtral-12B-2409",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "What color is this image? Respond with just the color name."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{red_pixel_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=10,
                temperature=0.0
            ),
            timeout=12.0
        )
        
        elapsed = time.time() - start_time
        result = response.choices[0].message.content.strip()
        
        print(f"✅ Vision test completed in {elapsed:.2f}s")
        print(f"🎨 Response: '{result}'")
        
        if "red" in result.lower():
            print("🎉 Vision capabilities working correctly!")
            return True
        else:
            print("⚠️  Vision responded but may not be analyzing images correctly")
            return False
            
    except asyncio.TimeoutError:
        print("⏰ Vision test timed out")
        return False
    except Exception as e:
        error_type = type(e).__name__
        print(f"❌ Vision test failed ({error_type}): {str(e)}")
        return False

if __name__ == "__main__":
    async def run_all_tests():
        print("🧪 Starting Pixtral Service Health Check\n")
        
        # Test 1: Basic health
        health_ok = await test_pixtral_health()
        
        if health_ok:
            # Test 2: Vision capabilities
            vision_ok = await test_simple_vision()
            
            if vision_ok:
                print(f"\n🎉 All tests passed! Pixtral is ready for menu OCR.")
            else:
                print(f"\n⚠️  Text works but vision may have issues.")
        else:
            print(f"\n❌ Service health check failed. OCR will likely timeout.")
    
    asyncio.run(run_all_tests())