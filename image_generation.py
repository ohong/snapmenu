import aiohttp
import asyncio
import time
import random
import os

async def generate_dish_images(dishes, timeout=30, max_images=20, style_prompt=""):
    """Generate images for dishes with aggressive retry to ensure minimum 3 images"""
    start_time = time.time()
    min_images = 3  # Minimum required images
    max_timeout = 30  # Hard maximum timeout
    
    # Prioritize dishes - spread across categories if possible
    priority_dishes = prioritize_dishes_for_images(dishes, max_images)
    
    # Initialize all dishes with None image URLs
    for dish in dishes:
        dish['generated_image_url'] = None
    
    print(f"🎯 MISSION: Generate minimum {min_images} images within {max_timeout}s")
    
    # Aggressive Phase: Keep trying until we get 3 images or hit max timeout
    successful_count = 0
    attempt_round = 1
    dish_pool = priority_dishes.copy()  # Pool of dishes to try
    
    while successful_count < min_images and (time.time() - start_time) < max_timeout:
        elapsed = time.time() - start_time
        remaining = max_timeout - elapsed
        
        print(f"🔄 Round {attempt_round}: {successful_count}/{min_images} images so far, {remaining:.1f}s remaining")
        
        if remaining < 5:  # Less than 5 seconds left, be more aggressive
            print("⚡ SPRINT MODE: Using simple prompts for speed")
            
        # Try to generate images for dishes that don't have them yet
        failed_dishes = [d for d in dish_pool if not d.get('generated_image_url')]
        
        if not failed_dishes:
            # All priority dishes tried, expand pool
            failed_dishes = [d for d in dishes if not d.get('generated_image_url')]
            if not failed_dishes:
                break  # All dishes have been tried
        
        # Limit attempts per round to avoid infinite loops
        dishes_this_round = failed_dishes[:min(5, min_images - successful_count + 2)]
        
        for dish in dishes_this_round:
            if successful_count >= min_images:
                break
                
            if (time.time() - start_time) >= max_timeout:
                print("⏰ Hard timeout reached")
                break
            
            try:
                dish_name = dish.get('name_translated') or dish.get('name_original', '')
                
                # Choose prompt strategy based on time remaining and attempt round
                if remaining < 10 or attempt_round > 2:
                    # Use simple prompt for speed
                    prompt = f"food photography, {dish_name}"
                    print(f"⚡ FAST attempt {attempt_round}: {dish_name}")
                else:
                    # Use full prompt
                    description = (dish.get('enhanced_description') or 
                                 dish.get('description_translated') or 
                                 dish.get('description_original', ''))
                    prompt = f"{style_prompt}. Dish: {dish_name}. {description}"
                    print(f"🔥 Full attempt {attempt_round}: {dish_name}")
                
                # Generate with shorter individual timeout as we get more aggressive
                individual_timeout = max(3, min(10, remaining / 3))
                image_url = await flux_generate_image_with_timeout(prompt, individual_timeout)
                
                if image_url:
                    dish['generated_image_url'] = image_url
                    successful_count += 1
                    print(f"✅ SUCCESS {successful_count}/{min_images}: {dish_name} (Round {attempt_round})")
                else:
                    print(f"❌ Failed: {dish_name}")
                    
            except Exception as e:
                print(f"❌ Error for {dish.get('name_translated', 'unknown')}: {str(e)}")
        
        attempt_round += 1
        
        # Quick break between rounds if we still need more
        if successful_count < min_images and (time.time() - start_time) < max_timeout - 1:
            await asyncio.sleep(0.5)  # Brief pause between rounds
    
    # Concurrent bonus phase if we achieved minimum and have time
    final_elapsed = time.time() - start_time
    remaining_time = max_timeout - final_elapsed
    
    if successful_count >= min_images and remaining_time > 3:
        print(f"🎨 BONUS PHASE: {remaining_time:.1f}s left for additional images")
        
        bonus_dishes = [d for d in dishes if not d.get('generated_image_url')][:5]
        if bonus_dishes:
            semaphore = asyncio.Semaphore(3)  # More aggressive concurrency
            
            async def generate_bonus_image(dish):
                async with semaphore:
                    try:
                        dish_name = dish.get('name_translated') or dish.get('name_original', '')
                        prompt = f"food photography, {dish_name}, restaurant dish"
                        image_url = await flux_generate_image_with_timeout(prompt, 4)
                        
                        if image_url:
                            dish['generated_image_url'] = image_url
                            print(f"🎁 Bonus image: {dish_name}")
                            return True
                        return False
                    except:
                        return False
            
            tasks = [generate_bonus_image(dish) for dish in bonus_dishes]
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=remaining_time - 1
                )
            except asyncio.TimeoutError:
                print("⏰ Bonus phase timeout")
    
    # Final count and status
    final_count = sum(1 for dish in dishes if dish.get('generated_image_url'))
    total_time = time.time() - start_time
    
    print(f"🏁 FINAL RESULT: {final_count}/{len(dishes)} images in {total_time:.1f}s")
    
    if final_count >= min_images:
        print(f"🎉 SUCCESS! Generated {final_count} images (minimum {min_images} achieved)")
    else:
        print(f"⚠️  PARTIAL SUCCESS: Only {final_count}/{min_images} minimum images generated")
    
    return dishes

async def flux_generate_image_with_timeout(prompt, timeout_seconds):
    """Generate image with specific timeout"""
    try:
        return await asyncio.wait_for(
            flux_generate_image(prompt),
            timeout=timeout_seconds
        )
    except asyncio.TimeoutError:
        print(f"   ⏰ Individual timeout ({timeout_seconds}s)")
        return None

def prioritize_dishes_for_images(dishes, max_count):
    """Prioritize dishes for image generation to ensure variety across categories"""
    if not dishes:
        return []
    
    # Group by category
    categories = {}
    for dish in dishes:
        category = dish.get('category', 'Other')
        if category not in categories:
            categories[category] = []
        categories[category].append(dish)
    
    # Select dishes round-robin across categories
    prioritized = []
    category_lists = list(categories.values())
    
    # Ensure we have dishes from each category first
    max_rounds = max(len(cat_list) for cat_list in category_lists) if category_lists else 0
    
    for round_num in range(max_rounds):
        for cat_list in category_lists:
            if round_num < len(cat_list) and len(prioritized) < max_count:
                prioritized.append(cat_list[round_num])
    
    return prioritized

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
        timeout = aiohttp.ClientTimeout(total=15)  # Increased timeout for FLUX
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for i, payload in enumerate(payloads_to_try):
                try:
                    print(f"   Trying FLUX payload format {i+1}...")
                    async with session.post(endpoint, json=payload, headers=headers) as response:
                        print(f"   FLUX response status: {response.status}")
                        
                        if response.status == 200:
                            result = await response.json()
                            print(f"   FLUX response keys: {list(result.keys())}")
                            
                            # Handle FLUX /predict response format
                            if 'images' in result and result['images']:
                                # FLUX returns images as base64 strings or URLs
                                image_data = result['images'][0]
                                print(f"   Got image data (length: {len(str(image_data))})")
                                
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
                                print(f"   Found image URL in alternate format")
                                return image_url
                                
                            print(f"   No image found in response: {result}")
                            
                        elif response.status == 404:
                            print(f"FLUX endpoint not found: {endpoint}")
                            break  # Don't try other payloads if endpoint doesn't exist
                        else:
                            error_text = await response.text()
                            print(f"FLUX API attempt {i+1} failed with status {response.status}: {error_text[:200]}...")
                            
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