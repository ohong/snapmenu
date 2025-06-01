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
    """Translate dish names and descriptions to target language"""
    if target_language == "en":
        # If target is English, just copy original to translated fields
        for dish in dishes:
            dish['name_translated'] = dish.get('name_original', '')
            dish['description_translated'] = dish.get('description_original', '')
        return dishes
    
    # Create translation tasks
    translation_tasks = []
    
    for dish in dishes:
        name_task = translate_text(
            dish.get('name_original', ''), 
            target_language
        )
        desc_task = translate_text(
            dish.get('description_original', ''), 
            target_language
        )
        translation_tasks.append((dish, name_task, desc_task))
    
    # Execute translations concurrently with timeout
    try:
        for dish, name_task, desc_task in translation_tasks:
            name_result, desc_result = await asyncio.gather(
                name_task, desc_task, return_exceptions=True
            )
            
            # Handle translation results
            dish['name_translated'] = name_result if isinstance(name_result, str) else dish.get('name_original', '')
            dish['description_translated'] = desc_result if isinstance(desc_result, str) else dish.get('description_original', '')
            
    except Exception as e:
        print(f"Translation batch failed: {str(e)}")
        # Fallback: use original text
        for dish in dishes:
            dish['name_translated'] = dish.get('name_original', '')
            dish['description_translated'] = dish.get('description_original', '')
    
    return dishes

async def translate_text(text, target_language):
    """Translate single text using translation API"""
    if not text or not text.strip():
        return text
    
    try:
        # Use a translation API (could be Google Translate, DeepL, etc.)
        endpoint = os.getenv('TRANSLATION_ENDPOINT')
        api_key = os.getenv('TRANSLATION_API_KEY')
        
        if not endpoint or not api_key:
            # Fallback to simple mapping for demo
            return await fallback_translation(text, target_language)
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": text,
            "target_language": target_language,
            "source_language": "auto"
        }
        
        timeout = aiohttp.ClientTimeout(total=2)  # 2 seconds per translation
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(endpoint, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('translated_text', text)
                else:
                    return text
                    
    except Exception as e:
        print(f"Translation failed for '{text}': {str(e)}")
        return text

async def fallback_translation(text, target_language):
    """Simple fallback translation for demo purposes"""
    # This is a very basic fallback - in production you'd want proper translation
    
    translations = {
        "zh": {
            "Caesar Salad": "凯撒沙拉",
            "Grilled Salmon": "烤三文鱼", 
            "Pasta Carbonara": "奶油培根意面",
            "Chocolate Cake": "巧克力蛋糕",
            "Fresh romaine lettuce": "新鲜罗马生菜",
            "Atlantic salmon": "大西洋三文鱼",
            "Traditional Italian": "传统意大利",
            "Rich chocolate": "浓郁巧克力"
        },
        "es": {
            "Caesar Salad": "Ensalada César",
            "Grilled Salmon": "Salmón a la Parrilla",
            "Pasta Carbonara": "Pasta Carbonara", 
            "Chocolate Cake": "Pastel de Chocolate",
            "Fresh romaine lettuce": "Lechuga romana fresca",
            "Atlantic salmon": "Salmón del Atlántico",
            "Traditional Italian": "Italiano tradicional",
            "Rich chocolate": "Chocolate rico"
        }
    }
    
    if target_language in translations:
        return translations[target_language].get(text, text)
    
    return text