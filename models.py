from pydantic import BaseModel, ConfigDict, Field

LANGUAGES = {"en": "English", "zh": "中文", "es": "Español", "hi": "हिन्दी", "ar": "العربية",
             "pt": "Português", "ru": "Русский", "ja": "日本語", "de": "Deutsch", "fr": "Français"}


class Dish(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name_original: str = Field(min_length=1, max_length=200)
    name_translated: str = Field(min_length=1, max_length=200)
    description_original: str = Field(max_length=1200)
    description_translated: str = Field(max_length=1200)
    # Literal prices preserve currency, variants, market prices, and uncertainty.
    price: str = Field(max_length=100)
    category: str = Field(min_length=1, max_length=100)
    course: str = Field(pattern="^(starter|main|dessert|drink|other)$")


class ExtractedMenu(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=160)
    source_language: str = Field(max_length=80)
    warnings: list[str] = Field(max_length=10)
    dishes: list[Dish] = Field(max_length=100)
