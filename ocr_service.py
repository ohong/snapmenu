import aiohttp
import asyncio
import os
import base64
from io import BytesIO

async def process_menu_ocr(image_file):
    """Process menu image using Pixtral 12B vision model on Koyeb"""
    try:
        # Convert uploaded file to base64
        image_bytes = image_file.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Reset file pointer for potential reuse
        image_file.seek(0)
        
        # Prepare API request
        endpoint = os.getenv('PIXTRAL_ENDPOINT')
        api_key = os.getenv('KOYEB_API_KEY')
        
        if not endpoint or not api_key:
            raise ValueError("Missing PIXTRAL_ENDPOINT or KOYEB_API_KEY environment variables")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "image": image_base64,
            "prompt": """Analyze this restaurant menu image and extract all text content. 
            
Please provide:
1. All dish names exactly as written
2. Complete descriptions for each dish
3. All prices with currency symbols
4. Category headers (appetizers, mains, desserts, etc.)

Maintain the original structure and formatting. Output the text in a clear, organized format that preserves the menu's hierarchy."""
        }
        
        # Make async request with timeout
        timeout = aiohttp.ClientTimeout(total=5)  # 5 second timeout for OCR
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(endpoint, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('text', '')
                else:
                    error_text = await response.text()
                    raise Exception(f"Pixtral OCR API failed with status {response.status}: {error_text}")
                    
    except asyncio.TimeoutError:
        raise Exception("OCR processing timed out")
    except Exception as e:
        raise Exception(f"OCR processing failed: {str(e)}")

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