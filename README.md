# Snapmenu

## Project Description

**Snapmenu** is an AI-powered web application that streamlines restaurant menu processing, translation, and visualization. Users can upload menu images or PDFs, and the app will automatically extract, categorize, and translate dish information, as well as generate representative images for each dish. Snapmenu supports multiple languages and leverages state-of-the-art AI services for OCR, translation, and image generation.

---

## Architecture & Technologies

- **Frontend/UI:** [Streamlit](https://streamlit.io/) – for building an interactive and user-friendly web interface.
- **Backend/Processing:** Python (with `asyncio` for concurrency).
- **Database:** PostgreSQL (hosted on [NeonDB](https://neon.tech/)) – stores menu uploads and processed dish data.
- **External AI Services (deployed on Koyeb):**
  - **OCR Service:** Extracts text from menu images.
  - **Image Generation Service:** Creates dish images from text descriptions.
  - **Translation Service:** Translates dish names and descriptions into supported languages.
- **Other Technologies:**
  - `python-dotenv` for environment variable management.
  - Modular Python codebase (`database.py`, `ocr_service.py`, `image_generation.py`, `translation_service.py`, `pixtral_service.py`, `utils.py`).

---

## Features

- Upload restaurant menus as images or PDFs.
- Automatic OCR and menu parsing.
- Categorize and enhance dish information.
- Translate menu content into multiple languages.
- Generate AI-powered images for each dish.
- “Omakase” (chef’s choice) dish selection and enhanced descriptions.

---

## Supported Languages

- English, Mandarin, Spanish, Hindi, Arabic, Portuguese, Russian, Japanese, German, French

---

## Getting Started

### Prerequisites

- Python 3.8+
- [pip](https://pip.pypa.io/en/stable/installation/)
- [PostgreSQL](https://www.postgresql.org/) database (NeonDB recommended)
- API keys and endpoints for Koyeb-hosted services (see `.env.example`)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/snapmenu.git
   cd snapmenu
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   - Copy `.env.example` to `.env` and fill in your credentials and endpoints:
     ```bash
     cp .env.example .env
     ```
   - Edit `.env` with your database URL, Koyeb API keys, and service endpoints.

4. **Initialize the database:**
   - (If needed) Run any database migrations or initialization scripts provided in `database.py`.

### Running the App

```bash
streamlit run app.py
```

The app will launch in your browser at `http://localhost:8501`.

---

## Notes

- Ensure your `.env` file is not committed to version control (it's already in `.gitignore`).
- For production use, secure your API keys and database credentials appropriately.

---
