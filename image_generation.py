import aiohttp
import asyncio
import time
import random
import os

async def generate_dish_images(dishes, timeout=8, max_images=20, style_prompt=""):
    """Generate images for dishes with timeout constraint"""
    start_time = time.time()
    generated = 0
    
    # Randomize order to ensure variety if timeout hit
    shuffled_dishes = random.sample(dishes, len(dishes))
    
    # Limit concurrent requests to avoid overwhelming the API
    semaphore = asyncio.Semaphore(3)
    
    async def generate_single_image(dish):
        nonlocal generated
        
        if generated >= max_images or (time.time() - start_time) > timeout:
            return dish
        
        async with semaphore:
            try:
                # Construct prompt for image generation using enhanced description
                dish_name = dish.get('name_translated') or dish.get('name_original', '')
                # Use enhanced description if available, otherwise fall back to regular description
                description = (dish.get('enhanced_description') or 
                             dish.get('description_translated') or 
                             dish.get('description_original', ''))
                
                prompt = f"{style_prompt}. Dish: {dish_name}. {description}"
                
                image_url = await flux_generate_image(prompt)
                if image_url:
                    dish['generated_image_url'] = image_url
                    generated += 1
                else:
                    dish['generated_image_url'] = None
                    
            except Exception as e:
                print(f"Image generation failed for {dish.get('name_translated', 'unknown')}: {str(e)}")
                dish['generated_image_url'] = None
            
            return dish
    
    # Generate images concurrently
    tasks = [generate_single_image(dish) for dish in shuffled_dishes]
    
    try:
        # Wait for all tasks with overall timeout
        remaining_time = max(0, timeout - (time.time() - start_time))
        await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=remaining_time
        )
    except asyncio.TimeoutError:
        print(f"Image generation timed out after {timeout} seconds")
    
    return dishes

async def flux_generate_image(prompt, resolution="512x512"):
    """Generate single image using FLUX.1 model on Koyeb"""
    try:
        endpoint = os.getenv('FLUX_ENDPOINT')
        api_key = os.getenv('KOYEB_API_KEY')
        
        if not endpoint or not api_key:
            raise ValueError("Missing FLUX_ENDPOINT or KOYEB_API_KEY environment variables")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "prompt": prompt,
            "num_inference_steps": 20,  # Reduced for speed
            "guidance_scale": 7.5,
            "width": 512,
            "height": 512
        }
        
        # Set timeout for individual image generation
        timeout = aiohttp.ClientTimeout(total=4)  # 4 seconds per image
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(endpoint, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('image_url')
                else:
                    error_text = await response.text()
                    print(f"FLUX API failed with status {response.status}: {error_text}")
                    return None
                    
    except asyncio.TimeoutError:
        print("Individual image generation timed out")
        return None
    except Exception as e:
        print(f"Image generation error: {str(e)}")
        return None

def get_placeholder_image_url():
    """Return placeholder image URL for dishes without generated images"""
    return "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTEyIiBoZWlnaHQ9IjUxMiIgdmlld0JveD0iMCAwIDUxMiA1MTIiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSI1MTIiIGhlaWdodD0iNTEyIiBmaWxsPSIjRjNGNEY2Ii8+CjxwYXRoIGQ9Ik0yNTYgMjAwVjMxMk0yMDAgMjU2SDMxMiIgc3Ryb2tlPSIjOUI5QkEwIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K"