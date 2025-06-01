import re
import json

def parse_menu_structure(menu_text):
    """Parse OCR text into structured dish data"""
    dishes = []
    
    if not menu_text:
        return dishes
    
    # Split into lines and clean
    lines = [line.strip() for line in menu_text.split('\n') if line.strip()]
    
    current_category = "Other"
    
    for line in lines:
        # Check if line is a category header
        if is_category_header(line):
            current_category = line.strip().title()
            continue
        
        # Try to parse dish from line
        dish = parse_dish_line(line, current_category)
        if dish:
            dishes.append(dish)
    
    return dishes

def is_category_header(line):
    """Identify if line is a category header"""
    line = line.strip().upper()
    
    category_keywords = [
        'APPETIZER', 'APPETIZERS', 'STARTER', 'STARTERS',
        'MAIN', 'MAINS', 'ENTREE', 'ENTREES', 'MAIN COURSE', 'MAIN COURSES',
        'DESSERT', 'DESSERTS', 'SWEET', 'SWEETS',
        'DRINK', 'DRINKS', 'BEVERAGE', 'BEVERAGES',
        'SOUP', 'SOUPS', 'SALAD', 'SALADS',
        'PASTA', 'PIZZA', 'SEAFOOD', 'MEAT', 'VEGETARIAN'
    ]
    
    # Check if line contains category keywords and no price
    has_keyword = any(keyword in line for keyword in category_keywords)
    has_price = bool(re.search(r'\$\d+', line))
    
    return has_keyword and not has_price and len(line.split()) <= 3

def parse_dish_line(line, category):
    """Parse individual dish line"""
    # Price patterns
    price_patterns = [
        r'\$(\d+\.?\d*)',  # $12.95, $12
        r'(\d+\.?\d*)\s*USD',  # 12.95 USD
        r'(\d+\.?\d*)\s*dollars?',  # 12 dollars
    ]
    
    price = None
    price_match = None
    
    # Find price in line
    for pattern in price_patterns:
        match = re.search(pattern, line)
        if match:
            price = f"${match.group(1)}"
            price_match = match
            break
    
    if not price_match:
        return None  # Skip lines without prices
    
    # Split line at price to get name and description
    price_start = price_match.start()
    before_price = line[:price_start].strip()
    
    # Try to separate name and description
    parts = before_price.split(' - ')
    
    if len(parts) >= 2:
        name = parts[0].strip()
        description = ' - '.join(parts[1:]).strip()
    else:
        # Use first few words as name, rest as description
        words = before_price.split()
        if len(words) > 3:
            name = ' '.join(words[:3])
            description = ' '.join(words[3:])
        else:
            name = before_price
            description = ""
    
    return {
        'name_original': name,
        'description_original': description,
        'price': price,
        'category': category
    }

def categorize_dishes(dishes):
    """Improve dish categorization using content analysis"""
    
    category_keywords = {
        'Appetizers': ['salad', 'soup', 'appetizer', 'starter', 'bruschetta', 'wings'],
        'Main Courses': ['salmon', 'steak', 'pasta', 'chicken', 'beef', 'pork', 'main', 'entree'],
        'Desserts': ['cake', 'ice cream', 'chocolate', 'dessert', 'pie', 'cookie', 'sweet'],
        'Beverages': ['coffee', 'tea', 'juice', 'soda', 'water', 'wine', 'beer', 'cocktail']
    }
    
    for dish in dishes:
        name = dish.get('name_original', '').lower()
        description = dish.get('description_original', '').lower()
        text = f"{name} {description}"
        
        # Try to match keywords to improve categorization
        best_category = dish.get('category', 'Other')
        max_matches = 0
        
        for category, keywords in category_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in text)
            if matches > max_matches:
                max_matches = matches
                best_category = category
        
        dish['category'] = best_category
    
    return dishes

def select_omakase_dishes(dishes):
    """Select chef's choice dishes from menu"""
    categorized = {
        'Appetizers': [],
        'Main Courses': [],
        'Desserts': []
    }
    
    # Group dishes by category
    for dish in dishes:
        category = dish.get('category', 'Other')
        if category in categorized:
            categorized[category].append(dish)
    
    # Select one from each category (simple random selection)
    import random
    selections = []
    
    for category, category_dishes in categorized.items():
        if category_dishes:
            selected = random.choice(category_dishes)
            selections.append(selected)
    
    return selections