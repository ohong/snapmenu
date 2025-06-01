#!/usr/bin/env python3
"""
Test OpenAI SDK integration with Pixtral
Run with: python test_openai_sdk.py
"""

import os
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

async def test_pixtral_sdk():
    """Test Pixtral using OpenAI SDK"""
    
    base_endpoint = os.getenv('PIXTRAL_ENDPOINT')
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not base_endpoint or not api_key:
        print("❌ Missing PIXTRAL_ENDPOINT or OPENAI_API_KEY in .env")
        return
    
    print(f"🔍 Testing Pixtral with OpenAI SDK")
    print(f"🔗 Endpoint: {base_endpoint}")
    print(f"🔑 API Key: {api_key[:10]}...")
    
    try:
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=f"{base_endpoint.rstrip('/')}/v1"
        )
        
        print("\n🧪 Testing text-only completion...")
        
        # Try different model names and longer timeout
        model_names = [
            "mistralai/Pixtral-12B-2409",
            "pixtral-12b", 
            "Pixtral-12B-2409",
            "pixtral"
        ]
        
        for model_name in model_names:
            print(f"   Trying model: {model_name}")
            try:
                response = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {
                                "role": "user",
                                "content": "Hello! Can you respond with 'Pixtral is working!' ?"
                            }
                        ],
                        max_tokens=50,
                        temperature=0.1
                    ),
                    timeout=20.0  # Increased timeout
                )
                
                result = response.choices[0].message.content
                print(f"✅ Success with {model_name}! Response: {result}")
                return True
                
            except asyncio.TimeoutError:
                print(f"   ⏰ Timeout with {model_name}")
                continue
            except Exception as e:
                print(f"   ❌ Error with {model_name}: {str(e)}")
                continue
        
        print("❌ All model names failed")
        return False
        
    except asyncio.TimeoutError:
        print("❌ Request timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_pixtral_sdk())
    if success:
        print("\n🎉 OpenAI SDK integration is working!")
    else:
        print("\n💥 OpenAI SDK integration failed")