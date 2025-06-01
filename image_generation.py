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
            print("Missing FLUX_ENDPOINT or KOYEB_API_KEY - using placeholder")
            return get_placeholder_image_url()
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Try different payload formats
        payloads_to_try = [
            # Format 1: Standard FLUX format
            {
                "prompt": prompt,
                "num_inference_steps": 20,
                "guidance_scale": 7.5,
                "width": 512,
                "height": 512
            },
            # Format 2: Simplified format
            {
                "prompt": prompt,
                "steps": 20,
                "guidance": 7.5
            },
            # Format 3: Minimal format
            {
                "prompt": prompt
            }
        ]
        
        # Set timeout for individual image generation
        timeout = aiohttp.ClientTimeout(total=10)  # Increased timeout
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for i, payload in enumerate(payloads_to_try):
                try:
                    async with session.post(endpoint, json=payload, headers=headers) as response:
                        if response.status == 200:
                            result = await response.json()
                            # Handle FLUX /predict response format
                            if 'images' in result and result['images']:
                                # FLUX returns images as base64 strings or URLs
                                image_data = result['images'][0]
                                if image_data.startswith('data:image'):
                                    return image_data  # Already a data URL
                                elif image_data.startswith('http'):
                                    return image_data  # Direct URL
                                else:
                                    # Assume base64, convert to data URL
                                    return f"data:image/png;base64,{image_data}"
                            
                            # Try other response formats as fallback
                            image_url = (result.get('image_url') or 
                                       result.get('url') or 
                                       result.get('image') or
                                       result.get('data', {}).get('url'))
                            if image_url:
                                return image_url
                        elif response.status == 404:
                            print(f"FLUX endpoint not found: {endpoint}")
                            break  # Don't try other payloads if endpoint doesn't exist
                        else:
                            error_text = await response.text()
                            print(f"FLUX API attempt {i+1} failed with status {response.status}: {error_text[:100]}...")
                            
                except asyncio.TimeoutError:
                    print(f"FLUX API attempt {i+1} timed out")
                    continue
                except Exception as e:
                    print(f"FLUX API attempt {i+1} error: {str(e)}")
                    continue
        
        print("All FLUX API attempts failed - using placeholder")
        return get_placeholder_image_url()
                    
    except Exception as e:
        print(f"Image generation error: {str(e)} - using placeholder")
        return get_placeholder_image_url()

def get_placeholder_image_url():
    """Return placeholder image URL for dishes without generated images"""
    return "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTEyIiBoZWlnaHQ9IjUxMiIgdmlld0JveD0iMCAwIDUxMiA1MTIiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSI1MTIiIGhlaWdodD0iNTEyIiBmaWxsPSIjRjNGNEY2Ii8+CjxwYXRoIGQ9Ik0yNTYgMjAwVjMxMk0yMDAgMjU2SDMxMiIgc3Ryb2tlPSIjOUI5QkEwIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K"