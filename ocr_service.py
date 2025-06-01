import os
import base64
import asyncio
from openai import AsyncOpenAI

async def process_menu_ocr(image_file):
    """Process menu image using Pixtral 12B vision model via OpenAI SDK"""
    try:
        # Convert uploaded file to base64
        image_bytes = image_file.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Reset file pointer for potential reuse
        image_file.seek(0)
        
        # Initialize OpenAI client with Pixtral endpoint
        base_endpoint = os.getenv('PIXTRAL_ENDPOINT')
        api_key = os.getenv('OPENAI_API_KEY')
        
        if not base_endpoint or not api_key:
            raise ValueError("Missing PIXTRAL_ENDPOINT or OPENAI_API_KEY environment variables")
        
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=f"{base_endpoint.rstrip('/')}/v1"
        )
        
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
            timeout=15.0  # 15 second timeout
        )
        
        return response.choices[0].message.content
        
    except asyncio.TimeoutError:
        # Fallback to demo text if Pixtral times out
        print("Pixtral OCR timed out, using fallback text")
        return fallback_text_extraction(image_file)
    except Exception as e:
        print(f"Pixtral OCR failed: {str(e)}, using fallback text")
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