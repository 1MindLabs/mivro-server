import json
from pathlib import Path

from mapping import food_icon
from database import user_reference

METADATA_DIR = Path(__file__).parent.parent / "metadata"

# Load the metadata files for food categories, additive names, and product schema
with open(METADATA_DIR / "food_categories.json") as file:
    food_categories = json.load(file)

with open(METADATA_DIR / "additive_names.json") as file:
    additive_names = json.load(file)

with open(METADATA_DIR / "product_schema.json") as file:
    product_schema = json.load(file)


# Function for filtering additive tags and removing the 'i' suffix (Used in search.py)
def filter_additive(additive_data: list) -> list:
    additive_info = [tag for tag in additive_data if not tag.endswith("i")]
    return additive_info


# Function for filtering ingredient data and extracting the name, icon, and percentage (Used in search.py)
def filter_ingredient(ingredient_data: list) -> list:
    ingredient_info = [
        {
            "name": ingredient.get("text", "").title(),
            "icon": food_icon(ingredient.get("text", "").title(), food_categories),
            "percentage": f"{abs(float(ingredient.get('percent_estimate', 0))):.2f} %",
        }
        for ingredient in ingredient_data
        if ingredient.get("text") and ingredient.get("percent_estimate", 0) != 0
    ]
    return ingredient_info


# Function for mapping the nutrient name to an icon (Used in search.py)
def filter_nutriment(nutriment_data: dict) -> dict:
    for category in ["negative_nutrient", "positive_nutrient"]:
        if category in nutriment_data:
            for nutrient in nutriment_data[category]:
                nutrient["icon"] = food_icon(nutrient.get("name", ""), food_categories)
    return nutriment_data


# DEPRECATED: Replaced by Gemini model for the same purpose
# Function for analysing the nutrient data based on the nutrient limits (Used in search.py)
def analyse_nutrient(nutrient_data: dict, nutrient_limits: dict) -> dict:
    positive_nutrients = {}
    negative_nutrients = {}

    nutrient_map = {
        nutrient: {
            "name": nutrient.title(),
            "icon": food_icon(nutrient.title(), food_categories),
            "quantity": f"{abs(float(nutrient_data.get(f'{nutrient}_100g', 0))):.2f} {value['unit']}",
        }
        for nutrient, value in nutrient_limits.items()
        if nutrient_data.get(f"{nutrient}_100g", 0) != 0
    }

    # Check if the nutrient quantity is within the recommended limits
    for nutrient, value in nutrient_map.items():
        lower_limit = nutrient_limits[nutrient]["lower_limit"]
        upper_limit = nutrient_limits[nutrient]["upper_limit"]

        if (
            float(value["quantity"].split()[0]) < lower_limit
            or float(value["quantity"].split()[0]) > upper_limit
        ):
            negative_nutrients[nutrient] = value
        else:
            positive_nutrients[nutrient] = value

    nutriment_info = {
        "positive_nutrient": list(positive_nutrients.values()),
        "negative_nutrient": list(negative_nutrients.values()),
    }
    return nutriment_info


# Function for filtering the product data and removing the 'en:' prefix (Used in search.py)
def filter_data(product_data: dict) -> dict:
    def clean_value(val):
        if isinstance(val, str):
            return val.removeprefix("en:")
        elif isinstance(val, list):
            return [clean_value(item) for item in val]
        return val

    filtered = {
        key: clean_value(product_data.get(key))
        for key in product_schema
        if key in product_data
    }

    return filtered


# Function for filtering the image data and extracting the image link (Used in search.py)
def filter_image(image_data: dict) -> dict:
    if not image_data or not isinstance(image_data, dict):
        return {}

    # Try to get front image with display quality
    if "front" in image_data:
        front = image_data["front"]
        if isinstance(front, dict):
            # New nested structure
            if "display" in front and isinstance(front["display"], dict):
                return front["display"]  # Return dict with all language options
            # Fallback: direct language dict
            return front

    # Fallback: try to extract any available image
    for image_type in ["front", "ingredients", "nutrition"]:
        if image_type in image_data:
            img = image_data[image_type]
            if isinstance(img, dict):
                if "display" in img:
                    return img["display"]
                return img

    return {}


# Function for retrieving the user's health profile from Firestore (Used in gemini.py)
def health_profile(email: str) -> dict:
    user_document = user_reference.document(email)
    health_profile = user_document.get().to_dict().get("health_profile", {})
    return health_profile


# Function for storing the chat history in Firestore (Used in gemini.py)
def chat_history(email: str, chat_entry: dict) -> None:
    user_document = user_reference.document(email)
    if not user_document.get().exists:
        user_document.set({"chat_history": []})

    chat_history = user_document.get().to_dict().get("chat_history", [])
    chat_history.append(chat_entry.to_dict())
    user_document.set({"chat_history": chat_history}, merge=True)


# Function for calculating the BMI based on the weight and height (Used in models.py)
def calculate_bmi(weight_kg: float, height_m: float) -> float:
    if not weight_kg or not height_m:
        return None

    return round(weight_kg / (height_m**2), 2)
