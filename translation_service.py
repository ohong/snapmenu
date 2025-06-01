import aiohttp
import asyncio
import os

LANGUAGE_CODES = {
    "en": "English",
    "zh": "Mandarin Chinese", 
    "es": "Spanish",
    "hi": "Hindi",
    "ar": "Arabic", 
    "pt": "Portuguese",
    "ru": "Russian",
    "ja": "Japanese",
    "de": "German",
    "fr": "French"
}

async def translate_dishes(dishes, target_language):
    """Translate dish names and descriptions using Mistral LLM"""
    if target_language == "en":
        # If target is English, just copy original to translated fields
        for dish in dishes:
            dish['name_translated'] = dish.get('name_original', '')
            dish['description_translated'] = dish.get('description_original', '')
        return dishes
    
    target_lang_name = LANGUAGE_CODES.get(target_language, "English")
    
    # Batch translate all dishes at once for efficiency
    try:
        translation_result = await translate_menu_with_pixtral(dishes, target_lang_name)
        
        if translation_result:
            # Parse the translation result and update dishes
            return parse_translation_result(dishes, translation_result)
        else:
            # Fallback: use original text
            for dish in dishes:
                dish['name_translated'] = dish.get('name_original', '')
                dish['description_translated'] = dish.get('description_original', '')
            return dishes
            
    except Exception as e:
        print(f"Translation failed: {str(e)}")
        # Fallback: use original text
        for dish in dishes:
            dish['name_translated'] = dish.get('name_original', '')
            dish['description_translated'] = dish.get('description_original', '')
        return dishes

async def translate_menu_with_pixtral(dishes, target_language):
    """Use Pixtral 12B to translate entire menu at once"""
    try:
        endpoint = os.getenv('PIXTRAL_ENDPOINT')
        api_key = os.getenv('KOYEB_API_KEY')
        
        if not endpoint or not api_key:
            raise ValueError("Missing PIXTRAL_ENDPOINT or KOYEB_API_KEY")
        
        # Prepare menu text for translation
        menu_items = []
        for i, dish in enumerate(dishes):
            name = dish.get('name_original', '')
            desc = dish.get('description_original', '')
            menu_items.append(f"{i+1}. {name} - {desc}")
        
        menu_text = "\n".join(menu_items)
        
        translation_prompt = f"""Translate the following restaurant menu items to {target_language}. 
Maintain the same numbering and structure. For each item, translate both the dish name and description.
Keep the format as: "Number. Dish Name - Description"

Provide accurate, culturally appropriate translations that would appeal to native speakers.

Menu items to translate:
{menu_text}

Translated menu:"""
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "prompt": translation_prompt,
            "max_tokens": 2000,
            "temperature": 0.3
        }
        
        timeout = aiohttp.ClientTimeout(total=5)  # 5 seconds for batch translation
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(endpoint, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('text', '')
                else:
                    error_text = await response.text()
                    print(f"Pixtral translation failed with status {response.status}: {error_text}")
                    return None
                    
    except Exception as e:
        print(f"Pixtral translation error: {str(e)}")
        return None

def parse_translation_result(original_dishes, translation_text):
    """Parse Pixtral translation result and update dishes"""
    if not translation_text:
        return original_dishes
    
    translated_lines = [line.strip() for line in translation_text.split('\n') if line.strip()]
    
    for i, dish in enumerate(original_dishes):
        # Try to find corresponding translated line
        translated_line = None
        
        # Look for line starting with the item number
        for line in translated_lines:
            if line.startswith(f"{i+1}."):
                translated_line = line
                break
        
        if translated_line:
            # Parse the translated line
            try:
                # Remove number prefix
                content = translated_line[translated_line.index('.') + 1:].strip()
                
                # Split on ' - ' to separate name and description
                if ' - ' in content:
                    name_part, desc_part = content.split(' - ', 1)
                    dish['name_translated'] = name_part.strip()
                    dish['description_translated'] = desc_part.strip()
                else:
                    dish['name_translated'] = content.strip()
                    dish['description_translated'] = dish.get('description_original', '')
                    
            except Exception as e:
                print(f"Failed to parse translation for dish {i+1}: {str(e)}")
                dish['name_translated'] = dish.get('name_original', '')
                dish['description_translated'] = dish.get('description_original', '')
        else:
            # No translation found, use original
            dish['name_translated'] = dish.get('name_original', '')
            dish['description_translated'] = dish.get('description_original', '')
    
    return original_dishes

