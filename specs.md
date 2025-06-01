# Snapmenu Product Specifications

## Overview
Snapmenu transforms text-only restaurant menus into visual, accessible experiences by generating photorealistic images for each dish. The application processes menu photos, translates content into the user's preferred language, and presents an elegant visual interface—all within 15 seconds.

## Technical Architecture

### Core Components
- **Frontend**: Streamlit application deployed on Koyeb
- **OCR Service**: Mistral LLM on Tenstorrent hardware via Koyeb
- **Image Generation**: FLUX.1 [dev] model on Koyeb
- **Database**: PostgreSQL on Neon
- **Runtime**: Python 3.11+

### Database Schema
```sql
CREATE TABLE menu_uploads (
    id SERIAL PRIMARY KEY,
    upload_timestamp TIMESTAMP DEFAULT NOW(),
    original_image_url TEXT NOT NULL,
    selected_language VARCHAR(10) NOT NULL,
    processing_status VARCHAR(20) DEFAULT 'pending'
);

CREATE TABLE processed_dishes (
    id SERIAL PRIMARY KEY,
    menu_upload_id INTEGER REFERENCES menu_uploads(id),
    dish_name_original TEXT,
    dish_name_translated TEXT,
    description_original TEXT,
    description_translated TEXT,
    price DECIMAL(10,2),
    category VARCHAR(50),
    generated_image_url TEXT,
    display_order INTEGER
);
```

## User Flow

### 1. Initial Upload Screen
- Single-page interface with:
  - Drag-and-drop zone for JPG menu upload (max 10MB)
  - Language selector dropdown: English, Mandarin, Spanish, Hindi, Arabic, Portuguese, Russian, Japanese, German, French
  - "Process Menu" button
  - Clean, minimal design with clear affordances

### 2. Processing Pipeline (15-second constraint)
```python
async def process_menu(image_file, target_language):
    # Phase 1: OCR (target: 3-4 seconds)
    menu_text = await mistral_ocr(image_file)
    
    # Phase 2: Parse and categorize (target: 1-2 seconds)
    dishes = parse_menu_structure(menu_text)
    dishes = categorize_dishes(dishes)  # Identify appetizers, mains, desserts
    
    # Phase 3: Translation if needed (target: 2-3 seconds)
    if source_language != target_language:
        dishes = await translate_dishes(dishes, target_language)
    
    # Phase 4: Image generation (remaining time, max 20 images)
    dishes = await generate_images_with_timeout(
        dishes, 
        timeout=8,  # Reserve 8 seconds for image generation
        max_images=20,
        style_prompt="professional food photography, restaurant dish, appetizing, consistent lighting"
    )
    
    return dishes
```

### 3. Visual Menu Display
- Grid layout (responsive 2-4 columns based on screen size)
- Each dish card contains:
  - Generated image (or placeholder if generation skipped)
  - Translated dish name (bold, prominent)
  - Price (clearly visible without interaction)
  - Click target for expanded view
- "Omakase!" button (floating action button, bottom right)
- Maintain original menu's category grouping

### 4. Dish Detail Modal (on click)
```javascript
// Modal content structure
{
    "image": "generated_image_url",
    "name": {
        "translated": "Grilled Salmon",
        "original": "鮭の塩焼き"
    },
    "description": {
        "translated": "Fresh Atlantic salmon...",
        "original": "新鮮なアトランティックサーモン..."
    },
    "price": "$24.95"
}
```

## Omakase Feature
```python
def select_omakase(dishes):
    categorized = {
        'appetizer': [],
        'main': [],
        'dessert': []
    }
    
    # Categorize available dishes
    for dish in dishes:
        if dish.category in categorized:
            categorized[dish.category].append(dish)
    
    # Select one from each category using LLM judgment
    selections = []
    prompt = f"Given these dishes, select the most compelling combination for a memorable meal..."
    
    return await llm_select_dishes(categorized, prompt)
```

## Image Generation Strategy
```python
async def generate_images_with_timeout(dishes, timeout, max_images, style_prompt):
    start_time = time.time()
    generated = 0
    
    # Randomize order to ensure variety if timeout hit
    shuffled_dishes = random.sample(dishes, len(dishes))
    
    for dish in shuffled_dishes:
        if generated >= max_images or (time.time() - start_time) > timeout:
            break
            
        prompt = f"{style_prompt}. Dish: {dish.name}. {dish.description or ''}"
        
        try:
            image_url = await flux_generate(prompt, resolution="512x512")
            dish.generated_image_url = image_url
            generated += 1
        except Exception:
            dish.generated_image_url = None
    
    return dishes
```

## Error Handling
- **OCR Failures**: Skip illegible sections, process readable content
- **Missing Descriptions**: Use dish name only for image generation
- **Translation Errors**: Display original text with error indicator
- **Image Generation Timeout**: Display text-only cards for remaining dishes
- **Invalid File Upload**: Clear error message with upload requirements

## API Integration Points

### Mistral OCR Endpoint
```python
MISTRAL_ENDPOINT = "https://your-koyeb-app.koyeb.app/ocr"
headers = {"Authorization": f"Bearer {KOYEB_API_KEY}"}
```

### FLUX.1 Image Generation
```python
FLUX_ENDPOINT = "https://your-flux-app.koyeb.app/generate"
payload = {
    "prompt": prompt,
    "num_inference_steps": 20,  # Reduced for speed
    "guidance_scale": 7.5
}
```

## Performance Optimizations
- Concurrent image generation (max 3 parallel requests)
- Progressive rendering: Display dishes as images complete
- Compressed image storage (WebP format, 80% quality)
- Connection pooling for database queries

## Deployment Configuration
```yaml
# koyeb.yaml
services:
  - name: snapmenu
    git:
      repository: github.com/your-repo/snapmenu
      branch: main
    instance_type: medium
    env:
      - key: STREAMLIT_SERVER_PORT
        value: "8000"
      - key: DATABASE_URL
        value: "${{ secrets.NEON_DATABASE_URL }}"
```

This specification provides the precise blueprint for transforming menu photos into accessible, visual experiences that help users order with confidence.