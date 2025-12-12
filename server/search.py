import sys
from datetime import datetime

from flask import Blueprint, Response, jsonify, request
from openfoodfacts import API, APIVersion, Country, Environment, Flavor
from utils import (
    filter_additive,
    filter_data,
    filter_image,
    filter_ingredient,
    filter_nutriment,
    product_schema,
    additive_names,
)
from mapping import additive_name, grade_color, nova_name, score_assessment
from gemini import lumi, swapr
from database import database_history, database_search, product_not_found, runtime_error
from config import API_TIMEOUT

# Blueprint for the search routes
search_blueprint = Blueprint("search", __name__)
# Initialize the Open Food Facts API client
api = API(
    user_agent="Mivro/1.0",
    country=Country.world,
    flavor=Flavor.off,
    version=APIVersion.v2,
    environment=Environment.org,
    timeout=API_TIMEOUT,
)


@search_blueprint.route("/barcode", methods=["GET"])
def barcode() -> Response:
    try:
        # Start the timer for measuring the response time
        start_time = datetime.now()
        # Get the email and product barcode values from the incoming JSON data
        email = request.headers.get("Mivro-Email")
        product_barcode = request.args.get("product_barcode")

        if not email or not product_barcode:
            return jsonify({"error": "Email and product barcode are required."}), 400

        # Define product schema fields and fetch data from Open Food Facts API using barcode
        product_data = api.product.get(product_barcode, fields=product_schema)
        if not product_data:
            # Store "Product not found" event in Firestore for analytics
            product_not_found("barcode", product_barcode)
            return jsonify({"error": "Product not found."}), 404

        # Check for missing fields in the product data
        missing_fields = set(product_schema) - set(product_data.keys())
        if missing_fields:
            print(f"Warning: Missing fields for {product_barcode}: {missing_fields}")

        # Filter the additive numbers, nutriments, and clean the product data
        product_data["additives_tags"] = filter_additive(
            product_data.get("additives_tags", [])
        )
        filtered_product_data = filter_data(product_data)
        filtered_product_data["nutriments"] = filter_nutriment(
            filtered_product_data.get("nutriments", {})
        )

        # Calculate the response time and size for the filtered product data
        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds()
        response_size = sys.getsizeof(filtered_product_data) / 1024

        nutriments = lumi(filtered_product_data.get("nutriments", {}))
        health_risk = lumi(filtered_product_data.get("ingredients", []))
        images = filter_image(filtered_product_data.get("selected_images", {}))
        recommendation = swapr(email, filtered_product_data)

        # Update the filtered product data with additional information for analytics
        filtered_product_data.update(
            {
                "search_type": "Open Food Facts API",
                "search_response": "200 OK",
                "response_time": f"{response_time:.2f} seconds",
                "response_size": f"{response_size:.2f} KB",
                "search_date": datetime.now().strftime("%Y-%m-%d"),
                "search_time": datetime.now().strftime("%H:%M:%S"),
                "additives_names": additive_name(
                    filtered_product_data.get("additives_tags", []),
                    additive_names,
                ),
                "ingredients": filter_ingredient(
                    filtered_product_data.get("ingredients", [])
                ),
                "nova_group_name": nova_name(
                    filtered_product_data.get("nova_group", "")
                ),
                "nutriments": nutriments,
                "total_nutriments": len(nutriments.get("positive_nutrient", []))
                + len(nutriments.get("negative_nutrient", [])),
                "nutriscore_grade_color": grade_color(
                    filtered_product_data.get("nutriscore_grade", "")
                ),
                "nutriscore_assessment": score_assessment(
                    filtered_product_data.get("nutriscore_score", None)
                ).title(),
                "health_risk": health_risk,
                "total_health_risks": len(health_risk.get("ingredient_warnings", [])),
                "selected_images": images,
                "recommeded_product": recommendation,
            }
        )

        # Store the scan history for the product barcode in Firestore
        database_history(email, product_barcode, filtered_product_data)
        return jsonify(filtered_product_data)
    except Exception as exc:
        runtime_error("barcode", str(exc), product_barcode=product_barcode)
        return jsonify({"error": str(exc)}), 500


