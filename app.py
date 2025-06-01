import streamlit as st
import asyncio
import os
from dotenv import load_dotenv
from database import init_db, store_menu_upload, store_processed_dishes
from ocr_service import process_menu_ocr
from image_generation import generate_dish_images
from translation_service import translate_dishes
from utils import parse_menu_structure, categorize_dishes
from pixtral_service import select_omakase_dishes, enhance_dish_descriptions

load_dotenv()

st.set_page_config(
    page_title="Snapmenu",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="collapsed"
)

SUPPORTED_LANGUAGES = {
    "English": "en",
    "Mandarin": "zh",
    "Spanish": "es", 
    "Hindi": "hi",
    "Arabic": "ar",
    "Portuguese": "pt",
    "Russian": "ru",
    "Japanese": "ja",
    "German": "de",
    "French": "fr"
}

async def process_menu_pipeline(image_file, target_language):
    """Main processing pipeline with 15-second constraint"""
    try:
        # Phase 1: OCR (3-4 seconds)
        with st.spinner("Reading menu text..."):
            menu_text = await process_menu_ocr(image_file)
        
        # Phase 2: Parse and categorize (1-2 seconds)
        with st.spinner("Analyzing menu structure..."):
            dishes = parse_menu_structure(menu_text)
            dishes = categorize_dishes(dishes)
        
        # Phase 3: Translation if needed (2-3 seconds)
        if target_language != "en":
            with st.spinner("Translating menu..."):
                dishes = await translate_dishes(dishes, target_language)
        
        # Phase 4: Enhance descriptions for better image generation (1 second)
        with st.spinner("Enhancing dish descriptions..."):
            dishes = await enhance_dish_descriptions(dishes)
        
        # Phase 5: Image generation (remaining time)
        with st.spinner("Generating dish images..."):
            dishes = await generate_dish_images(
                dishes,
                timeout=6,  # Reduced to account for enhancement step
                max_images=20,
                style_prompt="professional food photography, restaurant dish, appetizing, consistent lighting"
            )
        
        return dishes
    
    except Exception as e:
        st.error(f"Processing failed: {str(e)}")
        return None

def display_menu_grid(dishes):
    """Display dishes in responsive grid layout"""
    if not dishes:
        st.warning("No dishes found in menu")
        return
    
    # Add unique IDs to dishes if they don't have them
    for i, dish in enumerate(dishes):
        if 'id' not in dish:
            dish['id'] = f"dish_{i}"
    
    # Group dishes by category
    categories = {}
    for dish in dishes:
        category = dish.get('category', 'Other')
        if category not in categories:
            categories[category] = []
        categories[category].append(dish)
    
    # Display each category
    for category, category_dishes in categories.items():
        st.subheader(category.title())
        
        cols = st.columns(3)
        for idx, dish in enumerate(category_dishes):
            with cols[idx % 3]:
                with st.container():
                    # Display image or placeholder
                    if dish.get('generated_image_url'):
                        st.image(dish['generated_image_url'], use_container_width=True)
                    else:
                        st.empty()
                        st.markdown("📸 *Image not available*")
                    
                    # Dish name and price
                    st.markdown(f"**{dish.get('name_translated', dish.get('name_original', 'Unknown'))}**")
                    if dish.get('price'):
                        st.markdown(f"💰 {dish['price']}")
                    
                    # Click for details - use unique dish ID
                    if st.button(f"View Details", key=f"detail_{dish['id']}"):
                        show_dish_modal(dish)

def show_dish_modal(dish):
    """Display dish details in modal-like container"""
    with st.expander(f"📋 {dish.get('name_translated', 'Dish Details')}", expanded=True):
        col1, col2 = st.columns([1, 2])
        
        with col1:
            if dish.get('generated_image_url'):
                st.image(dish['generated_image_url'], use_container_width=True)
            else:
                st.markdown("📸 *No image available*")
        
        with col2:
            st.markdown(f"**{dish.get('name_translated', 'N/A')}**")
            if dish.get('name_original') != dish.get('name_translated'):
                st.markdown(f"*Original: {dish.get('name_original', 'N/A')}*")
            
            if dish.get('description_translated'):
                st.markdown(f"{dish['description_translated']}")
            
            if dish.get('description_original') != dish.get('description_translated'):
                st.markdown(f"*Original: {dish.get('description_original', 'N/A')}*")
            
            if dish.get('price'):
                st.markdown(f"**Price: {dish['price']}**")

