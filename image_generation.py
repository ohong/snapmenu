import aiohttp
import asyncio
import time
import random
import os

async def generate_dish_images(dishes, timeout=8, max_images=20, style_prompt=""):
    """Generate images for dishes with timeout constraint, ensuring minimum 3 images"""
    start_time = time.time()
    min_images = 3  # Minimum required images
    
    # Prioritize dishes - spread across categories if possible
    priority_dishes = prioritize_dishes_for_images(dishes, max_images)
    
    # Initialize all dishes with None image URLs
    for dish in dishes:
        dish['generated_image_url'] = None
    
    # Phase 1: Generate images for priority dishes (ensure minimum)
    successful_count = 0
    priority_count = min(min_images, len(priority_dishes))
    
    print(f"🎨 Phase 1: Generating {priority_count} priority images (minimum required)")
    
    for i, dish in enumerate(priority_dishes[:priority_count]):
        if (time.time() - start_time) > timeout * 0.8:  # Reserve 20% of time for phase 2
            print(f"⏰ Phase 1 timeout reached")
            break
            
        try:
            dish_name = dish.get('name_translated') or dish.get('name_original', '')
            description = (dish.get('enhanced_description') or 
                         dish.get('description_translated') or 
                         dish.get('description_original', ''))
            
            prompt = f"{style_prompt}. Dish: {dish_name}. {description}"
            
            print(f"🔥 Priority dish {i+1}/{priority_count}: {dish_name}")
            image_url = await flux_generate_image(prompt)
            
            if image_url:
                dish['generated_image_url'] = image_url
                successful_count += 1
                print(f"✅ Priority image {successful_count} generated: {dish_name}")
            else:
                print(f"❌ Priority image failed: {dish_name}")
                
        except Exception as e:
            print(f"❌ Priority image error for {dish.get('name_translated', 'unknown')}: {str(e)}")
    
    # Check if we have minimum images
    if successful_count < min_images:
        print(f"⚠️  Only {successful_count}/{min_images} priority images generated. Trying backup strategy...")
        
        # Phase 1.5: Retry with simpler prompts for failed priority dishes
        for dish in priority_dishes[:priority_count]:
            if dish.get('generated_image_url') is None and successful_count < min_images:
                if (time.time() - start_time) > timeout * 0.9:
                    break
                    
                try:
                    # Use simpler prompt
                    dish_name = dish.get('name_translated') or dish.get('name_original', '')
                    simple_prompt = f"food photography, {dish_name}, restaurant dish"
                    
                    print(f"🔄 Retry with simple prompt: {dish_name}")
                    image_url = await flux_generate_image(simple_prompt)
                    
                    if image_url:
                        dish['generated_image_url'] = image_url
                        successful_count += 1
                        print(f"✅ Retry success {successful_count}: {dish_name}")
                        
                except Exception as e:
                    print(f"❌ Retry failed for {dish.get('name_translated', 'unknown')}: {str(e)}")
    
    # Phase 2: Generate remaining images if time allows
    remaining_time = timeout - (time.time() - start_time)
    if remaining_time > 2 and successful_count < max_images:  # Need at least 2 seconds
        remaining_dishes = [d for d in priority_dishes[priority_count:] if not d.get('generated_image_url')]
        concurrent_count = min(len(remaining_dishes), max_images - successful_count)
        
        if concurrent_count > 0:
            print(f"🎨 Phase 2: Generating {concurrent_count} additional images concurrently")
            
            semaphore = asyncio.Semaphore(2)
            
            async def generate_concurrent_image(dish, dish_index):
                async with semaphore:
                    try:
                        dish_name = dish.get('name_translated') or dish.get('name_original', '')
                        description = (dish.get('enhanced_description') or 
                                     dish.get('description_translated') or 
                                     dish.get('description_original', ''))
                        
                        prompt = f"{style_prompt}. Dish: {dish_name}. {description}"
                        image_url = await flux_generate_image(prompt)
                        
                        if image_url:
                            dish['generated_image_url'] = image_url
                            print(f"✅ Additional image generated: {dish_name}")
                            return True
                        else:
                            print(f"❌ Additional image failed: {dish_name}")
                            return False
                            
                    except Exception as e:
                        print(f"❌ Additional image error: {str(e)}")
                        return False
            
            # Run concurrent generation with timeout
            tasks = [generate_concurrent_image(dish, i) for i, dish in enumerate(remaining_dishes[:concurrent_count])]
            
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=remaining_time - 1  # Reserve 1 second buffer
                )
            except asyncio.TimeoutError:
                print(f"⏰ Phase 2 concurrent generation timed out")
    
    # Final count
    final_count = sum(1 for dish in dishes if dish.get('generated_image_url'))
    print(f"🎨 Image generation complete: {final_count}/{len(dishes)} images generated")
    
    if final_count < min_images:
        print(f"⚠️  WARNING: Only {final_count}/{min_images} minimum images generated")
    else:
        print(f"✅ Success: {final_count} images generated (minimum {min_images} achieved)")
    
    return dishes

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