@search_blueprint.route('/text', methods=['GET'])
def text() -> Response:
    try:
        # Start the timer for measuring the response time
        start_time = datetime.now()
        # Get the email and product name values from the headers/request
        email = request.headers.get("Mivro-Email")
        product_name = request.json.get("product_name")
        
        if not email or not product_name:
            return jsonify({'error': 'Email and product name are required.'}), 400

        # Define product schema fields
        required_data = json.load(open("metadata/product_schema.json"))
        
        # Use the v2 API to search for products by name
        search_result = api.product.search(product_name, fields=required_data)
        
        if not search_result or not search_result.get('products'):
            # Store "Product not found" event in Firestore for analytics
            product_not_found("text", product_name)
            return jsonify({'error': 'Product not found.'}), 404
            
        # Get the first product from the search results
        product_data = search_result.get('products', [])[0]
        
        # Process the product data similar to the barcode route
        # Filter the additive numbers, nutriments, and clean the product data
        product_data["additives_tags"] = filter_additive(
            product_data.get("additives_tags", [])
        )
        filtered_product_data = filter_data(product_data)
        filtered_product_data["nutriments"] = filter_nutriment(
            filtered_product_data.get("nutriments", {})
        )

        # Calculate the response time and size for the filtered product data
        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds()
        response_size = sys.getsizeof(filtered_product_data) / 1024

        # Update the filtered product data with additional information for analytics
        filtered_product_data.update(
            {
                "search_type": "Open Food Facts API (Text)",
                "search_response": "200 OK",
                "response_time": f"{response_time:.2f} seconds",
                "response_size": f"{response_size:.2f} KB",
                "search_date": datetime.now().strftime("%d-%B-%Y"),
                "search_time": datetime.now().strftime("%I:%M %p"),
                "additives_names": additive_name(
                    filtered_product_data.get("additives_tags", []),
                    json.load(open("metadata/additive_names.json")),
                ),
                "ingredients": filter_ingredient(
                    filtered_product_data.get("ingredients", [])
                ),
                "nova_group_name": nova_name(
                    filtered_product_data.get("nova_group", "")
                ),
                "nutriments": lumi(filtered_product_data.get("nutriments", {})),
                "nutriscore_grade_color": grade_color(
                    filtered_product_data.get("nutriscore_grade", "")
                ),
                "nutriscore_assessment": score_assessment(
                    filtered_product_data.get("nutriscore_score", None)
                ).title(),
                "health_risk": lumi(filtered_product_data.get("ingredients", [])),
                "selected_images": filter_image(
                    filtered_product_data.get("selected_images", [])
                ),
                "recommeded_product": swapr(email, filtered_product_data),
            }
        )

        # Calculating derived fields outside as they're not directly provided by the API
        filtered_product_data["total_nutriments"] = len(
            filtered_product_data.get("nutriments", {}).get("positive_nutrient", [])
        ) + len(
            filtered_product_data.get("nutriments", {}).get("negative_nutrient", [])
        )
        filtered_product_data["total_health_risks"] = len(
            filtered_product_data.get("health_risk", {}).get("ingredient_warnings", [])
        )

        # Store the search history for the product name in Firestore
        database_history(email, product_name, filtered_product_data)
        return jsonify(filtered_product_data)
    except Exception as exc:
        runtime_error("text_search", str(exc), product_name=product_name)
        return jsonify({'error': str(exc)}), 500


@search_blueprint.route("/database", methods=["GET"])
def database() -> Response:
    try:
        # Start the timer for measuring the response time
        start_time = datetime.now()
        # Get the email and product keyword values from the incoming JSON data
        email = request.headers.get("Mivro-Email")
        product_keyword = request.args.get("product_keyword")

        if not email or not product_keyword:
            return jsonify({"error": "Email and product keyword are required."}), 400

        # Define the search keys and fetch the product data from Firestore using the keyword (fuzzy matching)
        search_keys = ["_keywords", "categories", "product_name"]
        product_data = database_search(email, product_keyword, search_keys)

        if product_data:
            # Calculate the response time and size for the product data from Firestore
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            response_size = sys.getsizeof(product_data) / 1024

            # Update the product data with additional information for analytics
            product_data.update(
                {
                    "search_type": "Google Firestore Database",
                    "search_response": "200 OK",
                    "response_time": f"{response_time:.2f} seconds",
                    "response_size": f"{response_size:.2f} KB",
                    "search_date": datetime.now().strftime("%d-%B-%Y"),
                    "search_time": datetime.now().strftime("%I:%M %p"),
                }
            )

            return jsonify(product_data)

        # Store "Product not found" event in Firestore for analytics
        product_not_found("database", product_keyword)
        return jsonify({"error": "Product not found."}), 404
    except Exception as exc:
        runtime_error("database", str(exc), product_keyword=product_keyword)
        return jsonify({"error": str(exc)}), 500
