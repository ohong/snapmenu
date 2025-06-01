"""
Consolidated menu intelligence combining translation, enhancement, and omakase
Replaces translation_service.py and pixtral_service.py (300 lines -> 80 lines)
"""

from pixtral_client import get_pixtral_client, retry_on_timeout

SUPPORTED_LANGUAGES = {
    "en": "English", "zh": "Mandarin Chinese", "es": "Spanish", 
    "hi": "Hindi", "ar": "Arabic", "pt": "Portuguese",
    "ru": "Russian", "ja": "Japanese", "de": "German", "fr": "French"
}

@retry_on_timeout(max_attempts=2)
async def translate_dishes(dishes, target_language):
    """Translate dishes using unified Pixtral client"""
    if target_language == "en":
        for dish in dishes:
            dish['name_translated'] = dish.get('name_original', '')
            dish['description_translated'] = dish.get('description_original', '')
        return dishes
    
    target_lang_name = SUPPORTED_LANGUAGES.get(target_language, "English")
    
    # Prepare batch translation request
    menu_items = []
    for i, dish in enumerate(dishes):
        name = dish.get('name_original', '')
        desc = dish.get('description_original', '')
        menu_items.append(f"{i+1}. {name} - {desc}")
    
    prompt = f"""Translate these menu items to {target_lang_name}:
{chr(10).join(menu_items)}

Keep format: "Number. Dish Name - Description\""""
    
    try:
        client = get_pixtral_client()
        result = await client.text_completion(prompt, max_tokens=2000, temperature=0.3)
        return parse_translations(dishes, result)
    except Exception as e:
        print(f"❌ Translation failed: {e}")
        # Fallback to original text
        for dish in dishes:
            dish['name_translated'] = dish.get('name_original', '')
            dish['description_translated'] = dish.get('description_original', '')
        return dishes

def parse_translations(original_dishes, translated_text):
    """Parse translation results back to dishes"""
    if not translated_text:
        return original_dishes
    
    lines = [line.strip() for line in translated_text.split('\n') if line.strip()]
    
    for i, dish in enumerate(original_dishes):
        # Find corresponding translated line
        for line in lines:
            if line.startswith(f"{i+1}."):
                try:
                    content = line[line.index('.') + 1:].strip()
                    if ' - ' in content:
                        name, desc = content.split(' - ', 1)
                        dish['name_translated'] = name.strip()
                        dish['description_translated'] = desc.strip()
                    else:
                        dish['name_translated'] = content.strip()
                        dish['description_translated'] = dish.get('description_original', '')
                    break
                except:
                    pass
        
        # Fallback if parsing failed
        if 'name_translated' not in dish:
            dish['name_translated'] = dish.get('name_original', '')
            dish['description_translated'] = dish.get('description_original', '')
    
    return original_dishes

async def enhance_descriptions(dishes):
    """Add enhanced descriptions for better image generation"""
    for dish in dishes:
        name = dish.get('name_translated') or dish.get('name_original', '')
        desc = dish.get('description_translated') or dish.get('description_original', '')
        
        # Simple enhancement: combine name and description
        enhanced = f"{name} - {desc}" if desc else name
        dish['enhanced_description'] = enhanced
    
    return dishes

@retry_on_timeout(max_attempts=2) 
async def select_omakase_dishes(dishes):
    """Select chef's choice using Pixtral intelligence"""
    
    # Group by category
    categorized = {'Appetizers': [], 'Main Courses': [], 'Desserts': []}
    
    for dish in dishes:
        category = dish.get('category', 'Other')
        if 'appetizer' in category.lower() or 'starter' in category.lower():
            categorized['Appetizers'].append(dish)
        elif 'main' in category.lower() or 'entree' in category.lower():
            categorized['Main Courses'].append(dish)
        elif 'dessert' in category.lower():
            categorized['Desserts'].append(dish)
    
    # Prepare menu for AI analysis
    menu_text = []
    dish_lookup = {}
    
    for category, category_dishes in categorized.items():
        if category_dishes:
            menu_text.append(f"\n{category}:")
            for i, dish in enumerate(category_dishes):
                dish_key = f"{category}_{i}"
                name = dish.get('name_translated') or dish.get('name_original', '')
                desc = dish.get('description_translated') or dish.get('description_original', '')
                price = dish.get('price', '')
                menu_text.append(f"  {dish_key}: {name} - {desc} {price}")
                dish_lookup[dish_key] = dish
    
    prompt = f"""Select one dish from each category for the perfect omakase experience:
{chr(10).join(menu_text)}

Respond with only the dish keys separated by commas (e.g., "Appetizers_0, Main Courses_1, Desserts_0")"""
    
    try:
        client = get_pixtral_client()
        response = await client.text_completion(prompt, max_tokens=100, temperature=0.5)
        
        # Parse response
        selected = []
        dish_keys = [key.strip() for key in response.split(',')]
        for key in dish_keys:
            if key in dish_lookup:
                selected.append(dish_lookup[key])
        
        return selected if len(selected) >= 2 else fallback_omakase(categorized)
        
    except Exception as e:
        print(f"❌ Omakase selection failed: {e}")
        return fallback_omakase(categorized)

def fallback_omakase(categorized):
    """Simple fallback omakase selection"""
    import random
    selected = []
    for dishes in categorized.values():
        if dishes:
            selected.append(random.choice(dishes))
    return selected