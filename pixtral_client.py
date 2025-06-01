"""
Unified Pixtral API client to replace duplicate implementations
in ocr_service.py, translation_service.py, and pixtral_service.py
"""

import os
import asyncio
import time
from openai import AsyncOpenAI

class PixtralClient:
    def __init__(self):
        self.base_endpoint = os.getenv('PIXTRAL_ENDPOINT')
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.client = None
        
        if not self.base_endpoint or not self.api_key:
            raise ValueError("Missing PIXTRAL_ENDPOINT or OPENAI_API_KEY")
    
    def get_client(self):
        if not self.client:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_endpoint.rstrip('/'),
                timeout=60.0  # Extended timeout for better reliability
            )
        return self.client
    
    async def text_completion(self, prompt, max_tokens=1000, temperature=0.3):
        """Simple text completion"""
        client = self.get_client()
        
        response = await client.chat.completions.create(
            model="mistralai/Pixtral-12B-2409",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return response.choices[0].message.content
    
    async def vision_completion(self, prompt, image_base64, max_tokens=2000, temperature=0.1):
        """Vision completion with image"""
        client = self.get_client()
        
        response = await client.chat.completions.create(
            model="mistralai/Pixtral-12B-2409",
            messages=[{
                "role": "user", 
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]
            }],
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return response.choices[0].message.content

# Global client instance
_pixtral_client = None

def get_pixtral_client():
    global _pixtral_client
    if _pixtral_client is None:
        _pixtral_client = PixtralClient()
    return _pixtral_client

# Retry decorator for common error handling
def retry_on_timeout(max_attempts=3, delay=1.0, timeout=30.0):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
                except asyncio.TimeoutError:
                    if attempt < max_attempts - 1:
                        print(f"⏰ Attempt {attempt + 1} timed out after {timeout}s, retrying...")
                        await asyncio.sleep(delay)
                        continue
                    raise
                except Exception as e:
                    if attempt < max_attempts - 1 and ("timeout" in str(e).lower() or "timed out" in str(e).lower()):
                        print(f"🔄 Attempt {attempt + 1} failed ({str(e)[:50]}), retrying...")
                        await asyncio.sleep(delay)
                        continue
                    raise
            return None
        return wrapper
    return decorator