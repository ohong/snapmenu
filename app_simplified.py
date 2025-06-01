"""
Simplified main application using consolidated services
Reduces app.py complexity while maintaining all features
"""

import streamlit as st
import asyncio
from database import init_db, store_menu_upload, store_processed_dishes
from ocr_service_simplified import process_menu_ocr
from image_generation_simplified import generate_dish_images
from menu_intelligence import translate_dishes, enhance_descriptions, select_omakase_dishes
from utils import parse_menu_structure, categorize_dishes

st.set_page_config(
    page_title="Snapmenu",
    page_icon="📱", 
    layout="wide"
)

SUPPORTED_LANGUAGES = {
    "English": "en", "Mandarin": "zh", "Spanish": "es", "Hindi": "hi",
    "Arabic": "ar", "Portuguese": "pt", "Russian": "ru", 
    "Japanese": "ja", "German": "de", "French": "fr"
}

class MenuProcessor:
    """Simplified menu processing pipeline"""
    
    @staticmethod
    async def process_complete_menu(image_file, target_language):
        """Process menu through entire pipeline"""
        try:
            # Phase 1: OCR
            with st.spinner("Reading menu..."):
                menu_text = await process_menu_ocr(image_file)
            
            # Phase 2: Parse and categorize
            with st.spinner("Analyzing menu structure..."):
                dishes = parse_menu_structure(menu_text)
                dishes = categorize_dishes(dishes)
            
            # Phase 3: Translation
            if target_language != "en":
                with st.spinner("Translating menu..."):
                    dishes = await translate_dishes(dishes, target_language)
            
            # Phase 4: Enhancement and image generation
            with st.spinner("Generating dish images..."):
                dishes = await enhance_descriptions(dishes)
                dishes = await generate_dish_images(dishes)
            
            return dishes
            
        except Exception as e:
            st.error(f"Processing failed: {str(e)}")
            return None

def display_menu_grid(dishes):
    """Simplified menu display"""
    if not dishes:
        st.warning("No dishes found")
        return
    
    # Add unique IDs
    for i, dish in enumerate(dishes):
        dish['id'] = f"dish_{i}"
    
    # Group by category
    categories = {}
    for dish in dishes:
        category = dish.get('category', 'Other')
        if category not in categories:
            categories[category] = []
        categories[category].append(dish)
    
    # Display categories
    for category, category_dishes in categories.items():
        st.subheader(category.title())
        
        cols = st.columns(3)
        for idx, dish in enumerate(category_dishes):
            with cols[idx % 3]:
                if dish.get('generated_image_url'):
                    st.image(dish['generated_image_url'], use_container_width=True)
                else:
                    st.markdown("🍽️ *Upgrade to see the full visual menu*")
                
                st.markdown(f"**{dish.get('name_translated', dish.get('name_original', 'Unknown'))}**")
                if dish.get('price'):
                    st.markdown(f"💰 {dish['price']}")
                
                if st.button("View Details", key=f"detail_{dish['id']}"):
                    show_dish_details(dish)

def show_dish_details(dish):
    """Simplified dish detail display"""
    with st.expander(f"📋 {dish.get('name_translated', 'Dish Details')}", expanded=True):
        col1, col2 = st.columns([1, 2])
        
        with col1:
            if dish.get('generated_image_url'):
                st.image(dish['generated_image_url'], use_container_width=True)
            else:
                st.markdown("🍽️ *Upgrade to see the full visual menu*")
        
        with col2:
            st.markdown(f"**{dish.get('name_translated', 'N/A')}**")
            if dish.get('name_original') != dish.get('name_translated'):
                st.markdown(f"*Original: {dish.get('name_original', 'N/A')}*")
            
            if dish.get('description_translated'):
                st.markdown(dish['description_translated'])
            
            if dish.get('price'):
                st.markdown(f"**Price: {dish['price']}**")

def main():
    st.title("📱 Snapmenu")
    st.markdown("Transform any menu into a visual experience")
    
    # Session state
    if 'processed_dishes' not in st.session_state:
        st.session_state.processed_dishes = None
    
    if st.session_state.processed_dishes is None:
        # Upload interface
        st.markdown("### Upload your menu")
        
        uploaded_file = st.file_uploader(
            "Choose a menu image",
            type=['jpg', 'jpeg', 'png'],
            help="Maximum file size: 10MB"
        )
        
        selected_language = st.selectbox(
            "Select target language",
            options=list(SUPPORTED_LANGUAGES.keys())
        )
        
        if uploaded_file and st.button("🚀 Process Menu", type="primary"):
            if uploaded_file.size > 10 * 1024 * 1024:
                st.error("File too large. Maximum size is 10MB.")
                return
            
            # Store upload
            upload_id = store_menu_upload(uploaded_file.name, SUPPORTED_LANGUAGES[selected_language])
            
            # Process menu
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                dishes = loop.run_until_complete(
                    MenuProcessor.process_complete_menu(uploaded_file, SUPPORTED_LANGUAGES[selected_language])
                )
                
                if dishes:
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
        
        display_menu_grid(st.session_state.processed_dishes)
        
        # Omakase feature
        if st.button("🎲 Omakase! (Chef's Choice)", type="secondary"):
            with st.spinner("Selecting the perfect combination..."):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    omakase = loop.run_until_complete(
                        select_omakase_dishes(st.session_state.processed_dishes)
                    )
                    
                    if omakase:
                        st.success("🍽️ Chef's Omakase Selection")
                        for i, dish in enumerate(omakase):
                            course_names = ["Appetizer", "Main Course", "Dessert"]
                            course = course_names[i] if i < len(course_names) else "Course"
                            
                            col1, col2 = st.columns([1, 2])
                            with col1:
                                if dish.get('generated_image_url'):
                                    st.image(dish['generated_image_url'], use_container_width=True)
                                else:
                                    st.markdown("🍽️ *Upgrade to see the full visual menu*")
                            
                            with col2:
                                st.markdown(f"**{course}**")
                                st.markdown(f"### {dish.get('name_translated', 'Unknown')}")
                                if dish.get('description_translated'):
                                    st.markdown(dish['description_translated'])
                                if dish.get('price'):
                                    st.markdown(f"**{dish['price']}**")
                            
                            st.divider()
                            
                finally:
                    loop.close()

if __name__ == "__main__":
    init_db()
    main()