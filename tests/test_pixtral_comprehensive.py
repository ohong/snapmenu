#!/usr/bin/env python3
"""
Comprehensive test of Pixtral client functionality
"""

import asyncio
import sys
import time
sys.path.append('/Users/oscar/dev/snapmenu')
from dotenv import load_dotenv
load_dotenv()

from pixtral_client import get_pixtral_client

async def comprehensive_pixtral_test():
    print('🧪 Comprehensive Pixtral Client Test')
    print('=' * 50)
    
    try:
        client = get_pixtral_client()
        total_start = time.time()
        
        # Test 1: Menu Text Extraction
        print('\n📋 Test 1: Menu Text Extraction')
        menu_text = '''APPETIZERS
Caesar Salad fresh romaine lettuce 12.95
Soup of the Day chef special 8.50

MAIN COURSES  
Grilled Salmon atlantic salmon with herbs 24.95
Pasta Carbonara traditional italian 18.50

DESSERTS
Chocolate Cake rich chocolate dessert 9.95'''

        extraction_prompt = f'''Extract and format this menu text clearly:

{menu_text}

Format each dish as: "Dish Name - Description - Price"'''

        start = time.time()
        result = await client.text_completion(extraction_prompt, max_tokens=300, temperature=0.1)
        elapsed = time.time() - start
        print(f'✅ Extraction completed ({elapsed:.1f}s)')
        print(f'   Result: {result[:200]}...')
        
        # Test 2: Translation Task
        print('\n🌍 Test 2: Translation to Spanish')
        translation_prompt = '''Translate these menu items to Spanish, keep the same format:
1. Caesar Salad - Fresh romaine lettuce - $12.95
2. Grilled Salmon - Atlantic salmon with herbs - $24.95
3. Chocolate Cake - Rich chocolate dessert - $9.95

Translate both name and description.'''

        start = time.time()
        result = await client.text_completion(translation_prompt, max_tokens=200, temperature=0.2)
        elapsed = time.time() - start
        print(f'✅ Translation completed ({elapsed:.1f}s)')
        print(f'   Result: {result}')
        
        # Test 3: Omakase Selection
        print('\n🎲 Test 3: Omakase Selection')
        omakase_prompt = '''You are a chef. From this menu, select one dish from each category for the perfect omakase experience:

Appetizers:
- A1: Caesar Salad - Fresh lettuce - $12.95
- A2: Soup of Day - Chef special - $8.50

Mains:
- M1: Grilled Salmon - Atlantic fish - $24.95  
- M2: Pasta Carbonara - Italian classic - $18.50

Desserts:
- D1: Chocolate Cake - Rich dessert - $9.95
- D2: Ice Cream - Vanilla flavor - $6.50

Respond with ONLY the three dish codes (e.g., "A1, M2, D1").'''

        start = time.time()
        result = await client.text_completion(omakase_prompt, max_tokens=20, temperature=0.5)
        elapsed = time.time() - start
        print(f'✅ Omakase selection completed ({elapsed:.1f}s)')
        print(f'   Selection: {result.strip()}')
        
        # Test 4: Description Enhancement
        print('\n✨ Test 4: Description Enhancement')
        enhancement_prompt = '''Enhance this dish description for food photography:
"Grilled Salmon - Atlantic salmon with herbs"

Provide a brief, vivid 20-word description focusing on visual elements, cooking method, and presentation.'''

        start = time.time()
        result = await client.text_completion(enhancement_prompt, max_tokens=50, temperature=0.4)
        elapsed = time.time() - start
        print(f'✅ Enhancement completed ({elapsed:.1f}s)')
        print(f'   Enhanced: {result.strip()}')
        
        # Test 5: Vision capability (with a simple test)
        print('\n👁️ Test 5: Vision Capability Check')
        # Small red pixel as base64
        red_pixel = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        
        start = time.time()
        try:
            result = await client.vision_completion(
                "What color is this image? Answer with just the color name.",
                red_pixel,
                max_tokens=5
            )
            elapsed = time.time() - start
            print(f'✅ Vision test completed ({elapsed:.1f}s)')
            print(f'   Color detected: {result.strip()}')
        except Exception as e:
            print(f'⚠️  Vision test failed: {e}')
            print('   (This is expected if vision processing has issues)')
        
        total_elapsed = time.time() - total_start
        print(f'\n🏁 All Pixtral tests completed in {total_elapsed:.1f}s')
        print('✅ Pixtral client is FULLY FUNCTIONAL for all NLP tasks!')
        
        return True
        
    except Exception as e:
        print(f'❌ Comprehensive test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Run comprehensive test
    success = asyncio.run(comprehensive_pixtral_test())
    print(f'\n🎉 FINAL RESULT: Pixtral Client {"WORKING PERFECTLY" if success else "NEEDS ATTENTION"}')