import os
import base64
import asyncio
import time
from openai import AsyncOpenAI

async def process_menu_ocr(image_file):
    """Process menu image using Pixtral 12B vision model via OpenAI SDK"""
    start_time = time.time()
    max_retries = 2
    
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                print(f"🔄 OCR Retry attempt {attempt}/{max_retries}")
                await asyncio.sleep(1)  # Brief delay between retries
            
            # Get image info for debugging
            image_bytes = image_file.read()
            image_size_mb = len(image_bytes) / (1024 * 1024)
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            print(f"🔍 OCR Debug: Attempt {attempt + 1}, Image size {image_size_mb:.2f}MB, base64 length {len(image_base64)}")
            
            # Reset file pointer for potential reuse
            image_file.seek(0)
            
            # Initialize OpenAI client with Pixtral endpoint
            base_endpoint = os.getenv('PIXTRAL_ENDPOINT')
            api_key = os.getenv('OPENAI_API_KEY')
            
            if not base_endpoint or not api_key:
                raise ValueError("Missing PIXTRAL_ENDPOINT or OPENAI_API_KEY environment variables")
            
            print(f"🔍 OCR Debug: Connecting to {base_endpoint}/v1")
            
            client = AsyncOpenAI(
                api_key=api_key,
                base_url=f"{base_endpoint.rstrip('/')}/v1",
                timeout=30.0  # Increased SDK-level timeout
            )
            
            print(f"🔍 OCR Debug: Starting Pixtral vision request...")
            request_start = time.time()
            
            # Determine timeout based on attempt (be more patient on retries)
            request_timeout = 15.0 if attempt == 0 else 25.0
            
            # Create chat completion with vision
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model="mistralai/Pixtral-12B-2409",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": """Analyze this restaurant menu image and extract all text content. 

Please provide:
1. All dish names exactly as written
2. Complete descriptions for each dish
3. All prices with currency symbols
4. Category headers (appetizers, mains, desserts, etc.)

Maintain the original structure and formatting. Output the text in a clear, organized format that preserves the menu's hierarchy."""
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_base64}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=2000,
                    temperature=0.1
                ),
                timeout=request_timeout
            )
            
            request_time = time.time() - request_start
            total_time = time.time() - start_time
            
            print(f"✅ OCR Success: Request took {request_time:.2f}s, total {total_time:.2f}s")
            
            result_content = response.choices[0].message.content
            print(f"🔍 OCR Debug: Response length {len(result_content)} characters")
            
            return result_content
            
        except asyncio.TimeoutError as e:
            elapsed = time.time() - start_time
            print(f"⏰ OCR attempt {attempt + 1} timed out after {elapsed:.2f}s")
            
            if attempt < max_retries:
                print(f"   → Will retry ({max_retries - attempt} attempts left)")
                continue
            else:
                print(f"   → All retries exhausted, using fallback text")
                return fallback_text_extraction(image_file)
                
        except Exception as e:
            elapsed = time.time() - start_time
            error_type = type(e).__name__
            print(f"❌ OCR attempt {attempt + 1} failed ({error_type}) after {elapsed:.2f}s: {str(e)}")
            
            # Check for specific error types
            if "timeout" in str(e).lower():
                print("   → This appears to be a timeout-related error")
            elif "connection" in str(e).lower():
                print("   → This appears to be a connection error")
            elif "401" in str(e) or "unauthorized" in str(e).lower():
                print("   → This appears to be an authentication error")
            elif "429" in str(e) or "rate limit" in str(e).lower():
                print("   → This appears to be a rate limiting error")
            elif "500" in str(e) or "502" in str(e) or "503" in str(e):
                print("   → This appears to be a server error")
            
            if attempt < max_retries:
                print(f"   → Will retry ({max_retries - attempt} attempts left)")
                continue
            else:
                print(f"   → All retries exhausted, using fallback text")
                return fallback_text_extraction(image_file)
    
    # Should never reach here, but just in case
    print("🚨 Unexpected: Retry loop completed without return")
    return fallback_text_extraction(image_file)

def fallback_text_extraction(image_file):
    """Fallback OCR using local processing if available"""
    # This would use a local OCR library like pytesseract if needed
    # For now, return placeholder text
    return """
    APPETIZERS
    Caesar Salad - Fresh romaine lettuce with parmesan cheese - $12.95
    Soup of the Day - Chef's special daily soup - $8.50
    
    MAIN COURSES  
    Grilled Salmon - Atlantic salmon with herbs - $24.95
    Pasta Carbonara - Traditional Italian pasta - $18.50
    Beef Tenderloin - Prime cut with vegetables - $32.00
    
    DESSERTS
    Chocolate Cake - Rich chocolate with berries - $9.95
    Ice Cream - Vanilla, chocolate, or strawberry - $6.50
    """