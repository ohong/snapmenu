"""
Simplified image generation focusing on the core requirement:
Generate minimum 3 images within 30 seconds
Reduces from 277 lines to ~100 lines
"""

import asyncio
import time
import aiohttp
import os

async def generate_dish_images(dishes, timeout=30, min_images=3, max_images=20):
    """Simplified image generation with guaranteed minimum"""
    
    start_time = time.time()
    
    # Prioritize dishes across categories
    priority_dishes = select_priority_dishes(dishes, max_images)
    
    # Initialize all with None
    for dish in dishes:
        dish['generated_image_url'] = None
    
    print(f"🎯 Generating minimum {min_images} images (30s timeout)")
    
    # Phase 1: Sequential generation for guaranteed minimum
    successful = 0
    for i, dish in enumerate(priority_dishes[:min_images]):
        if time.time() - start_time > timeout * 0.8:  # Reserve 20% for bonus
            break
            
        dish_name = dish.get('name_translated') or dish.get('name_original', '')
        print(f"🔥 Priority {i+1}/{min_images}: {dish_name}")
        
        try:
            image_url = await generate_single_image(dish_name)
            if image_url:
                dish['generated_image_url'] = image_url
                successful += 1
                print(f"✅ Success {successful}: {dish_name}")
        except Exception as e:
            print(f"❌ Failed: {dish_name}")
    
    # Phase 2: Concurrent generation for bonus images if time allows
    remaining_time = timeout - (time.time() - start_time)
    if remaining_time > 5 and successful >= min_images:
        remaining_dishes = [d for d in priority_dishes[min_images:] if not d.get('generated_image_url')][:5]
        
        if remaining_dishes:
            print(f"🎨 Bonus phase: {len(remaining_dishes)} additional images")
            tasks = [generate_single_image(d.get('name_translated') or d.get('name_original', '')) 
                    for d in remaining_dishes]
            
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=remaining_time - 1
                )
                
                for dish, result in zip(remaining_dishes, results):
                    if isinstance(result, str):  # Success
                        dish['generated_image_url'] = result
                        successful += 1
                        
            except asyncio.TimeoutError:
                print("⏰ Bonus phase timeout")
    
    print(f"🏁 Generated {successful}/{len(dishes)} images ({successful >= min_images and '✅' or '⚠️'})")
    return dishes

async def generate_single_image(dish_name):
    """Generate single image with simplified FLUX integration"""
    endpoint = os.getenv('FLUX_ENDPOINT')
    api_key = os.getenv('KOYEB_API_KEY')
    
    if not endpoint or not api_key:
        return None
    
    payload = {
        "prompt": f"food photography, {dish_name}, restaurant dish",
        "num_inference_steps": 20,
        "guidance_scale": 7.5,
        "width": 512,
        "height": 512
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        timeout = aiohttp.ClientTimeout(total=8)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(endpoint, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    if 'images' in result and result['images']:
                        image_data = result['images'][0]
                        if not image_data.startswith('data:image'):
                            image_data = f"data:image/png;base64,{image_data}"
                        return image_data
                return None
    except:
        return None

def select_priority_dishes(dishes, max_count):
    """Simple round-robin selection across categories"""
    if not dishes:
        return []
    
    # Group by category
    categories = {}
    for dish in dishes:
        category = dish.get('category', 'Other')
        if category not in categories:
            categories[category] = []
        categories[category].append(dish)
    
    # Round-robin selection
    selected = []
    category_lists = list(categories.values())
    max_rounds = max(len(cat) for cat in category_lists) if category_lists else 0
    
    for round_num in range(max_rounds):
        for cat_list in category_lists:
            if round_num < len(cat_list) and len(selected) < max_count:
                selected.append(cat_list[round_num])
    
    return selected