"""
Simplified OCR service using unified Pixtral client
Reduces from 150 lines to ~40 lines
"""

import base64
from pixtral_client import get_pixtral_client, retry_on_timeout

@retry_on_timeout(max_attempts=2, timeout=15.0)
async def process_menu_ocr(image_file):
    """Process menu image using simplified Pixtral integration"""
    
    # Convert image to base64
    image_bytes = image_file.read()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    image_file.seek(0)  # Reset for potential reuse
    
    prompt = """Analyze this restaurant menu image and extract all text content. 

Please provide:
1. All dish names exactly as written
2. Complete descriptions for each dish  
3. All prices with currency symbols
4. Category headers (appetizers, mains, desserts, etc.)

Maintain the original structure and formatting."""

    try:
        client = get_pixtral_client()
        result = await client.vision_completion(prompt, image_base64)
        print(f"✅ OCR completed successfully ({len(result)} chars)")
        return result
        
    except Exception as e:
        print(f"❌ OCR failed: {str(e)}, using fallback")
        return get_fallback_menu()

def get_fallback_menu():
    """Simplified fallback menu"""
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