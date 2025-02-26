import os
import json
import requests
import google.generativeai as genai
from google.generativeai import GenerativeModel
from config import GEMINI_API_KEY
from flask import Blueprint, Response, jsonify, request
from werkzeug.utils import secure_filename
from models import ChatHistory
from utils import chat_history, health_profile
from database import runtime_error

# Blueprint for the ai routes
ai_blueprint = Blueprint("ai", __name__)
# Load the Gemini API key from the environment variables
if GEMINI_API_KEY:
    print("GEMINI_API_KEY is set.")
else:
    print("GEMINI_API_KEY is not set.")
genai.configure(api_key=GEMINI_API_KEY)

# Generation settings to control the model's output
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "application/json",
}

# Safety settings to block harmful content (BLOCK_NONE is set to ignore triggers in product data for accurate context processing)
# Thresholds: https://ai.google.dev/gemini-api/docs/safety-settings
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]


# Load system instructions for the Gemini model
def load_instructions(file_path):
    with open(file_path, "r") as file:
        return file.read()


lumi_instructions = load_instructions("instructions/lumi_instructions.md")
swapr_instructions = load_instructions("instructions/swapr_instructions.md")
savora_instructions = load_instructions("instructions/savora_instructions.md")

# Initialize the Gemini model with custom settings and instructions
lumi_llm = GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=generation_config,
    safety_settings=safety_settings,
    system_instruction=lumi_instructions,
)

swapr_llm = GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=generation_config,
    safety_settings=safety_settings,
    system_instruction=swapr_instructions,
)

savora_llm = GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=generation_config,
    safety_settings=safety_settings,
    system_instruction=savora_instructions,
)

# Start a chat session with the Gemini model
lumi_chat_session = lumi_llm.start_chat(history=[])
swapr_chat_session = swapr_llm.start_chat(history=[])
savora_chat_session = savora_llm.start_chat(history=[])


@ai_blueprint.route("/lumi", methods=["POST"])
def lumi(product_data: dict) -> Response:
    try:
        # Get email value from the request headers
        email = request.headers.get("Mivro-Email")
        if not email or not product_data:
            return jsonify({"error": "Email and product data are required."}), 400

        # Retrieve the user's health profile from Firestore (if any)
        health_data = health_profile(email)
        # Send the user's health profile and product data to the Gemini model
        user_message = f"Health Profile: {health_data}\nProduct Data: {product_data}"
        bot_response = lumi_chat_session.send_message(user_message)

        # Filter the response to remove code blocks and return the evaluated product data
        # filtered_response = bot_response.text.replace("```python", "").replace("```", "")
        return json.loads(bot_response.text)
    except Exception as exc:
        runtime_error("lumi", str(exc), email=email)
        return jsonify({"error": str(exc)}), 500


@ai_blueprint.route("/swapr", methods=["POST"])
def swapr(email: str, product_data: dict) -> Response:
    try:
        # Send the product data to the Gemini model
        user_message = f"Product Data: {product_data}"
        bot_response = swapr_chat_session.send_message(user_message)

        # Filter the response to remove bold formatting and search the database for the product name
        filtered_response = bot_response.text.replace("**", "")
        database_response = requests.get(
            "http://localhost:5000/api/v1/search/database",
            headers={
                "Mivro-Email": email,
                "Mivro-Password": request.headers.get("Mivro-Password"),
            },
            json={"product_keyword": filtered_response.strip()},
        )

        if database_response.status_code != 200:
            # runtime_error('swapr', 'Database search failed.', middleware=database_response.json(), email=email)
            # return jsonify({'error': 'Database search failed.'}), database_response.status_code
            return {"product_name": filtered_response.strip()}

        return database_response.json()
    except Exception as exc:
        runtime_error("swapr", str(exc), email=email)
        return jsonify({"error": str(exc)}), 500


@ai_blueprint.route("/savora", methods=["POST"])
def savora() -> Response:
    try:
        # Check if the request contains a file upload (multipart/form-data)
        if "media" in request.files:
            user_email = request.headers.get("Mivro-Email")
            message_type = request.form.get("type")
            user_message = request.form.get("message")
            media_file = request.files.get("media")
        else:
            # Otherwise, expect JSON input (application/json)
            user_email = request.headers.get("Mivro-Email")
            message_type = request.json.get("type")
            user_message = request.json.get("message")
            media_file = None

        if not user_email or not message_type or not user_message:
            return (
                jsonify({"error": "Email, message type, and message are required."}),
                400,
            )

        # Send the user's message to the Gemini model
        if message_type == "text":
            bot_response = savora_chat_session.send_message(user_message)

        # Upload the media file to the Gemini model and generate content
        elif message_type == "media":
            if not media_file or media_file.filename == "":
                return jsonify({"error": "No file selected."}), 400

            # Check if the media file type is allowed
            if not media_file.filename.endswith(
                (".png", ".jpg", ".jpeg", ".pdf", ".txt")
            ):
                return (
                    jsonify(
                        {
                            "error": "Invalid file type. Allowed types: PNG, JPG, JPEG, PDF, TXT."
                        }
                    ),
                    400,
                )

            # Save the media file to a temporary location
            file_name = secure_filename(media_file.filename)
            temp_path = os.path.join(file_name)
            media_file.save(temp_path)

            # Upload the media file to the Gemini model using the temporary path
            user_file = genai.upload_file(temp_path)
            bot_response = savora_llm.generate_content(
                [user_file, "\n\n", user_message]
            )

            # Delete the temporary file after processing
            os.remove(temp_path)
        else:
            return jsonify({"error": "Invalid message type."}), 400

        # Store the chat history for the user's email in Firestore
        chat_entry = ChatHistory(
            user_message=user_message,
            bot_response=bot_response.text,
            message_type=message_type,
        )
        chat_history(user_email, chat_entry)

        return jsonify({"response": bot_response.text})
    except Exception as exc:
        runtime_error("savora", str(exc), email=user_email)
        return jsonify({"error": str(exc)}), 500
