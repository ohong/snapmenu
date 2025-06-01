import aiohttp
import asyncio
import os
import base64

async def call_pixtral(prompt, image_base64=None, max_tokens=1000, temperature=0.3):
    """General purpose Pixtral 12B API call"""
    try:
        endpoint = os.getenv('PIXTRAL_ENDPOINT')
        api_key = os.getenv('KOYEB_API_KEY')
        
        if not endpoint or not api_key:
            raise ValueError("Missing PIXTRAL_ENDPOINT or KOYEB_API_KEY environment variables")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # Add image if provided (for vision tasks)
        if image_base64:
            payload["image"] = image_base64
        
        timeout = aiohttp.ClientTimeout(total=10)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(endpoint, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('text', '')
                else:
                    error_text = await response.text()
                    raise Exception(f"Pixtral API failed with status {response.status}: {error_text}")
                    
    except asyncio.TimeoutError:
        raise Exception("Pixtral API call timed out")
    except Exception as e:
        raise Exception(f"Pixtral API call failed: {str(e)}")

async def select_omakase_dishes(dishes):
    """Use Pixtral 12B to select chef's choice dishes"""
    try:
        # Group dishes by category
        categorized = {
            'Appetizers': [],
            'Main Courses': [], 
            'Desserts': []
        }
        
        for dish in dishes:
            category = dish.get('category', 'Other')
            # Map common category variations
            if 'appetizer' in category.lower() or 'starter' in category.lower():
                categorized['Appetizers'].append(dish)
            elif 'main' in category.lower() or 'entree' in category.lower():
                categorized['Main Courses'].append(dish)
            elif 'dessert' in category.lower() or 'sweet' in category.lower():
                categorized['Desserts'].append(dish)
        
        # Prepare menu for analysis
        menu_description = []
        dish_lookup = {}
        
        for category, category_dishes in categorized.items():
            if category_dishes:
                menu_description.append(f"\n{category}:")
                for i, dish in enumerate(category_dishes):
                    dish_key = f"{category}_{i}"
                    name = dish.get('name_translated') or dish.get('name_original', '')
                    desc = dish.get('description_translated') or dish.get('description_original', '')
                    price = dish.get('price', '')
                    
                    menu_description.append(f"  {dish_key}: {name} - {desc} {price}")
                    dish_lookup[dish_key] = dish
        
        menu_text = "\n".join(menu_description)
        
        omakase_prompt = f"""You are an expert chef analyzing this restaurant menu. Please select one dish from each category (Appetizers, Main Courses, Desserts) to create the perfect "Omakase" (chef's choice) experience.

Consider:
- Flavor balance and variety
- Complementary cooking techniques  
- Progression from light to rich
- Overall dining experience

Available dishes:
{menu_text}

Please respond with ONLY the dish keys (e.g., "Appetizers_0, Main Courses_2, Desserts_1") for your selected combination, separated by commas."""

        response = await call_pixtral(omakase_prompt, max_tokens=200, temperature=0.5)
        
        # Parse the response to get selected dishes
        selected_dishes = []
        if response:
            dish_keys = [key.strip() for key in response.split(',')]
            for dish_key in dish_keys:
                if dish_key in dish_lookup:
                    selected_dishes.append(dish_lookup[dish_key])
        
        return selected_dishes
        
    except Exception as e:
        print(f"Omakase selection failed: {str(e)}")
        # Fallback: random selection
        import random
        fallback_selection = []
        for category_dishes in categorized.values():
            if category_dishes:
                fallback_selection.append(random.choice(category_dishes))
        return fallback_selection

async def enhance_dish_descriptions(dishes):
    """Use Pixtral 12B to enhance dish descriptions for better image generation"""
    try:
        enhanced_dishes = []
        
        for dish in dishes:
            name = dish.get('name_translated') or dish.get('name_original', '')
            current_desc = dish.get('description_translated') or dish.get('description_original', '')
            
            enhancement_prompt = f"""Given this dish name and description, create a brief, vivid description suitable for AI image generation:

Dish: {name}
Current description: {current_desc}

Please provide a concise description (20-30 words) that captures:
- Key visual elements
- Cooking method
- Main ingredients
- Presentation style

Enhanced description:"""
            
            try:
                enhanced_desc = await call_pixtral(enhancement_prompt, max_tokens=100, temperature=0.4)
                if enhanced_desc and enhanced_desc.strip():
                    dish['enhanced_description'] = enhanced_desc.strip()
                else:
                    dish['enhanced_description'] = current_desc
            except Exception as e:
                print(f"Failed to enhance description for {name}: {str(e)}")
                dish['enhanced_description'] = current_desc
            
            enhanced_dishes.append(dish)
        
        return enhanced_dishes
        
    except Exception as e:
        print(f"Description enhancement failed: {str(e)}")
        return dishes