def main():
    st.title("📱 Snapmenu")
    st.markdown("Transform any menu into a visual experience")
    
    # Initialize session state
    if 'processed_dishes' not in st.session_state:
        st.session_state.processed_dishes = None
    
    # Main upload interface
    if st.session_state.processed_dishes is None:
        st.markdown("### Upload your menu")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a menu image",
            type=['jpg', 'jpeg', 'png'],
            help="Maximum file size: 10MB"
        )
        
        # Language selector
        selected_language = st.selectbox(
            "Select target language",
            options=list(SUPPORTED_LANGUAGES.keys()),
            index=0
        )
        
        # Process button
        if uploaded_file is not None and st.button("🚀 Process Menu", type="primary"):
            if uploaded_file.size > 10 * 1024 * 1024:  # 10MB limit
                st.error("File too large. Maximum size is 10MB.")
                return
            
            # Store upload in database
            upload_id = store_menu_upload(
                uploaded_file.name,
                SUPPORTED_LANGUAGES[selected_language]
            )
            
            # Process the menu
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                dishes = loop.run_until_complete(
                    process_menu_pipeline(uploaded_file, SUPPORTED_LANGUAGES[selected_language])
                )
                
                if dishes:
                    # Store processed dishes
                    store_processed_dishes(upload_id, dishes)
                    st.session_state.processed_dishes = dishes
                    st.rerun()
                
            finally:
                loop.close()
    
    else:
        # Display processed menu
        col1, col2 = st.columns([1, 6])
        
        with col1:
            if st.button("← New Menu"):
                st.session_state.processed_dishes = None
                st.rerun()
        
        with col2:
            st.markdown("### Your Visual Menu")
        
        # Display dishes
        display_menu_grid(st.session_state.processed_dishes)
        
        # Omakase button (floating action)
        if st.button("🎲 Omakase! (Chef's Choice)", type="secondary"):
            with st.spinner("Chef is selecting the perfect combination..."):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    omakase_dishes = loop.run_until_complete(
                        select_omakase_dishes(st.session_state.processed_dishes)
                    )
                    
                    if omakase_dishes:
                        st.success("🍽️ Chef's Omakase Selection")
                        
                        # Display selected dishes in a special layout
                        for i, dish in enumerate(omakase_dishes):
                            with st.container():
                                col1, col2 = st.columns([1, 2])
                                
                                with col1:
                                    if dish.get('generated_image_url'):
                                        st.image(dish['generated_image_url'], use_container_width=True)
                                    else:
                                        st.markdown("📸 *Image not available*")
                                
                                with col2:
                                    course_names = ["Appetizer", "Main Course", "Dessert"]
                                    course_name = course_names[i] if i < len(course_names) else "Course"
                                    
                                    st.markdown(f"**{course_name}**")
                                    st.markdown(f"### {dish.get('name_translated', dish.get('name_original', 'Unknown'))}")
                                    
                                    if dish.get('description_translated'):
                                        st.markdown(dish['description_translated'])
                                    
                                    if dish.get('price'):
                                        st.markdown(f"**{dish['price']}**")
                                
                                st.divider()
                        
                        # Calculate total price
                        total_price = 0
                        for dish in omakase_dishes:
                            price_str = dish.get('price', '').replace('$', '').replace(',', '')
                            try:
                                price = float(price_str)
                                total_price += price
                            except (ValueError, AttributeError):
                                pass
                        
                        if total_price > 0:
                            st.markdown(f"### Total: ${total_price:.2f}")
                    
                    else:
                        st.error("Unable to create Omakase selection")
                        
                except Exception as e:
                    st.error(f"Omakase selection failed: {str(e)}")
                finally:
                    loop.close()

if __name__ == "__main__":
    # Initialize database on startup
    init_db()
    main()