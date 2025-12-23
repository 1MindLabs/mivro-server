import sys
from datetime import datetime

from flask import Blueprint, Response, jsonify, request
from openfoodfacts import API, APIVersion, Country, Environment, Flavor
from utils import (
    filter_additive,
    filter_data,
    filter_image,
    filter_ingredient,
    product_schema,
    additive_names,
)
from mapping import additive_name, nova_name, primary_score
from gemini import lumi, swapr
from database import database_history, product_not_found, runtime_error
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
            print(
                f"[OpenFoodFacts] Missing fields for {product_barcode}: {missing_fields}"
            )

        # Filter the additive numbers and clean the product data
        product_data["additives_tags"] = filter_additive(
            product_data.get("additives_tags", [])
        )
        filtered_product_data = filter_data(product_data)

        # Calculate the response time and size for the filtered product data
        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds()
        response_size = sys.getsizeof(filtered_product_data) / 1024

        # Call lumi() with minimal payload (only nutriments + ingredients)
        lumi_payload = {
            "nutriments": filtered_product_data.get("nutriments", {}),
            "ingredients": filtered_product_data.get("ingredients", []),
        }
        lumi_result = lumi(lumi_payload)
        nutriments = {
            "positive_nutrient": lumi_result.get("positive_nutrient", []),
            "negative_nutrient": lumi_result.get("negative_nutrient", []),
        }
        health_risk = {
            "ingredient_warnings": lumi_result.get("ingredient_warnings", [])
        }

        images = filter_image(filtered_product_data.get("selected_images", {}))

        # Call swapr() with minimal payload
        swapr_payload = {
            "product_name": filtered_product_data.get("product_name", ""),
            "categories": filtered_product_data.get("categories", ""),
            "brands": filtered_product_data.get("brands", ""),
            "ingredients": filtered_product_data.get("ingredients", []),
            "additives_tags": filtered_product_data.get("additives_tags", []),
            "nutriments": filtered_product_data.get("nutriments", {}),
        }
        recommendation = swapr(email, swapr_payload)

        # Update the filtered product data with additional information for analytics
        filtered_product_data.update(
            {
                "search_type": "Open Food Facts API - Barcode",
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
                "primary_score": primary_score(filtered_product_data),
                "health_risk": health_risk,
                "total_health_risks": len(health_risk.get("ingredient_warnings", [])),
                "selected_images": images,
                "recommended_product": recommendation,
            }
        )

        # Store the scan history for the product barcode in Firestore
        database_history(email, product_barcode, filtered_product_data)
        return jsonify(filtered_product_data)
    except Exception as exc:
        runtime_error("barcode", str(exc), product_barcode=product_barcode)
        return jsonify({"error": str(exc)}), 500


