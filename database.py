import os
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st
from datetime import datetime

def get_db_connection():
    """Get database connection using Neon PostgreSQL"""
    try:
        conn = psycopg2.connect(
            os.getenv('DATABASE_URL'),
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        st.error(f"Database connection failed: {str(e)}")
        return None

def init_db():
    """Initialize database tables"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            # Create menu_uploads table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS menu_uploads (
                    id SERIAL PRIMARY KEY,
                    upload_timestamp TIMESTAMP DEFAULT NOW(),
                    original_image_url TEXT NOT NULL,
                    selected_language VARCHAR(10) NOT NULL,
                    processing_status VARCHAR(20) DEFAULT 'pending'
                )
            """)
            
            # Create processed_dishes table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS processed_dishes (
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
                )
            """)
            
            conn.commit()
            return True
            
    except Exception as e:
        st.error(f"Database initialization failed: {str(e)}")
        return False
    finally:
        conn.close()

def store_menu_upload(image_name, selected_language):
    """Store menu upload record and return upload_id"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO menu_uploads (original_image_url, selected_language)
                VALUES (%s, %s)
                RETURNING id
            """, (image_name, selected_language))
            
            upload_id = cur.fetchone()['id']
            conn.commit()
            return upload_id
            
    except Exception as e:
        st.error(f"Failed to store upload: {str(e)}")
        return None
    finally:
        conn.close()

def store_processed_dishes(upload_id, dishes):
    """Store processed dishes in database"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            for idx, dish in enumerate(dishes):
                cur.execute("""
                    INSERT INTO processed_dishes (
                        menu_upload_id, dish_name_original, dish_name_translated,
                        description_original, description_translated, price,
                        category, generated_image_url, display_order
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    upload_id,
                    dish.get('name_original'),
                    dish.get('name_translated'),
                    dish.get('description_original'),
                    dish.get('description_translated'),
                    dish.get('price'),
                    dish.get('category'),
                    dish.get('generated_image_url'),
                    idx
                ))
            
            conn.commit()
            return True
            
    except Exception as e:
        st.error(f"Failed to store dishes: {str(e)}")
        return False
    finally:
        conn.close()

def update_processing_status(upload_id, status):
    """Update processing status for upload"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE menu_uploads 
                SET processing_status = %s 
                WHERE id = %s
            """, (status, upload_id))
            
            conn.commit()
            return True
            
    except Exception as e:
        st.error(f"Failed to update status: {str(e)}")
        return False
    finally:
        conn.close()