@search_blueprint.route("/text", methods=["GET"])
def text() -> Response:
    try:
        # Start the timer for measuring the response time
        start_time = datetime.now()
        # Get the email and search query values from the incoming request
        email = request.headers.get("Mivro-Email")
        search_query = request.args.get("search_query")
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 20, type=int)

        if not email or not search_query:
            return jsonify({"error": "Email and search query are required."}), 400

        # Limit page size to prevent excessive API calls
        page_size = min(page_size, 100)

        # Perform text search using Open Food Facts API
        search_result = api.product.text_search(
            search_query, page=page, page_size=page_size
        )

        if not search_result or not search_result.get("products"):
            # Store "Product not found" event in Firestore for analytics
            product_not_found("text", search_query)
            return jsonify({"error": "No products found."}), 404

        # Calculate the response time
        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds()

        # Process products and perform AI analysis on first result only
        processed_products = []
        for idx, product in enumerate(search_result.get("products", [])):
            # Filter and clean the product data
            product["additives_tags"] = filter_additive(
                product.get("additives_tags", [])
            )
            filtered_product = filter_data(product)

            # Perform AI analysis on first product only
            if idx == 0:
                # Call lumi() with minimal payload (only nutriments + ingredients)
                lumi_payload = {
                    "nutriments": filtered_product.get("nutriments", {}),
                    "ingredients": filtered_product.get("ingredients", []),
                }
                lumi_result = lumi(lumi_payload)
                nutriments = {
                    "positive_nutrient": lumi_result.get("positive_nutrient", []),
                    "negative_nutrient": lumi_result.get("negative_nutrient", []),
                }
                health_risk = {
                    "ingredient_warnings": lumi_result.get("ingredient_warnings", [])
                }

                images = filter_image(filtered_product.get("selected_images", {}))

                # Get product recommendation with minimal payload
                swapr_payload = {
                    "product_name": filtered_product.get("product_name", ""),
                    "categories": filtered_product.get("categories", ""),
                    "brands": filtered_product.get("brands", ""),
                    "ingredients": filtered_product.get("ingredients", []),
                    "additives_tags": filtered_product.get("additives_tags", []),
                    "nutriments": filtered_product.get("nutriments", {}),
                }
                rec_response = swapr(email, swapr_payload)
                rec_name = rec_response.get("product_name", "")

                # Search for the recommended product details if available
                if rec_name and rec_name != "No recommendation available":
                    try:
                        print(f"[Swapr] Searching for recommendation: {rec_name}")
                        rec_search = api.product.text_search(
                            rec_name, page=1, page_size=1
                        )

                        if rec_search and rec_search.get("products"):
                            rec_product = rec_search["products"][0]
                            print(
                                f"[Swapr] Found recommendation: {rec_product.get('product_name', rec_name)}"
                            )

                            # Get and filter images for recommendation
                            rec_images = filter_image(
                                rec_product.get("selected_images", {})
                            )

                            recommendation = {
                                "product_name": rec_product.get(
                                    "product_name", rec_name
                                ),
                                "brands": rec_product.get("brands", ""),
                                "selected_images": rec_images,
                                "code": rec_product.get("code", ""),
                                "primary_score": primary_score(rec_product),
                                "nova_group": rec_product.get("nova_group", ""),
                            }
                        else:
                            print(f"[Swapr] Not found in OpenFoodFacts: {rec_name}")
                            recommendation = {"product_name": rec_name}
                    except Exception as e:
                        print(f"[Swapr] Search failed: {e}")
                        recommendation = {"product_name": rec_name}
                else:
                    recommendation = rec_response
            else:
                nutriments = {"positive_nutrient": [], "negative_nutrient": []}
                health_risk = {"ingredient_warnings": []}
                images = filter_image(filtered_product.get("selected_images", {}))
                recommendation = None

            # Add enriched data for each product
            filtered_product.update(
                {
                    "additives_names": additive_name(
                        filtered_product.get("additives_tags", []),
                        additive_names,
                    ),
                    "ingredients": filter_ingredient(
                        filtered_product.get("ingredients", [])
                    ),
                    "nova_group_name": nova_name(
                        filtered_product.get("nova_group", "")
                    ),
                    "nutriments": nutriments,
                    "total_nutriments": len(nutriments.get("positive_nutrient", []))
                    + len(nutriments.get("negative_nutrient", [])),
                    "primary_score": primary_score(filtered_product),
                    "health_risk": health_risk,
                    "total_health_risks": len(
                        health_risk.get("ingredient_warnings", [])
                    ),
                    "selected_images": images,
                    "recommended_product": recommendation,
                }
            )

            processed_products.append(filtered_product)

        # Update the search result with metadata
        search_result.update(
            {
                "products": processed_products,
                "search_type": "Open Food Facts API - Text",
                "search_response": "200 OK",
                "response_time": f"{response_time:.2f} seconds",
                "response_size": f"{sys.getsizeof(search_result) / 1024:.2f} KB",
                "search_date": datetime.now().strftime("%Y-%m-%d"),
                "search_time": datetime.now().strftime("%H:%M:%S"),
                "query": search_query,
            }
        )

        return jsonify(search_result)
    except Exception as exc:
        runtime_error("text", str(exc), search_query=search_query)
        return jsonify({"error": str(exc)}), 500


# DEPRECATED: database search endpoint - replaced by text search (OpenFoodFacts API v3.3.0)
# Kept for backward compatibility and as cache fallback
# # @search_blueprint.route("/database", methods=["GET"])
# def database() -> Response:
#     try:
#         # Start the timer for measuring the response time
#         start_time = datetime.now()
#         # Get the email and product keyword values from the incoming JSON data
#         email = request.headers.get("Mivro-Email")
#         product_keyword = request.args.get("product_keyword")

#         if not email or not product_keyword:
#             return jsonify({"error": "Email and product keyword are required."}), 400

#         # Define the search keys and fetch the product data from Firestore using the keyword (fuzzy matching)
#         search_keys = ["_keywords", "categories", "product_name"]
#         product_data = database_search(email, product_keyword, search_keys)

#         if product_data:
#             # Calculate the response time and size for the product data from Firestore
#             end_time = datetime.now()
#             response_time = (end_time - start_time).total_seconds()
#             response_size = sys.getsizeof(product_data) / 1024

#             # Update the product data with additional information for analytics
#             product_data.update(
#                 {
#                     "search_type": "Google Firestore Database",
#                     "search_response": "200 OK",
#                     "response_time": f"{response_time:.2f} seconds",
#                     "response_size": f"{response_size:.2f} KB",
#                     "search_date": datetime.now().strftime("%d-%B-%Y"),
#                     "search_time": datetime.now().strftime("%I:%M %p"),
#                 }
#             )

#             return jsonify(product_data)

#         # Store "Product not found" event in Firestore for analytics
#         product_not_found("database", product_keyword)
#         return jsonify({"error": "Product not found."}), 404
#     except Exception as exc:
#         runtime_error("database", str(exc), product_keyword=product_keyword)
#         return jsonify({"error": str(exc)}), 500
